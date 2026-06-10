from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_calibration(mcp):
    # ===== Calibration against real data — the backtest loop (docs/calibration.md) =====
    @mcp.tool()
    def record_prediction_outcome(project_id: str, prediction_ref: dict[str, Any], observed: Any,
                                  source: dict[str, Any], note: str = "") -> dict[str, Any]:
        """Match ONE real outcome to one predicted behavior and score it. prediction_ref:
        {kind: session|council|synthesis, id, anchor: <pb id>}. observed: bool (it happened)
        or a rate 0..1 (35% of real users abandoned). source: a resolvable Ref (survey
        responses / evidence / {kind:'external', text}). The Brier score is DERIVED — both
        raw values stay on the auditable record."""
        t = time.perf_counter()
        return _env("record_prediction_outcome",
                    services.record_prediction_outcome(project_id, prediction_ref, observed, source, note), t)

    @mcp.tool()
    def calibration_report(project_id: str | None = None) -> dict[str, Any]:
        """Measure calibration NOW (mean Brier + hit rate + the reliability curve over
        scored predictions, plus the hypothesis hit rate) and persist the snapshot — each
        call extends the series calibration_trend reads."""
        t = time.perf_counter()
        return _env("calibration_report", services.calibration_report(project_id), t)

    @mcp.tool()
    def calibration_trend(project_id: str | None = None) -> dict[str, Any]:
        """Calibration quality OVER TIME: the persisted report series, the Brier delta
        first→last, and whether the loop is improving — the first-class trend metric."""
        t = time.perf_counter()
        return _env("calibration_trend", services.calibration_trend(project_id), t)

    @mcp.tool()
    def brief_calibration(project_id: str | None = None) -> dict[str, Any]:
        """Gather the MISSES (refuted bets, high-error predictions, each with its evidence
        trail) so YOU author corrections: persona patches where a trait drove the miss, new
        grounding where reality is the new evidence. Correct patterns, not noise."""
        t = time.perf_counter()
        return _env("brief_calibration", services.brief_calibration(project_id), t)

    @mcp.tool()
    def record_calibration_round(corrections: list[dict[str, Any]], note: str = "",
                                 project_id: str | None = None) -> dict[str, Any]:
        """Stamp one authored correction round ({persona_id, text, refs?} each) and snapshot
        a fresh calibration report — the before/after marker that makes 'corrections
        measurably improve predictions' checkable on the trend."""
        t = time.perf_counter()
        return _env("record_calibration_round",
                    services.record_calibration_round(corrections, note, project_id), t)
