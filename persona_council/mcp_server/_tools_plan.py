from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_plan(mcp):
    # ============ Research-plan engine (plan-driven analyze/act/verify; spec/research-plan-engine.md) ===
    # The orchestrator's source of truth. A methodology seeds a plan; freeform starts from one frame.
    # brief_next + record_judgment (above) DISPATCH to the plan when a project has one.
    @mcp.tool()
    def start_project(title: str, goal: str, methodology: str | None = None,
                      persona_ids: list[str] | None = None, description: str = "") -> dict[str, Any]:
        """Create a project + seed its research plan (methodology -> analyze/act/verify scaffolding;
        no methodology -> one dischargeable root frame task). The goal is the How-Might-We."""
        t = time.perf_counter()
        return _env("start_project", services.start_project(title, goal, methodology, persona_ids, description), t)

    @mcp.tool()
    def get_plan(project_id: str) -> dict[str, Any]:
        """The project's research plan (analyze/act/verify task DAG + evidence refs + judgments)."""
        t = time.perf_counter()
        return _env("get_plan", services.get_plan(project_id), t)

    @mcp.tool()
    def export_plan_md(project_id: str) -> dict[str, Any]:
        """Render the plan as a human-readable, bucketed plan.md (analyze/act/verify + status + gates)."""
        t = time.perf_counter()
        return _env("export_plan_md", {"markdown": services.export_plan_md(project_id)}, t)

    @mcp.tool()
    def add_task(project_id: str, bucket: str, capability: str, title: str, intent: str = "",
                 consumes: list[str] | None = None, requires: dict[str, Any] | None = None,
                 step: str = "", plan_note: str = "") -> dict[str, Any]:
        """Insert a task into the plan (shape the breadth): bucket analyze|act|verify, a capability
        tag, consumes (DAG edges), optional gates. Returns the created task."""
        t = time.perf_counter()
        return _env("add_task", services.add_task(project_id, bucket, capability, title, intent,
                                                  consumes, requires, step, plan_note), t)

    @mcp.tool()
    def record_frame(project_id: str, task_id: str, questions: list[str],
                     hypotheses: list[str] | None = None, memory_refs: list[str] | None = None) -> dict[str, Any]:
        """Discharge an ANALYZE frame task: author research questions + hypotheses grounded in cited
        persona memory (>=1 question + >=1 memory_ref). Understand before concluding."""
        t = time.perf_counter()
        return _env("record_frame", services.record_frame(project_id, task_id, questions, hypotheses, memory_refs), t)

    @mcp.tool()
    def link_evidence(project_id: str, task_id: str, kind: str, evidence_id: str) -> dict[str, Any]:
        """Attach an evidence ref (kind=council|synthesis|artifact|session, id) to a task (usually the
        act task whose run-council/scaffold/session just produced it)."""
        t = time.perf_counter()
        return _env("link_evidence", services.link_evidence(project_id, task_id, {"kind": kind, "id": evidence_id}), t)

    @mcp.tool()
    def complete_task(project_id: str, task_id: str) -> dict[str, Any]:
        """Mark a ready task done. Verify tasks are gate-checked (breadth + gate judgment + artifacts/
        sessions) and rejected until satisfied."""
        t = time.perf_counter()
        return _env("complete_task", services.complete_task(project_id, task_id), t)

    @mcp.tool()
    def assess_progress(project_id: str, task_id: str, rationale: str, evidence_refs: list[str],
                        delta: str = "") -> dict[str, Any]:
        """Record an evidence-backed assessment of progress toward the HMW goal. `delta` is a free
        host judgment (never a number); a non-binding coverage snapshot is attached."""
        t = time.perf_counter()
        return _env("assess_progress", services.assess_progress(project_id, task_id, rationale, evidence_refs, delta), t)

    @mcp.tool()
    def next_action(project_id: str) -> dict[str, Any]:
        """The ready task FULLY loaded for a lean autonomous loop: analyze→grounding (prior
        syntheses + open questions); act→the consumed frame's framed questions + segment-diverse
        suggested participants; verify→the fan + gate. Carries the project recommendation. Use this
        as the single per-iteration call: next_action → author via a subagent → persist."""
        t = time.perf_counter()
        return _env("next_action", services.next_action(project_id), t)

    @mcp.tool()
    def assess_project(project_id: str) -> dict[str, Any]:
        """Project-level meta-assessment (read-only, computed — no LLM verdict): coverage, open
        evidence gates, open questions, a saturation hint, structural gaps, and a computed
        continue/converge/complete/blocked recommendation. Call this every iteration of a long run
        to stay purposeful and to decide when to stop."""
        t = time.perf_counter()
        return _env("assess_project", services.assess_project(project_id), t)
