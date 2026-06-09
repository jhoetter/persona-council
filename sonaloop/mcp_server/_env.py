from __future__ import annotations

import time
from typing import Any

from ..config import MEMORY_SCHEMA_VERSION

SERVER_VERSION = "0.2.0"

# Implicit decision DAG: each tool hints the natural next
# step so the host agent can route the simulate -> consolidate -> digest loop.
_NEXT: dict[str, dict[str, Any]] = {
    "brief_persona": {"name": "record_persona", "reason": "persist the profile JSON you authored"},
    "record_persona": {"name": "brief_day", "reason": "plan the persona's first day before simulating"},
    "brief_day": {"name": "record_day", "reason": "author day_plan + activities, then persist the whole day"},
    "record_day": {"name": "brief_consolidation", "reason": "consolidate the day into memory"},
    "put_day_plan": {"name": "record_day", "reason": "persist the authored day (plan + activities)"},
    "brief_consolidation": {"name": "record_memory_deltas", "reason": "persist the entities/facts/threads you extracted"},
    "record_memory_deltas": {"name": "evaluate_simulation", "reason": "check quality, or brief_digest to roll up"},
    "brief_period": {"name": "put_period_plan", "reason": "persist the period plan + its sample_days"},
    "put_period_plan": {"name": "record_month_bundle", "reason": "persist the authored sampled days as a month bundle"},
    "brief_digest": {"name": "put_digest", "reason": "persist the digest you authored"},
    "brief_persona_revision": {"name": "record_persona_revision", "reason": "persist the (usually small) identity drift"},
    "recall_memory": {"name": "get_project", "reason": "open the timeline of a project a hit pointed to"},
    "list_active_projects": {"name": "get_project", "reason": "open one project's full timeline"},
    "get_persona": {"name": "get_persona_memory", "reason": "see the rendered memory (active projects, threads)"},
    "brief_eval_critic": {"name": "record_eval_critic", "reason": "persist the semantic verdict you authored"},
    "record_eval_critic": {"name": "evaluate_simulation_full", "reason": "combined structural+semantic top verdict"},
    "brief_cohort_critic": {"name": "record_cohort_critic", "reason": "persist the cohort outlier verdict you authored"},
    "create_research_project": {"name": "start_run", "reason": "create the run object, then loop run_step"},
    "brief_synthesis_outline": {"name": "record_synthesis_outline", "reason": "persist the outline you derived from the graph"},
    "record_synthesis_outline": {"name": "brief_synthesis_section", "reason": "author each section grounded in its source studies"},
    "brief_synthesis_section": {"name": "record_synthesis_section", "reason": "persist the authored section + citations"},
    "record_synthesis_section": {"name": "export_synthesis", "reason": "render the assembled report (by report id)"},
    "brief_month": {"name": "record_month_bundle", "reason": "persist the authored month bundle through the loop"},
    "record_month_bundle": {"name": "brief_month", "reason": "continue with the next month"},
    "brief_evidence_check": {"name": "record_evidence_check", "reason": "persist provenance verdict (confirmed/contradicted)"},
    "brief_synthesis": {"name": "record_synthesis", "reason": "persist the cross-council synthesis you authored"},
    "record_synthesis": {"name": "export_synthesis", "reason": "render the stakeholder report"},
    "brief_council": {"name": "record_council", "reason": "author the turns + synthesis, then persist the council"},
    "record_council": {"name": "brief_synthesis", "reason": "fold this council into a synthesis when you have several"},
    # --- methodologies = plan SEEDS; the runtime engine is the plan (spec/hx3-engine-collapse.md) ---
    "list_frameworks": {"name": "describe_framework", "reason": "read one Framework's plain-language shape before choosing it"},
    "describe_framework": {"name": "start_project", "reason": "start_project(methodology=<id>) runs the study through this Framework"},
    "list_methodologies": {"name": "get_methodology", "reason": "inspect a constellation's steps before starting"},
    "get_methodology": {"name": "start_project", "reason": "start_project(methodology=<key>) seeds the plan"},
    "set_project_methodology": {"name": "next_action", "reason": "load the next ready plan step fully"},
    "brief_next": {"name": "next_action", "reason": "load the ready task fully (grounding + participants + gate)"},
    "next_action": {"name": "complete_task", "reason": "author the step (frame/council/synthesis), persist, then complete"},
    "record_judgment": {"name": "complete_task", "reason": "complete the verify once its gate judgment is recorded"},
    "suggest_capabilities": {"name": "suggest_methodologies", "reason": "browse suggested step/whole-methodology templates"},
    # --- prototypes + harness ---
    "scaffold_prototype": {"name": "run_prototype", "reason": "start the generated app locally"},
    "run_prototype": {"name": "proto_open", "reason": "open the running app in a headless browser session"},
    "proto_open": {"name": "proto_act", "reason": "act on the snapshot (click/type), or proto_read"},
    "brief_prototype_session": {"name": "proto_open", "reason": "drive the app as the persona, then record the session"},
    "record_prototype_session": {"name": "brief_council", "reason": "fold the grounded reaction into a test council"},
}


def _env(tool: str, data: Any, started: float) -> dict[str, Any]:
    return {
        "ok": True,
        "data": data,
        "next_recommended_tool": _NEXT.get(tool),
        "_meta": {
            "tool": tool,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "server_version": SERVER_VERSION,
            "schema_version": MEMORY_SCHEMA_VERSION,
        },
    }
