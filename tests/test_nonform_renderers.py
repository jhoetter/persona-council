"""S1 — non-form renderer templates + the lofi/midfi/hifi fidelity ladder.

Every renderer template is resolved from DATA (suggestions/artifact_types.json). A prototype can be
a guided flow, an overview/dashboard, a card/list interface, or a comparison view — not just a form
— and an INVENTED artifact type renders with no code change. The fidelity ladder (lofi/midfi/hifi)
is data-declared discriminators of the `prototype` type.
"""
from __future__ import annotations

import json

import pytest

from persona_council import presentation, prototypes


def _two_screens(home_extra: dict | None = None) -> dict:
    home = {"id": "home", "title": "Start",
            "elements": [{"kind": "button", "id": "go", "label": "Los", "goto": "next"}]}
    if home_extra:
        home.update(home_extra)
    return {"title": "Demo", "summary": "S", "start": "home",
            "screens": [home,
                        {"id": "next", "title": "Ergebnis",
                         "elements": [{"kind": "text", "id": "t", "label": "fertig"}]}]}


# (type tag, expected template, a template-unique structural marker, screen rich-block)
CASES = [
    ("flow", "spa-flow", "Schritt ", {}),
    ("dashboard", "spa-dashboard", "tiles",
     {"metrics": [{"id": "m1", "label": "Lücke", "value": "480 €", "delta": "+12%", "trend": "up"}],
      "cards": [{"id": "c1", "title": "Familienschutz", "body": "x",
                 "action": {"id": "a1", "label": "Details", "goto": "next"}}]}),
    ("cards", "spa-cards", "clickable",
     {"cards": [{"id": "k1", "title": "Familienschutz", "body": "x", "goto": "next"}]}),
    ("comparison", "spa-comparison", "cols",
     {"columns": [{"id": "o1", "title": "Basis", "rows": [{"label": "Preis", "value": "9 €"}],
                   "cta": {"id": "cta1", "label": "Wählen", "goto": "next"}}]}),
]


@pytest.mark.parametrize("type_tag,template,marker,home_extra", CASES)
def test_nonform_template_scaffolds_clickable(type_tag, template, marker, home_extra, store, tmp_path, monkeypatch):
    monkeypatch.setattr(prototypes, "prototypes_dir", lambda: tmp_path)
    # the template is resolved purely from the type tag's default_template (data)
    assert presentation.resolve_template(type_tag) == template
    rec = prototypes.scaffold_artifact(f"demo-{type_tag}", "Demo", _two_screens(home_extra),
                                       type=type_tag, store=store)
    assert rec["type"] == type_tag
    html = (tmp_path / f"demo-{type_tag}" / "index.html").read_text(encoding="utf-8")
    assert marker in html                       # distinct non-form layout
    assert '"go"' in html and "Los" in html     # the clickable concept is embedded for the SPA


def test_fidelity_ladder_is_data_declared():
    # lofi/midfi/hifi are discriminators of `prototype`, each mapping to a real template — in DATA
    assert presentation.resolve_template("prototype", ["lofi"]) == "spa-sketch"
    assert presentation.resolve_template("prototype", ["midfi"]) == "spa-min"
    assert presentation.resolve_template("prototype", ["hifi"]) == "spa-hifi"
    assert set(presentation.discriminator_tags("prototype")) >= {"lofi", "midfi", "hifi"}
    assert presentation.present("hifi")["short"] == "hi-fi"


def test_hifi_scaffolds_polished_renderer(store, tmp_path, monkeypatch):
    monkeypatch.setattr(prototypes, "prototypes_dir", lambda: tmp_path)
    prototypes.scaffold_prototype("demo-hifi", "Demo", _two_screens(), fidelity="hifi", store=store)
    html = (tmp_path / "demo-hifi" / "index.html").read_text(encoding="utf-8")
    assert "Inter" in html and "data-fidelity" not in html.split("<body")[0]  # polished type, themed body
    assert "'hifi'" in html


def test_invented_artifact_type_renders_from_data(store, tmp_path, monkeypatch):
    """Declare a brand-new artifact type in a suggestions file → it renders with NO code change."""
    sdir = tmp_path / "sugg"
    sdir.mkdir()
    (sdir / "artifact_types.json").write_text(json.dumps({"kind": "artifact_types", "items": [
        {"tag": "concept_app", "renderer": "spa", "default_template": "spa-cards",
         "presentation": {"label": "Konzept-App", "short": "App", "color": "#123456", "glyph": "✦"}}]}),
        encoding="utf-8")
    orig = presentation.suggestions_dir
    presentation.suggestions_dir = lambda: sdir
    presentation.reload_hints()
    try:
        monkeypatch.setattr(prototypes, "prototypes_dir", lambda: tmp_path)
        rec = prototypes.scaffold_artifact("demo-invented", "Demo",
                                           _two_screens({"cards": [{"id": "c", "title": "X", "goto": "next"}]}),
                                           type="concept_app", store=store)
        html = (tmp_path / "demo-invented" / "index.html").read_text(encoding="utf-8")
        assert "clickable" in html                       # resolved to spa-cards from DATA
        assert rec["type"] == "concept_app"
        assert presentation.present("concept_app")["label"] == "Konzept-App"
    finally:
        presentation.suggestions_dir = orig
        presentation.reload_hints()


def test_dead_string_nav_rejected_and_action_alias_normalized(store, tmp_path, monkeypatch):
    """GAP-4: a card/element whose STRING nav target resolves to no screen is rejected at scaffold
    (no silently-dead, yet proband-tested, prototype); a valid `action` string is normalized to
    `goto` so goto-only templates navigate."""
    import persona_council.prototypes as P
    monkeypatch.setattr(P, "prototypes_dir", lambda: tmp_path / "p")
    from persona_council import services
    dead = {"title": "T", "start": "home", "screens": [
        {"id": "home", "title": "H", "cards": [{"id": "c", "title": "Go", "action": "ghost"}]},
        {"id": "real", "title": "R", "elements": [{"kind": "text", "id": "t", "label": "ok"}]}]}
    with pytest.raises(P.PrototypeError):
        services.scaffold_artifact("dead", "Dead", dead, type="prototype", tags=["lofi"], store=store)
    ok = {"title": "T", "start": "home", "screens": [
        {"id": "home", "title": "H", "cards": [{"id": "c", "title": "Go", "action": "real"}]},
        {"id": "real", "title": "R", "elements": [{"kind": "text", "id": "t", "label": "ok"}]}]}
    services.scaffold_artifact("okp", "Ok", ok, type="prototype", tags=["lofi"], store=store)
    import json
    concept = json.loads((tmp_path / "p" / "okp" / "concept.json").read_text())
    card = concept["screens"][0]["cards"][0]
    assert card["goto"] == "real" and card["action"] == "real"   # action string normalized to goto


def test_interactive_model_prototype_scaffolds_with_live_formula(store, tmp_path, monkeypatch):
    """GAP-1: a `model` artifact type renders an INTERACTIVE prototype — range/number inputs feeding
    `computed`/`bar` elements whose `formula` is evaluated live (a steerable model, e.g. a pension
    gap / compounding), not a static screen. Data-driven: the type resolves from artifact_types.json."""
    import persona_council.prototypes as P
    monkeypatch.setattr(P, "prototypes_dir", lambda: tmp_path / "p")
    from persona_council import services, presentation
    assert presentation.resolve_template("model", ["midfi"]) == "spa-model"   # from DATA
    concept = {"title": "Rentenluecke", "summary": "Steuere deine Sparrate", "start": "m",
               "fidelity": "midfi", "screens": [{"id": "m", "title": "Modell", "elements": [
        {"kind": "range", "id": "rate", "label": "Euro/Monat", "min": 0, "max": 500, "step": 10, "value": 100, "suffix": " EUR"},
        {"kind": "range", "id": "jahre", "label": "Jahre", "min": 0, "max": 45, "value": 40},
        {"kind": "computed", "id": "summe", "label": "Eingezahlt", "formula": "rate*12*jahre", "suffix": " EUR", "decimals": 0},
        {"kind": "bar", "id": "ziel", "label": "Richtung Ziel", "formula": "rate*12*jahre", "max": "200000", "suffix": " EUR"}]}]}
    services.scaffold_artifact("model1", "Modell", concept, type="model", tags=["midfi"], store=store)
    html = (tmp_path / "p" / "model1" / "index.html").read_text()
    assert "evalFormula" in html and "computedEls" in html        # the no-eval evaluator is shipped
    saved = json.loads((tmp_path / "p" / "model1" / "concept.json").read_text())
    el = {e["id"]: e for e in saved["screens"][0]["elements"]}
    assert el["summe"]["formula"] == "rate*12*jahre" and el["ziel"]["kind"] == "bar"  # formula preserved


def _journey_concept(rate, title="J"):
    return {"title": title, "summary": "s", "fidelity": "hifi", "start": "s", "screens": [{"id": "s", "title": "S",
        "elements": [
            {"kind": "range", "id": "rate", "label": "Sparrate", "min": 0, "max": 300, "step": 10, "value": rate},
            {"kind": "computed", "id": "sum", "label": "Eingezahlt", "formula": "rate*12*40", "suffix": " EUR"},
            {"kind": "chart", "id": "c", "label": "Verlauf", "x": {"id": "jahre", "from": 0, "to": 40, "step": 10},
             "series": [{"label": "V", "formula": "rate*12*jahre"}]},
            {"kind": "verdict", "id": "v", "cases": [
                {"when": "rate==0", "text": "Du legst nichts zurueck.", "tone": "bad"},
                {"when": "rate>=200", "text": "Starker Puffer.", "tone": "good"}], "else": "Solide.", "elseTone": "warn"}]}]}


def test_journey_type_validates_resolves_and_rejects_malformed(store, tmp_path, monkeypatch):
    """ESV5: the `journey` artifact type resolves to spa-journey (data); a journey with chart + verdict
    scaffolds; a verdict without cases or a chart without x/series is rejected at scaffold."""
    import persona_council.prototypes as P
    monkeypatch.setattr(P, "prototypes_dir", lambda: tmp_path / "p")
    from persona_council import services, presentation
    presentation.reload_hints()
    assert presentation.resolve_template("journey", ["hifi"]) == "spa-journey"
    services.scaffold_artifact("ok", "Ok", _journey_concept(50), type="journey", tags=["hifi"], store=store)
    bad_v = {"title": "T", "start": "s", "screens": [{"id": "s", "title": "S",
             "elements": [{"kind": "verdict", "id": "v"}]}]}            # no cases
    with pytest.raises(P.PrototypeError):
        services.scaffold_artifact("bv", "B", bad_v, type="journey", store=store)
    bad_c = {"title": "T", "start": "s", "screens": [{"id": "s", "title": "S",
             "elements": [{"kind": "chart", "id": "c"}]}]}              # no x/series
    with pytest.raises(P.PrototypeError):
        services.scaffold_artifact("bc", "B", bad_c, type="journey", store=store)


def test_journey_verdict_evaluates_live_in_browser(store, tmp_path, monkeypatch):
    """ESV5: the no-eval evaluator's comparison ops drive a `verdict` live — a journey with rate=0
    shows the bad-case verdict; one with rate=250 shows the good-case (proven via the real browser)."""
    import persona_council.prototypes as P
    monkeypatch.setattr(P, "prototypes_dir", lambda: tmp_path / "p")
    from persona_council import services, browser
    if not browser.available():
        pytest.skip("Playwright unavailable")
    import time
    seen = {}
    for slug, rate, expect in [("jz", 0, "Du legst nichts"), ("jp", 250, "Starker Puffer")]:
        art = services.scaffold_artifact(slug, slug, _journey_concept(rate), type="journey", tags=["hifi"],
                                         project_id=None, store=store)
        run = services.run_prototype(art["id"], store=store); time.sleep(0.6)
        sess = browser.open_session(run["url"], art["id"], "t")
        seen[slug] = sess["snapshot"]["text"]
        browser.close(sess["session_id"]); services.stop_prototype(art["id"], store=store)
        assert expect in seen[slug], (slug, seen[slug][:200])
