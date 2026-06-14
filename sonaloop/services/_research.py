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
    # The answer to "where can I look at this?" rides every creation result —
    # remote hosts (MCP connectors) surface it to the user.
    from ._common import web_url
    return {**project, "url": web_url(f"/projects/{pid}")}



def update_research_project(project_id: str, patch: dict[str, Any],
                            store: Store | None = None) -> dict[str, Any]:
    """Patch a project's STRUCTURAL metadata (title/goal/description/status) — the
    container fields only, never graph contents or authored study text. Unknown
    patch keys are ignored; the slug stays stable (it's a durable handle)."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    if "title" in patch and patch["title"] is not None:
        title = str(patch["title"]).strip()
        if not title:
            raise ValueError("a project needs a non-empty title")
        project["title"] = title[:200]
    for key in ("goal", "description"):
        if key in patch and patch[key] is not None:
            project[key] = str(patch[key]).strip()[:2000]
    if patch.get("status"):
        project["status"] = str(patch["status"]).strip()[:40]
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    emit_lifecycle_event("project.updated",  # noqa: F821 (bound)
                         {"project_id": project["id"], "title": project["title"]}, store)
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
        try:
            rs = _plan.project_run_state(p["id"], store=store)
        except Exception:
            rs = None
        out.append({"id": p["id"], "slug": p["slug"], "title": p["title"], "goal": p.get("goal", ""),
                    "status": p.get("status", "active"),
                    # the link to hand the user ("what are my projects") — absent before
                    "url": web_url(f"/projects/{p['id']}"),  # noqa: F821 (bound)
                    "persona_ids": list(p.get("persona_ids") or []),
                    **({"run_state": rs} if rs else {}),
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
    a plan verify task, not listed in the old `study_ids`) and for ones that DECLARE their project_id
    (record_synthesis project_id). Powers correct breadcrumbs. For a deliverable's asset attach the
    export path additionally falls back to the citation rule (owning_project_of_synthesis)."""
    store = store or Store()
    syn = store.get_synthesis(synthesis_id) or {}
    declared = store.get_research_project(syn["project_id"]) if syn.get("project_id") else None
    if declared:
        return {"id": declared["id"], "slug": declared["slug"], "title": declared["title"]}
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


def owning_project_of_synthesis(synthesis_id: str, store: Store | None = None) -> dict[str, Any] | None:
    """parent_project_of_synthesis + the absorption fallback: a synthesis that declares no project
    but cites ONLY one project's owned councils is owned by it. For SIDE EFFECTS (the deliverable
    export's asset attach) — off the breadcrumb resolver so a citing synthesis stays library-rooted."""
    store = store or Store()
    p = parent_project_of_synthesis(synthesis_id, store=store)
    if p:
        return p
    cited = list((store.get_synthesis(synthesis_id) or {}).get("council_ids") or [])
    if cited:
        for proj in store.list_research_projects():
            owned = set(proj.get("council_ids") or [])
            if owned and all(c in owned for c in cited):
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
    # decisions citing evidence (based_on) and naming alternatives (rejected) — so a synthesis
    # learns it "informed decision <title>" (ticket decision-record-artifact)
    for d in store.list_decisions(proj["id"]):
        for r in (d.get("based_on") or []) + (d.get("rejected") or []):
            add(r, d.get("title", ""), f'/decisions/{d["id"]}')
    return idx


def _study_node(store: Store, study_id: str) -> dict[str, Any] | None:
    """A graph node for a synthesis (study) — used by the plan-less / report study_ids path."""
    syn = store.get_synthesis(study_id)
    if not syn:
        return None
    sentiment = _A.synthesis_sentiment_counts(syn, store)   # aggregated over the REAL council voices
    # the voices' personas (the synthesis's OWN statements) — the row avatar cluster (§10 W11)
    spids: list[str] = []
    for st in syn.get("statements") or []:
        pid = st.get("persona_id") or ""
        if pid and pid not in spids:
            spids.append(pid)
    return {
        "study_id": study_id, "kind": "synthesis", "title": syn.get("title", study_id),
        "status": syn.get("status", "done"), "created_at": syn.get("created_at", ""),
        "goal": syn.get("goal", ""), "council_count": len(syn.get("council_ids", [])),
        "voices": len(spids) or sum(sentiment.values()), "sentiment": sentiment,
        "personas": _persona_stubs(store, spids),
        "recommendations": len(_A.synthesis_recommendations(syn)),
        "n_findings": len(syn.get("findings") or []),        # outline chip contract (_outline_chips)
        "phase": syn.get("phase", ""), "mode": syn.get("mode", ""), "role": syn.get("role", ""),
    }


def _persona_stubs(store: Store, pids: list[str]) -> list[dict[str, Any]]:
    """The ≤4 resolved avatar stubs a row's crew cluster renders (the council-node shape)."""
    out = []
    for pid in pids[:4]:
        pr = store.get_persona(pid) or {}
        out.append({"id": pid, "display_name": pr.get("display_name", "?"),
                    "avatar": pr.get("avatar")})
    return out


def prototype_participation(proto: dict, store: Store | None = None) -> dict[str, Any]:
    """Persona participation riding a prototype's DATA (ux-contract §10 W11): the personas who
    drove its sessions — BOTH kinds (recorded prototype reactions + usability walks whose
    subject is this prototype, matched by id or slug). Returns the crew enrichment every row
    surface shares: `n_sessions` (honest combined count), `voices` (distinct drivers) and
    `personas` (≤4 resolved avatar stubs, first-seen order)."""
    store = store or Store()
    pids: list[str] = []
    n = 0
    for s in store.list_prototype_sessions(prototype_id=proto["id"]):
        n += 1
        pid = s.get("persona_id") or ""
        if pid and pid not in pids:
            pids.append(pid)
    seen: set[str] = set()
    for key in (proto.get("id"), proto.get("slug")):
        for s in (list_usability_sessions(subject=key, store=store) if key else []):
            if s["id"] in seen:
                continue
            seen.add(s["id"])
            n += 1
            pid = s.get("persona_id") or ""
            if pid and pid not in pids:
                pids.append(pid)
    return {"n_sessions": n, "voices": len(pids), "personas": _persona_stubs(store, pids)}


def _protos_with_session_counts(project_id: str, store: Store) -> list[dict]:
    """The project's prototypes, each enriched with `n_sessions` — recorded persona reactions
    (prototype sessions) PLUS usability walks whose subject is this prototype — and the session
    drivers' crew (`personas`/`voices`, ux-contract §10 W11). Feeds the outline row's
    sessions-count chip + avatar cluster (§3.2) so both are honest by construction."""
    protos = list_prototypes_artifacts(project_id, store=store)
    for p in protos:
        p.update(prototype_participation(p, store))
    return protos


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
        g = _attach_reports(plan_graph(project_id, store=store), project_id, store)
        g["project"]["url"] = web_url(f"/projects/{project_id}")  # noqa: F821 (bound) — the link to hand the user
        return g
    # Plan-less fallback (start_project always seeds a plan, so this is only hit by hand-built data /
    # the study_ids-based report path): nodes from the project's councils/studies + notes — NO
    # study-edge layer (retired), so no edges.
    project = _require_research_project(store, project_id)
    tags = project.get("study_tags", {})
    nodes = []
    for cid in project.get("council_ids", []):
        c = store.get_council_session(cid)
        if c:
            nodes.append(_evidence_node("council", cid, c.get("prompt", cid), {}, store))
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
                    "methodology": project.get("methodology", ""), "phase": project.get("phase", ""),
                    "url": web_url(f"/projects/{project['id']}")},  # noqa: F821 (bound)
        "methodology_state": None,
        "prototypes": _protos_with_session_counts(project["id"], store),
        "artifacts": list(project.get("artifacts") or []),
        "assets": list(project.get("assets") or []),
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
    voices = 0
    personas: list[dict] = []
    stance_counts: dict[int, int] = {}
    mode = ""
    n_statements = 0
    n_findings = 0
    status = ""
    if kind == "council":
        c = store.get_council_session(eid) or {}
        created = c.get("created_at", "")
        council_count = 1
        # Outline chip contract (_outline_chips): the mode chip derives the way the council
        # page does (council_mode), the statement count rides the node.
        mode = council_mode(c)
        n_statements = len(c.get("statements") or [])
        # Outline detail (tracker: sonaloop/inspector-cinematic-detail-density):
        # WHO spoke + how the council leaned — feeds the row's avatar cluster
        # and stance dots, so the project page shows persona presence.
        pids: list[str] = []
        for st in c.get("statements") or []:
            pid = st.get("persona_id") or ""
            if pid and pid not in pids:
                pids.append(pid)
            val = (st.get("stance") or {}).get("value")
            if val is not None:
                stance_counts[int(val)] = stance_counts.get(int(val), 0) + 1
        voices = len(pids)
        personas = _persona_stubs(store, pids)
    elif kind == "synthesis":
        s = store.get_synthesis(eid) or {}
        created = s.get("created_at", "")
        council_count = len(s.get("council_ids", []))
        n_findings = len(s.get("findings") or [])            # outline chip contract
        status = s.get("status", "done")
        # WHO speaks in the report — the voices' personas (statements), so the outline row
        # carries the same avatar cluster as the council rows (ux-contract §10 W11).
        spids: list[str] = []
        for st in s.get("statements") or []:
            pid = st.get("persona_id") or ""
            if pid and pid not in spids:
                spids.append(pid)
        voices = len(spids)
        personas = _persona_stubs(store, spids)
    href = {"council": f"/councils/{eid}", "synthesis": f"/syntheses/{eid}"}.get(kind, "")
    tags = [kind] + list(prod_task.get("presentation", {}).get("tags") or [])
    return {"study_id": f"{kind}:{eid}", "kind": kind, "title": title, "phase": step,
            "bucket": prod_task.get("bucket", ""), "created_at": created, "council_count": council_count,
            "voices": voices, "sentiment": {}, "stance_counts": stance_counts,
            "personas": personas, "recommendations": 0, "role": prod_task.get("capability", ""),
            "mode": mode, "n_statements": n_statements, "n_findings": n_findings, "status": status,
            "theme_tags": tags, "color": pres["color"], "kind_label": pres["label"],
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
    # Absorb project-owned evidence the plan never produced: remote MCP hosts demonstrably
    # record_council/record_synthesis OUTSIDE the governed run loop, and a council the project
    # owns (record_council appends every one to project.council_ids) must not vanish from the
    # graph, the page and every count just because no task checkpointed it. Placement mirrors
    # the web outline's honest fallback: the phase active at created_at, else the first frame.
    plan_bound = sorted(nodes, key=lambda n: n.get("created_at", ""))
    first_frame = next((t["id"] for t in plan["tasks"] if t["bucket"] == "analyze"), "")

    def _phase_at(ts: str) -> str:
        best = ""
        for n in plan_bound:
            if (n.get("created_at") or "") <= (ts or ""):
                best = n.get("phase", "")
            else:
                break
        return best or first_frame

    for cid in project.get("council_ids") or []:
        nid = f"council:{cid}"
        c = store.get_council_session(cid)
        if nid in seen or not c:
            continue
        seen.add(nid)
        stub = {"bucket": "act", "consumes": [_phase_at(c.get("created_at", ""))]}
        nodes.append(_evidence_node("council", cid, c.get("prompt", cid), stub, store))
    owned = {nid.split(":", 1)[1] for nid in seen if nid.startswith("council:")}
    absorbed_syntheses: list[tuple[str, list[str]]] = []
    for syn in store.list_syntheses():
        sid, nid = syn["id"], f"synthesis:{syn['id']}"
        cited = list(syn.get("council_ids") or [])
        if syn.get("scope") == "project":  # reports already ride the graph via _attach_reports
            continue
        if nid in seen or not (syn.get("project_id") == project_id
                               or (cited and all(c in owned for c in cited))):
            continue
        seen.add(nid)
        stub = {"bucket": "act", "consumes": [_phase_at(syn.get("created_at", ""))]}
        nodes.append(_evidence_node("synthesis", sid, syn.get("title", sid), stub, store))
        absorbed_syntheses.append((sid, cited))
    nodes.extend(note_graph_nodes(project))  # note nodes are first-class (composable primitive)
    nodes.sort(key=lambda n: n.get("created_at", ""))
    # edges: each verify task's synthesis consolidates its act fan's councils (refines)
    edges: list[dict[str, Any]] = []
    node_ids = {n["study_id"] for n in nodes}
    # An absorbed synthesis still declares its evidence: cited councils that are graph nodes
    # connect with the same `refines` semantics the verify-fan edges carry.
    for sid, cited in absorbed_syntheses:
        for cid in cited:
            if f"council:{cid}" in node_ids:
                edges.append({"from_study": f"council:{cid}", "to_study": f"synthesis:{sid}",
                              "type": "refines", "rationale": ""})
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
        "prototypes": _protos_with_session_counts(project["id"], store),
        "artifacts": list(project.get("artifacts") or []),
        "assets": list(project.get("assets") or []),
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


# --- Deletes (D in CRUD; reachable from MCP/CLI and the web's structural
#     write routes — docs/web-mutations.md documents the boundary) -------------



def delete_research_project(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """Delete a project container + its graph metadata (edges/open questions).
    The syntheses stay (they are independent studies)."""
    store = store or Store()
    p = _require_research_project(store, project_id)
    return {"deleted": store.delete_research_project(p["id"]), "project_id": p["id"]}



# M-cleanup: remove_study_from_project / unlink_studies RETIRED (study-edge graph).
