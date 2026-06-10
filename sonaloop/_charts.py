"""sonaloop._charts — VENDORED COPY of the sonaloop-design chart components.

Do not edit by hand. Single source of truth: ../sonaloop-design (py/sonaloop_icons/charts.py +
styles/components.css `.sl-chart*`). Refresh with `make icons` / scripts/sync_icons.sh.
Vendored so the PyPI package has no local-path dependency.


The React side is ../../src/charts.tsx; the styling source of truth is ../../styles/components.css
(the `.sl-chart`/`.sl-bar*`/`.sl-pie*`/`.sl-quad*`/`.sl-legend*` classes). These functions emit
self-contained, static, print-safe HTML strings (no JS, no hover-only data) so a chart renders
identically in the Python-SSR app, on the website, and in headless-Chromium PDF/PPTX export.

    from sonaloop_icons.charts import (bar_chart, stacked_bar_chart, pie_chart, gauge_chart, effort_impact)
    bar_chart([{"label": "Plan", "value": 8}, {"label": "Cook", "value": 3}])
    stacked_bar_chart([{"label": "Pricing", "segments": [{"label": "For", "value": 6}, {"label": "Against", "value": 2}]}])
    pie_chart([{"label": "Support", "value": 12}, {"label": "Oppose", "value": 4}])
    gauge_chart([{"label": "Confidence", "value": 72}])  # ring fills value/max; centre shows the %
    diverging_bar_chart([{"label": "Pricing", "positive": 6, "negative": 2}])  # net for↔against
    heatmap_chart(["Cost", "Reach"], [{"label": "Plan A", "values": [2, 5]}])  # option × criteria
    dot_plot_chart([{"label": "Trust the AI", "values": [2, 3, 3, 4, 5]}])  # spread of voices on 1..5
    line_chart([{"label": "Confidence", "points": [2, 3, 5, 4, 6]}], labels=["R1", "R2", "R3", "R4", "R5"])
    effort_impact([{"label": "Auto shopping list", "x": 2, "y": 5}])  # x=effort, y=value (1..5)
    burnup_chart([{"label": "Done", "points": [0, 2, 5, 8]}], target=12, now=3)  # cycle progress
    stacked_area_chart([{"label": "For", "points": [2, 4, 6]}, {"label": "Against", "points": [3, 2, 1]}])
    column_chart([{"label": "1", "value": 2}, {"label": "2", "value": 5}], table=True)  # vertical bars
    strip_chart([{"label": "WTP", "values": [9, 12, 15, 29]}], unit="€")  # continuous dot strip
    stats_chart([{"label": "Personas", "value": 16}, {"label": "Agreement", "value": "72%", "sub": "+9 vs R1"}])
    progress_strip([{"label": "Validated", "value": 9}, {"label": "Open", "value": 4}])  # one 100% bar + legend
    sparkline([3, 5, 4, 6, 5, 8])                       # tiny inline trend (for list rows / table cells)
    progress_pie(11, 16)                                 # tiny inline pie — pairs with "69% of 16"

All text is rendered as-is (already-resolved/translated by the caller — this layer is i18n-agnostic).
Series colours come from position unless an item sets `color`.
"""

from __future__ import annotations

import html
import re
from typing import Any, Sequence

# Position → CSS custom property carrying that series' colour (defined on `.sl-chart`).
_SERIES = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)", "var(--c6)", "var(--c7)"]


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _md(s: Any) -> str:
    """Escape text, then render inline markdown (**bold**, *italic* / _italic_, `code`) — so a chart
    label authored in Markdown reads like the rest of a report instead of showing raw `**` markers."""
    t = _esc(s)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"__(.+?)__", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"<em>\1</em>", t)
    t = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def _color(item: dict, i: int) -> str:
    return str(item.get("color") or _SERIES[i % len(_SERIES)])


def _title(title: str) -> str:
    return f'<div class="sl-chart__title">{_md(title)}</div>' if title else ""


def bar_chart(items: Sequence[dict], *, title: str = "", max_value: float | None = None,
              show_values: bool = True) -> str:
    """Horizontal labelled bars. items: [{label, value, color?}]. Returns "" when nothing is scored."""
    rows = [it for it in items if _num(it.get("value")) is not None]
    if not rows:
        return ""
    mx = max_value if max_value else max((_num(it["value"]) or 0) for it in rows) or 1
    bars = []
    for i, it in enumerate(rows):
        v = _num(it["value"]) or 0
        pct = max(0.0, min(100.0, v / mx * 100)) if mx else 0
        val = f'<span class="sl-bar__val">{_fmt(v)}</span>' if show_values else ""
        bars.append(
            f'<div class="sl-bar">'
            f'<span class="sl-bar__label" title="{_esc(it.get("label"))}">{_md(it.get("label"))}</span>'
            f'<span class="sl-bar__track"><span class="sl-bar__fill" '
            f'style="--v:{pct:.1f}%;--c:{_color(it, i)}"></span></span>{val}</div>')
    return f'<figure class="sl-chart">{_title(title)}<div class="sl-bars">{"".join(bars)}</div></figure>'


def pie_chart(items: Sequence[dict], *, title: str = "", donut: bool = True,
              show_values: bool = True) -> str:
    """Pie/donut of proportions + a legend. items: [{label, value, color?}]. "" when empty/zero."""
    rows = [it for it in items if (_num(it.get("value")) or 0) > 0]
    total = sum(_num(it["value"]) or 0 for it in rows)
    if not rows or total <= 0:
        return ""
    stops, legend, acc = [], [], 0.0
    for i, it in enumerate(rows):
        v = _num(it["value"]) or 0
        c = _color(it, i)
        start = acc / total * 100
        acc += v
        end = acc / total * 100
        stops.append(f"{c} {start:.2f}% {end:.2f}%")
        val = f'<span class="sl-legend__val">{_fmt(v)} · {v / total * 100:.0f}%</span>' if show_values else ""
        legend.append(
            f'<span class="sl-legend__item"><span class="sl-legend__sw" style="--c:{c}"></span>'
            f'<span class="sl-legend__label">{_md(it.get("label"))}</span>{val}</span>')
    cls = "sl-pie sl-pie--donut" if donut else "sl-pie"
    grad = f"conic-gradient({', '.join(stops)})"
    return (f'<figure class="sl-chart">{_title(title)}<div class="sl-pie-wrap">'
            f'<div class="{cls}" style="--slices:{grad}" role="img"></div>'
            f'<div class="sl-legend">{"".join(legend)}</div></div></figure>')


def stacked_bar_chart(items: Sequence[dict], *, title: str = "", max_value: float | None = None,
                      show_values: bool = True) -> str:
    """Horizontal stacked bars + a shared series legend. items: [{label, segments: [{label, value, color?}]}].
    Series colour is keyed by segment label (first-seen order) so a series reads the same in every bar. "" if empty."""
    rows = [it for it in items
            if any(_num(s.get("value")) is not None for s in (it.get("segments") or []))]
    if not rows:
        return ""
    keys: list[str] = []
    for it in rows:
        for s in it["segments"]:
            if s.get("label") not in keys:
                keys.append(s.get("label"))

    def seg_color(s: dict) -> str:
        return str(s.get("color") or _SERIES[max(0, keys.index(s.get("label"))) % len(_SERIES)])

    totals = [sum(max(0.0, _num(s.get("value")) or 0) for s in it["segments"]) for it in rows]
    mx = max_value if max_value else max(totals) or 1
    bars = []
    for it, total in zip(rows, totals):
        segs = "".join(
            f'<span class="sl-bar__seg" title="{_esc(s.get("label"))}: {_fmt(_num(s.get("value")) or 0)}" '
            f'style="flex-grow:{_num(s.get("value")) or 0:g};--c:{seg_color(s)}"></span>'
            for s in it["segments"] if (_num(s.get("value")) or 0) > 0)
        pct = min(100.0, total / mx * 100) if mx else 0
        val = f'<span class="sl-bar__val">{_fmt(total)}</span>' if show_values else ""
        bars.append(
            f'<div class="sl-bar">'
            f'<span class="sl-bar__label" title="{_esc(it.get("label"))}">{_md(it.get("label"))}</span>'
            f'<span class="sl-bar__track"><span class="sl-bar__fill sl-bar__fill--stack" '
            f'style="--v:{pct:.1f}%">{segs}</span></span>{val}</div>')
    # Legend colour comes from each series' first occurrence across the rows.
    first = {s.get("label"): s for it in reversed(rows) for s in it["segments"]}
    legend = "".join(
        f'<span class="sl-legend__item"><span class="sl-legend__sw" style="--c:{seg_color(first[k])}"></span>'
        f'<span class="sl-legend__label">{_md(k)}</span></span>' for k in keys)
    return (f'<figure class="sl-chart">{_title(title)}<div class="sl-bars">{"".join(bars)}</div>'
            f'<div class="sl-legend sl-legend--row" style="margin-top:.9em">{legend}</div></figure>')


def gauge_chart(items: Sequence[dict], *, title: str = "", max_value: float = 100,
                show_values: bool = True) -> str:
    """Radial progress rings (one per item) — a KPI / % complete. items: [{label, value, max?, color?}].
    The ring fills value/max; the centre shows the percentage. "" when nothing is scored."""
    rows = [it for it in items if _num(it.get("value")) is not None]
    if not rows:
        return ""
    gauges = []
    for i, it in enumerate(rows):
        m = _num(it.get("max")) or max_value or 1
        v = _num(it["value"]) or 0
        pct = max(0.0, min(100.0, v / m * 100)) if m else 0
        sub = (f'<span class="sl-gauge__sub">{_fmt(v)} / {_fmt(m)}</span>'
               if show_values and m != 100 else "")
        gauges.append(
            f'<div class="sl-gauge-item">'
            f'<div class="sl-gauge" role="img" style="--p:{pct:.1f};--c:{_color(it, i)}">'
            f'<span class="sl-gauge__val">{round(pct)}%</span></div>'
            f'<span class="sl-gauge__label">{_md(it.get("label"))}</span>{sub}</div>')
    return (f'<figure class="sl-chart">{_title(title)}'
            f'<div class="sl-gauges">{"".join(gauges)}</div></figure>')


def diverging_bar_chart(items: Sequence[dict], *, title: str = "", positive_label: str = "Positive",
                        negative_label: str = "Negative", positive_color: str = "var(--sl-green)",
                        negative_color: str = "var(--sl-red)", max_value: float | None = None,
                        show_values: bool = True) -> str:
    """Net sentiment / for↔against bars around a centre axis. items: [{label, positive, negative}].
    Negative grows left, positive grows right; both share one magnitude scale. "" when empty."""
    rows = [it for it in items
            if _num(it.get("positive")) is not None or _num(it.get("negative")) is not None]
    if not rows:
        return ""
    mx = max_value if max_value else max(
        max(abs(_num(it.get("positive")) or 0), abs(_num(it.get("negative")) or 0)) for it in rows) or 1
    bars = []
    for it in rows:
        pos = max(0.0, _num(it.get("positive")) or 0)
        neg = max(0.0, _num(it.get("negative")) or 0)
        val = f'<span class="sl-dbar__val">+{_fmt(pos)} · −{_fmt(neg)}</span>' if show_values else ""
        bars.append(
            f'<div class="sl-dbar">'
            f'<span class="sl-dbar__label" title="{_esc(it.get("label"))}">{_md(it.get("label"))}</span>'
            f'<span class="sl-dbar__neg"><span class="sl-dbar__fill" '
            f'style="--v:{neg / mx * 100:.1f}%;--c:{negative_color}"></span></span>'
            f'<span class="sl-dbar__pos"><span class="sl-dbar__fill" '
            f'style="--v:{pos / mx * 100:.1f}%;--c:{positive_color}"></span></span>{val}</div>')
    legend = (
        f'<span class="sl-legend__item"><span class="sl-legend__sw" style="--c:{positive_color}"></span>'
        f'<span class="sl-legend__label">{_md(positive_label)}</span></span>'
        f'<span class="sl-legend__item"><span class="sl-legend__sw" style="--c:{negative_color}"></span>'
        f'<span class="sl-legend__label">{_md(negative_label)}</span></span>')
    return (f'<figure class="sl-chart">{_title(title)}<div class="sl-dbars">{"".join(bars)}</div>'
            f'<div class="sl-legend sl-legend--row" style="margin-top:.9em">{legend}</div></figure>')


def heatmap_chart(columns: Sequence[str], rows: Sequence[dict], *, title: str = "",
                  min_value: float | None = None, max_value: float | None = None,
                  color: str = "var(--sl-accent)", show_values: bool = True) -> str:
    """Option × criteria (or persona × theme) matrix; cells tinted by value via color-mix.
    columns: [str]; rows: [{label, values: [num]}] (values aligned to columns). "" when empty."""
    data = [r for r in rows if isinstance(r.get("values"), (list, tuple))]
    cols = list(columns)
    if not data or not cols:
        return ""
    allv = [v for r in data for v in (_num(x) for x in r["values"]) if v is not None]
    mn = min_value if min_value is not None else min(allv + [0])
    mx = max_value if max_value is not None else max(allv + [1])

    def tint(v: float) -> str:
        p = 0.0 if mx == mn else max(0.0, min(100.0, (v - mn) / (mx - mn) * 100))
        return f"color-mix(in srgb, {color} {p:.0f}%, var(--sl-surface-2))"

    head = '<span class="sl-heat__corner"></span>' + "".join(
        f'<span class="sl-heat__col">{_md(c)}</span>' for c in cols)
    body = []
    for r in data:
        body.append(f'<span class="sl-heat__row" title="{_esc(r.get("label"))}">{_md(r.get("label"))}</span>')
        vals = list(r["values"])
        for ci in range(len(cols)):
            v = _num(vals[ci]) if ci < len(vals) else None
            if v is None:
                body.append('<span class="sl-heat__cell"></span>')
            else:
                body.append(f'<span class="sl-heat__cell" style="background:{tint(v)}">'
                            f'{_fmt(v) if show_values else ""}</span>')
    grid = f"minmax(4.5em, auto) repeat({len(cols)}, minmax(2em, 1fr))"
    return (f'<figure class="sl-chart">{_title(title)}'
            f'<div class="sl-heat" style="grid-template-columns:{grid}">{head}{"".join(body)}</div></figure>')


def dot_plot_chart(items: Sequence[dict], *, title: str = "", min_value: float = 1, max_value: float = 5,
                   show_mean: bool = True) -> str:
    """Where N voices land on a scale (spread/disagreement). items: [{label, values: [num], color?}].
    Each value is a dot; the taller marker is the mean. "" when nothing is scored."""
    rows = [it for it in items if isinstance(it.get("values"), (list, tuple))
            and any(_num(v) is not None for v in it["values"])]
    if not rows:
        return ""
    span = (max_value - min_value) or 1

    def x_of(v: float) -> float:
        return max(0.0, min(100.0, (v - min_value) / span * 100))

    out = []
    for i, it in enumerate(rows):
        vals = [_num(v) for v in it["values"] if _num(v) is not None]
        mean = round(sum(vals) / len(vals) * 10) / 10
        c = it.get("color") or _SERIES[i % len(_SERIES)]
        dots = "".join(f'<span class="sl-dot-pt" style="left:{x_of(v):.1f}%;--c:{c}"></span>' for v in vals)
        meanm = (f'<span class="sl-dot-mean" style="left:{x_of(mean):.1f}%;--c:{c}" title="mean {_fmt(mean)}"></span>'
                 if show_mean else "")
        out.append(
            f'<div class="sl-dot-row">'
            f'<span class="sl-dot-label" title="{_esc(it.get("label"))}">{_md(it.get("label"))}</span>'
            f'<span class="sl-dot-track">{dots}{meanm}</span>'
            f'<span class="sl-dot-val">{_fmt(mean)}</span></div>')
    scale = ('<div class="sl-dot-scale"><span></span>'
             f'<span class="sl-dot-scale__axis"><span>{_fmt(min_value)}</span><span>{_fmt(max_value)}</span></span>'
             '<span></span></div>')
    return f'<figure class="sl-chart">{_title(title)}<div class="sl-dots">{"".join(out)}</div>{scale}</figure>'


def line_chart(series: Sequence[dict], *, title: str = "", labels: Sequence[str] | None = None,
               min_value: float | None = None, max_value: float | None = None,
               show_dots: bool = True) -> str:
    """Trend over time — a static inline-SVG polyline per series. series: [{label, points: [num], color?}];
    optional `labels` for the x axis. The one chart that needs SVG (still print-safe). "" when empty."""
    lines = [s for s in series if isinstance(s.get("points"), (list, tuple))
             and len([p for p in s["points"] if _num(p) is not None]) > 1]
    if not lines:
        return ""
    allv = [_num(p) for s in lines for p in s["points"] if _num(p) is not None]
    mn = min_value if min_value is not None else min(allv)
    mx = max_value if max_value is not None else max(allv)
    span = (mx - mn) or 1
    w, h = 100, 40

    def xy(pts: list[float]) -> list[tuple[float, float]]:
        return [((i / (len(pts) - 1)) * w, h - (v - mn) / span * h) for i, v in enumerate(pts)]

    paths = []
    for i, s in enumerate(lines):
        pts = xy([_num(p) for p in s["points"] if _num(p) is not None])
        c = s.get("color") or _SERIES[i % len(_SERIES)]
        poly = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        dots = ("".join(f'<circle class="sl-line__dot" cx="{x:.2f}" cy="{y:.2f}" r="1.4"></circle>'
                        for x, y in pts) if show_dots else "")
        paths.append(f'<g style="--c:{c}"><polyline class="sl-line__path" points="{poly}"></polyline>{dots}</g>')
    svg = (f'<svg viewBox="0 0 {w} {h}" role="img">'
           f'<line class="sl-line__axis" x1="0" y1="{h}" x2="{w}" y2="{h}"></line>{"".join(paths)}</svg>')
    labs = ('<div class="sl-line__labels">'
            + "".join(f"<span>{_esc(lab)}</span>" for lab in labels) + "</div>") if labels else ""
    legend = ""
    if len(lines) > 1:
        legend = ('<div class="sl-legend sl-legend--row" style="margin-top:.6em">' + "".join(
            f'<span class="sl-legend__item"><span class="sl-legend__sw" '
            f'style="--c:{s.get("color") or _SERIES[i % len(_SERIES)]}"></span>'
            f'<span class="sl-legend__label">{_md(s.get("label"))}</span></span>'
            for i, s in enumerate(lines)) + "</div>")
    return f'<figure class="sl-chart">{_title(title)}<div class="sl-line">{svg}{labs}</div>{legend}</figure>'


# Effort·impact leverage tint: high value vs effort → green; balanced → accent; costly → amber/red.
def _leverage(x: float, y: float) -> str:
    d = y - x
    return "var(--sl-green)" if d >= 2 else "var(--sl-accent)" if d >= 1 else \
        "var(--sl-red)" if d <= -1 else "var(--sl-amber)"


def effort_impact(items: Sequence[dict], *, title: str = "", x_label: str = "Effort",
                  y_label: str = "Value", quadrants: Sequence[str] = (
                      "Quick wins", "Big bets", "Fill-ins", "Time sinks")) -> str:
    """A 2×2 effort·impact scatter + a numbered legend. items: [{label, x, y, color?}] with x,y in 1..5
    (x=effort, y=value). Numbered dots; the legend keeps every label readable (and printable). "" if empty."""
    rows = [it for it in items if _num(it.get("x")) and _num(it.get("y"))]
    if not rows:
        return ""
    ql = list(quadrants) + ["", "", "", ""]
    dots, legend = [], []
    for i, it in enumerate(rows, 1):
        x, y = _num(it["x"]) or 1, _num(it["y"]) or 1
        c = it.get("color") or _leverage(x, y)
        left = (x - 1) / 4 * 100
        top = (1 - (y - 1) / 4) * 100
        dots.append(f'<span class="sl-quad__dot" style="--x:{left:.1f}%;--y:{top:.1f}%;--c:{c}">{i}</span>')
        legend.append(
            f'<span class="sl-legend__item"><span class="sl-legend__num" style="--c:{c}">{i}</span>'
            f'<span class="sl-legend__label">{_md(it.get("label"))}</span>'
            f'<span class="sl-legend__val">{x_label[:1]}{_fmt(x)}·{y_label[:1]}{_fmt(y)}</span></span>')
    quad = (f'<div class="sl-quad-wrap"><div class="sl-quad-ylab">{_esc(y_label)}</div>'
            f'<div class="sl-quad"><div class="sl-quad__gx"></div><div class="sl-quad__gy"></div>'
            f'<span class="sl-quad__q sl-quad__q--tl">{_esc(ql[0])}</span>'
            f'<span class="sl-quad__q sl-quad__q--tr">{_esc(ql[1])}</span>'
            f'<span class="sl-quad__q sl-quad__q--bl">{_esc(ql[2])}</span>'
            f'<span class="sl-quad__q sl-quad__q--br">{_esc(ql[3])}</span>'
            f'{"".join(dots)}</div><div class="sl-quad-xlab">{_esc(x_label)}</div></div>')
    return (f'<figure class="sl-chart">{_title(title)}{quad}'
            f'<div class="sl-legend" style="margin-top:.9em">{"".join(legend)}</div></figure>')


def burnup_chart(series: Sequence[dict], *, title: str = "", labels: Sequence[str] | None = None,
                 target: Any = None, now: Any = None, min_value: float | None = None,
                 max_value: float | None = None, show_dots: bool = True) -> str:
    """Progress over time, Linear-cycle style — cumulative lines with a soft band fill under each,
    an optional dotted ideal line rising to `target`, and an optional `now` marker (a point index)
    that hatches the future region. series: [{label, points: [num], color?}]; the y scale reads
    from 0 (or min_value) and stretches to include `target`. "" when empty."""
    lines = [s for s in series if isinstance(s.get("points"), (list, tuple))
             and len([p for p in s["points"] if _num(p) is not None]) > 1]
    if not lines:
        return ""
    tgt = _num(target)
    allv = [_num(p) for s in lines for p in s["points"] if _num(p) is not None]
    if tgt is not None:
        allv.append(tgt)
    mn = min_value if min_value is not None else min(allv + [0.0])
    mx = max_value if max_value is not None else max(allv)
    span = (mx - mn) or 1
    w, h = 100, 40
    n = max(len([p for p in s["points"] if _num(p) is not None]) for s in lines)

    def y_of(v: float) -> float:
        return h - (v - mn) / span * h

    def xy(pts: list[float]) -> list[tuple[float, float]]:
        return [((i / (len(pts) - 1)) * w, y_of(v)) for i, v in enumerate(pts)]

    parts = []
    # Future region first so the data draws over it: a faint wash + 45° hatch, clipped by hand
    # (no <clipPath> — ids would collide when several charts share a page).
    now_i = _num(now)
    if now_i is not None and n > 1:
        x_now = max(0.0, min(float(w), now_i / (n - 1) * w))
        if x_now < w:
            parts.append(f'<rect class="sl-burnup__future" x="{x_now:.2f}" y="0" '
                         f'width="{w - x_now:.2f}" height="{h}"></rect>')
            b = int(x_now) - h
            hatch = []
            while b < w:
                x1 = max(float(b), x_now)
                x2 = min(float(b + h), float(w))
                if x2 > x1:
                    hatch.append(f'<line class="sl-burnup__hatch" x1="{x1:.2f}" y1="{h - (x1 - b):.2f}" '
                                 f'x2="{x2:.2f}" y2="{h - (x2 - b):.2f}"></line>')
                b += 6
            parts.extend(hatch)
    if tgt is not None:
        first = next(_num(p) for p in lines[0]["points"] if _num(p) is not None)
        parts.append(f'<line class="sl-line__ref" x1="0" y1="{y_of(first):.2f}" '
                     f'x2="{w}" y2="{y_of(tgt):.2f}"></line>')
    for i, s in enumerate(lines):
        pts = xy([_num(p) for p in s["points"] if _num(p) is not None])
        c = s.get("color") or _SERIES[i % len(_SERIES)]
        poly = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        area = f"0,{h} {poly} {pts[-1][0]:.2f},{h}"
        dots = ("".join(f'<circle class="sl-line__dot" cx="{x:.2f}" cy="{y:.2f}" r="1.4"></circle>'
                        for x, y in pts) if show_dots else "")
        parts.append(f'<g style="--c:{c}"><polygon class="sl-line__area" points="{area}"></polygon>'
                     f'<polyline class="sl-line__path" points="{poly}"></polyline>{dots}</g>')
    if now_i is not None and n > 1:
        x_now = max(0.0, min(float(w), now_i / (n - 1) * w))
        parts.append(f'<line class="sl-line__now" x1="{x_now:.2f}" y1="0" x2="{x_now:.2f}" y2="{h}"></line>')
    svg = (f'<svg viewBox="0 0 {w} {h}" role="img">'
           f'<line class="sl-line__axis" x1="0" y1="{h}" x2="{w}" y2="{h}"></line>{"".join(parts)}</svg>')
    labs = ('<div class="sl-line__labels">'
            + "".join(f"<span>{_esc(lab)}</span>" for lab in labels) + "</div>") if labels else ""
    legend = ""
    if len(lines) > 1:
        legend = ('<div class="sl-legend sl-legend--row" style="margin-top:.6em">' + "".join(
            f'<span class="sl-legend__item"><span class="sl-legend__sw" '
            f'style="--c:{s.get("color") or _SERIES[i % len(_SERIES)]}"></span>'
            f'<span class="sl-legend__label">{_md(s.get("label"))}</span></span>'
            for i, s in enumerate(lines)) + "</div>")
    return f'<figure class="sl-chart">{_title(title)}<div class="sl-line">{svg}{labs}</div>{legend}</figure>'


def stacked_area_chart(series: Sequence[dict], *, title: str = "", labels: Sequence[str] | None = None,
                       max_value: float | None = None) -> str:
    """Composition over an ordered sequence (cumulative flow) — one soft band per series, stacked
    in order, each with a hairline top edge. series: [{label, points: [num], color?}]; points are
    aligned on the shortest series (missing values can't stack). "" when fewer than 2 shared points."""
    bands = [s for s in series if isinstance(s.get("points"), (list, tuple))
             and any(_num(p) is not None for p in s["points"])]
    if not bands:
        return ""
    length = min(len(s["points"]) for s in bands)
    if length < 2:
        return ""
    vals = [[max(0.0, _num(s["points"][i]) or 0.0) for i in range(length)] for s in bands]
    totals = [sum(v[i] for v in vals) for i in range(length)]
    mx = max_value if max_value else max(totals) or 1
    w, h = 100, 40

    def x_of(i: int) -> float:
        return i / (length - 1) * w

    def y_of(v: float) -> float:
        return h - min(1.0, v / mx) * h

    parts = []
    prev = [0.0] * length
    for k, s in enumerate(bands):
        top = [prev[i] + vals[k][i] for i in range(length)]
        c = s.get("color") or _SERIES[k % len(_SERIES)]
        upper = " ".join(f"{x_of(i):.2f},{y_of(top[i]):.2f}" for i in range(length))
        lower = " ".join(f"{x_of(i):.2f},{y_of(prev[i]):.2f}" for i in range(length - 1, -1, -1))
        parts.append(f'<g style="--c:{c}"><polygon class="sl-area__band" points="{upper} {lower}"></polygon>'
                     f'<polyline class="sl-area__edge" points="{upper}"></polyline></g>')
        prev = top
    svg = (f'<svg viewBox="0 0 {w} {h}" role="img">'
           f'<line class="sl-line__axis" x1="0" y1="{h}" x2="{w}" y2="{h}"></line>{"".join(parts)}</svg>')
    labs = ('<div class="sl-line__labels">'
            + "".join(f"<span>{_esc(lab)}</span>" for lab in labels) + "</div>") if labels else ""
    legend = ('<div class="sl-legend sl-legend--row" style="margin-top:.6em">' + "".join(
        f'<span class="sl-legend__item"><span class="sl-legend__sw" '
        f'style="--c:{s.get("color") or _SERIES[i % len(_SERIES)]}"></span>'
        f'<span class="sl-legend__label">{_md(s.get("label"))}</span></span>'
        for i, s in enumerate(bands)) + "</div>")
    return f'<figure class="sl-chart">{_title(title)}<div class="sl-line">{svg}{labs}</div>{legend}</figure>'


def column_chart(items: Sequence[dict], *, title: str = "", max_value: float | None = None,
                 show_values: bool = True, table: bool = False) -> str:
    """Thin VERTICAL bars over hairline gridlines (the Linear Insights panel) — distributions over
    an ordered category axis (scores 1..5, counts per status). items: [{label, value, color?}] or
    [{label, segments: [{label, value, color?}]}] for stacked composition; series colour is keyed
    by segment label like stacked_bar_chart. `table=True` appends a breakdown table that restates
    the numbers — chart for the shape, table for the values. "" when nothing is scored."""
    def _total(it: dict) -> float | None:
        if it.get("segments"):
            vals = [_num(s.get("value")) for s in it["segments"]]
            return sum(max(0.0, v) for v in vals if v is not None) if any(v is not None for v in vals) else None
        return _num(it.get("value"))

    rows = [(it, _total(it)) for it in items]
    rows = [(it, t) for it, t in rows if t is not None]
    if not rows:
        return ""
    keys: list[str] = []
    for it, _t in rows:
        for s in (it.get("segments") or []):
            if s.get("label") not in keys:
                keys.append(s.get("label"))

    def seg_color(s: dict) -> str:
        return str(s.get("color") or _SERIES[max(0, keys.index(s.get("label"))) % len(_SERIES)])

    mx = max_value if max_value else max(t for _it, t in rows) or 1
    cols = []
    for it, total in rows:
        pct = max(0.0, min(100.0, total / mx * 100)) if mx else 0
        if it.get("segments"):
            segs = "".join(
                f'<span class="sl-col__seg" title="{_esc(s.get("label"))}: {_fmt(_num(s.get("value")) or 0)}" '
                f'style="flex-grow:{_num(s.get("value")) or 0:g};--c:{seg_color(s)}"></span>'
                for s in it["segments"] if (_num(s.get("value")) or 0) > 0)
            bar = f'<span class="sl-col__bar sl-col__bar--stack" style="--v:{pct:.1f}%">{segs}</span>'
        else:
            c = str(it.get("color") or "var(--c1)")
            bar = f'<span class="sl-col__bar" title="{_esc(it.get("label"))}: {_fmt(total)}" style="--v:{pct:.1f}%;--c:{c}"></span>'
        val = f'<span class="sl-col__val">{_fmt(total)}</span>' if show_values else ""
        cols.append(f'<div class="sl-col">{val}{bar}</div>')
    labels = "".join(f'<span title="{_esc(it.get("label"))}">{_md(it.get("label"))}</span>' for it, _t in rows)
    axis = (f'<div class="sl-cols-axis"><span>{_fmt(mx)}</span><span>{_fmt(mx / 2)}</span><span>0</span></div>')
    legend = ""
    if keys:
        first = {s.get("label"): s for it, _t in reversed(rows) for s in (it.get("segments") or [])}
        legend = ('<div class="sl-legend sl-legend--row" style="margin-top:.7em">' + "".join(
            f'<span class="sl-legend__item"><span class="sl-legend__sw" style="--c:{seg_color(first[k])}"></span>'
            f'<span class="sl-legend__label">{_md(k)}</span></span>' for k in keys) + "</div>")
    tbl = ""
    if table:
        if keys:
            head = "<tr><th></th>" + "".join(f"<th>{_md(k)}</th>" for k in keys) + "<th>Total</th></tr>"
            body = []
            for it, total in rows:
                by = {s.get("label"): _num(s.get("value")) or 0 for s in (it.get("segments") or [])}
                cells = "".join(f"<td>{_fmt(by.get(k, 0))}</td>" for k in keys)
                body.append(f"<tr><td>{_md(it.get('label'))}</td>{cells}<td>{_fmt(total)}</td></tr>")
        else:
            head = "<tr><th></th><th>Value</th></tr>"
            body = [f"<tr><td>{_md(it.get('label'))}</td><td>{_fmt(total)}</td></tr>" for it, total in rows]
        tbl = (f'<table class="sl-table sl-chart__table"><thead>{head}</thead>'
               f'<tbody>{"".join(body)}</tbody></table>')
    return (f'<figure class="sl-chart">{_title(title)}<div class="sl-cols-wrap">{axis}'
            f'<div class="sl-cols">{"".join(cols)}</div>'
            f'<div class="sl-cols-labels">{labels}</div></div>{legend}{tbl}</figure>')


def strip_chart(items: Sequence[dict], *, title: str = "", min_value: float | None = None,
                max_value: float | None = None, unit: str = "", show_mean: bool = True) -> str:
    """Continuous-axis dot strip per category (the Linear issue-age pattern) — each value is a dot
    on a real scale, one lane per row, outliers visible at a glance. The continuous sibling of
    dot_plot_chart (auto-ranged min/max, a mid tick, optional unit suffix).
    items: [{label, values: [num], color?}]. "" when nothing is scored."""
    rows = [it for it in items if isinstance(it.get("values"), (list, tuple))
            and any(_num(v) is not None for v in it["values"])]
    if not rows:
        return ""
    allv = [v for it in rows for v in (_num(x) for x in it["values"]) if v is not None]
    mn = min_value if min_value is not None else min(allv)
    mx = max_value if max_value is not None else max(allv)
    span = (mx - mn) or 1
    u = _esc(unit)

    def x_of(v: float) -> float:
        return max(0.0, min(100.0, (v - mn) / span * 100))

    out = []
    for i, it in enumerate(rows):
        vals = [_num(v) for v in it["values"] if _num(v) is not None]
        mean = round(sum(vals) / len(vals) * 10) / 10
        c = it.get("color") or _SERIES[i % len(_SERIES)]
        dots = "".join(f'<span class="sl-dot-pt" style="left:{x_of(v):.1f}%;--c:{c}"></span>' for v in vals)
        meanm = (f'<span class="sl-dot-mean" style="left:{x_of(mean):.1f}%;--c:{c}" title="mean {_fmt(mean)}{u}"></span>'
                 if show_mean else "")
        out.append(
            f'<div class="sl-dot-row">'
            f'<span class="sl-dot-label" title="{_esc(it.get("label"))}">{_md(it.get("label"))}</span>'
            f'<span class="sl-dot-track">{dots}{meanm}</span>'
            f'<span class="sl-dot-val">{_fmt(mean)}{u}</span></div>')
    mid = mn + (mx - mn) / 2
    scale = ('<div class="sl-dot-scale"><span></span>'
             f'<span class="sl-dot-scale__axis"><span>{_fmt(mn)}{u}</span><span>{_fmt(mid)}{u}</span>'
             f'<span>{_fmt(mx)}{u}</span></span><span></span></div>')
    return f'<figure class="sl-chart">{_title(title)}<div class="sl-dots">{"".join(out)}</div>{scale}</figure>'


def stats_chart(items: Sequence[dict], *, title: str = "") -> str:
    """KPI number row — small label · big value · optional sub-line. items: [{label, value, sub?, color?}].
    The Linear-style stat header (Scope · Started · Completed) and the standalone headline-metrics row.
    `value` may be a number or an already-formatted string ("72%", "8 of 12"); a swatch renders only
    when an item sets `color` (stat headers are colour-keyed to their chart; plain KPIs stay quiet).
    "" when empty."""
    rows = [it for it in items
            if str(it.get("label", "")).strip() or it.get("value") not in (None, "")]
    if not rows:
        return ""
    tiles = []
    for it in rows:
        v = it.get("value")
        n = _num(v)
        val = _fmt(n) if (n is not None and not isinstance(v, str)) else _esc(v)
        sw = f'<span class="sl-kpi__sw" style="--c:{_esc(it["color"])}"></span>' if it.get("color") else ""
        sub = f'<span class="sl-kpi__sub">{_md(it["sub"])}</span>' if it.get("sub") else ""
        tiles.append(
            f'<div class="sl-kpi">'
            f'<span class="sl-kpi__label">{sw}{_md(it.get("label"))}</span>'
            f'<span class="sl-kpi__val">{val}</span>{sub}</div>')
    return f'<figure class="sl-chart">{_title(title)}<div class="sl-kpis">{"".join(tiles)}</div></figure>'


def progress_strip(items: Sequence[dict], *, title: str = "", show_values: bool = True) -> str:
    """ONE full-width segmented status bar + a count/% legend. items: [{label, value, color?}].
    Composition at a glance (finding status, sentiment split) — denser and calmer than a pie
    when the figure sits inline in a report section. "" when empty/zero."""
    rows = [it for it in items if (_num(it.get("value")) or 0) > 0]
    total = sum(_num(it["value"]) or 0 for it in rows)
    if not rows or total <= 0:
        return ""
    segs, legend = [], []
    for i, it in enumerate(rows):
        v = _num(it["value"]) or 0
        c = _color(it, i)
        segs.append(f'<span class="sl-pstrip__seg" title="{_esc(it.get("label"))}: {_fmt(v)}" '
                    f'style="flex-grow:{v:g};--c:{c}"></span>')
        val = f'<span class="sl-legend__val">{_fmt(v)} · {v / total * 100:.0f}%</span>' if show_values else ""
        legend.append(
            f'<span class="sl-legend__item"><span class="sl-legend__sw" style="--c:{c}"></span>'
            f'<span class="sl-legend__label">{_md(it.get("label"))}</span>{val}</span>')
    return (f'<figure class="sl-chart">{_title(title)}<div class="sl-pstrip">{"".join(segs)}</div>'
            f'<div class="sl-legend sl-legend--row" style="margin-top:.7em">{"".join(legend)}</div></figure>')


def sparkline(points: Sequence[Any], *, color: str = "var(--sl-accent)", fill: bool = True,
              width: str = "6em", height: str = "1.6em") -> str:
    """Tiny axis-free inline trend for list rows and table cells — the Python twin of the React
    <Sparkline> (same .sl-spark classes). Not a report figure-kind; embed it inside other markup.
    "" with fewer than 2 finite points."""
    pts = [p for p in (_num(x) for x in points) if p is not None]
    if len(pts) < 2:
        return ""
    mn, mx = min(pts), max(pts)
    span = (mx - mn) or 1
    w, h, pad = 100, 32, 2
    coords = [((i / (len(pts) - 1)) * w, h - pad - (v - mn) / span * (h - pad * 2))
              for i, v in enumerate(pts)]
    line = " ".join(f"{x:.2f},{y:.2f}" for x, y in coords)
    poly = f'<polygon class="sl-spark__fill" points="0,{h} {line} {w},{h}"></polygon>' if fill else ""
    return (f'<span class="sl-spark" style="width:{_esc(width)};height:{_esc(height)}">'
            f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" style="--c:{_esc(color)}">'
            f'{poly}<polyline class="sl-spark__line" points="{line}"></polyline></svg></span>')


def progress_pie(value: Any, max_value: Any = 100, *, color: str = "var(--sl-accent)") -> str:
    """Micro progress-pie — a tiny inline pie that fills value/max, for milestone/percent list rows.
    Pairs with text like "69% of 16". Not a report figure-kind; embed it inside other markup."""
    m = _num(max_value) or 1
    v = _num(value) or 0
    pct = max(0.0, min(100.0, v / m * 100)) if m else 0.0
    return f'<span class="sl-mpie" role="img" title="{round(pct)}%" style="--p:{pct:.1f};--c:{_esc(color)}"></span>'


def _num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"
