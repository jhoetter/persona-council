"""Chart-kind CATALOGUE — the single source of truth for the report `chart` figure-kind.

One entry per chart `of`: its agent-facing "when to use" + the author payload shape, and (for the
author-supplied kinds) the binding to the vendored design-system renderer (sonaloop._charts).

Adding a chart here wires it into the report renderer (web/_report.py via `render_chart`) AND the
agent-facing `suggest_chart_kinds` tool at once — no drift, no second place to edit. The chart
COMPONENTS themselves live in the design system (../sonaloop-design); this module is just the thin
"which chart, when, and how to call it" registry that makes the MCP surface modular.

These are RECOMMENDATIONS the authoring agent picks from, never constraints.
"""
from __future__ import annotations

from typing import Any, Callable

from . import _charts as _C


def _labels(fig: dict) -> list[str] | None:
    return [str(x) for x in (fig.get("labels") or [])] or None


def _columns(fig: dict) -> list[str]:
    return [str(x) for x in (fig.get("columns") or [])]


def _maybe_num(v) -> float | None:
    try:
        return float(v) if v is not None and v != "" else None
    except (TypeError, ValueError):
        return None


# of → renderer(figure, series) -> html. Each renderer pulls whatever extra figure-level keys it
# needs (labels/columns) so the dispatch stays data-driven. effort_impact is intentionally absent:
# it is source-driven (derived from a synthesis), handled directly in web/_report.py.
_RENDER: dict[str, Callable[[dict, list], str]] = {
    "bar": lambda fig, s: _C.bar_chart(s),
    "pie": lambda fig, s: _C.pie_chart(s),
    "stacked_bar": lambda fig, s: _C.stacked_bar_chart(s),
    "diverging_bar": lambda fig, s: _C.diverging_bar_chart(s),
    "gauge": lambda fig, s: _C.gauge_chart(s),
    "dot_plot": lambda fig, s: _C.dot_plot_chart(s),
    "heatmap": lambda fig, s: _C.heatmap_chart(_columns(fig), s),
    "line": lambda fig, s: _C.line_chart(s, labels=_labels(fig), target=_maybe_num(fig.get("target"))),
    "burnup": lambda fig, s: _C.burnup_chart(s, labels=_labels(fig), target=_maybe_num(fig.get("target")),
                                             now=_maybe_num(fig.get("now"))),
    "stacked_area": lambda fig, s: _C.stacked_area_chart(s, labels=_labels(fig)),
    "column": lambda fig, s: _C.column_chart(s, table=bool(fig.get("table"))),
    "strip": lambda fig, s: _C.strip_chart(s, min_value=_maybe_num(fig.get("min")),
                                           max_value=_maybe_num(fig.get("max")),
                                           unit=str(fig.get("unit") or "")),
    "progress_strip": lambda fig, s: _C.progress_strip(s),
    "stats": lambda fig, s: _C.stats_chart(s),
}

# Agent-facing catalogue — ordered roughly by how common the pick is. `series` documents the
# per-item author shape; `figure` notes any extra figure-level keys the kind reads.
CHART_KINDS: list[dict[str, Any]] = [
    {"of": "bar", "name": "Bar",
     "when_to_use": "Rank or compare one value across a few items (counts, scores, mentions).",
     "series": "[{label, value, color?}]"},
    {"of": "pie", "name": "Pie / donut",
     "when_to_use": "Parts of a whole — a distribution or sentiment split (≤ ~6 slices).",
     "series": "[{label, value, color?}]"},
    {"of": "stacked_bar", "name": "Stacked bar",
     "when_to_use": "Composition per category — how each item breaks down by series (e.g. stance per theme).",
     "series": "[{label, segments: [{label, value, color?}]}]"},
    {"of": "diverging_bar", "name": "Diverging bar",
     "when_to_use": "Net lean around a centre axis — for↔against, support/oppose, before·after.",
     "series": "[{label, positive, negative}]"},
    {"of": "gauge", "name": "Gauge / radial",
     "when_to_use": "A single KPI / % complete / confidence score as a progress ring.",
     "series": "[{label, value, max?, color?}]"},
    {"of": "dot_plot", "name": "Dot / range",
     "when_to_use": "The spread of N voices on a scale (default 1–5) — surfaces disagreement a mean hides.",
     "series": "[{label, values: [num], color?}]"},
    {"of": "heatmap", "name": "Heatmap / matrix",
     "when_to_use": "A 2D scoring matrix — option × criteria, or persona × theme; cells tinted by value.",
     "series": "[{label, values: [num]}]", "figure": "columns: [str]  (the column headers)"},
    {"of": "line", "name": "Line / trend",
     "when_to_use": "A trend across an ordered sequence (e.g. confidence across council rounds); "
                    "a single series gets a soft band fill.",
     "series": "[{label, points: [num], color?}]",
     "figure": "labels: [str] (x-axis ticks) · target: num (dotted reference line)"},
    {"of": "stats", "name": "Stats / KPI row",
     "when_to_use": "Headline metrics as big-number tiles (N personas · % agreement · mean confidence) — "
                    "also the stat header above a burnup.",
     "series": "[{label, value, sub?, color?}]  (value may be a pre-formatted string like '72%'; "
               "sub is a small secondary line)"},
    {"of": "progress_strip", "name": "Progress strip",
     "when_to_use": "Composition as ONE segmented status bar + count/% legend (finding status, sentiment "
                    "split) — denser and calmer than a pie inline.",
     "series": "[{label, value, color?}]"},
    {"of": "column", "name": "Column (vertical bars)",
     "when_to_use": "A distribution over an ordered category axis (scores 1–5, counts per status); "
                    "segments stack composition; table:true appends a breakdown table.",
     "series": "[{label, value, color?}] or [{label, segments: [{label, value}]}]",
     "figure": "table: bool  (append the breakdown table)"},
    {"of": "strip", "name": "Strip (continuous dots)",
     "when_to_use": "Per-voice values on a REAL scale (prices, latencies) — one dot per value, one lane "
                    "per row; the continuous sibling of dot_plot.",
     "series": "[{label, values: [num], color?}]",
     "figure": "min/max: num (fix the scale) · unit: str ('€', 'd')"},
    {"of": "burnup", "name": "Burn-up / progress over time",
     "when_to_use": "Cumulative progress against a target (consensus across rounds, scope vs completed) — "
                    "band-filled lines, dotted ideal line, hatched future after `now`.",
     "series": "[{label, points: [num], color?}]",
     "figure": "labels: [str] · target: num (dotted ideal) · now: num (point index of today)"},
    {"of": "stacked_area", "name": "Stacked area / flow",
     "when_to_use": "How a composition SHIFTS across an ordered sequence (stance per round, theme volume) — "
                    "soft stacked bands, cumulative-flow style.",
     "series": "[{label, points: [num], color?}]  (one band per series, stacked in order)",
     "figure": "labels: [str]  (x-axis ticks)"},
    {"of": "effort_impact", "name": "Effort · impact 2×2",
     "when_to_use": "A synthesis's recommendations as a leverage 2×2 (auto-derived — set source_id, no series).",
     "series": "— set source_id to the synthesis"},
]

# Guard: every author-renderable kind must appear in the catalogue (and vice versa, minus effort_impact).
assert set(_RENDER) | {"effort_impact"} == {k["of"] for k in CHART_KINDS}


def render_chart(of: str, figure: dict, series: list) -> str:
    """Render an author-supplied chart figure to HTML via the design-system components.

    Returns "" for kinds with no author renderer (e.g. effort_impact, which is source-driven and
    handled by the caller) and for unknown `of` (so a typo renders nothing rather than a wrong chart).
    """
    fn = _RENDER.get(of)
    return fn(figure, series) if fn else ""


def chart_kinds() -> dict[str, Any]:
    """The chart catalogue for the authoring agent: which chart to use when + its payload shape."""
    return {
        "kind": "chart_kinds",
        "note": ("Attach a chart as a section figure: "
                 "{kind:'chart', of:'<of>', series:[…], caption?}. "
                 "Pick the chart that fits the point — these are recommendations, not constraints."),
        "items": CHART_KINDS,
    }
