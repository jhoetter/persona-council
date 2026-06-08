"""Native PowerPoint rendering for reports — turns a neutral slide model into a branded .pptx.

This layer is domain-agnostic (no Sonaloop models, no i18n): the report service assembles a list of
plain slide dicts and hands them here. Charts are NATIVE python-pptx charts (editable in PowerPoint),
coloured from the Sonaloop brand series palette so a deck reads on-brand. Lazy-imported by the caller
so the package degrades gracefully when python-pptx is absent.

Slide model (list of dicts):
  {"kind": "title", "title": str, "subtitle": str, "lead": str}
  {"kind": "content", "heading": str,
     "bullets": [(level:int, text:str)],          # level 0 = paragraph, 1+ = nested bullet
     "chart": {...} | None,                         # see below
     "image": "/abs/path.png" | None,               # a figure image (prototype shot / avatar / asset)
     "footnote": str}
Chart shapes:
  {"type": "bar",  "categories": [str], "values": [num]}
  {"type": "pie",  "categories": [str], "values": [num]}
  {"type": "scatter", "points": [{"x":num,"y":num,"label":str}], "x_label": str, "y_label": str}
"""
from __future__ import annotations

import io
from typing import Any

# Sonaloop brand (light) — kept in sync with sonaloop-design tokens.data.mjs.
_INK = "1A1815"
_MUTED = "635E56"
_FAINT = "8C857A"
_ACCENT = "5E6AD2"
_BG = "FAF8F3"
_PANEL = "FFFFFF"
# Series palette (accent · violet · blue · green · amber · red · skep).
_SERIES = ["5E6AD2", "7A5ED1", "3D7FC4", "3D9B6B", "B87A25", "CF4D5F", "C2683F"]


def render(slides: list[dict], *, title: str = "Report") -> bytes:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    prs.core_properties.title = title
    prs.core_properties.author = "Sonaloop"
    blank = prs.slide_layouts[6]
    W, H = prs.slide_width, prs.slide_height
    rgb = lambda hexv: RGBColor.from_string(hexv)

    def _bg(slide, hexv=_BG):
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = rgb(hexv)

    def _box(slide, l, t, w, h):
        tb = slide.shapes.add_textbox(l, t, w, h)
        tb.text_frame.word_wrap = True
        return tb.text_frame

    def _run(p, text, *, size=14, bold=False, color=_INK, italic=False):
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.name = "Geist"
        r.font.color.rgb = rgb(color)
        return r

    # ── title slide ──────────────────────────────────────────────────────────
    def _title_slide(s):
        slide = prs.slides.add_slide(blank)
        _bg(slide)
        tf = _box(slide, Inches(0.9), Inches(2.2), W - Inches(1.8), Inches(3.0))
        p = tf.paragraphs[0]
        _run(p, s.get("title", title), size=40, bold=True)
        if s.get("subtitle"):
            p2 = tf.add_paragraph(); p2.space_before = Pt(10)
            _run(p2, s["subtitle"], size=15, color=_MUTED)
        if s.get("lead"):
            p3 = tf.add_paragraph(); p3.space_before = Pt(18)
            _run(p3, s["lead"], size=16, color=_INK)
        # accent rule
        bar = slide.shapes.add_shape(1, Inches(0.92), Inches(2.05), Inches(2.2), Pt(4))
        bar.fill.solid(); bar.fill.fore_color.rgb = rgb(_ACCENT); bar.line.fill.background()

    # ── content slide ────────────────────────────────────────────────────────
    def _content_slide(s):
        slide = prs.slides.add_slide(blank)
        _bg(slide)
        # heading
        htf = _box(slide, Inches(0.7), Inches(0.5), W - Inches(1.4), Inches(0.9))
        _run(htf.paragraphs[0], s.get("heading", ""), size=26, bold=True)
        slide.shapes.add_shape(1, Inches(0.72), Inches(1.32), Inches(0.9), Pt(3)).fill.solid()
        slide.shapes[-1].fill.fore_color.rgb = rgb(_ACCENT); slide.shapes[-1].line.fill.background()

        has_visual = bool(s.get("chart") or s.get("image"))
        body_w = (Inches(6.6) if has_visual else W - Inches(1.4))
        top = Inches(1.6)
        bullets = s.get("bullets") or []
        if bullets:
            tf = _box(slide, Inches(0.7), top, body_w, H - top - Inches(0.9))
            first = True
            for level, text in bullets:
                p = tf.paragraphs[0] if first else tf.add_paragraph()
                first = False
                p.level = max(0, min(4, level))
                p.space_after = Pt(6)
                if level == 0:
                    _run(p, text, size=14)
                else:
                    _run(p, "•  ", size=13, color=_ACCENT)
                    _run(p, text, size=13, color=_INK)
        if s.get("chart"):
            _chart(slide, s["chart"], Inches(7.5), top, Inches(5.1), Inches(4.6))
        elif s.get("image"):
            try:
                slide.shapes.add_picture(s["image"], Inches(7.5), top, width=Inches(5.1))
            except Exception:
                pass
        if s.get("footnote"):
            ftf = _box(slide, Inches(0.7), H - Inches(0.7), W - Inches(1.4), Inches(0.5))
            _run(ftf.paragraphs[0], s["footnote"], size=10, color=_FAINT, italic=True)

    def _style_points(plot):
        # colour each category point from the brand series palette
        try:
            pts = plot.series[0].points
            for i, pt in enumerate(pts):
                pt.format.fill.solid()
                pt.format.fill.fore_color.rgb = rgb(_SERIES[i % len(_SERIES)])
        except Exception:
            pass

    def _chart(slide, ch, x, y, cx, cy):
        from pptx.chart.data import CategoryChartData, XyChartData
        from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
        kind = ch.get("type")
        if kind in ("bar", "pie") and ch.get("categories"):
            cd = CategoryChartData()
            cd.categories = [str(c) for c in ch["categories"]]
            cd.add_series("", tuple(float(v or 0) for v in ch["values"]))
            xl = XL_CHART_TYPE.BAR_CLUSTERED if kind == "bar" else XL_CHART_TYPE.DOUGHNUT
            gf = slide.shapes.add_chart(xl, x, y, cx, cy, cd)
            chart = gf.chart
            chart.has_title = False
            if kind == "pie":
                chart.has_legend = True
                chart.legend.position = XL_LEGEND_POSITION.RIGHT
                chart.legend.include_in_layout = False
                chart.plots[0].has_data_labels = True
                chart.plots[0].data_labels.number_format = "0%"
                chart.plots[0].data_labels.number_format_is_linked = False
            else:
                chart.has_legend = False
            _style_points(chart.plots[0])
        elif kind == "scatter" and ch.get("points"):
            xy = XyChartData()
            ser = xy.add_series("")
            for pt in ch["points"]:
                ser.add_data_point(float(pt.get("x", 0)), float(pt.get("y", 0)))
            gf = slide.shapes.add_chart(XL_CHART_TYPE.XY_SCATTER, x, y, cx, cy, xy)
            chart = gf.chart
            chart.has_title = False
            chart.has_legend = False

    for s in slides:
        if s.get("kind") == "title":
            _title_slide(s)
        else:
            _content_slide(s)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def available() -> bool:
    try:
        import pptx  # noqa: F401
        return True
    except Exception:
        return False
