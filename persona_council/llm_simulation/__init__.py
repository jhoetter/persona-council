from __future__ import annotations

import json
from typing import Any

from ..config import language_instruction
from ._schemas import (
    ACTIVITY_SCHEMA_KEYS,
    PROFILE_SCHEMA_KEYS,
    DAY_PLAN_SCHEMA_KEYS,
    PERSONA_ANSWER_SCHEMA_KEYS,
    COUNCIL_TURN_SCHEMA_KEYS,
    COUNCIL_SYNTHESIS_SCHEMA_KEYS,
    COUNCIL_SELECTION_SCHEMA_KEYS,
    _KINDS,
    _CRITIC_DIMENSIONS,
    _json_from_text,
    _call_llm_json,
    _require_keys,
    _strings,
    _recs,
)
from ._prompts import (
    build_profile_prompt,
    build_consolidation_prompt,
    build_plan_prompt,
    build_digest_prompt,
    build_persona_revision_prompt,
    build_eval_critic_prompt,
    build_cohort_critic_prompt,
    build_evidence_check_prompt,
    build_meta_outline_prompt,
    build_meta_section_prompt,
    build_synthesis_prompt,
)
from ._validators import (
    validate_activity_payload,
    validate_profile_payload,
    generate_profile_with_llm,
    validate_day_plan_payload,
    generate_day_plan_with_llm,
    generate_activity_with_llm,
    generate_activity,
    generate_persona_answer_with_llm,
    generate_council_turn_with_llm,
    generate_council_selection_with_llm,
    generate_council_synthesis_with_llm,
    validate_memory_deltas_payload,
    validate_plan_payload,
    validate_digest_payload,
    validate_persona_revision_payload,
    validate_eval_critic_payload,
    validate_cohort_critic_payload,
    validate_evidence_check_payload,
    validate_meta_outline_payload,
    validate_meta_section_payload,
    validate_synthesis_payload,
)
