"""Research graph: projects, typed study edges, themes, open questions, frontier, plan graph.

Split out of the original persona_council/services.py (behavior-preserving).
Cross-module function references are bound at import time by services/__init__.py."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from ..config import (
    ROOT, utc_now_iso, content_language, ensure_content_language, language_instruction,
    critic_threshold, critic_sample_k,
)
from ..models import (
    CalendarEvent,
    CouncilSession,
    DailySummary,
    Evidence,
    ExperienceEvent,
    MetaReport,
    OpenQuestion,
    PainPointObservation,
    Persona,
    PrototypeSession,
    Reflection,
    ResearchProject,
    SimulationResult,
    StudyEdge,
    Synthesis,
)
from ..storage import Store
from ..taxonomy import GENERIC_TOOLS, normalized_tool_ids, normalized_tools
from .. import memory as memory_mod
from .. import evaluation as evaluation_mod
from ..llm_simulation import (
    build_cohort_critic_prompt,
    build_consolidation_prompt,
    build_meta_outline_prompt,
    build_meta_section_prompt,
    validate_meta_outline_payload,
    validate_meta_section_payload,
    build_digest_prompt,
    build_eval_critic_prompt,
    build_evidence_check_prompt,
    build_persona_revision_prompt,
    build_plan_prompt,
    build_profile_prompt,
    build_synthesis_prompt,
    generate_activity,
    generate_day_plan_with_llm,
    validate_activity_payload,
    validate_cohort_critic_payload,
    validate_digest_payload,
    validate_eval_critic_payload,
    validate_evidence_check_payload,
    validate_memory_deltas_payload,
    validate_persona_revision_payload,
    validate_plan_payload,
    validate_profile_payload,
    validate_synthesis_payload,
)


from ._common import *  # noqa: F401,F403  (shared helpers + constants)



def create_research_project(title: str, goal: str = "", persona_ids: list[str] | None = None,
                            description: str = "", store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    now = utc_now_iso()
    pid = stable_id("rproject", title, now)
    base = slugify(title)
    slug, n = base, 2
    while store.get_research_project(slug) is not None:
        slug, n = f"{base}-{n}", n + 1
    project = ResearchProject(
        id=pid, slug=slug, title=title, goal=goal, description=description,
        persona_ids=persona_ids or [], study_ids=[], study_tags={}, themes=[],
        status="active", created_at=now, updated_at=now, council_ids=[],
    ).to_dict()
    store.upsert_research_project(project)
    return project



def list_research_projects(store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    out = []
    for p in store.list_research_projects():
        out.append({"id": p["id"], "slug": p["slug"], "title": p["title"], "goal": p.get("goal", ""),
                    "status": p.get("status", "active"), "studies": len(p.get("study_ids", [])),
                    "edges": len(store.list_study_edges(p["id"])), "themes": p.get("themes", [])})
    return out



def get_research_project(project_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    return _require_research_project(store, project_id)



def parent_project_of_study(study_id: str, store: Store | None = None) -> dict[str, Any] | None:
    """Reverse lookup: which research project contains this synthesis (study)?
    Powers the Project > Synthesis > Council hierarchy/breadcrumbs."""
    store = store or Store()
    for p in store.list_research_projects():
        if study_id in (p.get("study_ids") or []):
            return {"id": p["id"], "slug": p["slug"], "title": p["title"]}
    return None



def parent_study_of_council(council_id: str, store: Store | None = None) -> dict[str, Any] | None:
    """Reverse lookup: which synthesis (study) folds in this council?"""
    store = store or Store()
    for s in store.list_syntheses():
        if council_id in (s.get("council_ids") or []):
            return {"id": s["id"], "title": s["title"]}
    return None



def parent_project_of_council(council_id: str, store: Store | None = None) -> dict[str, Any] | None:
    """Reverse lookup: which research project OWNS this council? Councils are scoped to a
    project at creation; this is the direct link (independent of whether a synthesis cites it)."""
    store = store or Store()
    council = store.get_council_session(council_id)
    pid = (council or {}).get("project_id")
    if pid:
        p = store.get_research_project(pid)
        if p:
            return {"id": p["id"], "slug": p["slug"], "title": p["title"]}
    # Fallback for projects that track the council in their list (e.g. legacy/migrated data).
    for p in store.list_research_projects():
        if council_id in (p.get("council_ids") or []):
            return {"id": p["id"], "slug": p["slug"], "title": p["title"]}
    return None



def add_study_to_project(project_id: str, study_id: str, theme_tags: list[str] | None = None,
                         store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project = _require_research_project(store, project_id)
    if not store.get_synthesis(study_id):
        raise KeyError(f"Unknown study (synthesis): {study_id}")
    if study_id not in project["study_ids"]:
        project["study_ids"].append(study_id)
    if theme_tags:
        _apply_themes(project, study_id, theme_tags)
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    return project



def _apply_themes(project: dict[str, Any], study_id: str, tags: list[str]) -> None:
    clean = [str(t).strip().lower() for t in tags if str(t).strip()][:10]
    project.setdefault("study_tags", {})[study_id] = clean
    vocab = project.setdefault("themes", [])
    for t in clean:
        if t not in vocab:
            vocab.append(t)



def set_study_themes(project_id: str, study_id: str, tags: list[str], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project = _require_research_project(store, project_id)
    if study_id not in project["study_ids"]:
        raise KeyError(f"Study {study_id} is not in project {project_id}")
    _apply_themes(project, study_id, tags)
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    return project



def link_studies(project_id: str, from_study_id: str, to_study_id: str, type: str,
                 rationale: str = "", store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project = _require_research_project(store, project_id)
    if type not in EDGE_TYPES:
        raise ValueError(f"Edge type must be one of {sorted(EDGE_TYPES)}")
    for sid in (from_study_id, to_study_id):
        if sid not in project["study_ids"]:
            raise KeyError(f"Study {sid} is not in project {project_id}")
    now = utc_now_iso()
    edge = StudyEdge(id=stable_id("edge", project_id, from_study_id, to_study_id, type),
                     project_id=project["id"], from_study=from_study_id, to_study=to_study_id,
                     type=type, rationale=rationale, created_at=now).to_dict()
    store.insert_study_edge(edge)
    return edge



def record_open_questions(project_id: str, questions: list[str], study_id: str | None = None,
                          store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    project = _require_research_project(store, project_id)
    now = utc_now_iso()
    out = []
    for q in questions:
        text = str(q).strip()
        if not text:
            continue
        oq = OpenQuestion(id=stable_id("oq", project["id"], text), project_id=project["id"],
                          study_id=study_id, text=text[:600], status="open",
                          answered_by_study_id=None, created_at=now).to_dict()
        store.upsert_open_question(oq)
        out.append(oq)
    return out



def resolve_open_question(project_id: str, question_id: str, answered_by_study_id: str,
                          store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project = _require_research_project(store, project_id)
    oqs = {o["id"]: o for o in store.list_open_questions(project["id"])}
    if question_id not in oqs:
        raise KeyError(f"Unknown open question: {question_id}")
    oq = oqs[question_id]
    oq["status"] = "answered"
    oq["answered_by_study_id"] = answered_by_study_id
    store.upsert_open_question(oq)
    # also record the graph edge: the answering study answers the raising study
    if oq.get("study_id") and answered_by_study_id in project["study_ids"] and oq["study_id"] in project["study_ids"]:
        try:
            link_studies(project["id"], answered_by_study_id, oq["study_id"], "answers",
                         f"answers: {oq['text'][:120]}", store=store)
        except (ValueError, KeyError):
            pass
    return oq



def _study_node(store: Store, study_id: str) -> dict[str, Any] | None:
    syn = store.get_synthesis(study_id)
    if not syn:
        return None
    sentiment: dict[str, int] = {}
    for v in syn.get("voices", []) or []:
        s = v.get("sentiment", "neutral")
        sentiment[s] = sentiment.get(s, 0) + 1
    return {
        "study_id": study_id, "title": syn.get("title", study_id),
        "status": syn.get("status", "done"), "created_at": syn.get("created_at", ""),
        "goal": syn.get("goal", ""), "council_count": len(syn.get("council_ids", [])),
        "voices": sum(sentiment.values()), "sentiment": sentiment,
        "recommendations": len(syn.get("handlungsempfehlungen", [])),
        "phase": syn.get("phase", ""), "mode": syn.get("mode", ""), "role": syn.get("role", ""),
    }



def get_project_graph(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """The core navigation call: nodes (studies + tags/sentiment), typed edges,
    themes, build order, and open questions for one research project. When the project has a
    research PLAN with recorded evidence, the graph is the heterogeneous plan-evidence graph
    (councils/syntheses/artifacts/frames as first-class nodes)."""
    store = store or Store()
    plan = _plan.get_plan(project_id, store=store)
    if plan is not None:                       # the plan engine is the single source of truth (HX3)
        return plan_graph(project_id, store=store)
    project = _require_research_project(store, project_id)
    tags = project.get("study_tags", {})
    nodes = []
    for sid in project["study_ids"]:
        node = _study_node(store, sid)
        if node:
            node["theme_tags"] = tags.get(sid, [])
            nodes.append(node)
    nodes.extend(note_graph_nodes(project))  # note nodes are first-class (composable primitive)
    nodes.sort(key=lambda n: n["created_at"])  # build order
    edges = [{"from_study": e["from_study"], "to_study": e["to_study"], "type": e["type"],
              "rationale": e.get("rationale", "")} for e in store.list_study_edges(project["id"])]
    oqs = store.list_open_questions(project["id"])
    methodology_state = None
    return {
        "project": {"id": project["id"], "slug": project["slug"], "title": project["title"],
                    "goal": project.get("goal", ""), "status": project.get("status", "active"),
                    "persona_ids": project.get("persona_ids", []), "themes": project.get("themes", []),
                    "methodology": project.get("methodology", ""), "phase": project.get("phase", "")},
        "methodology_state": methodology_state,
        "prototypes": list_prototypes_artifacts(project["id"], store=store),
        "sections": list(project.get("sections") or []),
        "nodes": nodes,
        "edges": edges,
        "open_questions": oqs,
        "build_order": [n["study_id"] for n in nodes],
        "counts": {"studies": len(nodes), "edges": len(edges),
                   "open_questions": sum(1 for o in oqs if o.get("status") == "open"),
                   "themes": len(project.get("themes", []))},
    }



def _plan_methodology_state(project: dict, plan: dict, store: Store) -> dict[str, Any] | None:
    """A layout-ready step state derived from the PLAN's real analyze→act→verify DAG: each frame
    (analyze) task is a fan/diverge step and each verify task is a waist/converge step, wired along
    the task `consumes` graph. Build steps (frames whose act tasks produced artifacts) declare the
    artifact_type + the fidelity discriminators built under them, so prototypes place in — and route
    out of — the right diamond. Reflects the actual constellation, not a static spec."""
    tasks = plan.get("tasks", [])
    if not tasks:
        return None
    builds_under: dict[str, set] = {}   # frame id -> fidelity tags of artifacts built from it
    syn_of_verify: dict[str, str] = {}  # verify id -> its synthesis node id (the convergence node)
    for t in tasks:
        if t["bucket"] == "act":
            for p in t.get("produces", []):
                if p.get("kind") == "artifact":
                    proto = store.get_prototype(p["id"]) or {}
                    fids = {x for x in (proto.get("tags") or []) if x and x != "prototype"} or {"prototype"}
                    for c in t.get("consumes", []):
                        builds_under.setdefault(c, set()).update(fids)
        elif t["bucket"] == "verify":
            syn = next((p["id"] for p in t.get("produces", []) if p["kind"] == "synthesis"), None)
            if syn:
                syn_of_verify[t["id"]] = f"synthesis:{syn}"
    steps = []
    for t in tasks:
        if t["bucket"] not in ("analyze", "verify"):
            continue
        is_fan = t["bucket"] == "analyze"
        produces: dict[str, Any] = {"role": t.get("capability", "")}
        if t["id"] in builds_under:
            produces["artifact_type"] = "prototype"
            produces["more_tags"] = sorted(builds_under[t["id"]])
        steps.append({"key": t["id"], "name": t.get("title", t["id"]),
                      "mode": "diverge" if is_fan else "converge", "is_fan": is_fan,
                      "role": t.get("capability", ""), "presentation": t.get("presentation") or {},
                      "tags": [t.get("capability", "")] if t.get("capability") else [],
                      "consumes": list(t.get("consumes", [])), "produces": produces,
                      "requires": t.get("requires", {}) or {},
                      "status": "done" if t.get("status") == "done" else "pending",
                      "exploration_count": 0, "convergence_node": syn_of_verify.get(t["id"]),
                      "judgments": []})
    return {"project_id": project["id"], "methodology": plan.get("methodology", ""), "phase": "",
            "complete": _plan.is_complete(plan), "steps": steps, "phases": steps}



def _evidence_node(kind: str, eid: str, title: str, prod_task: dict, store: Store) -> dict[str, Any]:
    """A heterogeneous graph node for one evidence item. Color/label come from data (present(kind))."""
    from .. import presentation as _pres
    pres = _pres.present(kind)
    # Bind the node to a layout column: a verify task's synthesis sits in that verify STEP (a waist);
    # an act task's evidence fans from the FRAME it consumes (the diverge step) — so diamonds emerge
    # from the plan's real analyze→act→verify DAG, not from a static spec.
    if prod_task.get("bucket") == "verify":
        step = prod_task.get("id", "")
    else:
        cons = prod_task.get("consumes") or []
        step = cons[0] if cons else prod_task.get("step", "")
    created = ""
    council_count = 0
    if kind == "council":
        c = store.get_council_session(eid) or {}
        created = c.get("created_at", "")
        council_count = 1
    elif kind == "synthesis":
        s = store.get_synthesis(eid) or {}
        created = s.get("created_at", "")
        council_count = len(s.get("council_ids", []))
    href = {"council": f"/councils/{eid}", "synthesis": f"/syntheses/{eid}"}.get(kind, "")
    tags = [kind] + list(prod_task.get("presentation", {}).get("tags") or [])
    return {"study_id": f"{kind}:{eid}", "kind": kind, "title": title, "phase": step,
            "bucket": prod_task.get("bucket", ""), "created_at": created, "council_count": council_count,
            "voices": 0, "sentiment": {}, "recommendations": 0, "role": prod_task.get("capability", ""),
            "mode": "", "theme_tags": tags, "color": pres["color"], "kind_label": pres["label"],
            "href": href}



def plan_graph(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """Heterogeneous evidence graph for a plan-based project: councils/syntheses/frames as
    first-class nodes (artifacts via the prototypes list), edges from the act fan to its verify
    synthesis, diamonds laid out over act->verify via the plan's constellation."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    plan = _plan.get_plan(project_id, store=store)
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _title(kind: str, eid: str, t: dict) -> str:
        if kind == "council":
            return (store.get_council_session(eid) or {}).get("prompt", eid)
        if kind == "synthesis":
            return (store.get_synthesis(eid) or {}).get("title", eid)
        if kind == "frame":
            return f"Frame · {t.get('title', eid)}"
        return eid

    for t in plan["tasks"]:
        for r in t["produces"]:
            kind, eid = r["kind"], r["id"]
            if kind not in ("council", "synthesis"):  # artifacts render via the prototypes list;
                continue                              # sessions live on their prototype; frames stay plan-internal
            nid = f"{kind}:{eid}"
            if nid in seen:
                continue
            seen.add(nid)
            nodes.append(_evidence_node(kind, eid, _title(kind, eid, t), t, store))
    nodes.extend(note_graph_nodes(project))  # note nodes are first-class (composable primitive)
    nodes.sort(key=lambda n: n.get("created_at", ""))
    # edges: each verify task's synthesis consolidates its act fan's councils (refines)
    edges: list[dict[str, Any]] = []
    node_ids = {n["study_id"] for n in nodes}
    for t in plan["tasks"]:
        if t["bucket"] != "verify":
            continue
        syn_refs = [r for r in t["produces"] if r["kind"] == "synthesis"]
        fan = _plan._fan_evidence(plan, t)
        for syn in syn_refs:
            for fr in fan:
                if fr["kind"] in ("council", "synthesis"):
                    edges.append({"from_study": f"{fr['kind']}:{fr['id']}",
                                  "to_study": f"synthesis:{syn['id']}", "type": "refines", "rationale": ""})
    # SPINE (GAP-6): connect each diamond's converging synthesis to the upstream diamonds' syntheses
    # that feed it, so the full double-diamond reads as ONE connected flow (Define→Select→Deliver→…)
    # rather than isolated, edge-less diamonds. Without this, a diamond whose fan is prototypes/sessions
    # (not councils) has no incoming edge and floats disconnected ("no lines").
    syn_of_verify = {t["id"]: next((r["id"] for r in t["produces"] if r["kind"] == "synthesis"), None)
                     for t in plan["tasks"] if t["bucket"] == "verify"}

    def _upstream_verifies(task_id: str, acc: set[str]) -> None:
        ct = _plan.task(plan, task_id)
        for c in (ct.get("consumes") or []) if ct else []:
            cc = _plan.task(plan, c)
            if not cc:
                continue
            if cc["bucket"] == "verify":
                acc.add(cc["id"])
            else:
                _upstream_verifies(c, acc)

    for t in plan["tasks"]:
        if t["bucket"] != "verify" or not syn_of_verify.get(t["id"]):
            continue
        ups: set[str] = set()
        _upstream_verifies(t["id"], ups)
        for up in ups:
            up_syn, this_syn = syn_of_verify.get(up), syn_of_verify[t["id"]]
            if up_syn and up_syn != this_syn and f"synthesis:{up_syn}" in node_ids:
                edges.append({"from_study": f"synthesis:{up_syn}", "to_study": f"synthesis:{this_syn}",
                              "type": "informs", "rationale": ""})
    ms = _plan_methodology_state(project, plan, store)
    if ms:
        step_tags = {s["key"]: list(s.get("tags") or []) for s in ms["steps"]}
        for n in nodes:
            extra = step_tags.get(n.get("phase", ""), [])
            if extra:
                n["theme_tags"] = list(dict.fromkeys((n.get("theme_tags") or []) + extra))
    oqs = store.list_open_questions(project["id"])
    return {
        "project": {"id": project["id"], "slug": project["slug"], "title": project["title"],
                    "goal": project.get("goal", ""), "status": project.get("status", "active"),
                    "persona_ids": project.get("persona_ids", []), "themes": project.get("themes", []),
                    "methodology": plan.get("methodology", ""), "phase": ""},
        "methodology_state": ms,
        "prototypes": list_prototypes_artifacts(project["id"], store=store),
        "sections": list(project.get("sections") or []),
        "nodes": nodes, "edges": edges, "open_questions": oqs,
        "build_order": [n["study_id"] for n in nodes],
        "counts": {"studies": len(nodes), "edges": len(edges),
                   "open_questions": sum(1 for o in oqs if o.get("status") == "open"),
                   "themes": len(project.get("themes", []))},
        "plan": plan,
    }



def get_research_frontier(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """The anti-explosion surface: the project's still-open questions, plus a flag
    when the graph has no edges yet (studies not connected)."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    open_qs = [o for o in store.list_open_questions(project["id"]) if o.get("status") == "open"]
    edges = store.list_study_edges(project["id"])
    notes = []
    if project["study_ids"] and not edges:
        notes.append("studies present but unconnected — add edges (link_studies) or they read as isolated.")
    if not open_qs:
        notes.append("no open questions tracked — the frontier looks closed (or unrecorded).")
    return {"project_id": project["id"], "open_questions": open_qs,
            "open_question_count": len(open_qs), "notes": notes}



def backfill_project_from_syntheses(title: str = "Research", synthesis_ids: list[str] | None = None,
                                    store: Store | None = None) -> dict[str, Any]:
    """Group existing syntheses into ONE project as graph nodes, ordered by creation
    time, with chronological `spawned_from` edges (rationale marks them as backfilled
    so they can be re-linked properly later). Returns the project graph."""
    store = store or Store()
    if synthesis_ids:
        studies = [store.get_synthesis(s) for s in synthesis_ids]
    else:
        studies = store.list_syntheses()
    studies = [s for s in studies if s]
    studies.sort(key=lambda s: s.get("created_at", ""))
    project = create_research_project(title, goal="Backfilled from existing syntheses.", store=store)
    pid = project["id"]
    for s in studies:
        add_study_to_project(pid, s["id"], store=store)
    ordered = [s["id"] for s in studies]
    for prev, cur in zip(ordered, ordered[1:]):
        link_studies(pid, prev, cur, "spawned_from", "backfilled by creation order (edit later)", store=store)
    # promote each study's open questions into the project frontier
    for s in studies:
        oq = s.get("offene_fragen") or []
        if oq:
            record_open_questions(pid, oq[:5], study_id=s["id"], store=store)
    return get_project_graph(pid, store=store)


# --- Deletes (D in CRUD; MCP/CLI only — the web UI is read-only) -------------



def delete_research_project(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """Delete a project container + its graph metadata (edges/open questions/meta-reports).
    The syntheses stay (they are independent studies)."""
    store = store or Store()
    p = _require_research_project(store, project_id)
    return {"deleted": store.delete_research_project(p["id"]), "project_id": p["id"]}



def remove_study_from_project(project_id: str, study_id: str, store: Store | None = None) -> dict[str, Any]:
    """Detach a study from a project (drops its edges in that project); keeps the synthesis."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    if study_id in project["study_ids"]:
        project["study_ids"].remove(study_id)
    project.get("study_tags", {}).pop(study_id, None)
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    edges = store.delete_edges_touching(project["id"], study_id)
    return {"project_id": project["id"], "removed_study": study_id, "edges_removed": edges}



def unlink_studies(project_id: str, from_study_id: str, to_study_id: str, type: str | None = None,
                   store: Store | None = None) -> dict[str, Any]:
    """Remove an edge (or all edges) between two studies in a project."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    return {"project_id": project["id"], "removed": store.delete_study_edges(project["id"], from_study_id, to_study_id, type)}
