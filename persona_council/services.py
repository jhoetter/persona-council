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

from .config import ROOT, utc_now_iso
from .models import (
    CalendarEvent,
    CouncilSession,
    DailySummary,
    Evidence,
    ExperienceEvent,
    PainPointObservation,
    Persona,
    Reflection,
    SimulationResult,
    Synthesis,
)
from .storage import Store
from .taxonomy import GENERIC_TOOLS, normalized_tool_ids, normalized_tools
from . import memory as memory_mod
from . import evaluation as evaluation_mod
from .llm_simulation import (
    build_consolidation_prompt,
    build_digest_prompt,
    build_eval_critic_prompt,
    build_evidence_check_prompt,
    build_persona_revision_prompt,
    build_plan_prompt,
    build_synthesis_prompt,
    generate_activity,
    generate_council_selection_with_llm,
    generate_council_synthesis_with_llm,
    generate_council_turn_with_llm,
    generate_day_plan_with_llm,
    generate_persona_answer_with_llm,
    generate_profile_with_llm,
    validate_digest_payload,
    validate_eval_critic_payload,
    validate_evidence_check_payload,
    validate_memory_deltas_payload,
    validate_persona_revision_payload,
    validate_plan_payload,
    validate_synthesis_payload,
)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or f"persona-{uuid.uuid4().hex[:8]}"


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def persona_dir(persona: dict[str, Any]) -> Path:
    # Runtime working dir for rendered SOUL.md/MEMORY.md. Lives under data/ (all
    # generated state is under data/; gitignored). The portable, local-only copy
    # is data/export/ (see export_snapshot/import_snapshot).
    return ROOT / "data" / "personas" / persona["slug"]


def soul_path(persona: dict[str, Any]) -> Path:
    return persona_dir(persona) / "SOUL.md"


def render_soul(persona: dict[str, Any], store: Store | None = None) -> str:
    store = store or Store()
    persona = effective_persona(persona, store)
    revisions = store.list_persona_revisions(persona["id"])
    summaries = store.list_daily_summaries(persona["id"])[-5:]
    reflections = store.list_reflections(persona["id"])[-3:]
    events = store.list_experience_events(persona["id"])[-8:]
    state_line = "No simulated day has been run yet."
    if events:
        latest = events[-1]
        state_line = (
            f"Last seen at {latest['timestamp']} doing `{latest['task']}` in "
            f"{latest.get('collaboration_mode', latest['event_type'])} mode."
        )
    recent_reflections = "\n".join(f"- {r['summary']}" for r in reflections) or "- None yet."
    recent_work_signals = "\n".join(
        f"- `{e['timestamp']}` {e['event_type']} / {e['task']}: {e.get('summary', '')}"
        for e in events
    ) or "- None yet."
    daily_reality = "\n".join(f"- {s['date']}: {s['mood']}; open loops: {', '.join(s['open_loops']) or 'none'}" for s in summaries) or "- Not simulated yet."
    relationships = "\n".join(f"- {r['name']} ({r['type']}): {r['friction']}" for r in persona["relationships"])
    return f"""# {persona['display_name']}

## Identity
{persona['display_name']} is a synthetic customer persona derived from:

> {persona['source_description']}

This is not a real person. Treat all non-evidence-backed details as simulation assumptions.

## Work Context
- Role: {persona['role']['title']}
- Company context: {persona['company_context']['industry']} ({persona['company_context']['size']} people)
- Tools: {', '.join(persona['tools'])}
- Operating model: {persona['company_context']['operating_model']}

## Inner Operating System
- Working style: {persona['personality']['working_style']}
- Communication style: {persona['personality']['communication_style']}
- Risk tolerance: {persona['personality']['risk_tolerance']}
- Decision filter: {', '.join(persona['success_criteria'])}

## Daily Reality
{daily_reality}

## Frictions
{chr(10).join(f'- {p}' for p in persona['pain_points'])}

## Motivations
{chr(10).join(f'- {g}' for g in persona['goals'])}

## Relationships
{relationships}

## Voice
Speak as a practical customer under real delivery pressure. Refer to concrete calendar moments, tools, handoffs, meetings, and open loops. Do not sound like a generic market research respondent.

## Simulation Rules
- Stay within the work context above unless new evidence is attached.
- Do not steer this persona toward BIM, AI, automation, or any product direction unless the source description, recent events, or explicit task context supports it.
- Treat inferred goals, tools, and pains as hypotheses, not facts; prefer ordinary daily work over vendor-friendly narratives.
- Prefer mundane repeated friction over dramatic invented events.
- Distinguish meetings, solo focus work, interruptions, admin, decisions, and follow-up.
- Preserve unresolved loops across days.
- Mark uncertainty instead of pretending inferred details are known.

## Current State
{state_line}

## Recent Work Signals
{recent_work_signals}

## Recent Reflections
{recent_reflections}

## Gewachsene Identität (Revisionen)
{chr(10).join(f"- {r['effective_on']}: {r.get('rationale','')[:200]}" for r in revisions) or "- Keine; Kern-Identität unverändert."}
"""


def write_soul(persona: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    path = soul_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = render_soul(persona, store)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path.relative_to(ROOT)), "updated_at": utc_now_iso()}


def _replace_legacy_inferred_defaults(persona: dict[str, Any]) -> bool:
    changed = False
    source_tool_ids, source_tools = normalized_tools(persona["source_description"])
    has_explicit_source_tools = bool(source_tools) and source_tools != [label for _, label in GENERIC_TOOLS]
    is_deterministically_inferred = persona.get("provenance", {}).get("profile_fields") == "deterministically inferred from source description"
    if is_deterministically_inferred and has_explicit_source_tools and persona.get("tools") != source_tools:
        persona["tool_ids"] = source_tool_ids
        persona["tools"] = source_tools
        changed = True
    company = persona.get("company_context", {})
    if is_deterministically_inferred and has_explicit_source_tools and company.get("stack") != source_tools:
        company["stack"] = source_tools
        persona["company_context"] = company
        changed = True
    return changed


def ensure_persona_runtime_fields(persona: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    changed = False
    if _replace_legacy_inferred_defaults(persona):
        changed = True
    if (
        "identity_traits" not in persona
        or "avatar_profile" not in persona.get("identity_traits", {})
        or "tool_ids" not in persona
        or "tools" not in persona
    ):
        profile = generate_profile_with_llm(
            persona["source_description"],
            persona.get("segment", {}).get("customer_type"),
            None,
        )
        refreshed = _profile_to_persona_dict(
            persona["source_description"],
            profile,
            persona.get("segment", {}).get("customer_type"),
            None,
            utc_now_iso(),
            persona_id=persona["id"],
            previous=persona,
        )
        persona.update(refreshed)
        changed = True
    if "soul" not in persona or not persona.get("soul"):
        persona["soul"] = write_soul(persona, store)
        changed = True
    else:
        path = ROOT / persona["soul"]["path"]
        if not path.exists():
            persona["soul"] = write_soul(persona, store)
            changed = True
    if changed:
        persona["soul"] = write_soul(persona, store)
        persona["updated_at"] = utc_now_iso()
        (store or Store()).upsert_persona(persona, reason="ensure runtime fields")
    return persona


def _profile_to_persona_dict(
    description: str,
    profile: dict[str, Any],
    segment_hint: str | None,
    evidence: str | None,
    now: str,
    persona_id: str | None = None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    display_name = profile["display_name"]
    return Persona(
        id=persona_id or stable_id("persona", description, segment_hint or ""),
        slug=previous.get("slug") if previous else slugify(display_name),
        display_name=display_name,
        source_description=description,
        provenance={
            "source_description": "user",
            "segment_hint": "user" if segment_hint else "not_provided",
            "profile_fields": "llm_derived_from_source_description",
            "evidence": "attached" if evidence else "none",
            "synthetic_notice": "This profile is simulated and must be validated against real customer evidence.",
        },
        identity_traits=profile["identity_traits"],
        segment=profile["segment"],
        demographics=profile["demographics"],
        role=profile["role"],
        company_context=profile["company_context"],
        goals=profile["goals"],
        constraints=profile["constraints"],
        tool_ids=profile["tool_ids"],
        tools=profile["tools"],
        relationships=profile["relationships"],
        personality=profile["personality"],
        pain_points=profile["pain_points"],
        success_criteria=profile["success_criteria"],
        avatar=previous.get("avatar") if previous else None,
        soul=previous.get("soul") if previous else None,
        created_at=previous.get("created_at") if previous else now,
        updated_at=now,
    ).to_dict()


def create_persona(
    description: str,
    segment_hint: str | None = None,
    evidence: str | None = None,
    generate_avatar: bool = False,
    store: Store | None = None,
) -> dict[str, Any]:
    store = store or Store()
    now = utc_now_iso()
    profile = generate_profile_with_llm(description, segment_hint, evidence)
    persona = _profile_to_persona_dict(description, profile, segment_hint, evidence, now)
    persona["soul"] = write_soul(persona, store)
    store.upsert_persona(persona, reason="create_persona")
    if evidence:
        attach_evidence(persona["id"], "user_note", evidence, "Initial persona evidence", store)
    if generate_avatar:
        from .avatar import generate_persona_avatar

        avatar = generate_persona_avatar(persona["id"], store=store)
        persona["avatar"] = avatar
        persona["updated_at"] = utc_now_iso()
        store.upsert_persona(persona, reason="generated avatar")
    return persona


def refresh_persona_from_source(persona_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    previous = store.get_persona(persona_id)
    if not previous:
        raise KeyError(f"Unknown persona: {persona_id}")
    evidence = None
    segment_hint = previous.get("segment", {}).get("customer_type")
    profile = generate_profile_with_llm(previous["source_description"], segment_hint, evidence)
    persona = _profile_to_persona_dict(
        previous["source_description"],
        profile,
        segment_hint,
        evidence,
        utc_now_iso(),
        persona_id=previous["id"],
        previous=previous,
    )
    persona["soul"] = write_soul(persona, store)
    store.upsert_persona(persona, reason="refresh persona from source with LLM")
    return persona


def bulk_create_personas(
    descriptions: list[str],
    segment_strategy: str | None = None,
    generate_avatars: bool = False,
    store: Store | None = None,
) -> list[dict[str, Any]]:
    store = store or Store()
    return [
        create_persona(d.strip(), segment_strategy, generate_avatar=generate_avatars, store=store)
        for d in descriptions
        if d.strip()
    ]


def get_persona(persona_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    persona = ensure_persona_runtime_fields(persona, store)
    return {
        "persona": persona,
        "calendar_events": store.list_calendar_events(persona["id"])[-10:],
        "experience_events": store.list_experience_events(persona["id"])[-20:],
        "daily_summaries": store.list_daily_summaries(persona["id"])[-10:],
        "pain_points": store.list_pain_points(persona["id"]),
        "reflections": store.list_reflections(persona["id"])[-5:],
    }


def list_personas(filters: dict[str, Any] | None = None, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    personas = [ensure_persona_runtime_fields(p, store) for p in store.list_personas()]
    if not filters:
        return personas
    out = []
    needle = " ".join(str(v).lower() for v in filters.values() if v)
    for p in personas:
        blob = json.dumps(p, ensure_ascii=False).lower()
        if needle in blob:
            out.append(p)
    return out


def clear_simulations(store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    deleted = store.clear_simulation_state()
    refreshed: list[str] = []
    for persona in store.list_personas():
        persona = ensure_persona_runtime_fields(persona, store)
        persona["soul"] = write_soul(persona, store)
        persona["updated_at"] = utc_now_iso()
        store.upsert_persona(persona, reason="clear simulations regenerated SOUL.md")
        refreshed.append(persona["id"])
    return {
        "deleted": deleted,
        "personas_refreshed": refreshed,
        "kept": ["personas", "avatars", "evidence", "audit_log"],
    }


def purge_runtime_data(remove_files: bool = True, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    deleted = store.purge_runtime_state()
    removed_files: list[str] = []
    if remove_files:
        for root in [ROOT / "data" / "avatars", ROOT / "data" / "personas", ROOT / "personas"]:
            if root.exists():
                for path in sorted(root.rglob("*"), reverse=True):
                    if path.is_file():
                        path.unlink()
                        removed_files.append(str(path.relative_to(ROOT)))
                    elif path.is_dir():
                        try:
                            path.rmdir()
                        except OSError:
                            pass
                try:
                    root.rmdir()
                except OSError:
                    pass
    return {
        "deleted": deleted,
        "removed_files": removed_files,
        "kept": ["empty database schema", ".env", ".env.example"],
    }


def update_persona(persona_id: str, patch: dict[str, Any], reason: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(persona.get(key), dict):
            persona[key].update(value)
        else:
            persona[key] = value
    persona["updated_at"] = utc_now_iso()
    persona["soul"] = write_soul(persona, store)
    store.upsert_persona(persona, reason=reason)
    return persona


def get_persona_soul(persona_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    persona = ensure_persona_runtime_fields(persona, store)
    path = ROOT / persona["soul"]["path"]
    if not path.exists():
        persona["soul"] = write_soul(persona, store)
        store.upsert_persona(persona, reason="recreated SOUL.md")
        path = ROOT / persona["soul"]["path"]
    return {"persona_id": persona["id"], "path": persona["soul"]["path"], "content": path.read_text(encoding="utf-8")}


def prepare_persona_agent_context(
    persona_id: str,
    task: str | None = None,
    recent_events: int = 8,
    store: Store | None = None,
) -> dict[str, Any]:
    """Build the context packet a subagent must receive to act as a persona.

    This is the MCP workflow guarantee: persona-facing agents do not infer from
    the visible UI. They receive the durable SOUL.md content, current state, and
    recent lived events from the server.
    """
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    persona = ensure_persona_runtime_fields(persona, store)
    soul = get_persona_soul(persona["id"], store)
    state = get_current_state(persona["id"], store=store)
    events = store.list_experience_events(persona["id"])[-max(0, recent_events):]
    event_lines = [
        f"- {e['timestamp']} [{e['event_type']} / {e.get('collaboration_mode', 'unknown')}]: "
        f"{e.get('what_happened', e['summary'])} "
        f"Actions: {', '.join(e.get('actions_done', []))}. "
        f"Open loops: {', '.join(e.get('open_loops', [])) or 'none'}"
        for e in events
    ]

    # --- Memory grounding (spec §5.2/§5.7): the persona can draw on its own
    # project history ON DEMAND, not narrate it constantly. Recall is keyed to
    # the actual task/question so only relevant past surfaces. ---
    active_projects = memory_mod.list_active_projects(store, persona["id"])
    open_threads = store.list_threads(persona["id"], "open")
    recall_hits = memory_mod.recall(store, persona["id"], task, k=6)["hits"] if task and task.strip() else []
    projects_block = "\n".join(
        f"- {p['name']} — Status: {p.get('status') or 'unbekannt'} (offene Fäden: {p['open_loops']})"
        for p in active_projects[:10]
    ) or "- (keine erfassten Projekte)"
    threads_block = "\n".join(f"- {t['text']}" for t in open_threads[:10]) or "- (keine offenen Fäden)"
    recall_block = "\n".join(
        f"- [{h['obj_type']}] {h['when'] or ''}: {h['text']}" for h in recall_hits
    ) or "- (nichts spezifisch Relevantes gefunden)"

    agent_context = f"""# Persona Subagent Context

You must act from the perspective of this synthetic customer persona.

## Required Source
The following SOUL.md has been loaded from `{soul['path']}`. Treat it as the
authoritative persona identity and simulation rules.

---

{soul['content']}

---

## Current State
{json.dumps(state, indent=2, ensure_ascii=False)}

## Recent Lived Events
{chr(10).join(event_lines) if event_lines else '- No simulated events yet.'}

## Active Projects (memory)
{projects_block}

## Open Loops (memory)
{threads_block}

## Relevant Memory (recalled for this task — background, use only if it fits)
{recall_block}

## Task
{task or 'No task supplied. Use this context for persona-grounded reasoning.'}

## Operating Rules
- Stay grounded in SOUL.md, recent events, and the persona's project memory.
- Speak from the persona's lived work context, not as a generic consultant.
- Memory is background: refer to past projects/loops only when the question
  genuinely calls for it — do not recite memories unprompted.
- When uncertain, say what is inferred or synthetic.
- Cite concrete calendar moments, tools, people, projects, and open loops when relevant.
"""
    return {
        "persona_id": persona["id"],
        "display_name": persona["display_name"],
        "soul_loaded": True,
        "soul_path": soul["path"],
        "current_state": state,
        "recent_event_ids": [e["id"] for e in events],
        "active_projects": active_projects,
        "open_threads": [t["id"] for t in open_threads],
        "recall_hits": recall_hits,
        "agent_context": agent_context,
    }


def _parse_date(value: str | None) -> date:
    if value:
        return date.fromisoformat(value)
    return date.today()


def _event_time(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime.combine(day, time(hour, minute))


def _make_rng(seed: str | None, *parts: str) -> random.Random:
    base = seed or "|".join(parts)
    return random.Random(int(hashlib.sha256(base.encode()).hexdigest(), 16))


def simulate_day(
    persona_id: str,
    date_value: str | None = None,
    timezone: str | None = None,
    seed: str | None = None,
    constraints: dict[str, Any] | None = None,
    store: Store | None = None,
) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    persona = ensure_persona_runtime_fields(persona, store)
    day = _parse_date(date_value)
    rng = _make_rng(seed, persona["id"], day.isoformat())
    now = utc_now_iso()
    tz = timezone or "Europe/Berlin"
    work_start = constraints.get("workday_start", 8) if constraints else 8
    soul = get_persona_soul(persona["id"], store)
    recent_events = store.list_experience_events(persona["id"])[-12:]
    recent_summaries = store.list_daily_summaries(persona["id"])[-5:]
    plan_frame = {
        "persona_name": persona["display_name"],
        "persona_id": persona["id"],
        "date": day.isoformat(),
        "timezone": tz,
        "workday_start_hour": int(work_start),
        "soul_path": soul["path"],
        "soul": soul["content"],
        "allowed_tools": persona["tools"],
        "allowed_tool_ids": persona.get("tool_ids", []),
        "allowed_pain_points": persona["pain_points"],
        "recent_events": [
            {
                "timestamp": e["timestamp"],
                "event_type": e["event_type"],
                "task": e["task"],
                "what_happened": e.get("what_happened"),
                "open_loops": e.get("open_loops", []),
            }
            for e in recent_events
        ],
        "recent_summaries": recent_summaries,
        "constraints": constraints or {},
        "seed_hint": seed or stable_id("day-plan", persona["id"], day.isoformat()),
    }
    # Plan/memory-aware: surface the covering plan, active projects, open threads,
    # relevant recalled memory and the world backdrop so the day knits into the arc.
    plan_frame["memory"] = _day_memory_context(store, persona, day.isoformat())
    day_plan = generate_day_plan_with_llm(plan_frame)

    calendar: list[dict[str, Any]] = []
    experience: list[dict[str, Any]] = []
    current = _event_time(day, int(work_start), rng.choice([0, 5, 10, 15, 20, 25, 35, 40, 45, 50]))
    blocks = day_plan["blocks"]
    open_loops: list[str] = []
    completed: list[str] = []
    blockers: list[str] = []
    day_pains: list[str] = []
    for idx, block in enumerate(blocks):
        title = block["title"]
        minutes = block["duration_minutes"]
        kind = block["event_type"]
        gap = rng.choice([5, 10, 15])
        start = current + timedelta(minutes=gap)
        end = start + timedelta(minutes=minutes)
        current = end
        participants = block.get("participants", [])
        tool = block["tool"]
        pain = rng.choice(persona["pain_points"])
        prior_events = store.list_experience_events(persona["id"])[-5:]
        frame = {
            "persona_name": persona["display_name"],
            "persona_id": persona["id"],
            "soul_path": soul["path"],
            "soul": soul["content"],
            "date": day.isoformat(),
            "start": start.isoformat(timespec="minutes"),
            "end": end.isoformat(timespec="minutes"),
            "title": title,
            "event_type": kind,
            "collaboration_mode": {
                "meeting": "meeting",
                "focus": "working alone",
                "interruption": "interruption with another stakeholder",
                "admin": "working alone",
            }.get(kind, "working alone"),
            "participants": participants,
            "tool": tool,
            "why_it_happens": block.get("why_it_happens"),
            "allowed_tools": persona["tools"],
            "allowed_tool_ids": persona.get("tool_ids", []),
            "allowed_pain_points": persona["pain_points"],
            "seed_hint": seed or stable_id("seed", persona["id"], day.isoformat(), title),
            "recent_events": [
                {
                    "timestamp": e["timestamp"],
                    "event_type": e["event_type"],
                    "summary": e["summary"],
                    "open_loops": e.get("open_loops", []),
                }
                for e in prior_events
            ],
        }
        generated = generate_activity(frame)
        generated_pains = generated.get("pain_points", []) or [pain]
        day_pains.extend(generated_pains)
        outcome = "left an open follow-up" if generated.get("open_loops") else "resolved enough to move forward"
        if "open" in outcome:
            open_loops.append(title)
            blockers.extend(generated_pains)
        else:
            completed.append(title)
        cal = CalendarEvent(
            id=stable_id("cal", persona["id"], start.isoformat(), title),
            persona_id=persona["id"],
            start=start.isoformat(timespec="minutes"),
            end=end.isoformat(timespec="minutes"),
            title=title,
            participants=participants,
            location_or_tool=tool,
            intent=f"{persona['display_name']} needs to {title}.",
            outcome=outcome,
            created_at=now,
        ).to_dict()
        exp = ExperienceEvent(
            id=stable_id("evt", persona["id"], start.isoformat(), title),
            persona_id=persona["id"],
            timestamp=start.isoformat(timespec="minutes"),
            event_type=kind,
            summary=f"{persona['display_name']} {title} using {tool}; outcome: {outcome}.",
            task=title,
            tool=tool,
            participants=participants,
            collaboration_mode=frame["collaboration_mode"],
            what_happened=generated["what_happened"],
            conversation=generated["conversation"],
            key_quotes=generated["key_quotes"],
            actions_done=generated["actions_done"],
            artifacts_touched=generated["artifacts_touched"],
            persona_thought=generated["persona_thought"],
            decision=generated["decision"],
            open_loops=generated["open_loops"],
            impact={
                "mood": generated["mood"],
                "energy_delta": generated["energy_delta"],
                "timezone": tz,
                "generation_mode": generated.get("generation_mode", "llm"),
                "llm_error": generated.get("llm_error"),
            },
            pain_points=generated_pains,
            goal_refs=persona["goals"][:2],
            calendar_event_id=cal["id"],
            created_at=now,
        ).to_dict()
        calendar.append(cal)
        experience.append(exp)
        store.insert_calendar_event(cal)
        store.insert_experience_event(exp)

    summary = DailySummary(
        id=stable_id("day", persona["id"], day.isoformat()),
        persona_id=persona["id"],
        date=day.isoformat(),
        mood=day_plan.get("mood_forecast") or ("mixed" if blockers else "steady"),
        completed=completed,
        blockers=sorted(set(blockers)),
        open_loops=open_loops,
        pain_points=sorted(set(day_pains)),
        notable_memories=[e["summary"] for e in experience[-3:]],
        created_at=now,
    ).to_dict()
    store.upsert_daily_summary(summary)

    # Reflection/consolidation is no longer hardcoded. Periodic, evidence-backed
    # summaries are host-authored via brief_digest/put_digest (spec §4 Phase D,
    # §12.5). Day-level memory (entities, facts, threads) is built by
    # brief_consolidation/record_memory_deltas. Kept None here on purpose.
    reflection = None

    persona["soul"] = write_soul(persona, store)
    persona["updated_at"] = utc_now_iso()
    store.upsert_persona(persona, reason="simulation updated soul")

    for pain in sorted(set(day_pains)):
        pain_obs = PainPointObservation(
            id=stable_id("pain", persona["id"], pain),
            persona_id=persona["id"],
            issue=pain,
            severity=min(5, 2 + day_pains.count(pain)),
            frequency=sum(1 for e in store.list_experience_events(persona["id"]) if pain in e.get("pain_points", [])),
            evidence_event_ids=[e["id"] for e in experience if pain in e["pain_points"]],
            affected_workflow="daily coordination and project delivery",
            opportunity="Reduce manual reconciliation and make ownership visible at the moment of work.",
            created_at=now,
        ).to_dict()
        store.upsert_pain_point(pain_obs)

    store.commit()
    return SimulationResult(
        persona=persona,
        date=day.isoformat(),
        calendar_events=calendar,
        experience_events=experience,
        daily_summary=summary,
        reflection=reflection,
    ).to_dict()


def simulate_range(persona_id: str, start_date: str, end_date: str, cadence: str | None = None, seed: str | None = None, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    results = []
    day = start
    while day <= end:
        if cadence != "all-days" and day.weekday() >= 5:
            day += timedelta(days=1)
            continue
        results.append(simulate_day(persona_id, day.isoformat(), seed=seed, store=store))
        day += timedelta(days=1)
    return results


def continue_simulation(persona_id: str | None = None, days: int = 1, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    personas = [store.get_persona(persona_id)] if persona_id else store.list_personas()
    out = []
    for persona in [p for p in personas if p]:
        summaries = store.list_daily_summaries(persona["id"])
        if summaries:
            start = date.fromisoformat(summaries[-1]["date"]) + timedelta(days=1)
        else:
            start = date.today()
        added = 0
        day = start
        while added < days:
            if day.weekday() < 5:
                out.append(simulate_day(persona["id"], day.isoformat(), store=store))
                added += 1
            day += timedelta(days=1)
    return out


def get_current_state(persona_id: str, at_time: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    events = store.list_experience_events(persona["id"])
    summaries = store.list_daily_summaries(persona["id"])
    latest = events[-1] if events else None
    return {
        "persona_id": persona["id"],
        "display_name": persona["display_name"],
        "at_time": at_time or utc_now_iso(),
        "current_activity": latest["task"] if latest else "not simulated yet",
        "current_tool": latest["tool"] if latest else None,
        "collaboration_mode": latest.get("collaboration_mode") if latest else None,
        "mood": latest["impact"]["mood"] if latest else "unknown",
        "current_thought": latest.get("persona_thought") if latest else "unknown",
        "blocked_by": summaries[-1]["blockers"] if summaries else [],
        "likely_next": summaries[-1]["open_loops"][:3] if summaries else persona["goals"][:2],
        "synthetic_notice": "State is simulated unless backed by attached evidence.",
    }


def get_calendar(persona_id: str, date_value: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    day = _parse_date(date_value).isoformat() if date_value else None
    start = f"{day}T00:00" if day else None
    end = f"{day}T23:59" if day else None
    calendar = store.list_calendar_events(persona["id"], start, end)
    events = store.list_experience_events(persona["id"], start, end)
    event_by_calendar = {e.get("calendar_event_id"): e for e in events}
    blocks = []
    for cal in calendar:
        exp = event_by_calendar.get(cal["id"])
        blocks.append(
            {
                "calendar_event": cal,
                "activity": exp,
                "collaboration_mode": exp.get("collaboration_mode") if exp else None,
                "persona_thought": exp.get("persona_thought") if exp else None,
                "open_loops": exp.get("open_loops", []) if exp else [],
            }
        )
    return {"persona": persona, "date": day, "blocks": blocks}


def _period_bounds(anchor: date, view: str) -> tuple[date, date]:
    if view == "week":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if view == "month":
        start = anchor.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, next_month - timedelta(days=1)
    if view == "year":
        return anchor.replace(month=1, day=1), anchor.replace(month=12, day=31)
    return anchor, anchor


def get_calendar_period(persona_id: str, date_value: str | None = None, view: str = "day", store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    anchor = _parse_date(date_value)
    view = view if view in {"day", "week", "month", "year"} else "day"
    start_day, end_day = _period_bounds(anchor, view)
    start = f"{start_day.isoformat()}T00:00"
    end = f"{end_day.isoformat()}T23:59"
    events = store.list_experience_events(persona["id"], start, end)
    days: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        days.setdefault(event["timestamp"][:10], []).append(event)
    summaries = store.list_daily_summaries(persona["id"], start_day.isoformat(), end_day.isoformat())
    return {
        "persona": persona,
        "view": view,
        "anchor_date": anchor.isoformat(),
        "period_start": start_day.isoformat(),
        "period_end": end_day.isoformat(),
        "days": days,
        "daily_summaries": summaries,
    }


def get_activity(activity_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    event = store.get_experience_event(activity_id)
    if not event:
        raise KeyError(f"Unknown activity: {activity_id}")
    persona = store.get_persona(event["persona_id"])
    return {"persona": persona, "activity": event}


def summarize_persona_period(persona_id: str, start_date: str | None = None, end_date: str | None = None, lens: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    events = store.list_experience_events(persona["id"], start_date, end_date)
    summaries = store.list_daily_summaries(persona["id"], start_date, end_date)
    pains: dict[str, int] = {}
    for e in events:
        for pain in e.get("pain_points", []):
            pains[pain] = pains.get(pain, 0) + 1
    return {
        "persona": {"id": persona["id"], "display_name": persona["display_name"], "slug": persona["slug"]},
        "period": {"start": start_date, "end": end_date, "lens": lens or "work experience"},
        "days": len(summaries),
        "events": len(events),
        "top_pain_points": sorted(pains.items(), key=lambda x: x[1], reverse=True),
        "completed": [item for s in summaries for item in s["completed"]][:20],
        "blockers": sorted(set(item for s in summaries for item in s["blockers"])),
        "open_loops": [item for s in summaries for item in s["open_loops"]][-10:],
    }


def extract_pain_points(persona_id: str, start_date: str | None = None, end_date: str | None = None, store: Store | None = None) -> list[dict[str, Any]]:
    summary = summarize_persona_period(persona_id, start_date, end_date, store=store)
    store = store or Store()
    persona = store.get_persona(persona_id)
    assert persona is not None
    observations = []
    for issue, frequency in summary["top_pain_points"]:
        obs = PainPointObservation(
            id=stable_id("pain", persona["id"], issue),
            persona_id=persona["id"],
            issue=issue,
            severity=min(5, max(1, frequency)),
            frequency=frequency,
            evidence_event_ids=[],
            affected_workflow="workday execution",
            opportunity="Investigate whether the real workflow can be changed without adding hidden work.",
            created_at=utc_now_iso(),
        ).to_dict()
        store.upsert_pain_point(obs)
        observations.append(obs)
    store.commit()
    return observations


def select_council(prompt: str, filters: dict[str, Any] | None = None, count: int = 3, disagreement_goal: str | None = None, store: Store | None = None) -> dict[str, Any]:
    personas = list_personas(filters, store)
    if not personas:
        return {"persona_ids": [], "reasoning": "No profiles available."}
    candidates = [
        {
            "persona_id": p["id"],
            "display_name": p["display_name"],
            "source_description": p["source_description"],
            "role": p.get("role", {}),
            "company_context": p.get("company_context", {}),
            "goals": p.get("goals", []),
            "constraints": p.get("constraints", []),
            "tools": p.get("tools", []),
            "relationships": p.get("relationships", []),
            "pain_points": p.get("pain_points", []),
            "success_criteria": p.get("success_criteria", []),
        }
        for p in personas
    ]
    return generate_council_selection_with_llm(
        {
            "prompt": prompt,
            "filters": filters,
            "count": min(max(1, count), len(candidates)),
            "disagreement_goal": disagreement_goal,
            "candidate_personas": candidates,
        }
    )


def run_council(
    prompt: str,
    persona_ids: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    rounds: int = 3,
    context: str | None = None,
    store: Store | None = None,
) -> dict[str, Any]:
    store = store or Store()
    if not persona_ids:
        selection = select_council(prompt, filters, count=3, store=store)
        persona_ids = selection["persona_ids"]
        reasoning = selection["reasoning"]
    else:
        reasoning = "Personas were explicitly provided."
    personas = [store.get_persona(pid) for pid in persona_ids]
    personas = [p for p in personas if p]
    turns: list[dict[str, Any]] = []
    contexts: list[dict[str, Any]] = []
    for round_no in range(rounds):
        for p in personas:
            ctx = prepare_persona_agent_context(
                p["id"],
                f"Council prompt: {prompt}\nExternal context: {context or 'none'}",
                store=store,
            )
            if round_no == 0:
                contexts.append(
                    {
                        "persona_id": p["id"],
                        "display_name": p["display_name"],
                        "soul_path": ctx["soul_path"],
                        "current_state": ctx["current_state"],
                        "recent_event_ids": ctx["recent_event_ids"],
                    }
                )
            generated = generate_council_turn_with_llm(
                {
                    "prompt": prompt,
                    "external_context": context,
                    "round": round_no + 1,
                    "speaker": p["display_name"],
                    "persona_agent_context": ctx["agent_context"],
                    "previous_turns": turns[-8:],
                }
            )
            turns.append(
                {
                    "round": round_no + 1,
                    "speaker": p["display_name"],
                    "persona_id": p["id"],
                    "content": generated["content"],
                    "stance": generated["stance"],
                    "questions_or_pushback": generated["questions_or_pushback"],
                    "memory_refs": [ctx["soul_path"], *generated["memory_refs"]],
                    "soul_loaded": ctx["soul_loaded"],
                    "soul_path": ctx["soul_path"],
                }
            )
    synthesis = generate_council_synthesis_with_llm(
        {
            "prompt": prompt,
            "external_context": context,
            "selection_reason": reasoning,
            "personas": contexts,
            "turns": turns,
        }
    )
    session = CouncilSession(
        id=stable_id("council", prompt, utc_now_iso()),
        prompt=prompt,
        persona_ids=[p["id"] for p in personas],
        selection_reason=reasoning,
        turns=turns,
        proposal=synthesis["proposal"],
        votes=synthesis["votes"],
        summary=synthesis["summary"],
        exec_summary=synthesis.get("exec_summary", ""),
        created_at=utc_now_iso(),
    ).to_dict()
    store.insert_council_session(session)
    return session


def ask_persona(persona_id: str, question: str, context: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    agent_ctx = prepare_persona_agent_context(persona_id, question, store=store)
    generated = generate_persona_answer_with_llm(
        {
            "question": question,
            "external_context": context,
            "persona_agent_context": agent_ctx["agent_context"],
        }
    )
    return {
        "persona_id": persona["id"],
        "display_name": persona["display_name"],
        "question": question,
        "answer": generated["answer"],
        "referenced_moments": generated["referenced_moments"],
        "uncertainties": generated["uncertainties"],
        "context_used": context,
        "soul_loaded": agent_ctx["soul_loaded"],
        "soul_path": agent_ctx["soul_path"],
        "recent_event_ids": agent_ctx["recent_event_ids"],
        "synthetic_notice": "This is a simulated interview answer.",
    }


def compare_personas(prompt: str, persona_ids: list[str], output_format: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    rows = []
    for pid in persona_ids:
        persona = store.get_persona(pid)
        if persona:
            answer = ask_persona(persona["id"], prompt, store=store)
            rows.append(
                {
                    "persona_id": persona["id"],
                    "display_name": persona["display_name"],
                    "comment": answer["answer"],
                    "referenced_moments": answer["referenced_moments"],
                    "uncertainties": answer["uncertainties"],
                    "soul_loaded": True,
                    "soul_path": get_persona_soul(persona["id"], store)["path"],
                }
            )
    return {"prompt": prompt, "format": output_format or "json", "comparisons": rows}


def attach_evidence(persona_id: str, source_type: str, content_or_path: str, notes: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    evidence = Evidence(
        id=stable_id("evidence", persona["id"], source_type, content_or_path[:120]),
        persona_id=persona["id"],
        source_type=source_type,
        content_or_path=content_or_path,
        notes=notes,
        created_at=utc_now_iso(),
    ).to_dict()
    store.insert_evidence(evidence)
    return evidence


def export_persona(persona_id: str, format: str = "json", store: Store | None = None) -> str:
    data = get_persona(persona_id, store)
    if format == "md":
        p = data["persona"]
        return f"# {p['display_name']}\n\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)}\n```\n"
    return json.dumps(data, indent=2, ensure_ascii=False)


def export_logs(persona_id: str, start_date: str | None = None, end_date: str | None = None, format: str = "json", store: Store | None = None) -> str:
    store = store or Store()
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    events = store.list_experience_events(persona["id"], start_date, end_date)
    if format == "csv":
        import io

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["timestamp", "event_type", "summary", "task", "tool"])
        writer.writeheader()
        for e in events:
            writer.writerow({k: e.get(k, "") for k in writer.fieldnames or []})
        return buf.getvalue()
    if format == "md":
        lines = [f"# Logs for {persona['display_name']}", ""]
        for e in events:
            lines.append(f"- `{e['timestamp']}` **{e['event_type']}**: {e['summary']}")
            if e.get("persona_thought"):
                lines.append(f"  - Thought: {e['persona_thought']}")
            if e.get("key_quotes"):
                lines.append(f"  - Quotes: {' | '.join(e['key_quotes'])}")
            if e.get("actions_done"):
                lines.append(f"  - Actions: {'; '.join(e['actions_done'])}")
        return "\n".join(lines) + "\n"
    return json.dumps(events, indent=2, ensure_ascii=False)


def export_council_session(session_id: str, format: str = "json", store: Store | None = None) -> str:
    store = store or Store()
    session = store.get_council_session(session_id)
    if not session:
        raise KeyError(f"Unknown council session: {session_id}")
    if format == "md":
        lines = [f"# Council Session", "", f"**Prompt:** {session['prompt']}", "", "## Turns"]
        for t in session["turns"]:
            lines.append(f"- **{t['speaker']}**: {t['content']}")
        lines.extend(["", "## Proposal", session["proposal"], "", "## Votes"])
        for v in session["votes"]:
            lines.append(f"- **{v['speaker']}**: {v['vote']} - {v['reason']}")
        lines.extend(["", "## Summary", session["summary"]])
        return "\n".join(lines) + "\n"
    return json.dumps(session, indent=2, ensure_ascii=False)


def write_export(content: str, path: str | Path) -> str:
    out = Path(path)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    return str(out)


# ===================================================================== #
# Memory & multi-resolution orchestration                               #
# spec/memory-and-simulation-architecture.md §3, §4, §4A, §12.          #
# Pattern: brief_* gathers context + builds the host prompt; the host   #
# LLM authors JSON; record_*/put_* validate and persist. No server text.#
# ===================================================================== #

_ANTI_STEERING = (
    "Do not steer toward BIM, AI, automation, or any product direction unless the "
    "persona's source/evidence supports it. Prefer ordinary work, skepticism, and stalls."
)


def memory_path(persona: dict[str, Any]) -> Path:
    return persona_dir(persona) / "MEMORY.md"


def _scope_bounds(anchor: date, scope: str) -> tuple[date, date]:
    if scope == "week":
        start = anchor - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=6)
    if scope == "month":
        start = anchor.replace(day=1)
        nxt = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        return start, nxt - timedelta(days=1)
    if scope == "quarter":
        q = (anchor.month - 1) // 3
        start = date(anchor.year, q * 3 + 1, 1)
        end_month_first = (date(anchor.year, q * 3 + 3, 28) + timedelta(days=4)).replace(day=1)
        return start, end_month_first - timedelta(days=1)
    if scope == "year":
        return anchor.replace(month=1, day=1), anchor.replace(month=12, day=31)
    return anchor, anchor


def effective_persona(persona: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    """Apply persona_revisions (slow, evidence-backed drift) as an overlay view.

    Does NOT mutate the stored base persona — the source identity is preserved;
    this returns the *grown* identity used for SOUL rendering and simulation.
    """
    store = store or Store()
    revisions = store.list_persona_revisions(persona["id"])
    if not revisions:
        return persona
    p = json.loads(json.dumps(persona))
    for rev in revisions:
        ch = rev.get("changes", {})
        for field, add_key, rm_key in [
            ("goals", "goals_add", "goals_remove"),
            ("constraints", "constraints_add", "constraints_remove"),
            ("pain_points", "pains_add", "pains_remove"),
            ("tools", "tools_add", "tools_remove"),
        ]:
            cur = list(p.get(field, []))
            for add in ch.get(add_key, []):
                if add not in cur:
                    cur.append(add)
            rm = set(ch.get(rm_key, []))
            p[field] = [x for x in cur if x not in rm]
        if "tools_add" in ch or "tools_remove" in ch:
            try:
                p["tool_ids"] = normalized_tool_ids(" ".join(p.get("tools", []))) or p.get("tool_ids", [])
            except Exception:  # noqa: BLE001
                pass
        if isinstance(ch.get("personality"), dict):
            p.setdefault("personality", {}).update(ch["personality"])
    return p


def _day_memory_context(store: Store, persona: dict[str, Any], day_iso: str) -> dict[str, Any]:
    pid = persona["id"]
    active = memory_mod.list_active_projects(store, pid)
    threads = store.list_threads(pid, "open")
    world = store.list_world_context(as_of=day_iso)
    seed = " ".join((persona.get("goals", [])[:2] + persona.get("pain_points", [])[:2]))
    hits = memory_mod.recall(store, pid, seed, as_of=day_iso, k=6)["hits"] if seed.strip() else []
    return {
        "covering_period_plan": store.find_covering_plan(pid, "month", day_iso),
        "covering_week_plan": store.find_covering_plan(pid, "week", day_iso),
        "day_plan": store.get_plan(pid, "day", day_iso),
        "active_projects": active,
        "open_threads": [{"id": t["id"], "text": t["text"], "entity_id": t.get("entity_id")} for t in threads],
        "world_context": [{"category": w["category"], "fact": w["fact"]} for w in world],
        "recall": hits,
    }


def _require_persona(store: Store, persona_id: str) -> dict[str, Any]:
    persona = store.get_persona(persona_id)
    if not persona:
        raise KeyError(f"Unknown persona: {persona_id}")
    return persona


# ---- Consolidation (Phase C) ---------------------------------------------

def brief_consolidation(persona_id: str, date_value: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    day = _parse_date(date_value).isoformat()
    events = store.list_experience_events(persona["id"], f"{day}T00:00", f"{day}T23:59")
    activities = [{
        "title": e["task"], "event_type": e["event_type"], "tool": e.get("tool"),
        "participants": e.get("participants", []), "what_happened": e.get("what_happened"),
        "decision": e.get("decision"), "open_loops": e.get("open_loops", []),
    } for e in events]
    frame = {
        "persona_name": persona["display_name"], "persona_id": persona["id"], "date": day,
        "activities": activities,
        "known_entities": [{"name": en["name"], "kind": en["kind"], "status": en.get("status")}
                           for en in store.list_entities(persona["id"])],
        "open_threads": [t["text"] for t in store.list_threads(persona["id"], "open")],
        "anti_steering": _ANTI_STEERING,
    }
    return {"persona_id": persona["id"], "date": day, "schema": "memory_deltas",
            "instructions": build_consolidation_prompt(frame), "frame": frame,
            "activity_count": len(activities)}


def record_memory_deltas(persona_id: str, date_value: str, deltas: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    pid = persona["id"]
    day = _parse_date(date_value).isoformat()
    now = utc_now_iso()
    payload = validate_memory_deltas_payload(deltas)
    mention_to_id: dict[str, str] = {}
    created = updated = 0

    def _register(eid: str, *mentions: str) -> None:
        for m in mentions:
            if m:
                mention_to_id[memory_mod.normalize_name(m)] = eid

    for e in payload["entities"]:
        existing = memory_mod.resolve_entity(store, pid, e["mention"], e["kind"])
        if existing:
            existing["status"] = e["status"] or existing.get("status")
            existing["aliases"] = sorted(set(existing.get("aliases", []) + e["aliases"]))
            existing["last_seen"] = day
            existing["updated_at"] = now
            store.upsert_entity(existing)
            _register(existing["id"], e["mention"], existing["name"], *e["aliases"])
            updated += 1
        else:
            eid = stable_id("ent", pid, e["kind"], memory_mod.normalize_name(e["mention"]))
            store.upsert_entity({
                "id": eid, "persona_id": pid, "kind": e["kind"], "name": e["mention"],
                "status": e["status"], "aliases": e["aliases"], "first_seen": day,
                "last_seen": day, "created_at": now, "updated_at": now,
            })
            _register(eid, e["mention"], *e["aliases"])
            created += 1

    def _eid(mention: str, kind: str = "topic") -> str:
        key = memory_mod.normalize_name(mention)
        if key in mention_to_id:
            return mention_to_id[key]
        existing = memory_mod.resolve_entity(store, pid, mention, None)
        if existing:
            _register(existing["id"], mention)
            return existing["id"]
        eid = stable_id("ent", pid, kind, key)
        store.upsert_entity({"id": eid, "persona_id": pid, "kind": kind, "name": mention, "status": None,
                             "aliases": [], "first_seen": day, "last_seen": day, "created_at": now, "updated_at": now})
        _register(eid, mention)
        return eid

    facts_written = 0
    for f in payload["facts"]:
        eid = _eid(f["entity"], "project")
        valid_from = f["valid_from"] or day
        if f["invalidates"]:
            inv = memory_mod.normalize_name(f["invalidates"])
            for old in store.list_entity_facts(eid, valid_only=True):
                on = memory_mod.normalize_name(old["fact"])
                if on == inv or inv in on or on in inv:
                    store.invalidate_entity_fact(old["id"], valid_from)
        if f["status"]:
            ns = memory_mod.normalize_name(f["status"])
            for old in store.list_entity_facts(eid, valid_only=True):
                if old.get("status") and memory_mod.normalize_name(old["status"]) != ns:
                    store.invalidate_entity_fact(old["id"], valid_from)
        fid = stable_id("fact", eid, f["fact"], valid_from)
        store.insert_entity_fact({
            "id": fid, "persona_id": pid, "entity_id": eid, "fact": f["fact"], "status": f["status"],
            "t_valid": valid_from, "t_invalid": f["valid_to"], "importance": f["importance"],
            "source_event_id": None, "created_at": now,
        })
        facts_written += 1
        if f["status"]:
            ent = store.get_entity(eid)
            ent["status"] = f["status"]
            ent["last_seen"] = day
            ent["updated_at"] = now
            store.upsert_entity(ent)

    threads_opened = threads_resolved = 0
    for t in payload["threads"]:
        teid = _eid(t["entity"]) if t["entity"] else None
        if t["action"] == "resolve":
            target = None
            ref = memory_mod.normalize_name(t["ref"] or t["text"])
            for th in store.list_threads(pid, "open"):
                tn = memory_mod.normalize_name(th["text"])
                if tn == ref or ref in tn or tn in ref:
                    target = th
                    break
            if target:
                target.update({"status": "resolved", "closed_on": day, "updated_at": now})
                store.upsert_thread(target)
                threads_resolved += 1
                continue
        tid = stable_id("thread", pid, t["text"])
        store.upsert_thread({
            "id": tid, "persona_id": pid, "entity_id": teid, "text": t["text"],
            "status": "resolved" if t["action"] == "resolve" else "open",
            "opened_on": day, "closed_on": day if t["action"] == "resolve" else None,
            "created_at": now, "updated_at": now,
        })
        threads_opened += 1

    events = store.list_experience_events(pid, f"{day}T00:00", f"{day}T23:59")
    by_title = {memory_mod.normalize_name(e["task"]): e for e in events}
    links = 0
    for link in payload["event_links"]:
        ev = by_title.get(memory_mod.normalize_name(link["activity_title"]))
        if not ev:
            continue
        for m in link["entities"]:
            store.link_event_entity(ev["id"], _eid(m), pid)
            links += 1
    store.commit()
    emb = memory_mod.backfill_persona_embeddings(store, pid)
    return {"persona_id": pid, "date": day, "entities_created": created, "entities_updated": updated,
            "facts": facts_written, "threads_opened": threads_opened, "threads_resolved": threads_resolved,
            "event_links": links, "embeddings": emb}


def consolidate_day(persona_id: str, date_value: str, deltas: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    """Convenience: record host-authored deltas for a day (alias of record_memory_deltas)."""
    return record_memory_deltas(persona_id, date_value, deltas, store)


# ---- Planning (Phase A, multi-resolution §4A) ----------------------------

def brief_day(persona_id: str, date_value: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    day = _parse_date(date_value).isoformat()
    frame = {"persona_name": persona["display_name"], "persona_id": persona["id"], "scope": "day",
             "date": day, "soul": get_persona_soul(persona["id"], store)["content"],
             "memory": _day_memory_context(store, persona, day), "anti_steering": _ANTI_STEERING}
    return {"persona_id": persona["id"], "date": day, "scope": "day", "schema": "plan",
            "instructions": build_plan_prompt(frame), "frame": frame}


def put_day_plan(persona_id: str, date_value: str, plan: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    day = _parse_date(date_value).isoformat()
    payload = validate_plan_payload(plan, "day")
    rec = {"id": stable_id("plan", persona["id"], "day", day), "persona_id": persona["id"],
           "scope": "day", "period_start": day, "period_end": day, "created_at": utc_now_iso(), **payload}
    store.upsert_plan(rec)
    store.commit()
    return rec


def get_day_plan(persona_id: str, date_value: str, store: Store | None = None) -> dict[str, Any] | None:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return store.get_plan(persona["id"], "day", _parse_date(date_value).isoformat())


def brief_period(persona_id: str, scope: str, date_value: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    scope = scope if scope in {"week", "month", "quarter", "year"} else "month"
    anchor = _parse_date(date_value)
    start, end = _scope_bounds(anchor, scope)
    candidate_days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            candidate_days.append(d.isoformat())
        d += timedelta(days=1)
    from .config import default_sample_days_per_month
    frame = {
        "persona_name": persona["display_name"], "persona_id": persona["id"], "scope": scope,
        "period_start": start.isoformat(), "period_end": end.isoformat(),
        "soul": get_persona_soul(persona["id"], store)["content"],
        "active_projects": memory_mod.list_active_projects(store, persona["id"]),
        "open_threads": [t["text"] for t in store.list_threads(persona["id"], "open")],
        "recent_digests": [d.get("text") for d in store.list_digests(persona["id"])[-4:]],
        "world_context": [{"category": w["category"], "fact": w["fact"]}
                          for w in store.list_world_context(as_of=end.isoformat())],
        "candidate_days": candidate_days,
        "suggested_sample_count": default_sample_days_per_month() if scope == "month" else max(2, len(candidate_days) // 10),
        "anti_steering": _ANTI_STEERING,
    }
    return {"persona_id": persona["id"], "scope": scope, "period_start": start.isoformat(),
            "period_end": end.isoformat(), "schema": "plan", "instructions": build_plan_prompt(frame), "frame": frame}


def put_period_plan(persona_id: str, scope: str, date_value: str, plan: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    scope = scope if scope in {"week", "month", "quarter", "year"} else "month"
    start, end = _scope_bounds(_parse_date(date_value), scope)
    payload = validate_plan_payload(plan, scope)
    rec = {"id": stable_id("plan", persona["id"], scope, start.isoformat()), "persona_id": persona["id"],
           "scope": scope, "period_start": start.isoformat(), "period_end": end.isoformat(),
           "created_at": utc_now_iso(), **payload}
    store.upsert_plan(rec)
    store.commit()
    return rec


def get_period_plan(persona_id: str, scope: str, date_value: str, store: Store | None = None) -> dict[str, Any] | None:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    start, _ = _scope_bounds(_parse_date(date_value), scope)
    return store.get_plan(persona["id"], scope, start.isoformat())


def list_period_plans(persona_id: str, scope: str | None = None, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return store.list_plans(persona["id"], scope)


# ---- Digests (Phase D, §12.6) --------------------------------------------

def brief_digest(persona_id: str, scope: str, date_value: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    scope = scope if scope in {"week", "month", "quarter", "year"} else "week"
    start, end = _scope_bounds(_parse_date(date_value), scope)
    summaries = store.list_daily_summaries(persona["id"], start.isoformat(), end.isoformat())
    frame = {
        "persona_name": persona["display_name"], "persona_id": persona["id"], "scope": scope,
        "period_start": start.isoformat(), "period_end": end.isoformat(),
        "daily_summaries": summaries,
        "active_projects": memory_mod.list_active_projects(store, persona["id"]),
        "valid_facts": [f["fact"] for f in store.list_persona_facts(persona["id"], valid_only=True)][:40],
        "open_threads": [t["text"] for t in store.list_threads(persona["id"], "open")],
        "anti_steering": _ANTI_STEERING,
    }
    return {"persona_id": persona["id"], "scope": scope, "period_start": start.isoformat(),
            "period_end": end.isoformat(), "schema": "digest",
            "instructions": build_digest_prompt(frame), "frame": frame}


def put_digest(persona_id: str, scope: str, date_value: str, digest: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    scope = scope if scope in {"week", "month", "quarter", "year"} else "week"
    start, end = _scope_bounds(_parse_date(date_value), scope)
    payload = validate_digest_payload(digest)
    rec = {"id": stable_id("digest", persona["id"], scope, start.isoformat()), "persona_id": persona["id"],
           "scope": scope, "period_start": start.isoformat(), "period_end": end.isoformat(),
           "created_at": utc_now_iso(), **payload}
    store.upsert_digest(rec)
    store.commit()
    memory_mod.upsert_object_embedding(store, "digest", rec["id"], persona["id"], payload["text"])
    store.commit()
    return rec


def list_digests(persona_id: str, scope: str | None = None, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return store.list_digests(persona["id"], scope)


# ---- World context (§12.3) -----------------------------------------------

def set_world_context(items: list[dict[str, Any]], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    now = utc_now_iso()
    written = 0
    for it in items or []:
        if not str(it.get("fact", "")).strip() or not str(it.get("category", "")).strip():
            continue
        valid_from = str(it.get("valid_from", "")).strip()[:10] or now[:10]
        rec = {
            "id": stable_id("world", it["category"], it["fact"], valid_from),
            "category": str(it["category"]).strip()[:80], "fact": str(it["fact"]).strip()[:400],
            "t_valid": valid_from, "t_invalid": (str(it["valid_to"]).strip()[:10] if it.get("valid_to") else None),
            "relevance_tags": [str(x).strip()[:60] for x in (it.get("relevance_tags") or [])][:8],
            "created_at": now,
        }
        store.insert_world_context(rec)
        written += 1
    store.commit()
    return {"written": written}


def get_world_context(as_of: str | None = None, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    return store.list_world_context(as_of=as_of)


# ---- Persona evolution (§12.2) -------------------------------------------

def brief_persona_revision(persona_id: str, date_value: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    eff = effective_persona(persona, store)
    as_of = _parse_date(date_value).isoformat()
    frame = {
        "persona_name": persona["display_name"], "persona_id": persona["id"], "as_of": as_of,
        "source_description": persona["source_description"],
        "current_goals": eff.get("goals"), "current_pains": eff.get("pain_points"),
        "current_tools": eff.get("tools"), "current_personality": eff.get("personality"),
        "recent_digests": [d.get("text") for d in store.list_digests(persona["id"])[-4:]],
        "valid_facts": [f["fact"] for f in store.list_persona_facts(persona["id"], valid_only=True)][:40],
        "anti_steering": _ANTI_STEERING,
    }
    return {"persona_id": persona["id"], "as_of": as_of, "schema": "persona_revision",
            "instructions": build_persona_revision_prompt(frame), "frame": frame}


def record_persona_revision(persona_id: str, revision: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    payload = validate_persona_revision_payload(revision)
    eff_on = payload["effective_on"] or utc_now_iso()[:10]
    rec = {"id": stable_id("rev", persona["id"], eff_on, payload["rationale"][:40]),
           "persona_id": persona["id"], "effective_on": eff_on,
           "rationale": payload["rationale"], "changes": payload["changes"], "created_at": utc_now_iso()}
    store.insert_persona_revision(rec)
    # re-render SOUL with the new effective identity
    persona["soul"] = write_soul(persona, store)
    persona["updated_at"] = utc_now_iso()
    store.upsert_persona(persona, reason="persona revision")
    store.commit()
    return rec


def list_persona_revisions(persona_id: str, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return store.list_persona_revisions(persona["id"])


# ---- Retrieval / inspection (§5.2, §5.6) ---------------------------------

def recall_memory(persona_id: str, query: str, as_of: str | None = None, k: int = 8, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return memory_mod.recall(store, persona["id"], query, as_of=as_of, k=k)


def list_active_projects(persona_id: str, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return memory_mod.list_active_projects(store, persona["id"])


def get_project(persona_id: str, entity_id: str, as_of: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return memory_mod.get_project_timeline(store, persona["id"], entity_id, as_of=as_of)


def get_state_at(persona_id: str, as_of: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return memory_mod.get_state_at(store, persona["id"], _parse_date(as_of).isoformat())


def get_timeline(persona_id: str, start: str | None = None, end: str | None = None, entity_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    pid = persona["id"]
    if entity_id:
        facts = store.list_entity_facts(entity_id)
    else:
        facts = store.list_persona_facts(pid)
    if start:
        facts = [f for f in facts if f["t_valid"][:10] >= start]
    if end:
        facts = [f for f in facts if f["t_valid"][:10] <= end]
    events = store.list_experience_events(pid, start, end)
    return {"persona_id": pid, "start": start, "end": end, "facts": facts,
            "events": [{"timestamp": e["timestamp"], "task": e["task"], "event_type": e["event_type"]} for e in events]}


def search_entities(persona_id: str, kind: str | None = None, name: str | None = None, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    ents = store.list_entities(persona["id"], kind)
    if name:
        n = memory_mod.normalize_name(name)
        ents = [e for e in ents if n in memory_mod.normalize_name(e["name"]) or n in memory_mod.normalize_name(" ".join(e.get("aliases", [])))]
    return ents


def get_open_loops(persona_id: str, status: str | None = "open", store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return store.list_threads(persona["id"], status)


def resolve_entity(persona_id: str, mention: str, kind: str | None = None, store: Store | None = None) -> dict[str, Any] | None:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    return memory_mod.resolve_entity(store, persona["id"], mention, kind)


def list_memory_anomalies(persona_id: str | None = None, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    return store.list_anomalies(persona_id)


def get_persona_memory(persona_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    content = memory_mod.render_memory_md(store, persona)
    path = memory_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path.relative_to(ROOT)), "content": content}


# ---- Evaluation (§12.5) & embeddings/forgetting (§12.6) ------------------

def evaluate_simulation(persona_id: str | None = None, start: str | None = None, end: str | None = None, store: Store | None = None, persist: bool = True) -> dict[str, Any]:
    store = store or Store()
    period = {"start": start, "end": end} if (start or end) else None
    return evaluation_mod.evaluate_simulation(persona_id, period, store=store, persist=persist)


def backfill_embeddings(persona_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    personas = [store.get_persona(persona_id)] if persona_id else store.list_personas()
    out = {}
    for p in [x for x in personas if x]:
        out[p["slug"]] = memory_mod.backfill_persona_embeddings(store, p["id"])
    return out


def prune_memory(persona_id: str, keep_days: int = 120, as_of: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Salience-based forgetting (§12.6): drop embeddings of old, low-salience
    episodes (not linked to any entity, no open loop reference) so they fall out
    of semantic recall. Raw events, facts and digests are retained."""
    store = store or Store()
    persona = _require_persona(store, persona_id)
    pid = persona["id"]
    ref = _parse_date(as_of).isoformat() if as_of else max(
        [e["timestamp"][:10] for e in store.list_experience_events(pid)] or [utc_now_iso()[:10]])
    cutoff = (date.fromisoformat(ref) - timedelta(days=keep_days)).isoformat()
    linked = set()
    for ent in store.list_entities(pid):
        linked.update(store.list_entity_events(ent["id"]))
    pruned = 0
    for e in store.list_experience_events(pid):
        if e["timestamp"][:10] < cutoff and e["id"] not in linked and not e.get("open_loops"):
            if store.has_embedding("event", e["id"]):
                store.conn.execute("DELETE FROM embeddings WHERE obj_type='event' AND obj_id=?", (e["id"],))
                pruned += 1
    store.commit()
    return {"persona_id": pid, "cutoff": cutoff, "pruned_event_embeddings": pruned}


# ===================================================================== #
# F2 — LLM critic (semantic eval stage).                                #
# ===================================================================== #

CRITIC_THRESHOLD = 4  # each dimension must reach this for semantic "top"


def _sample_activities(store: Store, persona_id: str, start: str | None, end: str | None, k: int) -> list[dict[str, Any]]:
    events = store.list_experience_events(persona_id, start, end)
    if not events:
        return []
    if len(events) > k:
        step = len(events) / k
        events = [events[int(i * step)] for i in range(k)]
    out = []
    for e in events:
        out.append({
            "ref_id": e["id"],
            "timestamp": e["timestamp"],
            "task": e["task"],
            "persona_thought": e.get("persona_thought"),
            "key_quotes": e.get("key_quotes", []),
            "conversation": e.get("conversation", [])[:3],
            "decision": e.get("decision"),
        })
    return out


def brief_eval_critic(persona_id: str, start: str | None = None, end: str | None = None, sample_k: int = 12, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    pid = persona["id"]
    arcs = []
    for ent in store.list_entities(pid, "project"):
        facts = store.list_entity_facts(ent["id"])
        arcs.append({"entity_id": ent["id"], "name": ent["name"], "status": ent.get("status"),
                     "facts": [{"ref_id": f["id"], "t_valid": f["t_valid"], "status": f.get("status"), "fact": f["fact"]} for f in facts]})
    frame = {
        "persona_name": persona["display_name"], "persona_id": pid,
        "source_description": persona["source_description"],
        "soul": get_persona_soul(pid, store)["content"],
        "period": {"start": start, "end": end},
        "sample_activities": _sample_activities(store, pid, start, end, sample_k),
        "project_arcs": arcs,
        "digests": [{"scope": d["scope"], "period": d["period_start"], "text": d.get("text")} for d in store.list_digests(pid)],
    }
    return {"persona_id": pid, "schema": "eval_critic", "instructions": build_eval_critic_prompt(frame), "frame": frame}


def record_eval_critic(persona_id: str, verdict: dict[str, Any], start: str | None = None, end: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    pid = persona["id"]
    now = utc_now_iso()
    payload = validate_eval_critic_payload(verdict)
    dims = payload["dimensions"]
    low = sorted([d for d, v in dims.items() if v < CRITIC_THRESHOLD])
    green = not low
    report = {
        "id": stable_id("critic", pid, now), "persona_id": pid, "kind": "llm_critic",
        "period_start": start, "period_end": end, "green": green,
        "dimensions": dims, "low_dimensions": low,
        "findings": payload["findings"], "flagged_items": payload["flagged_items"],
        "overall_note": payload["overall_note"], "created_at": now,
    }
    store.insert_eval_report(report)
    for d in low:
        store.insert_anomaly({"id": stable_id("anom", pid, "critic", d, now), "persona_id": pid,
                              "kind": f"critic:{d}", "severity": 3 if dims[d] <= 2 else 2,
                              "detail": f"{d}={dims[d]}/5", "created_at": now})
    for fi in payload["flagged_items"]:
        store.insert_anomaly({"id": stable_id("anom", pid, "critic-flag", fi["ref_id"], fi["issue"][:30]),
                              "persona_id": pid, "kind": f"critic_flag:{fi['dimension']}", "severity": fi["severity"],
                              "detail": fi["issue"], "ref_id": fi["ref_id"], "created_at": now})
    store.commit()
    return report


def latest_critic_report(persona_id: str, store: Store | None = None) -> dict[str, Any] | None:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    crit = [r for r in store.list_eval_reports(persona["id"]) if r.get("kind") == "llm_critic"]
    return crit[0] if crit else None  # list_eval_reports is DESC by created_at


def evaluate_simulation_full(persona_id: str, start: str | None = None, end: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Combined 'top' verdict (definition v2): structural harness + latest LLM critic."""
    store = store or Store()
    structural = evaluate_simulation(persona_id, start, end, store=store)
    critic = latest_critic_report(persona_id, store=store)
    critic_green = bool(critic and critic.get("green"))
    top = structural["green"] and critic_green
    return {
        "persona_id": persona_id,
        "top": top,
        "structural": {"verdict": structural["verdict"], "green": structural["green"], "summary": structural["summary"]},
        "critic": None if not critic else {
            "green": critic["green"], "dimensions": critic["dimensions"],
            "low_dimensions": critic.get("low_dimensions", []), "flagged": len(critic.get("flagged_items", [])),
        },
        "note": ("top" if top else
                 "structural not green" if not structural["green"] else
                 "no critic run yet" if not critic else
                 f"critic below threshold: {', '.join(critic.get('low_dimensions', []))}"),
    }


# ===================================================================== #
# F3 — Autonomous loop driver (in-package month bundle). roadmap F3.    #
# ===================================================================== #

def brief_month(persona_id: str, month: str, store: Store | None = None) -> dict[str, Any]:
    """Gather context to author a whole MONTH bundle (period plan + sample days +
    digest). Chains on the prior month's digest + current project state."""
    store = store or Store()
    persona = _require_persona(store, persona_id)
    pid = persona["id"]
    start = date.fromisoformat(f"{month}-01")
    prev_end = start - timedelta(days=1)
    prev_digests = [d for d in store.list_digests(pid, "month") if d["period_end"] <= prev_end.isoformat()]
    frame = {
        "persona_name": persona["display_name"], "persona_id": pid, "month": month,
        "soul": get_persona_soul(pid, store)["content"],
        "active_projects": memory_mod.list_active_projects(store, pid),
        "open_threads": [t["text"] for t in store.list_threads(pid, "open")],
        "prior_month_digest": prev_digests[-1]["text"] if prev_digests else None,
        "world_context": [{"category": w["category"], "fact": w["fact"]}
                          for w in store.list_world_context(as_of=start.isoformat())],
        "anti_steering": _ANTI_STEERING,
    }
    instructions = (
        "Author a MONTH bundle as JSON {period_plan, days:[{date, workday_start_hour, seed, "
        "day_plan, plan, activities, deltas}], digest}. Pick 3-4 working-day sample_days that "
        "show an arc (routine, conflict, milestone). Continue the SAME projects from "
        "active_projects/prior_month_digest with progressing status; use exact persona tools and "
        "pain_points; vary start hours and block counts; realistic done/open mix. See the "
        "simulate-cohort skill for the full schema. Anti-steering: " + _ANTI_STEERING
    )
    return {"persona_id": pid, "month": month, "schema": "month_bundle", "instructions": instructions, "frame": frame}


def record_month_bundle(persona_id: str, month: str, bundle: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    """Persist a host-authored month bundle through the full loop:
    put_period_plan -> per sample day (put_day_plan, simulate, consolidate) -> put_digest -> embed.
    """
    store = store or Store()
    persona = _require_persona(store, persona_id)
    pid = persona["id"]
    first = f"{month}-01"
    from . import llm_simulation as _llm

    put_period_plan(pid, "month", first, bundle["period_plan"], store=store)
    saved_plan = globals()["generate_day_plan_with_llm"]
    saved_act = globals()["generate_activity"]
    days_done = []
    try:
        for day in bundle["days"]:
            d = day["date"]
            put_day_plan(pid, d, day["day_plan"], store=store)
            plan, acts = day["plan"], day["activities"]
            globals()["generate_day_plan_with_llm"] = lambda frame, _p=plan: _llm.validate_day_plan_payload(_p, frame)

            def _act(frame, _a=acts):
                out = _llm.validate_activity_payload(_a[frame["title"]], frame)
                out["generation_mode"] = "host_authored"
                out["llm_error"] = None
                return out

            globals()["generate_activity"] = _act
            cons = {"workday_start": int(day["workday_start_hour"])} if day.get("workday_start_hour") is not None else None
            sim = simulate_day(pid, d, seed=day.get("seed"), constraints=cons, store=store)
            rec = record_memory_deltas(pid, d, day["deltas"], store=store)
            days_done.append({"date": d, "activities": len(sim["experience_events"]),
                              "entities": rec["entities_created"], "facts": rec["facts"]})
    finally:
        globals()["generate_day_plan_with_llm"] = saved_plan
        globals()["generate_activity"] = saved_act

    put_digest(pid, "month", first, bundle["digest"], store=store)
    backfill_embeddings(pid, store=store)
    return {"persona_id": pid, "month": month, "days": days_done, "sample_days": len(days_done)}


# ===================================================================== #
# F5 — Evidence integration (validate synthesis vs real evidence). F5.  #
# ===================================================================== #

def _evidence_for(store: Store, persona_id: str, limit: int = 8) -> list[dict[str, Any]]:
    out = []
    for ev in store.list_evidence(persona_id)[:limit]:
        out.append({"source_type": ev.get("source_type"), "notes": ev.get("notes"),
                    "content": str(ev.get("content_or_path", ""))[:1200]})
    return out


def brief_evidence_check(persona_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    evidence = _evidence_for(store, persona["id"], limit=20)
    if not evidence:
        return {"persona_id": persona["id"], "schema": "evidence_check", "evidence_count": 0,
                "instructions": "No evidence attached. Use attach_evidence first.", "frame": {}}
    frame = {
        "persona_name": persona["display_name"], "persona_id": persona["id"],
        "claims": {"goals": persona.get("goals"), "pain_points": persona.get("pain_points"),
                   "tools": persona.get("tools"), "constraints": persona.get("constraints"),
                   "relationships": persona.get("relationships")},
        "evidence": evidence,
    }
    return {"persona_id": persona["id"], "schema": "evidence_check", "evidence_count": len(evidence),
            "instructions": build_evidence_check_prompt(frame), "frame": frame}


def record_evidence_check(persona_id: str, result: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    persona = _require_persona(store, persona_id)
    pid = persona["id"]
    now = utc_now_iso()
    payload = validate_evidence_check_payload(result)
    report = {"id": stable_id("evcheck", pid, now), "persona_id": pid, "kind": "evidence_check",
              "green": len(payload["contradicted"]) == 0, **payload, "created_at": now}
    store.insert_eval_report(report)
    for c in payload["contradicted"]:
        store.insert_anomaly({"id": stable_id("anom", pid, "evidence", c["claim"][:40]), "persona_id": pid,
                              "kind": "evidence_contradiction", "severity": 3,
                              "detail": f"{c['claim']} — Evidenz: {c['evidence_says']}", "created_at": now})
    # provenance summary on the persona (evidence-backed vs assumption)
    persona.setdefault("provenance", {})["evidence_validation"] = {
        "confirmed": len(payload["confirmed"]), "contradicted": len(payload["contradicted"]),
        "unsupported": len(payload["unsupported"]), "checked_at": now,
    }
    persona["updated_at"] = now
    persona["soul"] = write_soul(persona, store)
    store.upsert_persona(persona, reason="evidence check")
    store.commit()
    return report


# ===================================================================== #
# Portable snapshot export of generated state → data/export/ (local-only)#
# (DB stays gitignored; this is the diffable, reproducible artifact).    #
# ===================================================================== #

def export_snapshot(out_dir: str | None = None, store: Store | None = None) -> dict[str, Any]:
    import shutil

    store = store or Store()
    base = Path(out_dir) if out_dir else (ROOT / "data" / "export")
    if not base.is_absolute():
        base = ROOT / base
    personas = store.list_personas()

    def _w(path: Path, obj: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")

    counts = {"personas": 0, "experience_events": 0, "entities": 0, "facts": 0, "avatars": 0}
    index = []
    for p in personas:
        pid = p["id"]
        pdir = base / "personas" / p["slug"]
        pdir.mkdir(parents=True, exist_ok=True)
        _w(pdir / "profile.json", p)
        (pdir / "SOUL.md").write_text(get_persona_soul(pid, store)["content"], encoding="utf-8")
        (pdir / "MEMORY.md").write_text(memory_mod.render_memory_md(store, p), encoding="utf-8")
        events = store.list_experience_events(pid)
        _w(pdir / "calendar.json", store.list_calendar_events(pid))
        _w(pdir / "experiences.json", events)
        _w(pdir / "daily_summaries.json", store.list_daily_summaries(pid))
        _w(pdir / "memory.json", {
            "entities": store.list_entities(pid),
            "entity_facts": store.list_persona_facts(pid),
            "event_links": store.list_event_entities(pid),
            "threads": store.list_threads(pid),
            "plans": store.list_plans(pid),
            "digests": store.list_digests(pid),
        })
        _w(pdir / "eval.json", {"reports": store.list_eval_reports(pid), "anomalies": store.list_anomalies(pid)})
        avatar = p.get("avatar")
        if avatar and avatar.get("path"):
            src = ROOT / avatar["path"]
            if src.exists():
                shutil.copyfile(src, pdir / "avatar.png")
                counts["avatars"] += 1
        counts["personas"] += 1
        counts["experience_events"] += len(events)
        counts["entities"] += len(store.list_entities(pid))
        counts["facts"] += len(store.list_persona_facts(pid))
        index.append({"slug": p["slug"], "display_name": p["display_name"],
                      "role": p.get("role", {}).get("title"), "has_avatar": bool(avatar)})

    _w(base / "world_context.json", store.list_world_context())
    sessions = store.list_council_sessions()
    for sess in sessions:
        _w(base / "councils" / f"{sess['id']}.json", sess)
    counts["councils"] = len(sessions)
    syns = store.list_syntheses()
    for syn in syns:
        _w(base / "syntheses" / f"{syn['id']}.json", syn)
    counts["syntheses"] = len(syns)
    _w(base / "manifest.json", {
        "generated_at": utc_now_iso(), "schema_version": store.schema_version(),
        "counts": counts, "personas": index,
        "note": "Reproducible snapshot of generated state. Rebuild the DB by re-running the simulation loop; this is the portable, local-only artifact (the SQLite DB stays gitignored).",
    })
    store.commit()
    return {"out_dir": str(base.relative_to(ROOT)), "counts": counts}


def import_snapshot(in_dir: str | None = None, store: Store | None = None, embed: bool = True) -> dict[str, Any]:
    """Rebuild the runtime DB (+ avatars, SOUL/MEMORY) from a portable snapshot.

    The portable round-trip: on another machine, copy data/export/ across (it is
    local-only, not in git), then `persona-council import-snapshot` reproduces
    this exact state — no re-generation. Embeddings are re-derived (not stored,
    to keep snapshots lean); pass embed=False to skip (recall stays keyword-only
    until backfilled).
    """
    import shutil

    store = store or Store()
    base = Path(in_dir) if in_dir else (ROOT / "data" / "export")
    if not base.is_absolute():
        base = ROOT / base
    if not (base / "manifest.json").exists():
        raise FileNotFoundError(f"No snapshot manifest at {base}")
    pdirs = sorted((base / "personas").glob("*/")) if (base / "personas").exists() else []
    counts = {"personas": 0, "experience_events": 0, "calendar_events": 0, "entities": 0,
              "facts": 0, "threads": 0, "plans": 0, "digests": 0, "avatars": 0}

    def _load(path: Path, default):
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    for pdir in pdirs:
        persona = _load(pdir / "profile.json", None)
        if not persona:
            continue
        # avatar: copy the snapshot png back into the runtime avatar dir at its recorded path
        avatar = persona.get("avatar")
        if avatar and avatar.get("path") and (pdir / "avatar.png").exists():
            dest = ROOT / avatar["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(pdir / "avatar.png", dest)
            counts["avatars"] += 1
        store.upsert_persona(persona, reason="import_snapshot")
        pid = persona["id"]
        for ev in _load(pdir / "calendar.json", []):
            store.insert_calendar_event(ev); counts["calendar_events"] += 1
        for ev in _load(pdir / "experiences.json", []):
            store.insert_experience_event(ev); counts["experience_events"] += 1
        for s in _load(pdir / "daily_summaries.json", []):
            store.upsert_daily_summary(s)
        mem = _load(pdir / "memory.json", {})
        for ent in mem.get("entities", []):
            store.upsert_entity(ent); counts["entities"] += 1
        for f in mem.get("entity_facts", []):
            store.insert_entity_fact(f); counts["facts"] += 1
        for link in mem.get("event_links", []):
            store.link_event_entity(link["event_id"], link["entity_id"], link.get("persona_id", pid), link.get("role"))
        for th in mem.get("threads", []):
            store.upsert_thread(th); counts["threads"] += 1
        for pl in mem.get("plans", []):
            store.upsert_plan(pl); counts["plans"] += 1
        for dg in mem.get("digests", []):
            store.upsert_digest(dg); counts["digests"] += 1
        ev_data = _load(pdir / "eval.json", {})
        for rep in ev_data.get("reports", []):
            store.insert_eval_report(rep)
        for an in ev_data.get("anomalies", []):
            store.insert_anomaly(an)
        # re-render SOUL/MEMORY from the restored persona
        persona["soul"] = write_soul(persona, store)
        store.upsert_persona(persona, reason="import_snapshot soul")
        counts["personas"] += 1

    for w in _load(base / "world_context.json", []):
        store.insert_world_context(w)
    cdir = base / "councils"
    if cdir.exists():
        for cf in sorted(cdir.glob("*.json")):
            store.insert_council_session(_load(cf, None))
            counts["councils"] = counts.get("councils", 0) + 1
    sdir = base / "syntheses"
    if sdir.exists():
        for sf in sorted(sdir.glob("*.json")):
            store.upsert_synthesis(_load(sf, None))
            counts["syntheses"] = counts.get("syntheses", 0) + 1
    store.commit()

    embedded = {}
    if embed:
        for pdir in pdirs:
            persona = _load(pdir / "profile.json", None)
            if persona:
                embedded[persona["slug"]] = memory_mod.backfill_persona_embeddings(store, persona["id"])
    return {"in_dir": str(base.relative_to(ROOT)), "counts": counts,
            "embeddings": "skipped" if not embed else "re-derived"}


# ===================================================================== #
# Synthesis — a study arc: chain of councils -> cross-council learnings. #
# ===================================================================== #

def _council_brief_row(store: Store, cid: str) -> dict[str, Any]:
    c = store.get_council_session(cid)
    if not c:
        return {"council_id": cid, "missing": True}
    # Per-persona material so the host can author the `voices` layer (who/why/shift).
    turns = [{"persona_id": t.get("persona_id"), "speaker": t.get("speaker"),
              "stance": t.get("stance"), "content": t.get("content")}
             for t in c.get("turns", [])]
    votes = [{"persona_id": v.get("persona_id"), "speaker": v.get("speaker"),
              "vote": v.get("vote"), "reason": v.get("reason")}
             for v in c.get("votes", [])]
    return {
        "council_id": cid, "prompt": c.get("prompt"), "created_at": c.get("created_at"),
        "exec_summary": c.get("exec_summary") or c.get("summary"),
        "vote_tally": {v: sum(1 for x in c.get("votes", []) if x.get("vote") == v)
                       for v in ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]},
        "turns": turns, "votes": votes,
        "proposal": c.get("proposal"),
    }


def brief_synthesis(council_ids: list[str], title: str | None = None, start_input: str | None = None,
                    goal: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """GATHER an ordered chain of councils so the host can author a synthesis."""
    store = store or Store()
    chain = [_council_brief_row(store, cid) for cid in council_ids]
    frame = {
        "title": title, "goal": goal, "start_input": start_input,
        "councils_in_order": chain,
    }
    return {"schema": "synthesis", "council_ids": council_ids,
            "instructions": build_synthesis_prompt(frame), "frame": frame}


def record_synthesis(title: str, start_input: str, council_ids: list[str], payload: dict[str, Any],
                     goal: str = "", synthesis_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Persist a host-authored synthesis over an ordered chain of councils.

    For the iterative driver loop: pass the SAME synthesis_id each round to update
    one growing study arc in place (chain + interim learnings + next_council_question).
    """
    store = store or Store()
    data = validate_synthesis_payload(payload)
    existing = store.get_synthesis(synthesis_id) if synthesis_id else None
    sid = (existing or {}).get("id") or stable_id("synthesis", title or "synthesis", utc_now_iso())
    created = (existing or {}).get("created_at") or utc_now_iso()
    rec = Synthesis(
        id=sid, title=title, start_input=start_input, council_ids=council_ids,
        arc_narrative=data["arc_narrative"], gesamtbild=data["gesamtbild"],
        handlungsempfehlungen=data["handlungsempfehlungen"], positionierung=data["positionierung"],
        pain_solvers=data["pain_solvers"], segmente=data["segmente"],
        offene_fragen=data["offene_fragen"], references=data["references"],
        created_at=created,
        goal=goal or (existing or {}).get("goal", ""),
        status=data["status"], next_council_question=data["next_council_question"],
        stop_reason=data["stop_reason"], iterations=len(council_ids),
        voices=data["voices"],
    ).to_dict()
    rec["updated_at"] = utc_now_iso()
    store.upsert_synthesis(rec)
    return rec


def get_synthesis(synthesis_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    syn = store.get_synthesis(synthesis_id)
    if not syn:
        raise KeyError(f"Unknown synthesis: {synthesis_id}")
    return syn


def list_syntheses(store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    return store.list_syntheses()


def export_synthesis(synthesis_id: str, format: str = "md", store: Store | None = None) -> str:
    """Render the synthesis as a stakeholder report (Markdown), referencing each council."""
    store = store or Store()
    syn = get_synthesis(synthesis_id, store)
    if format == "json":
        return json.dumps(syn, indent=2, ensure_ascii=False)
    role = {r["council_id"]: r.get("role", "") for r in syn.get("references", [])}
    status = syn.get("status", "done")
    lines = [f"# Synthese-Report: {syn['title']}", "",
             f"*Studien-Bogen aus {len(syn['council_ids'])} Councils · Status: {status} · erzeugt {syn['created_at']}.*", ""]
    if syn.get("goal"):
        lines += ["## Ziel", syn["goal"], ""]
    if status == "in_progress" and syn.get("next_council_question"):
        lines += ["## Vorgeschlagener nächster Council (self-contained)", syn["next_council_question"], ""]
    if status == "done" and syn.get("stop_reason"):
        lines += ["## Abschlussgrund", syn["stop_reason"], ""]
    lines += ["## Ausgangspunkt", syn.get("start_input", ""), "",
             "## Bogen / Verlauf", syn.get("arc_narrative", ""), "",
             "## Gesamtbild", syn.get("gesamtbild", ""), "",
             "## Handlungsempfehlungen"]
    def _rec_md(x: Any) -> str:
        if isinstance(x, dict):
            t = x.get("text", ""); a, n = x.get("aufwand"), x.get("nutzen")
            return f"{t} _(Aufwand {a}/5 · Nutzen {n}/5)_" if a and n else str(t)
        return str(x)
    lines += [f"{i}. {_rec_md(x)}" for i, x in enumerate(syn.get("handlungsempfehlungen", []), 1)] or ["—"]
    lines += ["", "## Positionierung", syn.get("positionierung", ""), "",
              "## Validierte Pain-Solver / Delight-Engines"]
    lines += [f"- {x}" for x in syn.get("pain_solvers", [])] or ["—"]
    lines += ["", "## Segmente"]
    lines += [f"- **{s['segment']}** ({s.get('stance','')}): {s.get('why','')}" for s in syn.get("segmente", [])] or ["—"]
    voices = syn.get("voices", [])
    if voices:
        lines += ["", "## Stimmen (pro Persona)"]
        order = {"positiv": 0, "bedingt": 1, "neutral": 2, "skeptisch": 3, "ablehnend": 4}
        for v in sorted(voices, key=lambda x: order.get(x.get("sentiment", "neutral"), 2)):
            name = v.get("persona_name") or v.get("persona_id")
            head = f"- **{name}** — {v.get('sentiment','')} · Relevanz: {v.get('relevance','')}"
            if v.get("segment"):
                head += f" · {v['segment']}"
            lines.append(head)
            if v.get("key_argument"):
                lines.append(f"  - Argument: {v['key_argument']}")
            sh = v.get("shift")
            if sh and (sh.get("trigger") or sh.get("to")):
                lines.append(f"  - Wandel: {sh.get('from','')}→{sh.get('to','')} — {sh.get('trigger','')}")
            for e in v.get("evidence", []):
                lines.append(f"  - „{e.get('quote','')}“ [{e.get('council_id','')}]")
    lines += ["", "## Offene Fragen / Nächste Studie"]
    lines += [f"- {x}" for x in syn.get("offene_fragen", [])] or ["—"]
    lines += ["", "## Quellen (Councils in Reihenfolge)"]
    for cid in syn["council_ids"]:
        c = store.get_council_session(cid)
        prompt = (c.get("prompt") if c else cid)
        lines.append(f"- `{cid}` — {role.get(cid, '')}".rstrip(" —") + (f"  ·  {prompt}" if prompt else ""))
    return "\n".join(lines) + "\n"


# ===================================================================== #
# Council write-back + reads (MCP parity for host-authored councils).    #
# Lets the run-council / synthesize skills persist via MCP instead of    #
# writing the store directly.                                            #
# ===================================================================== #

def record_council(prompt: str, persona_ids: list[str], turns: list[dict[str, Any]],
                   votes: list[dict[str, Any]] | None = None, proposal: str = "", summary: str = "",
                   exec_summary: str = "", selection_reason: str = "", store: Store | None = None) -> dict[str, Any]:
    """Persist a host-authored council (openings/moderator/directed turns + synthesis)."""
    store = store or Store()
    session = CouncilSession(
        id=stable_id("council", prompt, utc_now_iso()),
        prompt=prompt, persona_ids=persona_ids, selection_reason=selection_reason or "host-authored",
        turns=turns or [], proposal=proposal, votes=votes or [], summary=summary,
        exec_summary=exec_summary, created_at=utc_now_iso(),
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
