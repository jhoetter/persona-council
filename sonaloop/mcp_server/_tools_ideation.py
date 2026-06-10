"""Structured HMW ideation tools (taxonomy job `ideation_hmw`, protocol reframe → diverge →
converge) — the gather/write-back surface over services/_ideation.py. The host authors every HMW
question, idea, cluster tag and rationale; the server validates structure and persists on existing
primitives (open questions, idea notes, an `ideation` council block decision records can cite)."""
from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_ideation(mcp) -> None:
    # ============ Ideation (How-Might-We): reframe → diverge → converge ============

    @mcp.tool()
    def record_hmw_reframe(project_id: str, problem: str, hmws: list[Any]) -> dict[str, Any]:
        """REFRAME (ideation_hmw protocol step 1): persist your How-Might-We reframe of a raw problem —
        3 to 5 host-authored HMW questions, each a string or {question, prediction?}. Every question
        becomes a stable question record (the `hmw_ref` ideas attach to). Supply a falsifiable
        `prediction` ({metric, expected_value|expected_direction}) for an HMW you can bet on and it is
        ALSO stamped as a real hypothesis (record_hypothesis validation applies). Then run the diverge
        council (brief_council with these questions) and record_ideas."""
        t = time.perf_counter()
        return _env("record_hmw_reframe", services.record_hmw_reframe(project_id, problem, hmws), t)

    @mcp.tool()
    def record_ideas(project_id: str, ideas: list[dict[str, Any]]) -> dict[str, Any]:
        """DIVERGE (step 2): persist council-generated ideas as first-class, queryable idea records.
        Each idea is {text, persona_id (the source voice — must exist), hmw_ref (the recorded HMW
        question it answers — must resolve), cluster? (your affinity tag)}. Unattributed or unanchored
        ideas are REJECTED — attribution is the protocol. Ideas land in the project graph (sections and
        edges work on them); query them with list_ideas; converge with record_ideation_summary."""
        t = time.perf_counter()
        return _env("record_ideas", {"ideas": services.record_ideas(project_id, ideas)}, t)

    @mcp.tool()
    def list_ideas(project_id: str, hmw_ref: str | None = None, persona_id: str | None = None,
                   cluster: str | None = None) -> dict[str, Any]:
        """The project's idea records, filterable by HMW question, source persona, or cluster tag —
        the synthesis surface for the diverge output."""
        t = time.perf_counter()
        return _env("list_ideas", {"ideas": services.list_ideas(project_id, hmw_ref, persona_id, cluster)}, t)

    @mcp.tool()
    def record_ideation_summary(project_id: str, problem: str, shortlist: list[dict[str, Any]],
                                statements: list[dict[str, Any]] | None = None, summary: str = "",
                                exec_summary: str = "", selection_reason: str = "",
                                key: str | None = None) -> dict[str, Any]:
        """CONVERGE (step 3): persist the FORCED ranking as an ideation summary. `shortlist` is your
        ordered picks — [{idea_id, rationale}], rank = position — every pick must be a recorded idea
        and carry a rationale (a ranking without reasons is rejected). Stored as a CouncilSession with
        an `ideation` block (problem + HMW questions + the full idea pool + the ranked shortlist); the
        returned `cite_as` ref plugs straight into record_decision's based_on — the ideation output IS
        decision-record evidence. Pass a stable `key` for a deterministic id (idempotent upsert)."""
        t = time.perf_counter()
        return _env("record_ideation_summary", services.record_ideation_summary(project_id, problem, shortlist, statements, summary, exec_summary, selection_reason, key), t)

    @mcp.tool()
    def get_ideation(session_id: str) -> dict[str, Any]:
        """Fetch one ideation summary by session id — problem, HMW questions, idea pool, ranked
        shortlist, and the ready-made cite_as ref for record_decision."""
        t = time.perf_counter()
        return _env("get_ideation", services.get_ideation(session_id), t)
