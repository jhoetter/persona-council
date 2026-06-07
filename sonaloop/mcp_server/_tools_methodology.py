from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_methodology(mcp):
    # ============ Methodologies: tag-driven constellation SEEDS for the plan engine ============
    # A methodology = a DAG of steps carrying OPEN TAGS. It is purely data: starting one SEEDS the
    # research plan (analyze/act/verify) — the single runtime engine is the plan (see _tools_plan +
    # spec/hx3-engine-collapse.md). Common building blocks are SUGGESTED as data (suggest_*), never
    # enforced. See spec/methodology-constellations.md.
    @mcp.tool()
    def suggest_capabilities() -> dict[str, Any]:
        """SUGGESTED capability tags (explore/cluster/decide/build/test/synthesize, …) for a step's
        `tags`. Recommendations only — adopt, tweak, or invent your own; the engine never enforces."""
        t = time.perf_counter()
        return _env("suggest_capabilities", services.suggest_capabilities(), t)

    @mcp.tool()
    def suggest_roles() -> dict[str, Any]:
        """SUGGESTED role tags for a step's produces.role. Recommendations only."""
        t = time.perf_counter()
        return _env("suggest_roles", services.suggest_roles(), t)

    @mcp.tool()
    def suggest_artifact_types() -> dict[str, Any]:
        """SUGGESTED artifact-type tags for produces.artifact_type / requires.*_tags (matched by
        tag-equality, no string is special-cased). Recommendations only."""
        t = time.perf_counter()
        return _env("suggest_artifact_types", services.suggest_artifact_types(), t)

    @mcp.tool()
    def suggest_methodologies() -> dict[str, Any]:
        """SUGGESTED whole-constellation templates to copy and adapt (the registered methodologies
        + any extra templates). Tags are free; nothing here constrains what you may author."""
        t = time.perf_counter()
        return _env("suggest_methodologies", services.suggest_methodologies(), t)

    @mcp.tool()
    def list_methodologies() -> dict[str, Any]:
        """List available methodologies (built-in + user-defined) and their step keys."""
        t = time.perf_counter()
        return _env("list_methodologies", services.list_methodologies(), t)

    @mcp.tool()
    def get_methodology(key: str) -> dict[str, Any]:
        """The full constellation spec for one methodology (steps, tags, consumes, produces, requires)."""
        t = time.perf_counter()
        return _env("get_methodology", services.get_methodology(key), t)

    # start_methodology_project — RETIRED (a back-compat alias for start_project(methodology=...); M1).
    # Use start_project with methodology=<key>. The service fn remains for back-compat callers.

    @mcp.tool()
    def set_project_methodology(project_id: str, methodology_key: str) -> dict[str, Any]:
        """Bind an existing research project to a methodology by (re)seeding its plan from the
        constellation. The plan is the single engine; drive it via the plan tools."""
        t = time.perf_counter()
        return _env("set_project_methodology", services.set_project_methodology(project_id, methodology_key), t)

    @mcp.tool()
    def brief_next(project_id: str) -> dict[str, Any]:
        """GATHER what the plan's ready frontier needs now: the primary ready task (+ the full ready
        set), its bucket/capability, consumed frames, and unmet gates. The plan router — for richer
        per-iteration grounding use next_action."""
        t = time.perf_counter()
        return _env("brief_next", services.brief_next(project_id), t)

    @mcp.tool()
    def record_judgment(project_id: str, task_id: str, gate_tag: str, decided: bool, rationale: str,
                        evidence_refs: list[str] | None = None) -> dict[str, Any]:
        """Record an evidence-backed LLM gate judgment on a plan TASK (usually a verify task). `gate_tag`
        is a FREE tag (e.g. divergence_complete, or whatever the verify task requires). The engine
        requires its presence to complete the verify but never dictates its content or a number."""
        t = time.perf_counter()
        return _env("record_judgment",
                    services.record_judgment(project_id, task_id, gate_tag, decided, rationale, evidence_refs), t)
