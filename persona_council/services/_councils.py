"""Council briefs/asks + council write-back/reads + export.

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



def brief_council(prompt: str, persona_ids: list[str] | None = None, filters: dict[str, Any] | None = None,
                  count: int = 3, context: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Gather everything needed to run a host-authored council and persist it with
    record_council. Returns candidate personas (to select from) OR, when persona_ids
    are given, each participant's loaded agent context to author turns against.

    Methodology lives in the run-council skill: load each persona's SOUL + memory,
    react in character (support/skepticism/indifference/rejection all valid), then
    author proposal/votes/exec_summary and call record_council."""
    store = store or Store()
    language = ensure_content_language(" ".join(filter(None, [prompt, context])))
    if not persona_ids:
        personas = list_personas(filters, store)
        candidates = [
            {"persona_id": p["id"], "display_name": p["display_name"],
             "source_description": p["source_description"], "role": p.get("role", {}),
             "company_context": p.get("company_context", {}), "goals": p.get("goals", []),
             "constraints": p.get("constraints", []), "tools": p.get("tools", []),
             "pain_points": p.get("pain_points", []), "success_criteria": p.get("success_criteria", [])}
            for p in personas
        ]
        return {
            "schema": "council_selection", "language": language, "prompt": prompt,
            "count": min(max(1, count), len(candidates)) if candidates else 0,
            "candidate_personas": candidates,
            "instructions": (
                "Select the personas whose lived contexts produce useful, honest contrast on this "
                "prompt (never bias toward support; do not invent IDs). Then call brief_council again "
                f"with persona_ids=[...] to get each participant's context. {language_instruction(language)}"
                if candidates else "No personas exist yet. Create some via brief_persona/record_persona first."
            ),
        }
    participants = []
    for pid in persona_ids:
        p = store.get_persona(pid)
        if not p:
            continue
        ctx = prepare_persona_agent_context(
            p["id"], f"Council prompt: {prompt}\nExternal context: {context or 'none'}", store=store)
        participants.append({
            "persona_id": p["id"], "display_name": p["display_name"],
            "soul_path": ctx["soul_path"], "agent_context": ctx["agent_context"],
        })
    return {
        "schema": "council", "language": language, "prompt": prompt, "external_context": context,
        "participants": participants,
        "instructions": (
            "Author one or more turns per participant grounded in their agent_context (SOUL + memory), "
            "honest and anti-steering. Then author proposal, votes (SUPPORT/MAYBE/ABSTAIN/OPPOSE), a "
            "short summary, and a rich Markdown exec_summary. Persist via record_council(prompt, "
            f"persona_ids, turns, votes, proposal, summary, exec_summary). {language_instruction(language)}"
        ),
    }



def select_council(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    raise NotImplementedError(
        "Council selection is host-authored: brief_council(prompt) returns candidates; "
        "you pick. See the run-council skill."
    )



def run_council(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    raise NotImplementedError(
        "Councils are host-authored: brief_council(prompt) -> pick personas -> "
        "brief_council(prompt, persona_ids) -> author turns + synthesis -> record_council(...). "
        "See the run-council skill."
    )



def brief_ask(persona_id: str, question: str, context: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Gather one persona's loaded agent context to author an honest answer to a
    question. The host writes the answer from the returned agent_context (the
    persona's SOUL + recent events + task-keyed memory)."""
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    language = ensure_content_language(" ".join(filter(None, [question, context])))
    agent_ctx = prepare_persona_agent_context(persona_id, question, store=store)
    return {
        "schema": "persona_answer", "language": language, "persona_id": persona["id"],
        "display_name": persona["display_name"], "question": question, "external_context": context,
        "soul_path": agent_ctx["soul_path"], "agent_context": agent_ctx["agent_context"],
        "instructions": (
            "Answer AS this persona, grounded in the agent_context — do not force support; "
            "say what is uncertain if the record is thin. " + language_instruction(language)
        ),
    }



def ask_persona(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    raise NotImplementedError(
        "Persona answers are host-authored: brief_ask(persona_id, question) returns the "
        "persona's loaded context; you write the answer in character."
    )



def compare_personas(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    raise NotImplementedError(
        "Compare is host-authored: brief_ask per persona on the same question, then author "
        "each answer and contrast them."
    )



def export_council_session(session_id: str, format: str = "json", store: Store | None = None) -> str:
    store = store or Store()
    session = store.get_council_session(session_id)
    if not session:
        raise KeyError(f"Unknown council session: {session_id}")
    if format == "md":
        de = content_language() == "de"
        h_session = "Council-Sitzung" if de else "Council Session"
        h_turns = "Wortbeiträge" if de else "Turns"
        h_proposal = "Vorschlag" if de else "Proposal"
        h_votes = "Stimmen" if de else "Votes"
        h_summary = "Zusammenfassung" if de else "Summary"
        lines = [f"# {h_session}", "", f"**Prompt:** {session['prompt']}", "", f"## {h_turns}"]
        for turn in session["turns"]:
            lines.append(f"- **{turn['speaker']}**: {turn['content']}")
        lines.extend(["", f"## {h_proposal}", session["proposal"], "", f"## {h_votes}"])
        for v in session["votes"]:
            lines.append(f"- **{v.get('speaker') or v.get('persona_id', '')}**: {v.get('vote', '')} - {v.get('reason', '')}")
        lines.extend(["", f"## {h_summary}", session["summary"]])
        return "\n".join(lines) + "\n"
    return json.dumps(session, indent=2, ensure_ascii=False)



def record_council(prompt: str, persona_ids: list[str], turns: list[dict[str, Any]],
                   votes: list[dict[str, Any]] | None = None, proposal: str = "", summary: str = "",
                   exec_summary: str = "", selection_reason: str = "", key: str | None = None,
                   store: Store | None = None) -> dict[str, Any]:
    """Persist a host-authored council (openings/moderator/directed turns + synthesis). Pass a stable
    `key` (e.g. "<project>:<step>:<angle>") to get a DETERMINISTIC id so re-running the step is an
    idempotent upsert — makes long autonomous runs resumable/replayable (spec/harness-evaluation HX6)."""
    store = store or Store()
    existing = store.get_council_session(stable_id("council", key)) if key else None
    cid = stable_id("council", key) if key else stable_id("council", prompt, utc_now_iso())
    session = CouncilSession(
        id=cid,
        prompt=prompt, persona_ids=persona_ids, selection_reason=selection_reason or "host-authored",
        turns=turns or [], proposal=proposal, votes=votes or [], summary=summary,
        exec_summary=exec_summary, created_at=(existing or {}).get("created_at") or utc_now_iso(),
    ).to_dict()
    store.insert_council_session(session)
    return session



def get_council(session_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    c = store.get_council_session(session_id)
    if not c:
        raise KeyError(f"Unknown council session: {session_id}")
    return c



def list_councils(store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    return [{"id": c["id"], "prompt": c["prompt"], "created_at": c["created_at"],
             "personas": len(c.get("persona_ids", [])), "turns": len(c.get("turns", [])),
             "votes": {v: sum(1 for x in c.get("votes", []) if x.get("vote") == v) for v in ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]}}
            for c in store.list_council_sessions()]


# ===================================================================== #
# Research graph: Project container + typed study edges + theme tags +   #
# open questions + frontier. A Study(=Synthesis) is a node; councils sit  #
# inside a node. See spec/research-graph-and-meta-report.md.              #
# ===================================================================== #



def delete_council(session_id: str, store: Store | None = None) -> dict[str, Any]:
    """Delete a council session. Syntheses keep their council_id reference (harmless)."""
    store = store or Store()
    return {"deleted": store.delete_council_session(session_id)}
