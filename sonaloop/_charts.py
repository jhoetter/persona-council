"""sonaloop._charts — VENDORED COPY of the sonaloop-design chart components.

Do not edit by hand. Single source of truth: ../sonaloop-design (py/sonaloop_icons/charts.py +
styles/components.css `.sl-chart*`). Refresh with `make icons` / scripts/sync_icons.sh.
Vendored so the PyPI package has no local-path dependency.


The React side is ../../src/charts.tsx; the styling source of truth is ../../styles/components.css
(the `.sl-chart`/`.sl-bar*`/`.sl-pie*`/`.sl-quad*`/`.sl-legend*` classes). These functions emit
self-contained, static, print-safe HTML strings (no JS, no hover-only data) so a chart renders
identically in the Python-SSR app, on the website, and in headless-Chromium PDF/PPTX export.

    from sonaloop_icons.charts import bar_chart, pie_chart, effort_impact
    bar_chart([{"label": "Plan", "value": 8}, {"label": "Cook", "value": 3}])
    pie_chart([{"label": "Support", "value": 12}, {"label": "Oppose", "value": 4}])
    effort_impact([{"label": "Auto shopping list", "x": 2, "y": 5}])  # x=effort, y=value (1..5)

All text is rendered as-is (already-resolved/translated by the caller — this layer is i18n-agnostic).
Series colours come from position unless an item sets `color`.
"""

from __future__ import annotations

import html
from typing import Any, Sequence

# Position → CSS custom property carrying that series' colour (defined on `.sl-chart`).
_SERIES = ["var(--c1)", "var(--c2)", "var(--c3)", "var(--c4)", "var(--c5)", "var(--c6)", "var(--c7)"]


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def _color(item: dict, i: int) -> str:
    return str(item.get("color") or _SERIES[i % len(_SERIES)])


def _title(title: str) -> str:
    return f'<div class="sl-chart__title">{_esc(title)}</div>' if title else ""


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
            f'<span class="sl-bar__label" title="{_esc(it.get("label"))}">{_esc(it.get("label"))}</span>'
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
            f'<span class="sl-legend__label">{_esc(it.get("label"))}</span>{val}</span>')
    cls = "sl-pie sl-pie--donut" if donut else "sl-pie"
    grad = f"conic-gradient({', '.join(stops)})"
    return (f'<figure class="sl-chart">{_title(title)}<div class="sl-pie-wrap">'
            f'<div class="{cls}" style="--slices:{grad}" role="img"></div>'
            f'<div class="sl-legend">{"".join(legend)}</div></div></figure>')


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
            f'<span class="sl-legend__label">{_esc(it.get("label"))}</span>'
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


def _num(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"
