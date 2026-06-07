from __future__ import annotations

import json
from typing import Any


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




def _require_keys(payload: dict[str, Any], schema: dict[str, Any], label: str) -> dict[str, Any]:
    for key, expected in schema.items():
        if key not in payload:
            raise ValueError(f"{label} payload missing `{key}`.")
        if not isinstance(payload[key], expected):
            raise ValueError(f"{label} payload `{key}` has wrong type.")
    return payload


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


_KINDS = {"project", "person", "org", "building", "authority", "topic"}


_CRITIC_DIMENSIONS = ["anti_steering", "in_character", "dialogue_believability",
                      "arc_plausibility", "mundane_balance"]
