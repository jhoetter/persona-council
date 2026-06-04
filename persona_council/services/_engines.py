"""Methodology-engine seam + research-plan-engine seam + prototypes/Playwright seam.

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


from ..methodology import (  # noqa: E402
    MethodologyError,
    list_methodologies,
    get_methodology,
    register_methodology,
    start_methodology_project,
    set_project_methodology,
    brief_next,
    brief_phase,
    record_node,
    record_exploration,
    record_judgment,
    record_decision,
    record_convergence,
    advance,
    advance_phase,
    get_methodology_state,
)
from ..suggestions import (  # noqa: E402
    suggest_capabilities,
    suggest_roles,
    suggest_artifact_types,
    suggest_section_kinds,
    suggest_methodologies,
)
from .. import plan as _plan  # noqa: E402
from ..plan import (  # noqa: E402
    PlanError,
    new_plan,
    validate_plan,
    seed_plan_from_methodology,
    ready_tasks,
    is_complete,
    render_plan_md,
)
from .. import prototypes as _proto  # noqa: E402
from .. import browser as _browser   # noqa: E402



def start_project(title: str, goal: str, methodology: str | None = None,
                  persona_ids: list[str] | None = None, description: str = "",
                  store: Store | None = None) -> dict[str, Any]:
    """Unified project entry: create a research project + seed its plan. With a methodology the plan
    is seeded from the constellation (analyze/act/verify scaffolding); freeform seeds one root frame
    task (analyze, dischargeable). The methodology engine binding is kept for back-compat."""
    store = store or Store()
    project = create_research_project(title, goal=goal, persona_ids=persona_ids,
                                      description=description, store=store)
    if methodology:
        spec = get_methodology(methodology, store=store)
        set_project_methodology(project["id"], methodology, store=store)   # phase_log (back-compat)
        plan = _plan.seed_plan_from_methodology(project["id"], goal, spec)
    else:
        root = {"id": "frame__root", "title": "Frame the inquiry", "bucket": "analyze",
                "capability": "frame", "consumes": [],
                "intent": "Understand before concluding: read persona memory + author the research "
                          "questions/hypotheses this inquiry needs before any council runs."}
        plan = _plan.new_plan(project["id"], goal, "", [root])
    _plan.save_plan(plan, store=store)
    return store.get_research_project(project["id"])



def get_plan(project_id: str, store: Store | None = None) -> dict[str, Any] | None:
    return _plan.get_plan(project_id, store=store)



def save_plan(plan: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    return _plan.save_plan(plan, store=store)



def add_task(project_id, bucket, capability, title, intent="", consumes=None, requires=None,
             step="", plan_note="", task_id=None, store: Store | None = None) -> dict[str, Any]:
    return _plan.add_task(project_id, bucket, capability, title, intent, consumes, requires,
                          step, plan_note, task_id, store=store)



def record_frame(project_id, task_id, questions, hypotheses=None, memory_refs=None,
                 store: Store | None = None) -> dict[str, Any]:
    return _plan.record_frame(project_id, task_id, questions, hypotheses, memory_refs, store=store)



def link_evidence(project_id, task_id, ref, store: Store | None = None) -> dict[str, Any]:
    return _plan.link_evidence(project_id, task_id, ref, store=store)



def complete_task(project_id, task_id, store: Store | None = None) -> dict[str, Any]:
    return _plan.complete_task(project_id, task_id, store=store)



def assess_progress(project_id, task_id, rationale, evidence_refs, delta="",
                    store: Store | None = None) -> dict[str, Any]:
    return _plan.assess_progress(project_id, task_id, rationale, evidence_refs, delta, store=store)



def plan_coverage(project_id, store: Store | None = None) -> dict[str, Any]:
    return _plan.coverage_hint(project_id, store=store)


# brief_next + record_judgment DISPATCH: plan-driven when the project has a plan, else the legacy
# methodology engine. (These names were imported from .methodology above; redefined here to dispatch.)



_m_brief_next = brief_next            # the methodology engine's router (legacy fallback)



_m_record_judgment = record_judgment



def brief_next(project_id: str, store: Store | None = None) -> dict[str, Any]:  # noqa: F811
    store = store or Store()
    if _plan.get_plan(project_id, store=store) is not None:
        return _plan.brief_next(project_id, store=store)
    return _m_brief_next(project_id, store=store)



def record_judgment(project_id, task_id_or_step, gate_tag, decided, rationale,  # noqa: F811
                    evidence_refs=None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    if _plan.get_plan(project_id, store=store) is not None:
        return _plan.record_judgment(project_id, task_id_or_step, gate_tag, decided, rationale,
                                     evidence_refs, store=store)
    return _m_record_judgment(project_id, task_id_or_step, gate_tag, decided, rationale,
                              evidence_refs, store=store)



def export_plan_md(project_id: str, store: Store | None = None) -> str:
    store = store or Store()
    p = _plan.get_plan(project_id, store=store)
    if not p:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    return _plan.render_plan_md(p)


# --- Prototypes + Playwright harness seam (spec §6/§7) -------------------------
from .. import prototypes as _proto  # noqa: E402
from .. import browser as _browser   # noqa: E402



def scaffold_artifact(slug, name, concept, type="prototype", tags=None, template=None,
                      project_id=None, store: Store | None = None):
    return _proto.scaffold_artifact(slug, name, concept, type=type, tags=tags, template=template,
                                    project_id=project_id, store=store)



def scaffold_prototype(slug, name, concept, kind="web", template=None,
                       project_id=None, fidelity=None, store: Store | None = None):
    return _proto.scaffold_prototype(slug, name, concept, kind, template, project_id, fidelity=fidelity, store=store)



def register_prototype(slug, name, path, entry="index.html", run="static", run_cmd=None,
                       version="v0.1", project_id=None, notes="", fidelity="", store: Store | None = None):
    return _proto.register_prototype(slug, name, path, entry, run, run_cmd, version, project_id, notes,
                                     fidelity=fidelity, store=store)



def list_prototypes_artifacts(project_id=None, store: Store | None = None):
    return _proto.list_prototypes(project_id, store=store)



def get_prototype_artifact(prototype_id, store: Store | None = None):
    return _proto.get_prototype(prototype_id, store=store)



def run_prototype(prototype_id, store: Store | None = None):
    return _proto.run_prototype(prototype_id, store=store)



def stop_prototype(prototype_id, store: Store | None = None):
    return _proto.stop_prototype(prototype_id, store=store)



def delete_prototype_artifact(prototype_id, store: Store | None = None):
    return _proto.delete_prototype(prototype_id, store=store)



def proto_open(prototype_id=None, url=None, persona_id=None, store: Store | None = None):
    store = store or Store()
    if prototype_id and not url:
        url = _proto.run_prototype(prototype_id, store=store)["url"]
    if not url:
        raise ValueError("proto_open needs a prototype_id or a url")
    return _browser.open_session(url, prototype_id, persona_id)



def proto_act(session_id, action, store: Store | None = None):
    return _browser.act(session_id, action)



def proto_read(session_id, store: Store | None = None):
    return _browser.read(session_id)



def proto_close(session_id, store: Store | None = None):
    return _browser.close(session_id)



def list_proto_sessions(store: Store | None = None):
    return _browser.list_sessions()



def brief_prototype_session(persona_id, prototype_id, store: Store | None = None):
    store = store or Store()
    proto = _proto.get_prototype(prototype_id, store=store)
    ctx = prepare_persona_agent_context(
        persona_id, task=f"Use the prototype '{proto['name']}' as you really would and report what you experienced",
        recent_events=8, store=store)
    screens = []
    try:
        import json as _json
        cpath = ROOT / proto["path"] / "concept.json"
        if cpath.exists():
            screens = [{"id": s["id"], "title": s.get("title", s["id"])}
                       for s in _json.loads(cpath.read_text(encoding="utf-8")).get("screens", [])]
    except Exception:
        pass
    return {
        "schema": "prototype_session", "persona_id": persona_id,
        "prototype": {"id": proto["id"], "name": proto["name"], "slug": proto["slug"], "screens": screens},
        "agent_context": ctx.get("agent_context"),
        "instructions": ("Open the running app (proto_open), drive it like THIS persona "
                         "(proto_act click/type/select on refs from the latest snapshot), observe the REAL "
                         "state, then author a grounded reaction. Anti-steering: only praise what you actually "
                         "exercised; honest friction and rejection are first-class. Cite the states you saw in "
                         "observed_state_refs."),
    }



def record_prototype_session(persona_id, prototype_id, session_id, date_value, reaction,
                             store: Store | None = None):
    store = store or Store()
    proto = _proto.get_prototype(prototype_id, store=store)
    refs = [str(r).strip() for r in (reaction.get("observed_state_refs") or []) if str(r).strip()]
    if not refs:
        raise ValueError("reaction.observed_state_refs must cite >= 1 observed state (a ref or text actually seen)")
    log = _browser.session_log(session_id)
    grounded = True
    if log:
        seen_refs: set[str] = set()
        seen_text = ""
        for entry in log:
            if entry.get("kind") == "snapshot":
                seen_refs.update(entry.get("refs", []))
                seen_text += " " + (entry.get("text") or "")
        unmatched = [r for r in refs if r not in seen_refs and r.lower() not in seen_text.lower()]
        if unmatched:
            raise ValueError(f"prototype-reaction groundedness: observed_state_refs not present in the session log: {unmatched}")
    else:
        grounded = False  # session closed / harness unavailable — record but mark unverified
    now = utc_now_iso()
    sess = PrototypeSession(
        id=stable_id("protosession", persona_id, prototype_id, now), persona_id=persona_id,
        prototype_id=proto["id"], session_id=session_id, date=date_value, reaction=reaction,
        observed_state_refs=refs, created_at=now).to_dict()
    sess["grounded_verified"] = grounded
    store.insert_prototype_session(sess)
    # write the real use into persona memory so the test council surfaces it
    name = proto["name"]
    facts = []
    for h in (reaction.get("liked") or [])[:4]:
        facts.append({"entity": name, "fact": str(h), "status": "positiv", "valid_from": date_value, "importance": 4})
    for h in (reaction.get("friction") or [])[:4]:
        facts.append({"entity": name, "fact": str(h), "status": "offen", "valid_from": date_value, "importance": 4})
    if reaction.get("verdict"):
        facts.append({"entity": name, "fact": "Verdict: " + str(reaction["verdict"]), "status": "neutral",
                      "valid_from": date_value, "importance": 3})
    deltas = {
        "entities": [{"mention": name, "kind": "topic", "status": "ausprobiert", "aliases": [proto["slug"]]}],
        "facts": facts or [{"entity": name, "fact": str(reaction.get("summary", "Prototype tried")),
                            "status": "neutral", "valid_from": date_value, "importance": 3}],
        "threads": [], "event_links": [],
    }
    try:
        record_memory_deltas(persona_id, date_value, deltas, store=store)
        memory_written = True
    except Exception:
        memory_written = False
    return {"prototype_session": sess, "grounded_verified": grounded, "memory_written": memory_written}
