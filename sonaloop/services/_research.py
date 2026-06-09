"""Research graph: projects, typed study edges, themes, open questions, frontier, plan graph.

Split out of the original sonaloop/services.py (behavior-preserving).
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
    OpenQuestion,
    PainPointObservation,
    Persona,
    PrototypeSession,
    Reflection,
    ResearchProject,
    SimulationResult,
    Synthesis,
)
from ..storage import Store
from .. import artifacts as _A
from ..taxonomy import GENERIC_TOOLS, normalized_tool_ids, normalized_tools
from .. import memory as memory_mod
from .. import evaluation as evaluation_mod
from ..llm_simulation import (
    build_cohort_critic_prompt,
    build_consolidation_prompt,
    build_synthesis_outline_prompt,
    build_synthesis_section_prompt,
    validate_synthesis_outline_payload,
    validate_synthesis_section_payload,
    build_digest_prompt,
    build_eval_critic_prompt,
    build_evidence_check_prompt,
    build_persona_revision_prompt,
    build_plan_prompt,
    build_profile_prompt,
    build_synthesis_prompt,
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
    """Project summaries for the inspector list. Counts come from the project GRAPH —
    the plan-evidence graph is the source of truth, and `study_ids` is empty for
    plan-based projects, so a raw len(study_ids) would read 0. `studies` counts
    synthesis nodes (matching the list's label); `edges` is the build-order count."""
    store = store or Store()
    out = []
    for p in store.list_research_projects():
        graph = get_project_graph(p["id"], store=store)
        out.append({"id": p["id"], "slug": p["slug"], "title": p["title"], "goal": p.get("goal", ""),
                    "status": p.get("status", "active"),
                    "studies": sum(1 for n in graph["nodes"] if n.get("kind") == "synthesis"),
                    "councils": sum(1 for n in graph["nodes"] if n.get("kind") == "council"),
                    "notes": sum(1 for n in graph["nodes"] if n.get("kind") == "note"),
                    "prototypes": len(graph.get("prototypes") or []),
                    "edges": graph["counts"].get("edges", 0),
                    "themes": p.get("themes", [])})
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


def parent_project_of_synthesis(synthesis_id: str, store: Store | None = None) -> dict[str, Any] | None:
    """Which project owns this synthesis? Robust for PLAN-based projects (the synthesis is produced by
    a plan verify task, not listed in the old `study_ids`). Powers correct breadcrumbs."""
    store = store or Store()
    p = parent_project_of_study(synthesis_id, store=store)        # legacy/constellation path
    if p:
        return p
    for proj in store.list_research_projects():                   # plan path: a task produces it
        plan = _plan.get_plan(proj["id"], store=store) or {}
        for task in plan.get("tasks", []):
            if any(r.get("kind") == "synthesis" and r.get("id") == synthesis_id
                   for r in task.get("produces", [])):
                return {"id": proj["id"], "slug": proj["slug"], "title": proj["title"]}
    return None



# M-cleanup: the constellation study-graph service (add_study_to_project / set_study_themes /
# link_studies + _apply_themes/_study_node) is RETIRED — the plan engine is the single graph (HX3).


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
                          study_id=study_id, text=text[:600], status="open", created_at=now).to_dict()
        store.upsert_open_question(oq)
        out.append(oq)
    return out






def ref_backlinks(project_id: str, store: Store | None = None) -> dict[str, list[dict[str, Any]]]:
    """Reverse cross-reference index for a project (spec/artifact-cross-references.md §4): for every
    addressed part, who points AT it. Returns {address: [{href, label, role}]}. Built by scanning every
    artifact's outgoing refs — so a council statement learns it is 'cited by' the synthesis that derives
    from it (the bidirectional knowledge graph), without any data duplication."""
    store = store or Store()
    proj = _require_research_project(store, project_id)
    idx: dict[str, list[dict[str, Any]]] = {}

    def add(target: dict, label: str, href: str):
        if not (target and target.get("id")):
            return
        addr = _A.part_address(target["kind"], target["id"], target.get("anchor"))
        idx.setdefault(addr, []).append({"href": href, "label": label, "role": target.get("role")})

    syns = store.list_syntheses()
    councils = {c["id"]: c for c in store.list_council_sessions() if c.get("project_id") == proj["id"]}
    for syn in syns:
        if not any(cid in councils for cid in (syn.get("council_ids") or [])) and \
           syn["id"] not in (proj.get("study_ids") or []):
            continue
        for f in (syn.get("findings") or []):
            for r in (f.get("refs") or []):
                add(r, syn.get("title", ""), f'/syntheses/{syn["id"]}#{f.get("id", "")}')
    # councils referencing each other / earlier parts
    for c in councils.values():
        for s in (c.get("statements") or []):
            for r in (s.get("refs") or []):
                if r.get("kind") in ("council", "synthesis", "note"):
                    add(r, c.get("prompt", ""), f'/councils/{c["id"]}#{s.get("id", "")}')
    return idx


def _study_node(store: Store, study_id: str) -> dict[str, Any] | None:
    """A graph node for a synthesis (study) — used by the plan-less / report study_ids path."""
    syn = store.get_synthesis(study_id)
    if not syn:
        return None
    sentiment = _A.synthesis_sentiment_counts(syn, store)   # aggregated over the REAL council voices
    return {
        "study_id": study_id, "title": syn.get("title", study_id),
        "status": syn.get("status", "done"), "created_at": syn.get("created_at", ""),
        "goal": syn.get("goal", ""), "council_count": len(syn.get("council_ids", [])),
        "voices": sum(sentiment.values()), "sentiment": sentiment,
        "recommendations": len(_A.synthesis_recommendations(syn)),
        "phase": syn.get("phase", ""), "mode": syn.get("mode", ""), "role": syn.get("role", ""),
    }


def _attach_reports(g: dict, project_id: str, store: Store) -> dict:
    """Reports (project-scope syntheses) are first-class project artifacts — expose them on the graph so
    the outline lists them inline (among the methodology rows), not just as a top-bar button."""
    g["reports"] = [{"id": r["id"], "title": r.get("title", ""), "created_at": r.get("created_at", ""),
                     "n_sections": len(r.get("sections") or [])} for r in store.list_reports(project_id)]
    return g


def get_project_graph(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """The core navigation call: nodes (studies + tags/sentiment), typed edges,
    themes, build order, and open questions for one research project. When the project has a
    research PLAN with recorded evidence, the graph is the heterogeneous plan-evidence graph
    (councils/syntheses/artifacts/frames as first-class nodes)."""
    store = store or Store()
    plan = _plan.get_plan(project_id, store=store)
    if plan is not None:                       # the plan engine is the single source of truth (HX3)
        return _attach_reports(plan_graph(project_id, store=store), project_id, store)
    # Plan-less fallback (start_project always seeds a plan, so this is only hit by hand-built data /
    # the study_ids-based report path): nodes from the project's studies + notes — NO study-edge
    # layer (retired), so no edges.
    project = _require_research_project(store, project_id)
    tags = project.get("study_tags", {})
    nodes = []
    for sid in project.get("study_ids", []):
        node = _study_node(store, sid)
        if node:
            node["theme_tags"] = tags.get(sid, [])
            nodes.append(node)
    nodes.extend(note_graph_nodes(project))
    nodes.sort(key=lambda n: n.get("created_at", ""))
    oqs = store.list_open_questions(project["id"])
    g = {
        "project": {"id": project["id"], "slug": project["slug"], "title": project["title"],
                    "goal": project.get("goal", ""), "status": project.get("status", "active"),
                    "persona_ids": project.get("persona_ids", []), "themes": project.get("themes", []),
                    "methodology": project.get("methodology", ""), "phase": project.get("phase", "")},
        "methodology_state": None,
        "prototypes": list_prototypes_artifacts(project["id"], store=store),
        "artifacts": list(project.get("artifacts") or []),
        "sections": list(project.get("sections") or []),
        "nodes": nodes,
        "edges": [],
        "open_questions": oqs,
        "build_order": [n["study_id"] for n in nodes],
        "counts": {"studies": len(nodes), "edges": 0,
                   "open_questions": sum(1 for o in oqs if o.get("status") == "open"),
                   "themes": len(project.get("themes", []))},
    }
    return _attach_reports(g, project_id, store)



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
    # ONE note entity: a BUILT note (data.prototype_id) routes through its prototype (the layout draws
    # note→prototype→tested-synthesis); a plain note is a standalone observation. No concept-kind edge.
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
        "artifacts": list(project.get("artifacts") or []),
        "sections": list(project.get("sections") or []),
        "nodes": nodes, "edges": edges, "open_questions": oqs,
        "build_order": [n["study_id"] for n in nodes],
        "counts": {"studies": len(nodes), "edges": len(edges),
                   "open_questions": sum(1 for o in oqs if o.get("status") == "open"),
                   "themes": len(project.get("themes", []))},
        "plan": plan,
    }



def derive_sections(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """ESV1 — auto-organization: derive persisted SECTION overlays from the plan so a finished run is
    organized BY CONSTRUCTION (not agent-dependent). One section per methodology phase (a fan + its
    converging waist synthesis; label from the step name — no hardcoded vocabulary), a Prototype-ladder
    section, a Deliver/Conclusion section (the terminal verify synthesis), and a Run-Journal section
    (note nodes). Idempotent by title (re-run updates members). Makes assess_project.finish.organized
    flip true. (spec/exhaustive-self-verifying-runs.md §D.1)"""
    store = store or Store()
    graph = get_project_graph(project_id, store=store)
    nodes = graph["nodes"]
    steps = (graph.get("methodology_state") or {}).get("steps") or []
    by_phase: dict[str, list[str]] = {}
    for n in nodes:
        by_phase.setdefault(n.get("phase", ""), []).append(n["study_id"])
    waist_consumes = {s["key"]: s.get("consumes", []) for s in steps if not s.get("is_fan")}
    existing = {x["title"]: x for x in list_sections(project_id, store=store)}
    created: list[str] = []

    def _upsert(title: str, kind: str, members: list[str], note: str = "") -> None:
        members = [m for m in dict.fromkeys(members) if m]   # dedupe, preserve order
        if not members:
            return
        if title in existing:
            set_section_members(existing[title]["id"], members, store=store)
        else:
            create_section(project_id, title, kind=kind, member_ids=members, note=note, store=store)
            created.append(title)

    for fs in [s for s in steps if s.get("is_fan")]:
        members = list(by_phase.get(fs["key"], []))
        for wkey, cons in waist_consumes.items():
            if fs["key"] in cons:
                members += by_phase.get(wkey, [])
        label = (fs.get("name") or fs["key"]).split("·")[-1].strip() or fs["key"]
        _upsert(label, "phase", members, note=f"Phase: {label}")
    protos = [p["id"] for p in graph.get("prototypes") or []]
    _upsert("Prototypen-Leiter", "theme", protos, note="Prototypen Lo-Fi → Mid-Fi → Hi-Fi")
    verify_syns = [n["study_id"] for n in nodes
                   if n.get("bucket") == "verify" and str(n["study_id"]).startswith("synthesis:")]
    if verify_syns:
        _upsert("Deliver — Conclusion", "deliver", [verify_syns[-1]], note="Lösungspräsentation / buildbare Antwort")
    # Built notes (data.prototype_id) — the ideas that became prototypes (former "concepts").
    built_ids = [n["study_id"] for n in nodes if str(n["study_id"]).startswith("note:") and n.get("prototype_ids")]
    _upsert("Gebaute Ideen", "theme", built_ids, note="Notizen, die zu Prototypen wurden")
    journal_ids = [n["study_id"] for n in nodes if str(n["study_id"]).startswith("note:")]
    _upsert("Run-Journal", "invented", journal_ids, note="Plan-Rationale + Iterations-Journal")
    return {"project_id": project_id, "created": created,
            "sections": len(list_sections(project_id, store=store))}


def scaffold_synthesis(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """ESV1 — seed a project REPORT outline from the project's phases so the conclusion hand-off is one
    author step (brief_synthesis_section → record_synthesis_section), not authored from scratch. Makes
    assess_project.finish.handed_off flip true. Idempotent: returns the existing report if one exists."""
    store = store or Store()
    existing = store.list_reports(project_id)
    if existing:
        return existing[0]
    graph = get_project_graph(project_id, store=store)
    nodes = graph["nodes"]
    steps = (graph.get("methodology_state") or {}).get("steps") or []
    by_phase: dict[str, list[str]] = {}
    for n in nodes:
        by_phase.setdefault(n.get("phase", ""), []).append(n["study_id"])
    # one section PER PHASE in order (fans AND verifies) — Discover/Define/Ideate/Down-Select/Refine/
    # Deliver — so the outline tells the WHOLE story, not just the diverge phases.
    sections = []
    for s in steps:
        srcs = [x for x in dict.fromkeys(by_phase.get(s["key"], [])) if x]
        label = (s.get("name") or s["key"]).split("·")[-1].strip() or s["key"]
        role = "diverge" if s.get("is_fan") else "converge"
        sections.append({"heading": label, "theme_tags": [], "source_study_ids": srcs,
                         "intent": f"Author the {label} phase ({role}) grounded in its evidence + what it produced."})
    if not sections:                                  # freeform / no methodology: one catch-all section
        sections = [{"heading": "Findings", "intent": "Author the project's findings + conclusion.",
                     "theme_tags": [], "source_study_ids": graph.get("build_order", [])}]
    outline = {"build_order_narrative": f"Auto-seeded outline for {graph['project'].get('title','')}.",
               "sections": sections}
    return record_synthesis_outline(project_id, outline, store=store)


def get_research_frontier(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """The anti-explosion surface: the project's still-open questions."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    open_qs = [o for o in store.list_open_questions(project["id"]) if o.get("status") == "open"]
    notes = []
    if not open_qs:
        notes.append("no open questions tracked — the frontier looks closed (or unrecorded).")
    return {"project_id": project["id"], "open_questions": open_qs,
            "open_question_count": len(open_qs), "notes": notes}



# M-cleanup: backfill_project_from_syntheses RETIRED (a one-time study-graph migration).


# --- Deletes (D in CRUD; MCP/CLI only — the web UI is read-only) -------------



def delete_research_project(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """Delete a project container + its graph metadata (edges/open questions).
    The syntheses stay (they are independent studies)."""
    store = store or Store()
    p = _require_research_project(store, project_id)
    return {"deleted": store.delete_research_project(p["id"]), "project_id": p["id"]}



# M-cleanup: remove_study_from_project / unlink_studies RETIRED (study-edge graph).
