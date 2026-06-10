from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_hypotheses(mcp):
    # ===== Hypotheses — falsifiable predictions scored against reality (sim-vs-reality calibration) =====
    # House triplet: brief_hypothesis (gather: contested findings, predicted behaviors, open
    # questions worth betting on) → the host authors the statement + checkable prediction →
    # record_hypothesis (validate + persist, status=open). When reality answers,
    # record_hypothesis_result attaches the observation and DERIVES the verdict (both raw values
    # kept — auditable, never asserted); eval_scorecard aggregates the hit-rate across resolved
    # hypotheses into eval_reports — the record that shows the simulations are predictive, not
    # merely plausible.
    @mcp.tool()
    def brief_hypothesis(project_id: str) -> dict[str, Any]:
        """GATHER what is worth betting on: the project's contested findings (councils whose
        statements span support AND opposition), the predicted behaviors recorded in usability
        sessions (promotable into hypotheses without reshaping), and the open questions. Author
        the falsifiable statement + checkable prediction, then record_hypothesis."""
        t = time.perf_counter()
        return _env("brief_hypothesis", services.brief_hypothesis(project_id), t)

    @mcp.tool()
    def record_hypothesis(project_id: str, text: str, prediction: dict[str, Any],
                          derived_from: list[dict[str, Any]] | None = None,
                          key: str | None = None) -> dict[str, Any]:
        """Persist a host-authored hypothesis with status=open — the bet stamped BEFORE reality
        answers. `prediction` = {metric, expected_value (+tolerance?) OR expected_direction
        (increase|decrease), confidence (0..1)?} — unfalsifiable predictions (no metric, no
        expected value/direction) are REJECTED. `derived_from` = Refs to what the bet
        operationalizes ({kind: open_question|council|synthesis|session, id, anchor?, role});
        unresolvable refs are REJECTED. A stable `key` gives a deterministic id (idempotent
        upsert); a resolved hypothesis cannot be re-authored."""
        t = time.perf_counter()
        return _env("record_hypothesis",
                    services.record_hypothesis(project_id, text, prediction, derived_from, key), t)

    @mcp.tool()
    def record_hypothesis_result(hypothesis_id: str, observed_value: Any, source: dict[str, Any],
                                 note: str = "") -> dict[str, Any]:
        """Attach the REAL-WORLD observation and flip the status. `source` is a Ref that must
        RESOLVE: a survey's imported responses ({kind:'survey', id}), attached evidence
        ({kind:'evidence', id}), a council/synthesis/session — or a free observation carried as
        text ({kind:'external', text}). The status (validated|refuted|inconclusive) is DERIVED by
        comparing observed against predicted; both raw values stay on the record, your argument
        goes in `note` — the verdict is auditable, never asserted."""
        t = time.perf_counter()
        return _env("record_hypothesis_result",
                    services.record_hypothesis_result(hypothesis_id, observed_value, source, note), t)

    @mcp.tool()
    def drop_hypothesis(hypothesis_id: str, note: str = "") -> dict[str, Any]:
        """Retire an OPEN bet without scoring it (the question became moot, the metric
        unmeasurable). Dropped bets stay on the record but never enter the scorecard — only
        reality may validate or refute. A resolved verdict cannot be dropped after the fact."""
        t = time.perf_counter()
        return _env("drop_hypothesis", services.drop_hypothesis(hypothesis_id, note), t)

    @mcp.tool()
    def eval_scorecard(project_id: str | None = None) -> dict[str, Any]:
        """Aggregate the hit-rate across RESOLVED hypotheses (per project, or global with a
        per-project breakdown) and write the sim-vs-reality calibration record into eval_reports.
        Open/dropped bets are excluded; hit_rate = validated / (validated + refuted) —
        inconclusive resolutions count as resolved but not decisive."""
        t = time.perf_counter()
        return _env("eval_scorecard", services.eval_scorecard(project_id), t)

    @mcp.tool()
    def get_hypothesis(hypothesis_id: str) -> dict[str, Any]:
        """One hypothesis by id — the bet, its prediction, and (once resolved) the recorded
        result with both raw values."""
        t = time.perf_counter()
        return _env("get_hypothesis", services.get_hypothesis(hypothesis_id), t)

    @mcp.tool()
    def list_hypotheses(project_id: str | None = None, status: str | None = None) -> dict[str, Any]:
        """List hypotheses (optionally per project and/or status:
        open|validated|refuted|inconclusive|dropped)."""
        t = time.perf_counter()
        return _env("list_hypotheses", {"hypotheses": services.list_hypotheses(project_id, status)}, t)
