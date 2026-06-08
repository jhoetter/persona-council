"""Charts are design-system components (sonaloop._charts, vendored from sonaloop-design) embedded in
reports via the `chart` figure-kind: bar · pie · effort·impact. (Phase 2 — spec/unified-synthesis-report.)"""
from __future__ import annotations

import base64

from sonaloop import _charts
from sonaloop.web._report import render_report


def test_chart_components_render_and_are_empty_safe():
    bar = _charts.bar_chart([{"label": "Plan", "value": 8}, {"label": "Cook", "value": 3}])
    assert "sl-bars" in bar and "sl-bar__fill" in bar and "--v:100.0%" in bar  # max value → full bar
    pie = _charts.pie_chart([{"label": "Support", "value": 12}, {"label": "Oppose", "value": 4}])
    assert "conic-gradient(" in pie and "sl-pie--donut" in pie and "75%" in pie  # 12/16
    ei = _charts.effort_impact([{"label": "Auto list", "x": 2, "y": 5}], x_label="Effort", y_label="Value")
    assert "sl-quad__dot" in ei and "sl-legend__num" in ei and "Quick wins" in ei
    stacked = _charts.stacked_bar_chart([
        {"label": "Pricing", "segments": [{"label": "For", "value": 6}, {"label": "Against", "value": 2}]},
        {"label": "Support", "segments": [{"label": "For", "value": 2}, {"label": "Against", "value": 5}]}])
    # series colour keyed by segment label → one shared legend with 2 series (not 4)
    assert stacked.count("sl-bar__fill--stack") == 2 and "sl-bar__seg" in stacked
    assert "sl-legend--row" in stacked and stacked.count("sl-legend__sw") == 2
    gauge = _charts.gauge_chart([{"label": "Confidence", "value": 72}, {"label": "Done", "value": 9, "max": 12}])
    assert "sl-gauge" in gauge and "--p:72.0" in gauge and "72%" in gauge and "75%" in gauge  # 9/12
    assert "9 / 12" in gauge  # non-100 max shows the raw ratio
    diverging = _charts.diverging_bar_chart(
        [{"label": "Pricing", "positive": 6, "negative": 2}], positive_label="For", negative_label="Against")
    assert "sl-dbar__pos" in diverging and "sl-dbar__neg" in diverging and "+6 · −2" in diverging
    heat = _charts.heatmap_chart(["Cost", "Reach"], [{"label": "Plan A", "values": [2, 5]}])
    assert "sl-heat" in heat and "color-mix(in srgb" in heat and "grid-template-columns" in heat
    dots = _charts.dot_plot_chart([{"label": "Trust", "values": [2, 3, 3, 4, 5]}])
    assert dots.count("sl-dot-pt") == 5 and "sl-dot-mean" in dots and "3.4" in dots  # mean of values
    line = _charts.line_chart([{"label": "Conf", "points": [2, 3, 5, 4, 6]}], labels=["R1", "R2", "R3", "R4", "R5"])
    assert "<svg" in line and "sl-line__path" in line and "<polyline" in line and "sl-line__labels" in line
    # empty / unscored inputs never fabricate a chart
    assert _charts.bar_chart([]) == "" and _charts.pie_chart([{"label": "x", "value": 0}]) == ""
    assert _charts.effort_impact([{"label": "no score", "x": None, "y": 2}]) == ""
    assert _charts.stacked_bar_chart([]) == "" and _charts.gauge_chart([]) == ""
    assert _charts.diverging_bar_chart([]) == "" and _charts.heatmap_chart([], []) == ""
    assert _charts.dot_plot_chart([]) == "" and _charts.line_chart([{"label": "x", "points": [1]}]) == ""


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


def test_report_embeds_author_supplied_stacked_bar_and_gauge(store):
    html = render_report(_report_with_figures([
        {"kind": "chart", "of": "stacked_bar", "caption": "Stance per theme", "series": [
            {"label": "Pricing", "segments": [{"label": "For", "value": 6}, {"label": "Against", "value": 2}]}]},
        {"kind": "chart", "of": "gauge", "series": [{"label": "Confidence", "value": 72}]},
    ]), store)
    assert "sl-bar__fill--stack" in html and "sl-bar__seg" in html
    assert "sl-gauge" in html and "72%" in html


def test_section_validator_preserves_gauge_max_and_stacked_segments():
    from sonaloop.llm_simulation._validators import validate_synthesis_section_payload
    out = validate_synthesis_section_payload({"markdown": "Body.", "figures": [
        {"kind": "chart", "of": "gauge", "series": [{"label": "Confidence", "value": 72, "max": 100}]},
        {"kind": "chart", "of": "stacked_bar", "series": [
            {"label": "Pricing", "segments": [{"label": "For", "value": 6}, {"label": "Against", "value": 2}]}]},
    ]})
    gauge, stacked = out["figures"]
    assert gauge["series"][0]["max"] == 100  # gauge scale survives sanitization
    segs = stacked["series"][0]["segments"]
    assert [s["label"] for s in segs] == ["For", "Against"] and segs[0]["value"] == 6


def test_report_embeds_diverging_heatmap_dotplot_line(store):
    html = render_report(_report_with_figures([
        {"kind": "chart", "of": "diverging_bar", "series": [{"label": "Pricing", "positive": 6, "negative": 2}]},
        {"kind": "chart", "of": "heatmap", "columns": ["Cost", "Reach"],
         "series": [{"label": "Plan A", "values": [2, 5]}]},
        {"kind": "chart", "of": "dot_plot", "series": [{"label": "Trust", "values": [2, 3, 4, 5]}]},
        {"kind": "chart", "of": "line", "labels": ["R1", "R2", "R3"],
         "series": [{"label": "Conf", "points": [2, 4, 6]}]},
    ]), store)
    assert "sl-dbar__pos" in html  # diverging
    assert "sl-heat" in html and "color-mix(in srgb" in html  # heatmap
    assert "sl-dot-track" in html  # dot plot
    assert "sl-line__path" in html and "<svg" in html  # line


def test_section_validator_preserves_new_chart_fields():
    from sonaloop.llm_simulation._validators import validate_synthesis_section_payload
    out = validate_synthesis_section_payload({"markdown": "Body.", "figures": [
        {"kind": "chart", "of": "diverging_bar", "series": [{"label": "Pricing", "positive": 6, "negative": 2}]},
        {"kind": "chart", "of": "heatmap", "columns": ["Cost", "Reach"],
         "series": [{"label": "Plan A", "values": [2, 5]}]},
        {"kind": "chart", "of": "dot_plot", "series": [{"label": "Trust", "values": [2, 3, 4, 5]}]},
        {"kind": "chart", "of": "line", "labels": ["R1", "R2"], "series": [{"label": "Conf", "points": [2, 4]}]},
    ]})
    diverging, heat, dots, line = out["figures"]
    assert diverging["series"][0]["positive"] == 6 and diverging["series"][0]["negative"] == 2
    assert heat["columns"] == ["Cost", "Reach"] and heat["series"][0]["values"] == [2, 5]
    assert dots["series"][0]["values"] == [2, 3, 4, 5]
    assert line["labels"] == ["R1", "R2"] and line["series"][0]["points"] == [2, 4]


def test_chart_catalogue_is_the_single_source_of_truth():
    """The agent-facing catalogue, the renderer registry, and the report dispatch never drift:
    every author-renderable `of` is documented, and every documented `of` actually renders."""
    from sonaloop import services
    from sonaloop.charts_catalogue import _RENDER, render_chart
    cat = services.suggest_chart_kinds()
    kinds = {k["of"] for k in cat["items"]}
    # catalogue = the renderable kinds + the source-driven effort_impact, and nothing else
    assert kinds == set(_RENDER) | {"effort_impact"}
    # each documented entry carries the agent's "when to use" guidance
    assert all(k.get("when_to_use") for k in cat["items"])
    # every renderable kind produces a chart from a minimal series; unknown/source-driven → ""
    sample = {
        "bar": [{"label": "A", "value": 3}], "pie": [{"label": "A", "value": 3}],
        "stacked_bar": [{"label": "A", "segments": [{"label": "x", "value": 2}]}],
        "diverging_bar": [{"label": "A", "positive": 2, "negative": 1}],
        "gauge": [{"label": "A", "value": 50}], "dot_plot": [{"label": "A", "values": [1, 2, 3]}],
        "heatmap": [{"label": "A", "values": [2]}], "line": [{"label": "A", "points": [1, 2, 3]}],
    }
    for of in _RENDER:
        fig = {"columns": ["c"]} if of == "heatmap" else {"labels": ["a", "b", "c"]} if of == "line" else {}
        assert render_chart(of, fig, sample[of]).startswith('<figure class="sl-chart">'), of
    assert render_chart("effort_impact", {}, []) == "" and render_chart("bogus", {}, []) == ""


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


# a minimal valid 1×1 PNG (so add_picture accepts it)
_PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


def test_pptx_embeds_image_figure(tmp_path):
    """Prototype screenshots / image assets must travel in the deck (the PDF loads them by URL; a PPTX
    has to carry the bytes). An image slide embeds the picture."""
    import io
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    from sonaloop import _pptx
    png = tmp_path / "shot.png"; png.write_bytes(_PNG_1X1)
    data = _pptx.render([{"kind": "image", "heading": "Prototype", "num": "03",
                          "image": str(png), "caption": "v0.2"}], title="R")
    prs = Presentation(io.BytesIO(data))
    assert any(sh.shape_type == MSO_SHAPE_TYPE.PICTURE for sl in prs.slides for sh in sl.shapes)


def test_write_export_bytes_round_trip(tmp_path):
    """Binary exports (pdf/pptx) write to disk — the MCP export tool / CLI return this path."""
    from sonaloop import services
    out = services.write_export_bytes(b"%PDF-x", tmp_path / "r.pdf")
    assert out.endswith("r.pdf")
    with open(out, "rb") as fh:
        assert fh.read() == b"%PDF-x"


def test_report_section_image_figure_becomes_image_slide(store, tmp_path, monkeypatch):
    """A section's prototype/asset figure resolves to a file and exports as an image slide."""
    import io
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    from sonaloop import services, assets
    monkeypatch.setattr(assets, "ASSETS_DIR", tmp_path / "assets")
    monkeypatch.setattr("sonaloop.config.DATA_DIR", tmp_path)
    aid = assets.put_asset(_PNG_1X1, "png")
    rep = {"id": "rimg", "title": "Demo — Report", "scope": "project", "project_id": "",
           "created_at": "2026-06-08T00:00:00+00:00", "lead": "", "council_ids": [],
           "findings": [], "statements": [], "prompts": [], "graph_snapshot": None,
           "sections": [{"id": "s1", "heading": "Deliver", "markdown": "Body.", "citations": [],
                         "source_study_ids": [], "figures": [{"kind": "asset", "id": aid, "caption": "Shot"}]}]}
    store.upsert_synthesis(rep)
    data = services.export_synthesis_pptx("rimg", store=store)
    prs = Presentation(io.BytesIO(data))
    assert any(sh.shape_type == MSO_SHAPE_TYPE.PICTURE for sl in prs.slides for sh in sl.shapes)


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
    assert len(prs.slides) >= 5  # title + big picture + positioning + key problems + recommendations + open Qs
    # the effort·impact 2×2 is drawn from native shapes (frame, dashed cross, numbered dots, legend)
    assert sum(len(sl.shapes) for sl in prs.slides) > 20


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
