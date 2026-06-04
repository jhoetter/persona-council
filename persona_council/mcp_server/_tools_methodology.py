from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_methodology(mcp):
    # ============ Methodology engine: tag-driven constellations (structure+LLM-judged) ============
    # A methodology = a DAG of steps carrying OPEN TAGS. The engine is tag-agnostic; common
    # building blocks are SUGGESTED as data (suggest_*), never enforced. See
    # spec/methodology-constellations.md. Old tool names (brief_phase/record_exploration/
    # record_convergence/advance_phase) remain as aliases.
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

    @mcp.tool()
    def start_methodology_project(title: str, goal: str, methodology_key: str,
                                  persona_ids: list[str] | None = None, description: str = "") -> dict[str, Any]:
        """Create a research project bound to a methodology (the goal is the How-Might-We)."""
        t = time.perf_counter()
        return _env("start_methodology_project",
                    services.start_methodology_project(title, goal, methodology_key, persona_ids, description), t)

    @mcp.tool()
    def set_project_methodology(project_id: str, methodology_key: str) -> dict[str, Any]:
        """Bind an existing research project to a methodology (resets the frontier to the roots)."""
        t = time.perf_counter()
        return _env("set_project_methodology", services.set_project_methodology(project_id, methodology_key), t)

    @mcp.tool()
    def brief_next(project_id: str) -> dict[str, Any]:
        """GATHER what the ready frontier needs now: the primary ready step (+ the full ready set),
        its tags, strategy, unmet `requires`, consumed nodes. The engine's heartbeat — a fan step:
        record_node each + judge its gate_tag; a decide step: record_decision."""
        t = time.perf_counter()
        return _env("brief_next", services.brief_next(project_id), t)

    @mcp.tool()
    def brief_phase(project_id: str) -> dict[str, Any]:
        """Alias of brief_next, shaped like the legacy single-step brief."""
        t = time.perf_counter()
        return _env("brief_phase", services.brief_phase(project_id), t)

    @mcp.tool()
    def record_node(project_id: str, title: str, council_ids: list[str], payload: dict[str, Any],
                    start_input: str = "", step_id: str | None = None) -> dict[str, Any]:
        """Record ONE exploration node (a synthesis over council(s)) against a ready fan step."""
        t = time.perf_counter()
        return _env("record_node",
                    services.record_node(project_id, title, council_ids, payload, start_input, step_id=step_id), t)

    @mcp.tool()
    def record_exploration(project_id: str, title: str, council_ids: list[str], payload: dict[str, Any],
                           start_input: str = "") -> dict[str, Any]:
        """Alias of record_node."""
        t = time.perf_counter()
        return _env("record_exploration",
                    services.record_exploration(project_id, title, council_ids, payload, start_input), t)

    @mcp.tool()
    def record_judgment(project_id: str, step_id: str, gate_tag: str, decided: bool, rationale: str,
                        evidence_refs: list[str] | None = None) -> dict[str, Any]:
        """Record an evidence-backed LLM gate judgment on a step. `gate_tag` is a FREE tag (e.g.
        divergence_complete, or whatever the consuming decide step requires). The engine requires
        its presence to decide but never dictates its content or a number."""
        t = time.perf_counter()
        return _env("record_judgment",
                    services.record_judgment(project_id, step_id, gate_tag, decided, rationale, evidence_refs), t)

    @mcp.tool()
    def record_decision(project_id: str, title: str, from_node_ids: list[str], payload: dict[str, Any],
                        start_input: str = "", step_id: str | None = None) -> dict[str, Any]:
        """Consolidate a fan into one decision node on a ready decide step (validates the invariants)."""
        t = time.perf_counter()
        return _env("record_decision",
                    services.record_decision(project_id, title, from_node_ids, payload, start_input, step_id=step_id), t)

    @mcp.tool()
    def record_convergence(project_id: str, title: str, from_node_ids: list[str], payload: dict[str, Any],
                           start_input: str = "") -> dict[str, Any]:
        """Alias of record_decision."""
        t = time.perf_counter()
        return _env("record_convergence",
                    services.record_convergence(project_id, title, from_node_ids, payload, start_input), t)

    @mcp.tool()
    def advance(project_id: str, step_id: str | None = None) -> dict[str, Any]:
        """Mark a ready step complete and recompute the frontier (or loop back); errors if a
        decide step has no decision node yet."""
        t = time.perf_counter()
        return _env("advance", services.advance(project_id, step_id), t)

    @mcp.tool()
    def advance_phase(project_id: str) -> dict[str, Any]:
        """Alias of advance (primary ready step)."""
        t = time.perf_counter()
        return _env("advance_phase", services.advance_phase(project_id), t)

    @mcp.tool()
    def get_methodology_state(project_id: str) -> dict[str, Any]:
        """Step-by-step progress: status, node counts, judgments, decision nodes, tags, the DAG."""
        t = time.perf_counter()
        return _env("get_methodology_state", services.get_methodology_state(project_id), t)
