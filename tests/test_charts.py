"""Charts are design-system components (sonaloop._charts, vendored from sonaloop-design) embedded in
reports via the `chart` figure-kind: bar · pie · effort·impact. (Phase 2 — spec/unified-synthesis-report.)"""
from __future__ import annotations

from sonaloop import _charts
from sonaloop.web._report import render_report


def test_chart_components_render_and_are_empty_safe():
    bar = _charts.bar_chart([{"label": "Plan", "value": 8}, {"label": "Cook", "value": 3}])
    assert "sl-bars" in bar and "sl-bar__fill" in bar and "--v:100.0%" in bar  # max value → full bar
    pie = _charts.pie_chart([{"label": "Support", "value": 12}, {"label": "Oppose", "value": 4}])
    assert "conic-gradient(" in pie and "sl-pie--donut" in pie and "75%" in pie  # 12/16
    ei = _charts.effort_impact([{"label": "Auto list", "x": 2, "y": 5}], x_label="Effort", y_label="Value")
    assert "sl-quad__dot" in ei and "sl-legend__num" in ei and "Quick wins" in ei
    # empty / unscored inputs never fabricate a chart
    assert _charts.bar_chart([]) == "" and _charts.pie_chart([{"label": "x", "value": 0}]) == ""
    assert _charts.effort_impact([{"label": "no score", "x": None, "y": 2}]) == ""


def test_chart_escapes_labels():
    out = _charts.bar_chart([{"label": "<script>", "value": 1}])
    assert "<script>" not in out and "&lt;script&gt;" in out


def _report_with_figures(figures):
    return {"scope": "project", "title": "R — Report", "created_at": "2026-06-08T00:00:00+00:00",
            "lead": "", "graph_snapshot": None,
            "sections": [{"id": "s1", "heading": "Findings", "markdown": "Body.",
                          "citations": [], "figures": figures, "source_study_ids": []}]}


def test_report_embeds_author_supplied_pie_and_bar(store):
    html = render_report(_report_with_figures([
        {"kind": "chart", "of": "pie", "series": [{"label": "A", "value": 3}, {"label": "B", "value": 1}], "caption": "Split"},
        {"kind": "chart", "of": "bar", "series": [{"label": "X", "value": 5}]},
    ]), store)
    assert "sl-pie" in html and "conic-gradient" in html and "sl-bars" in html


def test_report_embeds_synthesis_effort_impact_2x2(store):
    from sonaloop import services
    syn = services.record_synthesis(
        "Solutions", "hmw", [], {"findings": [
            {"kind": "recommendation", "text": "Auto shopping list", "score": {"effort": 2, "value": 5}},
            {"kind": "recommendation", "text": "Hire a coach", "score": {"effort": 4, "value": 2}}]},
        store=store)
    html = render_report(_report_with_figures(
        [{"kind": "chart", "of": "effort_impact", "source_id": syn["id"], "caption": "Leverage"}]), store)
    assert "sl-quad" in html and "sl-quad__dot" in html and "sl-legend__num" in html


def _has_chart(shape):
    return bool(getattr(shape, "has_chart", False))


def test_pptx_export_convergence_synthesis(store):
    """A structured synthesis exports to a native .pptx deck: title + analytic-layer slides + the
    effort·impact 2×2 as a native scatter chart."""
    import io
    from pptx import Presentation
    from sonaloop import services
    syn = services.record_synthesis(
        "Solutions", "hmw", [], {
            "gesamtbild": "G" * 80, "positionierung": "P" * 80,
            "findings": [
                {"kind": "key_problem", "text": "Evenings are the bottleneck"},
                {"kind": "recommendation", "text": "Auto shopping list", "score": {"effort": 2, "value": 5}},
                {"kind": "recommendation", "text": "Hire a coach", "score": {"effort": 4, "value": 2}},
                {"kind": "open_question", "text": "Does it survive week 3?"}]},
        store=store)
    data = services.export_synthesis_pptx(syn["id"], store=store)
    assert data[:2] == b"PK"
    prs = Presentation(io.BytesIO(data))
    assert len(prs.slides) >= 4  # title + big picture + positioning + key problems + recommendations + open Qs
    assert any(_has_chart(sh) for sl in prs.slides for sh in sl.shapes)  # the effort·impact scatter


def test_pptx_export_project_report_with_chart(store):
    """A project report exports one slide per section + author-supplied charts as native pptx charts."""
    import io
    from pptx import Presentation
    from sonaloop import services
    rep = {"id": "rep1", "title": "Demo — Report", "scope": "project", "project_id": "",
           "created_at": "2026-06-08T00:00:00+00:00", "lead": "How the understanding was built.",
           "council_ids": [], "findings": [], "statements": [], "prompts": [], "graph_snapshot": None,
           "sections": [{"id": "s1", "heading": "Findings", "markdown": "- Point one\n- Point two",
                         "citations": [], "source_study_ids": [],
                         "figures": [{"kind": "chart", "of": "pie",
                                      "series": [{"label": "A", "value": 3}, {"label": "B", "value": 1}]}]}]}
    store.upsert_synthesis(rep)
    data = services.export_synthesis_pptx("rep1", store=store)
    assert data[:2] == b"PK"
    prs = Presentation(io.BytesIO(data))
    assert len(prs.slides) >= 2  # title + section
    assert any(_has_chart(sh) for sl in prs.slides for sh in sl.shapes)  # the pie
