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
from ._authoring import MARKDOWN_CONTRACT, PRIMITIVES_CONTRACT
from .. import artifacts as _artifacts
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



def brief_council(project_id: str, prompt: str, persona_ids: list[str] | None = None,
                  filters: dict[str, Any] | None = None, count: int = 3, context: str | None = None,
                  store: Store | None = None) -> dict[str, Any]:
    """Gather everything needed to run a host-authored council and persist it with
    record_council. A council is scoped to a research project, so `project_id` is required
    and validated up front (create one with create_research_project first; personas are
    global and need no project). Returns candidate personas (to select from) OR, when
    persona_ids are given, each participant's loaded agent context to author turns against.

    Methodology lives in the run-council skill: load each persona's SOUL + memory,
    react in character (support/skepticism/indifference/rejection all valid), then
    author proposal/votes/exec_summary and call record_council."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # fail fast if no/unknown project
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
            "schema": "council_selection", "language": language, "project_id": project["id"], "prompt": prompt,
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
        "schema": "council", "language": language, "project_id": project["id"], "prompt": prompt,
        "external_context": context, "participants": participants,
        "instructions": (
            "Run this council in the shape the task calls for (the UI derives the mode):\n"
            "• DISCOVERY (default for early research): pass `questions` = the OPEN, conversational "
            "user-research questions you ask. Author ONE `statement` per (persona, question) — that "
            "persona's honest answer — with about={kind:'prompt', id:'q0'|'q1'|…} pointing at the "
            "question it answers, so the page renders a moderated Q→A transcript. Do NOT invent a "
            "hypothesis and do NOT collect votes — you are LISTENING. Leave proposal/votes empty.\n"
            "• EVALUATION (reacting to a concept/prototype): set `proposal`; each statement reacts with "
            "about={kind:'prompt', id:'proposal'} + a `stance` ({value -2..2}); no hard votes.\n"
            "• DECISION (rare — an explicit choice): set `proposal` + `votes` (SUPPORT/MAYBE/ABSTAIN/"
            "OPPOSE) for the tally.\n"
            "On each statement set persona_id, text (the persona's words, in voice), stance where "
            "applicable, about (the prompt it answers), and refs (the memories/sources drawn on, incl. "
            "{kind:'memory', text}). Ground every statement in agent_context, honest + anti-steering. "
            "Add `findings` for any council-level analysis + a rich Markdown exec_summary. Persist via "
            "record_council(project_id, prompt, persona_ids, statements=[...], questions=[...] | "
            f"proposal=…, votes=…, summary, exec_summary, findings=[...]). {language_instruction(language)}"
            + MARKDOWN_CONTRACT + PRIMITIVES_CONTRACT
        ),
    }






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
        for st in _artifacts.council_statements(session):
            who = (store.get_persona(st.get("persona_id", "")) or {}).get("name") or st.get("persona_id", "")
            lines.append(f"- **{who}**: {st.get('text', '')}")
        lines.extend(["", f"## {h_proposal}", session["proposal"], "", f"## {h_votes}"])
        for v in session["votes"]:
            lines.append(f"- **{v.get('speaker') or v.get('persona_id', '')}**: {v.get('vote', '')} - {v.get('reason', '')}")
        lines.extend(["", f"## {h_summary}", session["summary"]])
        return "\n".join(lines) + "\n"
    return json.dumps(session, indent=2, ensure_ascii=False)



def council_mode(council: dict[str, Any]) -> str:
    """DERIVE a council's shape (no closed vocabulary, no stored type): `decision` (a proposal put to a
    vote — For/Against), `evaluation` (a concept/proposal reacted to conversationally, no hard vote), or
    `discovery` (open user-research questions → answers). spec/methodology-and-clarity-redesign.md Q2."""
    has_prop = bool((council.get("proposal") or "").strip())
    has_votes = bool(council.get("votes"))
    if has_prop and has_votes:
        return "decision"
    if has_prop:
        return "evaluation"
    return "discovery"


def record_council(project_id: str, prompt: str, persona_ids: list[str],
                   statements: list | None = None, votes: list[dict[str, Any]] | None = None,
                   proposal: str = "", summary: str = "", exec_summary: str = "",
                   selection_reason: str = "", questions: list[str] | None = None,
                   key: str | None = None, findings: list | None = None,
                   prompts: list | None = None, created_at: str | None = None,
                   store: Store | None = None) -> dict[str, Any]:
    """Persist a host-authored council. A council is a research artefact and MUST live inside a research
    project — `project_id` is required and validated. Author the voices as `statements` (the ONE voice
    primitive: {persona_id, text, stance, about:{kind:'prompt',id}, refs}); set `questions` (discovery) or
    `proposal`(+`votes` for a decision) to shape the mode. `findings`/`prompts` are optional. Pass a stable
    `key` for a DETERMINISTIC id (idempotent upsert → resumable runs; spec/harness-evaluation HX6)."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # fail fast if no/unknown project
    existing = store.get_council_session(stable_id("council", key)) if key else None
    cid = stable_id("council", key) if key else stable_id("council", prompt, utc_now_iso())

    def _nvote(v):
        v = dict(v) if isinstance(v, dict) else {"vote": str(v)}
        if not v.get("vote"):
            v["vote"] = v.get("stance") or v.get("label") or ""   # keep a displayable value
        return v

    votes = [_nvote(v) for v in (votes or [])]
    qs = [str(q).strip() for q in (questions or []) if str(q).strip()]
    # Primitives-only: statements are the ONE voice representation; prompts are built from the council's
    # canonical question/proposal fields when not authored explicitly.
    statements_out = [_artifacts.validate_statement(s) for s in (statements or [])]
    nat_prompts = [_artifacts.validate_prompt(p) for p in (prompts or [])]
    prompts_out = nat_prompts or _artifacts.council_prompts(
        {"prompt": prompt, "questions": qs, "proposal": proposal})
    findings_out = [_artifacts.validate_finding(f) for f in (findings or [])]
    # Stable part ids so other artifacts can cross-reference these statements/findings + the UI can
    # deep-link to them (spec/artifact-cross-references.md). Prompts keep their semantic ids (q0/proposal).
    _artifacts.assign_part_ids(statements_out, "st")
    _artifacts.assign_part_ids(findings_out, "f")
    _artifacts.assign_part_ids(prompts_out, "p")
    session = CouncilSession(
        id=cid,
        prompt=prompt, persona_ids=persona_ids, selection_reason=selection_reason or "host-authored",
        proposal=proposal, votes=votes, summary=summary,
        exec_summary=exec_summary, questions=qs,
        created_at=(existing or {}).get("created_at") or created_at or utc_now_iso(),
        project_id=project["id"],
        statements=statements_out,
        findings=findings_out,
        prompts=prompts_out,
    ).to_dict()
    store.insert_council_session(session)
    # Register the council on its project so the project owns it directly (idempotent).
    council_ids = project.setdefault("council_ids", [])
    if cid not in council_ids:
        council_ids.append(cid)
        project["updated_at"] = utc_now_iso()
        store.upsert_research_project(project)
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
             "personas": len(c.get("persona_ids", [])), "turns": len(_artifacts.council_statements(c)),
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
