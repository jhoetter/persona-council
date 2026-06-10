from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_predictions(mcp):
    # ========= Predicted behavior (ticket behavioral-prediction-output) =========
    @mcp.tool()
    def suggest_likelihood_levels() -> dict[str, Any]:
        """The CANONICAL likelihood vocabulary for predicted behaviors (rare → certain,
        each with the numeric midpoint calibration scores against) — call before authoring
        predicted_behaviors anywhere (usability outcomes, councils, syntheses). A raw 0..1
        number is also accepted and kept exact; unknown tokens are REJECTED on record."""
        t = time.perf_counter()
        return _env("suggest_likelihood_levels", services.suggest_likelihood_levels(), t)

    @mcp.tool()
    def aggregate_predictions(project_id: str) -> dict[str, Any]:
        """The segment roll-up of every predicted behavior in a project — grouped by
        (action, step, subject) with persona attribution, mean likelihood, evidence refs
        and a by-step funnel ("3 of 5 personas abandon at the price reveal"). Surface this
        in syntheses/reports; promote recurring groups into hypotheses (brief_hypothesis
        carries the same aggregate)."""
        t = time.perf_counter()
        return _env("aggregate_predictions", services.aggregate_predictions(project_id), t)
