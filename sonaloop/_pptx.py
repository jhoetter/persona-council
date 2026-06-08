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
_LINE = "E9E5DB"
_SURFACE2 = "F1EFE8"
_GREEN, _AMBER, _RED = "3D9B6B", "B87A25", "CF4D5F"


def _num(v: float) -> str:
    """Compact number for labels: 8 not 8.0, 7.5 stays 7.5."""
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else f"{f:g}"
    except (TypeError, ValueError):
        return str(v)


def _leverage_color(x: float, y: float) -> str:
    """Effort·impact dot tint — mirrors sonaloop-design _charts: high value vs effort → green;
    balanced → accent; costly → amber/red."""
    d = y - x
    return _GREEN if d >= 2 else _ACCENT if d >= 1 else _RED if d <= -1 else _AMBER


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

    def _rule(slide, l, t, w):
        bar = slide.shapes.add_shape(1, Inches(l), Inches(t), Inches(w), Pt(3.5))
        bar.fill.solid(); bar.fill.fore_color.rgb = rgb(_ACCENT); bar.line.fill.background()
        _noshadow(bar)

    def _footer(slide):
        ft = _box(slide, W - Inches(5.0), H - Inches(0.42), Inches(4.3), Inches(0.3))
        p = ft.paragraphs[0]; p.alignment = PP_ALIGN.RIGHT
        _run(p, title, size=9, color=_FAINT)

    # ── title slide ──────────────────────────────────────────────────────────
    def _title_slide(s):
        slide = prs.slides.add_slide(blank)
        _bg(slide)
        _rule(slide, 0.92, 2.0, 1.0)
        tf = _box(slide, Inches(0.9), Inches(2.15), W - Inches(1.8), Inches(3.4))
        p0 = tf.paragraphs[0]
        eb = _run(p0, (s.get("eyebrow", "") or "").upper(), size=12, bold=True, color=_ACCENT)
        eb.font.name = "Geist Mono"
        p1 = tf.add_paragraph(); p1.space_before = Pt(8)
        _run(p1, s.get("title", title), size=38, bold=True)
        if s.get("subtitle"):
            p2 = tf.add_paragraph(); p2.space_before = Pt(12)
            _run(p2, s["subtitle"], size=14, color=_MUTED)
        if s.get("lead"):
            p3 = tf.add_paragraph(); p3.space_before = Pt(20)
            _run(p3, s["lead"], size=17, color=_INK)
        _footer(slide)

    # ── content slide ────────────────────────────────────────────────────────
    _CALLOUT_RGB = {"accent": _ACCENT, "green": _GREEN, "amber": _AMBER}

    def _content_slide(s):
        slide = prs.slides.add_slide(blank)
        _bg(slide)
        # heading: mono section number + bold title, accent rule beneath
        htf = _box(slide, Inches(0.7), Inches(0.5), W - Inches(1.4), Inches(0.9))
        hp = htf.paragraphs[0]
        if s.get("num"):
            r = _run(hp, s["num"] + "   ", size=16, bold=True, color=_FAINT); r.font.name = "Geist Mono"
        _run(hp, s.get("heading", ""), size=24, bold=True)
        _rule(slide, 0.72, 1.34, 0.85)

        has_visual = bool(s.get("chart") or s.get("image"))
        body_w = (Inches(6.5) if has_visual else W - Inches(1.4))
        top = Inches(1.65)
        blocks = s.get("blocks") or []
        if blocks:
            tf = _box(slide, Inches(0.7), top, body_w, H - top - Inches(0.9))
            first = True
            for b in blocks:
                p = tf.paragraphs[0] if first else tf.add_paragraph()
                first = False
                bt = b.get("type", "p"); txt = b.get("text", "")
                if bt == "li":
                    p.space_after = Pt(5)
                    _run(p, "•  ", size=13, bold=True, color=_ACCENT)
                    _run(p, txt, size=13, color=_INK)
                elif bt == "quote":
                    p.space_before = Pt(6); p.space_after = Pt(8)
                    _run(p, txt, size=15, italic=True, color=_MUTED)
                elif bt == "callout":
                    p.space_before = Pt(6); p.space_after = Pt(8)
                    _run(p, b.get("label", "Insight") + "  ", size=13, bold=True,
                         color=_CALLOUT_RGB.get(b.get("kind"), _ACCENT))
                    _run(p, txt, size=13, color=_INK)
                elif bt == "h":
                    p.space_before = Pt(10); p.space_after = Pt(3)
                    _run(p, txt, size=15, bold=True, color=_INK)
                else:
                    p.space_after = Pt(7)
                    _run(p, txt, size=14, color=_INK)
        if s.get("chart"):
            _chart(slide, s["chart"], Inches(7.4), top, Inches(5.2), Inches(4.5))
        elif s.get("image"):
            try:
                slide.shapes.add_picture(s["image"], Inches(7.4), top, width=Inches(5.2))
            except Exception:
                pass
        if s.get("footnote"):
            ftf = _box(slide, Inches(0.7), H - Inches(0.72), W - Inches(1.4), Inches(0.5))
            _run(ftf.paragraphs[0], s["footnote"], size=10, color=_FAINT, italic=True)
        _footer(slide)

    # ── image slide (prototype screenshots / images / avatars) — fitted + centred ──
    def _image_slide(s):
        slide = prs.slides.add_slide(blank)
        _bg(slide)
        htf = _box(slide, Inches(0.7), Inches(0.5), W - Inches(1.4), Inches(0.9))
        hp = htf.paragraphs[0]
        if s.get("num"):
            r = _run(hp, s["num"] + "   ", size=16, bold=True, color=_FAINT); r.font.name = "Geist Mono"
        _run(hp, s.get("heading", ""), size=24, bold=True)
        _rule(slide, 0.72, 1.34, 0.85)
        L, T = 0.7, 1.7
        maxw, maxh = W.inches - 1.4, H.inches - T - 0.95
        try:
            pic = slide.shapes.add_picture(s["image"], Inches(L), Inches(T))
            scale = min(Inches(maxw) / pic.width, Inches(maxh) / pic.height)
            pic.width = int(pic.width * scale); pic.height = int(pic.height * scale)
            pic.left = Inches(L) + (Inches(maxw) - pic.width) // 2
            pic.top = Inches(T) + (Inches(maxh) - pic.height) // 2
            pic.line.color.rgb = rgb(_LINE); pic.line.width = Pt(0.75)
            if s.get("caption"):
                cap_t = (pic.top + pic.height) / 914400 + 0.06
                _text(slide, L, cap_t, maxw, 0.3, s["caption"], size=10, color=_MUTED, align=PP_ALIGN.CENTER)
        except Exception:
            pass
        _footer(slide)

    from pptx.oxml.ns import qn
    from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
    from pptx.enum.text import MSO_ANCHOR

    def _clean_area(chart):
        """Transparent chart area (blend into the slide) + brand default font — for the donut ring,
        which stays a native chart (arcs are impractical as shapes)."""
        try:
            chart.font.name = "Geist"; chart.font.size = Pt(10); chart.font.color.rgb = rgb(_MUTED)
            cs = chart._chartSpace
            spPr = cs.makeelement(qn("c:spPr"), {})
            cs.find(qn("c:chart")).addnext(spPr)
            spPr.append(spPr.makeelement(qn("a:noFill"), {}))
            ln = spPr.makeelement(qn("a:ln"), {}); spPr.append(ln)
            ln.append(ln.makeelement(qn("a:noFill"), {}))
        except Exception:
            pass

    # ── chart primitives: native, EDITABLE shapes, pixel-matched to the .sl-chart components ──
    def _noshadow(sp):
        # autoshapes/connectors carry a <p:style> with a theme effectRef (drop shadow). The DS shapes
        # are flat — drop the style entirely (explicit fill/line are set on every shape anyway).
        try:
            sp.shadow.inherit = False
            st = sp._element.find(qn("p:style"))
            if st is not None:
                sp._element.remove(st)
        except Exception:
            pass

    def _text(slide, l, t, w, h, text, *, size=11, color=_INK, bold=False,
              anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.LEFT, rot=0):
        tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
        if rot:
            tb.rotation = rot
        tf = tb.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = anchor
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Pt(0)
        p = tf.paragraphs[0]; p.alignment = align
        _run(p, text, size=size, color=color, bold=bold)
        return tb

    def _rrect(slide, l, t, w, h, color, *, radius=0.5, line=None):
        sp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
        try:
            sp.adjustments[0] = radius
        except Exception:
            pass
        sp.fill.solid(); sp.fill.fore_color.rgb = rgb(color)
        if line:
            sp.line.color.rgb = rgb(line); sp.line.width = Pt(1)
        else:
            sp.line.fill.background()
        _noshadow(sp)
        return sp

    def _connector(slide, x1, y1, x2, y2, color, *, width=0.75, dash=False):
        ln = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
        ln.line.color.rgb = rgb(color); ln.line.width = Pt(width)
        if dash:
            try:
                ln.line._get_or_add_ln().append(ln.line._get_or_add_ln().makeelement(qn("a:prstDash"), {"val": "dash"}))
            except Exception:
                pass
        _noshadow(ln)
        return ln

    def _dot(slide, cxp, cyp, d, fill, edge, num):
        ov = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(cxp - d / 2), Inches(cyp - d / 2), Inches(d), Inches(d))
        ov.fill.solid(); ov.fill.fore_color.rgb = rgb(fill)
        ov.line.color.rgb = rgb(edge); ov.line.width = Pt(1.5)
        _noshadow(ov)
        tf = ov.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = Pt(0)
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
        _run(p, str(num), size=9, bold=True, color=edge)
        return ov

    def _bar_chart(slide, ch, bx, by, bw, bh):
        cats = [str(c) for c in ch["categories"]]
        vals = [float(v or 0) for v in ch["values"]]
        n = max(len(cats), 1); mx = max(vals + [1]) or 1
        label_w = min(1.5, bw * 0.34); value_w = 0.42
        tx = bx + label_w; tw = max(0.5, bw - label_w - value_w)
        row_h = min(bh / n, 0.5); bar_h = min(0.16, row_h * 0.38)
        y0 = by + (bh - row_h * n) / 2          # centre the bar group vertically (DS rows are tight)
        for i, (c, v) in enumerate(zip(cats, vals)):
            ry = y0 + i * row_h; cy0 = ry + (row_h - bar_h) / 2
            _text(slide, bx, ry, label_w - 0.08, row_h, c, size=11, color=_INK)
            _rrect(slide, tx, cy0, tw, bar_h, _SURFACE2)
            _rrect(slide, tx, cy0, max(bar_h, tw * v / mx), bar_h, _SERIES[i % len(_SERIES)])
            _text(slide, tx + tw + 0.05, ry, value_w, row_h, _num(v), size=10, color=_MUTED)

    def _donut_chart(slide, ch, bx, by, bw, bh):
        from pptx.chart.data import CategoryChartData
        from pptx.enum.chart import XL_CHART_TYPE
        cats = [str(c) for c in ch["categories"]]
        vals = [float(v or 0) for v in ch["values"]]; total = sum(vals) or 1
        size = min(bw * 0.46, bh, 3.4)
        cd = CategoryChartData(); cd.categories = cats; cd.add_series("", tuple(vals))
        chart = slide.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(bx), Inches(by + (bh - size) / 2),
                                       Inches(size), Inches(size), cd).chart
        chart.has_title = False; chart.has_legend = False
        _clean_area(chart)
        plot = chart.plots[0]; plot.has_data_labels = False
        try:
            for j, pt in enumerate(plot.series[0].points):
                pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(_SERIES[j % len(_SERIES)])
                pt.format.line.fill.background()
            plot._element.append(plot._element.makeelement(qn("c:holeSize"), {"val": "62"}))
        except Exception:
            pass
        lx = bx + size + 0.4; lw = max(1.0, bw - size - 0.4)
        rh = min(0.36, bh / max(len(cats), 1)); ly0 = by + (bh - rh * len(cats)) / 2
        for i, (c, v) in enumerate(zip(cats, vals)):
            ry = ly0 + i * rh
            sw = _rrect(slide, lx, ry + rh / 2 - 0.07, 0.14, 0.14, _SERIES[i % len(_SERIES)], radius=0.28)
            tb = _text(slide, lx + 0.26, ry, lw - 0.26, rh, c + "  ", size=11, color=_INK)
            _run(tb.text_frame.paragraphs[0], f"{_num(v)} · {round(v / total * 100)}%", size=10, color=_MUTED)

    def _effort_chart(slide, ch, bx, by, bw, bh):
        pts = ch.get("points") or []
        xlab, ylab = ch.get("x_label", "Effort"), ch.get("y_label", "Value")
        q = (ch.get("quadrants") or ["Quick wins", "Big bets", "Fill-ins", "Time sinks"]) + ["", "", "", ""]
        legend_h = min(bh * 0.46, 0.27 * len(pts) + 0.05)
        ylab_w, xlab_h = 0.32, 0.3
        plot_h = max(1.4, bh - xlab_h - legend_h - 0.2)
        ox, oy, ow, oh = bx + ylab_w, by, bw - ylab_w, plot_h
        # L-shaped frame (left + bottom, like .sl-quad) + dashed centre cross
        _connector(slide, ox, oy, ox, oy + oh, _LINE, width=1)
        _connector(slide, ox, oy + oh, ox + ow, oy + oh, _LINE, width=1)
        _connector(slide, ox + ow / 2, oy, ox + ow / 2, oy + oh, _LINE, dash=True)
        _connector(slide, ox, oy + oh / 2, ox + ow, oy + oh / 2, _LINE, dash=True)
        _text(slide, ox + 0.06, oy + 0.02, ow / 2 - 0.1, 0.22, q[0], size=9, color=_FAINT, anchor=MSO_ANCHOR.TOP)
        _text(slide, ox + ow / 2, oy + 0.02, ow / 2 - 0.06, 0.22, q[1], size=9, color=_FAINT, anchor=MSO_ANCHOR.TOP, align=PP_ALIGN.RIGHT)
        _text(slide, ox + 0.06, oy + oh - 0.24, ow / 2 - 0.1, 0.22, q[2], size=9, color=_FAINT, anchor=MSO_ANCHOR.BOTTOM)
        _text(slide, ox + ow / 2, oy + oh - 0.24, ow / 2 - 0.06, 0.22, q[3], size=9, color=_FAINT, anchor=MSO_ANCHOR.BOTTOM, align=PP_ALIGN.RIGHT)
        for i, pt in enumerate(pts, 1):
            px, py = float(pt.get("x", 1)), float(pt.get("y", 1)); col = _leverage_color(px, py)
            _dot(slide, ox + (px - 1) / 4 * ow, oy + (1 - (py - 1) / 4) * oh, 0.3, _BG, col, i)
        _text(slide, ox, by + oh + 0.02, ow, xlab_h, xlab, size=10, color=_INK, align=PP_ALIGN.CENTER)
        _text(slide, bx - 0.5, by + oh / 2 - 0.15, 1.3, 0.3, ylab, size=10, color=_INK, align=PP_ALIGN.CENTER, rot=270)
        # numbered legend (matches the DS dot legend) below the axis label
        leg_y = by + oh + xlab_h + 0.04
        for i, pt in enumerate(pts, 1):
            px, py = float(pt.get("x", 1)), float(pt.get("y", 1)); col = _leverage_color(px, py)
            ry = leg_y + (i - 1) * 0.27
            _dot(slide, bx + 0.11, ry + 0.115, 0.2, _BG, col, i)
            _text(slide, bx + 0.3, ry, bw - 1.0, 0.23, pt.get("label", ""), size=10, color=_INK)
            _text(slide, bx + bw - 0.7, ry, 0.7, 0.23, f"{xlab[:1]}{_num(px)}·{ylab[:1]}{_num(py)}", size=9, color=_MUTED, align=PP_ALIGN.RIGHT)

    def _chart(slide, ch, x, y, cx, cy):
        bx, by, bw, bh = x.inches, y.inches, cx.inches, cy.inches
        kind = ch.get("type")
        try:
            if kind == "bar" and ch.get("categories"):
                _bar_chart(slide, ch, bx, by, bw, bh)
            elif kind == "pie" and ch.get("categories"):
                _donut_chart(slide, ch, bx, by, bw, bh)
            elif kind == "scatter" and ch.get("points"):
                _effort_chart(slide, ch, bx, by, bw, bh)
        except Exception:
            pass

    for s in slides:
        kind = s.get("kind")
        if kind == "title":
            _title_slide(s)
        elif kind == "image":
            _image_slide(s)
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
