from __future__ import annotations

import json
from typing import Any

from .config import language_instruction


ACTIVITY_SCHEMA_KEYS = {
    "what_happened": str,
    "conversation": list,
    "key_quotes": list,
    "actions_done": list,
    "artifacts_touched": list,
    "persona_thought": str,
    "decision": (str, type(None)),
    "open_loops": list,
    "mood": str,
    "energy_delta": (int, float, str),
    "pain_points": list,
}

PROFILE_SCHEMA_KEYS = {
    "display_name": str,
    "identity_traits": dict,
    "segment": dict,
    "demographics": dict,
    "role": dict,
    "company_context": dict,
    "goals": list,
    "constraints": list,
    "tool_ids": list,
    "tools": list,
    "relationships": list,
    "personality": dict,
    "pain_points": list,
    "success_criteria": list,
}

DAY_PLAN_SCHEMA_KEYS = {
    "mood_forecast": str,
    "blocks": list,
}

PERSONA_ANSWER_SCHEMA_KEYS = {
    "answer": str,
    "referenced_moments": list,
    "uncertainties": list,
}

COUNCIL_TURN_SCHEMA_KEYS = {
    "content": str,
    "stance": str,
    "memory_refs": list,
    "questions_or_pushback": list,
}

COUNCIL_SYNTHESIS_SCHEMA_KEYS = {
    "proposal": str,
    "votes": list,
    "summary": str,
}

COUNCIL_SELECTION_SCHEMA_KEYS = {
    "persona_ids": list,
    "reasoning": str,
}


def _json_from_text(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end >= start:
        stripped = stripped[start : end + 1]
    data = json.loads(stripped)
    if not isinstance(data, dict):
        raise ValueError("LLM activity payload must be a JSON object.")
    return data


def _call_llm_json(prompt: str, timeout: int = 180) -> dict[str, Any]:
    del timeout
    raise RuntimeError(
        "Server-side text generation is disabled. Persona Council text must be "
        "authored by the MCP host agent, such as Claude Code or Codex, then "
        "submitted as JSON to validation/persistence tools. Prompt:\n\n" + prompt
    )


def _require_keys(payload: dict[str, Any], schema: dict[str, Any], label: str) -> dict[str, Any]:
    for key, expected in schema.items():
        if key not in payload:
            raise ValueError(f"{label} payload missing `{key}`.")
        if not isinstance(payload[key], expected):
            raise ValueError(f"{label} payload `{key}` has wrong type.")
    return payload


def validate_activity_payload(payload: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    for key, expected in ACTIVITY_SCHEMA_KEYS.items():
        if key not in out:
            raise ValueError(f"LLM activity payload missing `{key}`.")
        if not isinstance(out[key], expected):
            raise ValueError(f"LLM activity payload `{key}` has wrong type.")
    allowed_tools = set(frame["allowed_tools"])
    artifacts = [str(x) for x in out["artifacts_touched"]]
    out["artifacts_touched"] = artifacts[:8]
    if frame["tool"] not in allowed_tools:
        raise ValueError("Activity frame tool is outside persona tool enum.")
    out["conversation"] = [
        {"speaker": str(item.get("speaker", ""))[:80], "text": str(item.get("text", ""))[:500]}
        for item in out["conversation"][:8]
        if isinstance(item, dict)
    ]
    out["key_quotes"] = [str(x)[:300] for x in out["key_quotes"][:5]]
    out["actions_done"] = [str(x)[:300] for x in out["actions_done"][:8]]
    out["open_loops"] = [str(x)[:300] for x in out["open_loops"][:5]]
    out["pain_points"] = [p for p in [str(x) for x in out["pain_points"]] if p in frame["allowed_pain_points"]][:5]
    out["mood"] = str(out["mood"])[:80]
    out["persona_thought"] = str(out["persona_thought"])[:500]
    out["what_happened"] = str(out["what_happened"])[:1200]
    out["decision"] = str(out["decision"])[:300] if out["decision"] else None
    try:
        out["energy_delta"] = max(-3, min(2, int(float(out["energy_delta"]))))
    except (TypeError, ValueError):
        out["energy_delta"] = -1
    return out


def _strings(items: list[Any], limit: int, item_limit: int = 180) -> list[str]:
    return [str(item).strip()[:item_limit] for item in items if str(item).strip()][:limit]


def _recs(items: list[Any], limit: int = 20) -> list[dict]:
    """Normalize handlungsempfehlungen to [{text, aufwand, nutzen}].

    `aufwand` (effort) and `nutzen` (value) are ints 1-5 or None. Accepts plain
    strings (-> unscored) for backward compatibility, or dicts carrying the axes.
    Powers the Aufwand/Nutzen-Matrix in the UI.
    """
    def _sc(v: Any) -> int | None:
        try:
            return min(5, max(1, int(round(float(v)))))
        except (TypeError, ValueError):
            return None

    out: list[dict] = []
    for it in (items or [])[:limit]:
        if isinstance(it, dict):
            t = str(it.get("text", "")).strip()
            if t:
                out.append({"text": t[:400], "aufwand": _sc(it.get("aufwand")), "nutzen": _sc(it.get("nutzen"))})
        else:
            t = str(it).strip()
            if t:
                out.append({"text": t[:400], "aufwand": None, "nutzen": None})
    return out


def build_profile_prompt(description: str, segment_hint: str | None = None, evidence: str | None = None, language: str | None = None) -> str:
    return f"""Create one authentic synthetic customer profile from the source description.

Return ONLY one JSON object with exactly these keys:
display_name: string
identity_traits: object
segment: object
demographics: object
role: object
company_context: object
goals: array of strings
constraints: array of strings
tool_ids: array of strings
tools: array of strings
relationships: array of objects {{name:string,type:string,friction:string}}
personality: object
pain_points: array of strings
success_criteria: array of strings

Rules:
- Derive the profile from the source description and evidence. Do not use shared stock defaults.
- identity_traits must include gender_presentation, gender_confidence, age_range, appearance_notes, avatar_profile, avatar_constraints.
- role must include title, responsibilities, seniority, decision_power.
- company_context must include industry, size, stack, operating_model.
- personality must include working_style, communication_style, risk_tolerance, character_notes.
- If a detail is not supported, mark it as unspecified or low-confidence in the relevant object.
- Make relationships, goals, constraints, pains, and personality specific to this person's actual work context.
- Do not infer interest in BIM, AI, automation, or any product direction unless source/evidence says so.
- Do not include vendor-friendly language. This is a lived customer profile, not a sales persona.
- tools must be only actual tools, media, channels, or recurring work surfaces mentioned or strongly implied.
- tool_ids must be lowercase stable slugs matching tools, e.g. "e_mail" for "E-Mail".
- Avoid slogans, repeated catchphrases, and generic consultant language.
- {language_instruction(language)} (proper names and tool names keep their real spelling).

Source description:
{description}

Segment hint:
{segment_hint or "none"}

Evidence:
{evidence or "none"}
"""


def validate_profile_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out = _require_keys(payload, PROFILE_SCHEMA_KEYS, "Profile")
    out["display_name"] = str(out["display_name"]).strip()[:120] or "Unnamed Profile"
    out["goals"] = _strings(out["goals"], 8)
    out["constraints"] = _strings(out["constraints"], 8)
    out["tool_ids"] = _strings(out["tool_ids"], 12, 80)
    out["tools"] = _strings(out["tools"], 12, 80)
    out["pain_points"] = _strings(out["pain_points"], 8)
    out["success_criteria"] = _strings(out["success_criteria"], 8)
    out["relationships"] = [
        {
            "name": str(item.get("name", "")).strip()[:120],
            "type": str(item.get("type", "")).strip()[:80],
            "friction": str(item.get("friction", "")).strip()[:220],
        }
        for item in out["relationships"][:8]
        if isinstance(item, dict) and item.get("name")
    ]
    if not out["tools"]:
        raise ValueError("Profile payload must contain at least one concrete tool/channel/work surface.")
    if not out["relationships"]:
        raise ValueError("Profile payload must contain specific relationships.")
    for key in ["goals", "constraints", "pain_points", "success_criteria"]:
        if not out[key]:
            raise ValueError(f"Profile payload must contain `{key}`.")
    nested_requirements = {
        "identity_traits": ["gender_presentation", "gender_confidence", "age_range", "appearance_notes", "avatar_profile", "avatar_constraints"],
        "role": ["title", "responsibilities", "seniority", "decision_power"],
        "company_context": ["industry", "size", "stack", "operating_model"],
        "personality": ["working_style", "communication_style", "risk_tolerance", "character_notes"],
    }
    for obj_key, required in nested_requirements.items():
        for nested_key in required:
            if nested_key not in out[obj_key]:
                raise ValueError(f"Profile `{obj_key}` missing `{nested_key}`.")
    for key in ["working_style", "communication_style", "risk_tolerance"]:
        if not str(out["personality"].get(key, "")).strip():
            raise ValueError(f"Profile personality missing `{key}`.")
    return out


def generate_profile_with_llm(description: str, segment_hint: str | None = None, evidence: str | None = None, language: str | None = None) -> dict[str, Any]:
    """Legacy one-shot path. Server-side generation is disabled, so this raises;
    use brief_persona -> (host authors) -> record_persona instead."""
    return validate_profile_payload(_call_llm_json(build_profile_prompt(description, segment_hint, evidence, language)))


def validate_day_plan_payload(payload: dict[str, Any], frame: dict[str, Any]) -> dict[str, Any]:
    out = _require_keys(payload, DAY_PLAN_SCHEMA_KEYS, "Day plan")
    allowed_tools = set(frame["allowed_tools"])
    blocks = []
    for item in out["blocks"]:
        if not isinstance(item, dict):
            continue
        block = {
            "title": str(item.get("title", "")).strip()[:120],
            "event_type": str(item.get("event_type", "")).strip(),
            "duration_minutes": int(item.get("duration_minutes", 45)),
            "collaboration_mode": str(item.get("collaboration_mode", "")).strip(),
            "participants": _strings(item.get("participants", []), 6, 80) if isinstance(item.get("participants", []), list) else [],
            "tool": str(item.get("tool", "")).strip(),
            "why_it_happens": str(item.get("why_it_happens", "")).strip()[:300],
        }
        if not block["title"]:
            continue
        if block["event_type"] not in {"meeting", "focus", "interruption", "admin", "decision", "site_visit"}:
            raise ValueError(f"Day plan has unsupported event_type `{block['event_type']}`.")
        if block["tool"] not in allowed_tools:
            raise ValueError(f"Day plan tool `{block['tool']}` is outside allowed tools.")
        block["duration_minutes"] = max(15, min(150, block["duration_minutes"]))
        blocks.append(block)
    if len(blocks) < 5:
        raise ValueError("Day plan must contain at least five usable blocks.")
    out["blocks"] = blocks[:8]
    out["mood_forecast"] = str(out["mood_forecast"]).strip()[:160]
    return out


def generate_day_plan_with_llm(frame: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""Plan one authentic workday for a synthetic customer profile.

Return ONLY one JSON object with exactly these keys:
mood_forecast: string
blocks: array of objects with keys:
  title: string
  event_type: one of meeting, focus, interruption, admin, decision, site_visit
  duration_minutes: integer
  collaboration_mode: string
  participants: array of strings
  tool: string chosen only from allowed_tools
  why_it_happens: string

Rules:
- Use SOUL.md, recent events, and open loops as the source of truth.
- Do not use a fixed template. The day rhythm should fit this specific person.
- Avoid repeated titles across days unless the recent calendar genuinely implies repetition.
- Participants must be realistic named roles for this person's world, not generic placeholders.
- Do not force meetings; mix solitude, interruptions, admin, travel/site/customer moments as appropriate.
- Do not infer product interest or vendor-friendly pain. Simulate ordinary work.
- Avoid catchphrases and repeated internal monologue.

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""
    return validate_day_plan_payload(_call_llm_json(prompt), frame)


def generate_activity_with_llm(frame: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""You simulate one activity in a synthetic professional workday.

Return ONLY one JSON object with exactly these keys:
what_happened: string
conversation: array of objects {{speaker:string,text:string}}
key_quotes: array of strings
actions_done: array of strings
artifacts_touched: array of strings
persona_thought: string
decision: string or null
open_loops: array of strings
mood: string
energy_delta: integer from -3 to 2
pain_points: array of strings chosen only from allowed_pain_points

Rules:
- Use the loaded SOUL.md as the persona's authoritative identity.
- Do not infer that the persona likes, needs, or is moving toward BIM, AI, automation, or any product direction unless the SOUL.md/frame explicitly supports it.
- Treat the repository/app name as irrelevant context; simulate the person's actual workday, not a vendor narrative.
- Make the activity feel like a real work moment, not a generic summary.
- If event_type is meeting, include realistic concise dialogue between participants.
- If working alone, include internal thinking and concrete artifacts/actions.
- Do not use tools outside allowed_tools.
- Keep timestamps and participants consistent with the frame.
- Prefer mundane repeated work friction over drama.
- Include disagreement, uncertainty, boredom, skepticism, or satisfaction when that is realistic for the persona and activity.
- Do not start persona_thought with a repeated slogan or catchphrase from recent thoughts.
- If recent thoughts repeat a phrase, vary the wording and add new concrete context instead of echoing it.
- Language may be German or English, but should fit the persona context.

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""
    return validate_activity_payload(_call_llm_json(prompt, timeout=180), frame)


def generate_activity(frame: dict[str, Any]) -> dict[str, Any]:
    out = generate_activity_with_llm(frame)
    out["generation_mode"] = "llm"
    out["llm_error"] = None
    return out


def generate_persona_answer_with_llm(frame: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""Answer one question from the perspective of a synthetic customer persona.

Return ONLY one JSON object with exactly these keys:
answer: string
referenced_moments: array of strings
uncertainties: array of strings

Rules:
- The supplied persona_agent_context contains SOUL.md and recent lived events. Treat it as authoritative.
- Answer as the persona, not as an analyst or vendor.
- Do not force support, resistance, BIM, AI, automation, or any product direction unless the context supports it.
- Ground claims in calendar moments, tools, handoffs, relationships, and open loops when available.
- If the simulated record is thin, say what is uncertain instead of inventing confidence.
- Avoid templates, catchphrases, and generic market-research wording.

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""
    out = _require_keys(_call_llm_json(prompt, timeout=180), PERSONA_ANSWER_SCHEMA_KEYS, "Persona answer")
    out["answer"] = str(out["answer"]).strip()[:2500]
    out["referenced_moments"] = _strings(out["referenced_moments"], 8, 220)
    out["uncertainties"] = _strings(out["uncertainties"], 6, 220)
    return out


def generate_council_turn_with_llm(frame: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""Write one council debate turn from a synthetic customer persona.

Return ONLY one JSON object with exactly these keys:
content: string
stance: string
memory_refs: array of strings
questions_or_pushback: array of strings

Rules:
- Use the persona_agent_context, including SOUL.md, current state, and recent events.
- Speak as that persona in a concrete work context, not as a generic consultant.
- React to the council prompt and previous turns without defaulting to support.
- Disagreement, indifference, uncertainty, or changing the subject to actual work constraints are valid.
- Do not steer toward BIM, AI, automation, or any product direction unless the prompt/context/persona supports it.
- Avoid repeated debate boilerplate; make the turn specific to this persona's lived calendar.

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""
    out = _require_keys(_call_llm_json(prompt, timeout=180), COUNCIL_TURN_SCHEMA_KEYS, "Council turn")
    out["content"] = str(out["content"]).strip()[:2500]
    out["stance"] = str(out["stance"]).strip()[:120]
    out["memory_refs"] = _strings(out["memory_refs"], 8, 160)
    out["questions_or_pushback"] = _strings(out["questions_or_pushback"], 6, 220)
    return out


def generate_council_selection_with_llm(frame: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""Select personas for a synthetic customer council.

Return ONLY one JSON object with exactly these keys:
persona_ids: array of strings
reasoning: string

Rules:
- Select from candidate_personas only. Never invent IDs.
- Choose personas whose lived contexts can produce useful, honest disagreement or contrast.
- Do not select personas because the app/repository name suggests a topic.
- Do not bias toward BIM, AI, automation, or product-friendly views unless the prompt and persona evidence support that.
- If the candidate set is small, return fewer personas rather than inventing diversity.
- Reasoning should explain why this set is useful without claiming guaranteed support.

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""
    out = _require_keys(_call_llm_json(prompt, timeout=180), COUNCIL_SELECTION_SCHEMA_KEYS, "Council selection")
    valid_ids = {str(item["persona_id"]) for item in frame["candidate_personas"]}
    selected: list[str] = []
    for persona_id in _strings(out["persona_ids"], int(frame["count"]), 120):
        if persona_id in valid_ids and persona_id not in selected:
            selected.append(persona_id)
    if not selected and frame["candidate_personas"]:
        raise ValueError("Council selection did not return any valid candidate persona IDs.")
    out["persona_ids"] = selected
    out["reasoning"] = str(out["reasoning"]).strip()[:1000]
    return out


def generate_council_synthesis_with_llm(frame: dict[str, Any]) -> dict[str, Any]:
    prompt = f"""Synthesize a council session among synthetic customer personas.

Return ONLY one JSON object with exactly these keys:
proposal: string
votes: array of objects with keys persona_id, speaker, vote, reason
summary: string
exec_summary: string (rich Markdown — the readable debrief shown in the UI)

Rules:
- Use only the supplied prompt, turns, persona contexts, and optional external context.
- Valid votes are SUPPORT, MAYBE, ABSTAIN, OPPOSE.
- Do not invent consensus. Preserve disagreement and uncertainty.
- Do not create vendor-friendly conclusions unless the personas' lived context supports them.
- Keep reasons grounded in concrete work constraints and simulated calendar evidence.
- `exec_summary` is the value the reader keeps: Markdown with a short verdict, the
  spectrum (who is for/skeptical/against and WHY), the cross-cutting conditions
  almost everyone shares, the sharpest tensions, and a one-line bottom line. Use
  ## headings, bullet lists, **bold**, and short verbatim quotes from the turns.

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""
    out = _require_keys(_call_llm_json(prompt, timeout=180), COUNCIL_SYNTHESIS_SCHEMA_KEYS, "Council synthesis")
    out["proposal"] = str(out["proposal"]).strip()[:1800]
    out["summary"] = str(out["summary"]).strip()[:1800]
    out["exec_summary"] = str(out.get("exec_summary", "")).strip()[:8000]
    votes = []
    valid_votes = {"SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"}
    for item in out["votes"]:
        if not isinstance(item, dict):
            continue
        vote = str(item.get("vote", "")).strip().upper()
        if vote not in valid_votes:
            vote = "ABSTAIN"
        votes.append(
            {
                "persona_id": str(item.get("persona_id", "")).strip()[:120],
                "speaker": str(item.get("speaker", "")).strip()[:120],
                "vote": vote,
                "reason": str(item.get("reason", "")).strip()[:600],
            }
        )
    out["votes"] = votes
    return out


# ===================================================================== #
# Memory & multi-resolution planning (spec §4, §4A, §12).               #
# These are AUTHORED BY THE HOST: brief_* builds the prompt + context,   #
# the host LLM writes JSON, validate_* coerces it before persistence.    #
# No server-side text generation here either.                           #
# ===================================================================== #

_KINDS = {"project", "person", "org", "building", "authority", "topic"}


def build_consolidation_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    return f"""You consolidate ONE simulated workday into persistent memory for a synthetic persona.

You are given the day's activities and the persona's currently known entities.
Return ONLY one JSON object with exactly these keys:
entities: array of {{mention:string, kind:one of [project,person,org,building,authority,topic], status:string|null, aliases:array of strings}}
facts: array of {{entity:string(mention), fact:string, status:string|null, valid_from:"YYYY-MM-DD", valid_to:string|null, importance:1-5, invalidates:string|null}}
threads: array of {{text:string, entity:string|null, action:one of [open,resolve], ref:string|null}}
event_links: array of {{activity_title:string, entities:array of strings(mention)}}

Rules:
- Extract the REAL entities the day touched (projects, people, authorities, buildings). Reuse existing names from known_entities verbatim when it is the same thing (avoid duplicates / aliases drift).
- A status/outcome (won, lost, delayed, in construction, approved, finished, …) is YOUR judgement from the day — never a fixed rule. Justify implausible jumps via the fact text.
- `valid_from` is the simulation date of the day (or earlier if the fact clearly started before). `valid_to` only if it definitively ended.
- `invalidates` = the prior fact text this fact supersedes (e.g. an old status), so it can be retired.
- threads: open NEW loops or resolve existing ones (ref = the loop text you are closing).
- Do not invent product interest / BIM / AI / automation adoption unless the day's evidence shows it.
- {language_instruction(language)} Match the persona's voice.

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_memory_deltas_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Memory deltas must be a JSON object.")
    out: dict[str, Any] = {"entities": [], "facts": [], "threads": [], "event_links": []}
    for e in payload.get("entities", []) or []:
        if not isinstance(e, dict) or not str(e.get("mention", "")).strip():
            continue
        kind = str(e.get("kind", "topic")).strip().lower()
        out["entities"].append({
            "mention": str(e["mention"]).strip()[:160],
            "kind": kind if kind in _KINDS else "topic",
            "status": (str(e["status"]).strip()[:80] if e.get("status") else None),
            "aliases": _strings(e.get("aliases", []) or [], 6, 160),
        })
    for f in payload.get("facts", []) or []:
        if not isinstance(f, dict) or not str(f.get("fact", "")).strip() or not str(f.get("entity", "")).strip():
            continue
        try:
            imp = max(1, min(5, int(f.get("importance", 3))))
        except (TypeError, ValueError):
            imp = 3
        out["facts"].append({
            "entity": str(f["entity"]).strip()[:160],
            "fact": str(f["fact"]).strip()[:400],
            "status": (str(f["status"]).strip()[:80] if f.get("status") else None),
            "valid_from": str(f.get("valid_from", "")).strip()[:10] or None,
            "valid_to": (str(f["valid_to"]).strip()[:10] if f.get("valid_to") else None),
            "importance": imp,
            "invalidates": (str(f["invalidates"]).strip()[:400] if f.get("invalidates") else None),
        })
    for t in payload.get("threads", []) or []:
        if not isinstance(t, dict) or not str(t.get("text", "")).strip():
            continue
        action = str(t.get("action", "open")).strip().lower()
        out["threads"].append({
            "text": str(t["text"]).strip()[:300],
            "entity": (str(t["entity"]).strip()[:160] if t.get("entity") else None),
            "action": action if action in {"open", "resolve"} else "open",
            "ref": (str(t["ref"]).strip()[:300] if t.get("ref") else None),
        })
    for link in payload.get("event_links", []) or []:
        if not isinstance(link, dict) or not str(link.get("activity_title", "")).strip():
            continue
        out["event_links"].append({
            "activity_title": str(link["activity_title"]).strip()[:200],
            "entities": _strings(link.get("entities", []) or [], 8, 160),
        })
    return out


def build_plan_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    scope = frame.get("scope", "day")
    extra = (
        "Because this is a PERIOD plan, also pick `sample_days` (YYYY-MM-DD): the few "
        "representative days within the period worth simulating in detail (milestones, "
        "conflicts, and ordinary routine — not only drama)."
        if scope != "day" else
        "Because this is a DAY plan, `sample_days` should be just this one date."
    )
    return f"""You plan a synthetic persona's upcoming {scope} BEFORE simulation, using memory.

Return ONLY one JSON object with exactly these keys:
summary: string (the arc — what is interesting / at stake in this {scope})
intentions: array of strings (threads/projects to advance, foci)
expected_milestones: array of strings
mood_trajectory: string
sample_days: array of strings ("YYYY-MM-DD")

Rules:
- Ground the plan in the supplied active projects, open threads, recent digests, and world context.
- {extra}
- This is analysis, not narration: name what plausibly moves, what stays stuck, what is overdue.
- Do not steer the persona toward any product/tool adoption unless memory supports it.
- {language_instruction(language)}

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_plan_payload(payload: dict[str, Any], scope: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Plan must be a JSON object.")
    return {
        "scope": scope,
        "summary": str(payload.get("summary", "")).strip()[:1200],
        "intentions": _strings(payload.get("intentions", []) or [], 12, 300),
        "expected_milestones": _strings(payload.get("expected_milestones", []) or [], 12, 300),
        "mood_trajectory": str(payload.get("mood_trajectory", "")).strip()[:300],
        "sample_days": _strings(payload.get("sample_days", []) or [], 31, 10),
    }


def build_digest_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    return f"""You write a consolidated {frame.get('scope','period')} digest for a synthetic persona.

Return ONLY one JSON object with exactly these keys:
text: string (a compact narrative of what actually happened and where things stand)
themes: array of strings
project_arcs: array of {{name:string, arc:string}}
trends: array of strings (longer-running tendencies, e.g. workload, market, mood)

Rules:
- Summarize from the supplied days, facts, and threads. Capture arcs and trends, not every detail.
- Be honest about stalls and unresolved loops; do not invent progress or product enthusiasm.
- {language_instruction(language)}

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_digest_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict) or not str(payload.get("text", "")).strip():
        raise ValueError("Digest must contain non-empty `text`.")
    arcs = []
    for a in payload.get("project_arcs", []) or []:
        if isinstance(a, dict) and str(a.get("name", "")).strip():
            arcs.append({"name": str(a["name"]).strip()[:160], "arc": str(a.get("arc", "")).strip()[:400]})
    return {
        "text": str(payload["text"]).strip()[:3000],
        "themes": _strings(payload.get("themes", []) or [], 10, 160),
        "project_arcs": arcs[:20],
        "trends": _strings(payload.get("trends", []) or [], 10, 240),
    }


def build_persona_revision_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    return f"""You propose SLOW, evidence-backed drift in a synthetic persona's identity.

Return ONLY one JSON object with exactly these keys:
rationale: string (why this drift is justified by consolidated facts — cite them)
effective_on: "YYYY-MM-DD"
changes: object with optional keys:
  goals_add, goals_remove, constraints_add, constraints_remove,
  pains_add, pains_remove, tools_add, tools_remove: arrays of strings
  personality: object (partial overrides of working_style/communication_style/risk_tolerance/character_notes)
  notes: string

Rules:
- Change is the EXCEPTION, not the default. Inertia is realistic; most periods need little or no change.
- Every change must be justified by the supplied facts/digests — never from nothing.
- Never drift the persona toward product/tool enthusiasm unless evidence forces it (and then say why).
- If nothing should change, return empty `changes` and say so in `rationale`.
- {language_instruction(language)}

Frame:
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_persona_revision_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Persona revision must be a JSON object.")
    raw = payload.get("changes", {}) or {}
    changes: dict[str, Any] = {}
    for key in ["goals_add", "goals_remove", "constraints_add", "constraints_remove",
                "pains_add", "pains_remove", "tools_add", "tools_remove"]:
        vals = _strings(raw.get(key, []) or [], 10, 220)
        if vals:
            changes[key] = vals
    if isinstance(raw.get("personality"), dict):
        pers = {k: str(v).strip()[:400] for k, v in raw["personality"].items()
                if k in {"working_style", "communication_style", "risk_tolerance", "character_notes"} and str(v).strip()}
        if pers:
            changes["personality"] = pers
    if str(raw.get("notes", "")).strip():
        changes["notes"] = str(raw["notes"]).strip()[:600]
    return {
        "rationale": str(payload.get("rationale", "")).strip()[:1200],
        "effective_on": str(payload.get("effective_on", "")).strip()[:10] or None,
        "changes": changes,
    }


# ===================================================================== #
# F2 — LLM critic (semantic eval stage).                                #
# Host-authored: brief gathers, host scores, validate coerces.          #
# Anti-steering is checked here (semantic), NOT via hardcoded keywords.  #
# ===================================================================== #

_CRITIC_DIMENSIONS = ["anti_steering", "in_character", "dialogue_believability",
                      "arc_plausibility", "mundane_balance"]


def build_eval_critic_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    return f"""You are a strict quality critic for a synthetic persona simulation.
Judge the SAMPLE below against the persona's own SOUL and source description.

Return ONLY one JSON object with exactly these keys:
dimensions: object with integer 0-5 scores for each of:
  anti_steering        (5 = stays true to the brief; LOW if the persona drifts toward
                        unsupported enthusiasm/adoption of any tool/method/product not
                        in its source — judge against THIS persona's source, any industry)
  in_character         (consistency with SOUL personality/stance; a skeptic stays skeptical)
  dialogue_believability (conversations sound real and specific, not generic)
  arc_plausibility     (project status/time progressions are realistic)
  mundane_balance      (enough ordinary routine/friction, not constant drama)
findings: array of short strings (what is good / what is off)
flagged_items: array of {{ref_id:string, dimension:string, issue:string, severity:1-5}}
  (ref_id = an event/fact id from the sample that evidences the problem)
overall_note: string

Rules:
- Be specific and skeptical. Cite ref_ids in flagged_items.
- anti_steering is the priority: any ungrounded product/method drift => low score + flag.
- Do not reward vendor-friendly narratives; reward honest, ordinary, in-character work.
- The acceptance bar is {frame.get("threshold", 4)}/5 per dimension: any dimension below
  it marks the run as not "top". Score honestly against that bar.
- {language_instruction(language)}

Frame (persona source, SOUL, sampled activities with ids, project arcs, digests):
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_eval_critic_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Critic verdict must be a JSON object.")
    dims_in = payload.get("dimensions", {}) or {}
    dims: dict[str, int] = {}
    for key in _CRITIC_DIMENSIONS:
        try:
            dims[key] = max(0, min(5, int(dims_in.get(key, 3))))
        except (TypeError, ValueError):
            dims[key] = 3
    flagged = []
    for it in payload.get("flagged_items", []) or []:
        if not isinstance(it, dict) or not str(it.get("issue", "")).strip():
            continue
        try:
            sev = max(1, min(5, int(it.get("severity", 3))))
        except (TypeError, ValueError):
            sev = 3
        dim = str(it.get("dimension", "")).strip()
        flagged.append({
            "ref_id": str(it.get("ref_id", "")).strip()[:80],
            "dimension": dim if dim in _CRITIC_DIMENSIONS else "general",
            "issue": str(it["issue"]).strip()[:300],
            "severity": sev,
        })
    return {
        "dimensions": dims,
        "findings": _strings(payload.get("findings", []) or [], 12, 300),
        "flagged_items": flagged[:20],
        "overall_note": str(payload.get("overall_note", "")).strip()[:1000],
    }


# --- Cohort-wide critic (cross-persona outlier detection) --------------------
# The per-persona critic judges one persona against its own SOUL. The cohort
# critic judges each persona against its PEERS: who falls out of the cohort's
# range (an implausible outlier in believability/consistency/voice, or a clone
# that adds no distinct perspective). Host-authored, like the per-persona critic.

def build_cohort_critic_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    return f"""You are a quality critic comparing a COHORT of synthetic personas against
each other (not against their own brief). Find the personas that fall OUT of the
cohort's range.

You are given a compact profile per persona (source, segment, role, pains, and — when
available — its per-persona critic dimensions and a couple of sample utterances).

Return ONLY one JSON object with exactly these keys:
outliers: array of {{persona_id:string, persona_name:string, reason:string,
  dimension:string (one of: believability | consistency | distinctiveness | tone | range),
  severity:1-5}}
  Include a persona ONLY if it genuinely stands out from the others — e.g. it reads as
  far less believable/consistent than its peers, or it is a near-clone that contributes
  no distinct perspective. An empty list is a valid, good result.
cohort_note: string (one paragraph: is the cohort balanced and diverse, or skewed?)

Rules:
- Judge RELATIVE to the cohort, not against an absolute ideal.
- Do not invent problems to fill the list; flag only real outliers.
- Distinctiveness matters: two interchangeable personas are an outlier pair, not a strength.
- {language_instruction(language)}

Cohort frame (one compact record per persona):
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_cohort_critic_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Cohort critic verdict must be a JSON object.")
    allowed_dims = {"believability", "consistency", "distinctiveness", "tone", "range"}
    outliers = []
    for it in payload.get("outliers", []) or []:
        if not isinstance(it, dict) or not str(it.get("persona_id", "")).strip():
            continue
        try:
            sev = max(1, min(5, int(it.get("severity", 3))))
        except (TypeError, ValueError):
            sev = 3
        dim = str(it.get("dimension", "")).strip().lower()
        outliers.append({
            "persona_id": str(it["persona_id"]).strip()[:80],
            "persona_name": str(it.get("persona_name", "")).strip()[:120],
            "reason": str(it.get("reason", "")).strip()[:400],
            "dimension": dim if dim in allowed_dims else "range",
            "severity": sev,
        })
    return {"outliers": outliers[:50], "cohort_note": str(payload.get("cohort_note", "")).strip()[:1000]}


# ===================================================================== #
# F5 — Evidence check (validate synthetic profile against real evidence).#
# ===================================================================== #

def build_evidence_check_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    return f"""Compare a SYNTHETIC persona profile against attached REAL evidence.

Return ONLY one JSON object with exactly these keys:
confirmed: array of strings (profile claims the evidence supports)
contradicted: array of {{claim:string, evidence_says:string}}
unsupported: array of strings (profile claims with no evidence either way — stay assumptions)
notes: string

Rules:
- Judge goals, pain_points, tools, constraints, relationships against the evidence only.
- Be conservative: only 'confirmed' when the evidence clearly supports it.
- 'contradicted' must quote what the evidence actually says.
- Do not invent evidence. If evidence is thin, most claims are 'unsupported'.
- {language_instruction(language)}

Frame (profile claims + attached evidence):
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_evidence_check_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Evidence check must be a JSON object.")
    contradicted = []
    for c in payload.get("contradicted", []) or []:
        if isinstance(c, dict) and str(c.get("claim", "")).strip():
            contradicted.append({"claim": str(c["claim"]).strip()[:300],
                                 "evidence_says": str(c.get("evidence_says", "")).strip()[:300]})
    return {
        "confirmed": _strings(payload.get("confirmed", []) or [], 30, 300),
        "contradicted": contradicted[:30],
        "unsupported": _strings(payload.get("unsupported", []) or [], 30, 300),
        "notes": str(payload.get("notes", "")).strip()[:1000],
    }


# --- Meta-Report: second-order synthesis over a whole project graph ----------
# Two host-authored steps: derive an OUTLINE from the graph (topology + build
# order), then author each SECTION grounded in its source studies (two-level
# provenance: meta-section -> study -> council).

def build_meta_outline_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    return f"""You are writing a META-REPORT over a whole research PROJECT: a graph of studies
(each study = a council chain consolidated into a synthesis). Derive the report's OUTLINE
from the graph — its themes and dependency edges — not from a fixed template.

Return ONLY one JSON object with exactly these keys:
build_order_narrative: string (how the understanding was BUILT over time — read the studies
  in creation order and describe the trajectory: what was asked first, what each answer spawned)
sections: array of objects {{heading:string, theme_tags:array of strings,
  source_study_ids:array of strings (the study ids this section draws on — use ids from the frame),
  intent:string (one line: what this section establishes)}}
  Organize by THEME/logic (cluster studies by theme + dependency), NOT by chronology. Always
  include three cross-cutting sections somewhere: one for how-understanding-was-built (trajectory),
  one for tensions & deliberate non-targets, and one for the open frontier (unresolved questions).

Rules:
- Derive structure from the actual graph (themes, edges, build order in the frame). Different
  graphs must yield different outlines.
- Every section's source_study_ids must be real ids present in the frame.
- {language_instruction(language)}

Project graph frame (project, nodes with themes/sentiment, edges, build order, open questions,
and each study's compact content):
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_meta_outline_payload(payload: dict[str, Any], study_ids: list[str] | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Meta outline must be a JSON object.")
    allowed = set(study_ids or [])
    sections = []
    for i, s in enumerate(payload.get("sections", []) or []):
        if not isinstance(s, dict) or not str(s.get("heading", "")).strip():
            continue
        srcs = [str(x).strip() for x in (s.get("source_study_ids", []) or []) if str(x).strip()]
        if allowed:
            srcs = [x for x in srcs if x in allowed]
        sections.append({
            "id": f"sec{i + 1}",
            "heading": str(s["heading"]).strip()[:200],
            "theme_tags": _strings(s.get("theme_tags", []) or [], 8, 40),
            "source_study_ids": srcs[:50],
            "intent": str(s.get("intent", "")).strip()[:400],
        })
    if not sections:
        raise ValueError("Meta outline must contain at least one section with a heading.")
    return {"build_order_narrative": str(payload.get("build_order_narrative", "")).strip()[:6000],
            "sections": sections[:40]}


def build_meta_section_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    return f"""You are authoring ONE section of a research meta-report. Write it grounded in the
source studies provided — every load-bearing claim must cite a study (and, where possible, the
council inside it).

Return ONLY one JSON object with exactly these keys:
markdown: string (the section body in Markdown; clear, concise, honest — preserve dissent and
  non-targets where relevant; do not invent consensus)
citations: array of objects {{study_id:string, council_id:string (may be empty), quote:string}}
  (the provenance behind the section's claims; use study ids/council ids from the frame)

Rules:
- Ground every claim; a section with zero citations is wrong. Use only ids present in the frame.
- {language_instruction(language)}

Section frame (heading + intent + the full content of the source studies + their councils):
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_meta_section_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Meta section must be a JSON object.")
    citations = []
    for c in payload.get("citations", []) or []:
        if isinstance(c, dict) and str(c.get("study_id", "")).strip():
            citations.append({"study_id": str(c["study_id"]).strip()[:80],
                              "council_id": str(c.get("council_id", "")).strip()[:80],
                              "quote": str(c.get("quote", "")).strip()[:600]})
    return {"markdown": str(payload.get("markdown", "")).strip()[:20000], "citations": citations[:50]}


# ===================================================================== #
# Synthesis — consolidate an ordered chain of councils into learnings.   #
# ===================================================================== #

def build_synthesis_prompt(frame: dict[str, Any], language: str | None = None) -> str:
    return f"""You synthesize an ordered CHAIN of councils (a study arc) into cross-council learnings.
This is like the meta-analysis over several iterations of user studies.

Return ONLY one JSON object with exactly these keys:
arc_narrative: string (the trajectory: what we started with -> how positions/sentiment evolved across the councils in order -> where we landed)
gesamtbild: string (the overall picture)
handlungsempfehlungen: array of {{text, aufwand (1-5), nutzen (1-5)}} (prioritized actions on an effort/value matrix; plain strings also accepted, then unscored)
positionierung: string (positioning statement(s) implied by the evidence)
pain_solvers: array of strings (the validated pains/delight-engines the product addresses)
segmente: array of objects {{segment:string, stance:string, why:string}} (who to win, who is a deliberate non-target)
offene_fragen: array of strings (open questions / what to study next)
references: array of objects {{council_id:string, role:string}} (each council's role in the arc)
citations: array of objects {{kind:"evidence"|"recall"|"council", ref:string, quote:string}}
  (inline provenance for the load-bearing conclusions: when a pain_solver / positionierung /
  recommendation rests on attached real EVIDENCE or a specific RECALLed fact, cite it here using
  the ids from frame.provenance; council quotes use kind="council" + the council_id. May be empty.)
voices: array of objects, ONE per persona that appears in the chain — the structured per-persona record:
  {{persona_id:string, persona_name:string, segment:string (which segment from `segmente` they belong to),
    sentiment: one of "positiv"|"bedingt"|"neutral"|"skeptisch"|"ablehnend",
    relevance: one of "stark"|"teilweise"|"kaum"|"irrelevant" (how much the topic touches THEIR work),
    key_argument:string (the ONE-LINE reason WHY they hold this stance — the single most important point, in their voice),
    shift: object {{from:string, to:string, trigger:string, council_id:string}} OR null
      (ONLY if their stance moved across the chain — e.g. neutral->positiv — with the concrete argument/feature that moved them and the council where it happened),
    evidence: array of objects {{council_id:string, quote:string}} (1-3 grounded quotes from that persona's turns/votes)}}
status: "in_progress" | "done"  (is the study arc finished, given the goal?)
next_council_question: string (ONLY if status=in_progress: the SELF-CONTAINED question to run as the next council — see rule below; else "")
stop_reason: string (ONLY if status=done: why you stop — goal reached / no productive follow-up / max councils)

Rules:
- Capture the PROGRESSION, do not flatten: how did sentiment/positions change across the ordered councils?
- Keep every conclusion traceable to a council (use references; mention which council a learning came from).
- Be honest: preserve who stays neutral/negative and why that is fine; do not invent consensus or product enthusiasm.
- PROVENANCE: prefer conclusions you can ground. Where `frame.provenance` offers attached evidence or
  recalled facts that back a pain_solver / positioning / recommendation, cite them in `citations`. Never
  fabricate a citation ref — only use ids present in the frame.
- VOICES: author one voice per distinct persona across the chain. `key_argument` must be the persona's
  actual point (grounded in their turns/votes), not a generic label. Set `shift` ONLY when the evidence shows
  a real change of stance across councils; otherwise null. `relevance` reflects how much the topic touches the
  persona's own work — independent of whether they like the product (a skeptic can have relevance "stark").
  `sentiment` and `relevance` are independent axes. Use the persona_id/persona_name exactly as in the frame.
- ITERATION DECISION (driver loop): given the `goal`, decide whether ANOTHER council
  would yield materially new insight. If yes → status="in_progress" and write
  `next_council_question` as a **fully self-contained** prompt: the personas are
  STATELESS across councils and remember nothing, so it must include all needed
  context (the product briefing essentials + the precise new angle) to stand alone.
  If the goal is reached or follow-ups would only repeat → status="done" + stop_reason.
- {language_instruction(language)}

Frame (start input + the councils in order with exec_summaries, per-persona turns and votes — use the turns/votes to author `voices`):
{json.dumps(frame, indent=2, ensure_ascii=False)}
"""


def validate_synthesis_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("Synthesis must be a JSON object.")
    seg = []
    for sgm in payload.get("segmente", []) or []:
        if isinstance(sgm, dict) and str(sgm.get("segment", "")).strip():
            seg.append({"segment": str(sgm["segment"]).strip()[:120],
                        "stance": str(sgm.get("stance", "")).strip()[:60],
                        "why": str(sgm.get("why", "")).strip()[:400]})
    refs = []
    for r in payload.get("references", []) or []:
        if isinstance(r, dict) and str(r.get("council_id", "")).strip():
            refs.append({"council_id": str(r["council_id"]).strip()[:80],
                         "role": str(r.get("role", "")).strip()[:300]})
    sentiments = {"positiv", "bedingt", "neutral", "skeptisch", "ablehnend"}
    relevances = {"stark", "teilweise", "kaum", "irrelevant"}
    voices = []
    for v in payload.get("voices", []) or []:
        if not isinstance(v, dict):
            continue
        pid = str(v.get("persona_id", "")).strip()
        if not pid:
            continue
        sent = str(v.get("sentiment", "")).strip().lower()
        rel = str(v.get("relevance", "")).strip().lower()
        shift = v.get("shift")
        sh = None
        if isinstance(shift, dict) and (str(shift.get("trigger", "")).strip() or str(shift.get("to", "")).strip()):
            sh = {"from": str(shift.get("from", "")).strip()[:40], "to": str(shift.get("to", "")).strip()[:40],
                  "trigger": str(shift.get("trigger", "")).strip()[:400], "council_id": str(shift.get("council_id", "")).strip()[:80]}
        ev = []
        for e in v.get("evidence", []) or []:
            if isinstance(e, dict) and str(e.get("quote", "")).strip():
                ev.append({"council_id": str(e.get("council_id", "")).strip()[:80], "quote": str(e["quote"]).strip()[:600]})
        voices.append({
            "persona_id": pid[:80],
            "persona_name": str(v.get("persona_name", "")).strip()[:120],
            "segment": str(v.get("segment", "")).strip()[:120],
            "sentiment": sent if sent in sentiments else "neutral",
            "relevance": rel if rel in relevances else "teilweise",
            "key_argument": str(v.get("key_argument", "")).strip()[:400],
            "shift": sh,
            "evidence": ev[:3],
        })
    cite_kinds = {"evidence", "recall", "council"}
    citations = []
    for c in payload.get("citations", []) or []:
        if not isinstance(c, dict) or not str(c.get("ref", "")).strip():
            continue
        kind = str(c.get("kind", "")).strip().lower()
        citations.append({
            "kind": kind if kind in cite_kinds else "council",
            "ref": str(c["ref"]).strip()[:80],
            "quote": str(c.get("quote", "")).strip()[:600],
        })
    return {
        "arc_narrative": str(payload.get("arc_narrative", "")).strip()[:6000],
        "gesamtbild": str(payload.get("gesamtbild", "")).strip()[:4000],
        "handlungsempfehlungen": _recs(payload.get("handlungsempfehlungen", []) or [], 20),
        "positionierung": str(payload.get("positionierung", "")).strip()[:2000],
        "pain_solvers": _strings(payload.get("pain_solvers", []) or [], 20, 400),
        "segmente": seg[:30],
        "offene_fragen": _strings(payload.get("offene_fragen", []) or [], 20, 400),
        "references": refs[:50],
        "citations": citations[:50],
        "voices": voices[:200],
        "status": ("in_progress" if str(payload.get("status", "")).strip().lower() == "in_progress" else "done"),
        "next_council_question": str(payload.get("next_council_question", "")).strip()[:2000],
        "stop_reason": str(payload.get("stop_reason", "")).strip()[:600],
    }
