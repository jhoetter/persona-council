"""Presentation-from-data (spec/methodology-presentation-from-data.md).

The UI + artifact subsystem must carry ZERO hardcoded methodology/artifact values: every label,
color, glyph and template comes from data (tag strings / `presentation` blocks / generic functions).
A grep gate fails if a forbidden literal reappears; an INVENTED artifact type renders entirely from
its own data with no code change.
"""
from __future__ import annotations

import json
from pathlib import Path

from persona_council import methodology as M
from persona_council import presentation as P
from persona_council import prototypes, services, web


# --------------------------------------------------------------------------- P4: grep gate

FORBIDDEN = {
    "persona_council/web.py": [
        '"lofi"', '"midfi"', '"lo-fi"', '"mid-fi"', '"Prototyp"', '"▢"',
        '== "lofi"', '== "midfi"', '{"lofi"', '{"midfi"',
    ],
    "persona_council/prototypes.py": [
        "TEMPLATES = {", '{"lofi"', '{"midfi"', '== "lofi"', '== "midfi"',
        '"lo-fi"', '"mid-fi"', 'in ("lofi"', 'in ("midfi"',
    ],
}


def test_no_hardcoded_methodology_values_in_ui():
    root = Path(__file__).resolve().parent.parent
    for rel, literals in FORBIDDEN.items():
        src = (root / rel).read_text(encoding="utf-8")
        for lit in literals:
            assert lit not in src, f"{rel} must not contain hardcoded artifact literal {lit!r}"


# --------------------------------------------------------------------------- P1: resolver

def test_present_fallbacks_are_generic():
    # an unknown tag → raw label + a deterministic hashed color, no icon/glyph
    r = P.present("totally-invented-tag")
    assert r["label"] == "totally-invented-tag"
    assert r["color"] in P.PALETTE
    assert r["color"] == P.present("totally-invented-tag")["color"]  # deterministic
    assert r["icon"] == "" and r["glyph"] == ""


def test_object_presentation_overrides_data():
    r = P.present("prototype", own={"label": "MY LABEL", "color": "#123456"})
    assert r["label"] == "MY LABEL" and r["color"] == "#123456"


def test_builtin_artifact_hints_come_from_data():
    # the lofi/midfi/prototype labels live in suggestions/artifact_types.json, not code
    assert P.present("lofi")["short"] == "lo-fi"
    assert P.present("midfi")["short"] == "mid-fi"
    assert P.present("prototype")["label"] == "Prototyp"
    assert P.resolve_template("prototype", ["lofi"]) == "spa-sketch"
    assert P.resolve_template("prototype", ["midfi"]) == "spa-min"


def test_structural_glyph_not_value_keyed():
    assert P.step_glyph(True) == P.FAN_GLYPH and P.step_glyph(False) == P.WAIST_GLYPH
    assert P.step_glyph(False, own={"glyph": "★"}) == "★"  # data override


# --------------------------------------------------------------------------- P2: invented type

def test_invented_artifact_type_renders_from_data(store, tmp_path, monkeypatch):
    """An artifact type the host invents via MCP data (journey-map, draft/final) scaffolds and
    renders its node label/color FROM ITS OWN DATA — zero code changes, no value literal."""
    sdir = tmp_path / "suggestions"
    sdir.mkdir()
    (sdir / "artifact_types.json").write_text(json.dumps({"kind": "artifact_types", "items": [
        {"tag": "journey-map", "renderer": "spa", "default_template": "spa-min",
         "presentation": {"label": "Journey Map", "color": "#abcdef", "glyph": "🗺"},
         "discriminators": [
             {"tag": "draft", "template": "spa-sketch", "presentation": {"label": "Entwurf", "short": "Entwurf"}},
             {"tag": "final", "template": "spa-min", "presentation": {"label": "Final", "short": "final"}}]},
    ]}), encoding="utf-8")
    monkeypatch.setattr(P, "suggestions_dir", lambda: sdir)
    monkeypatch.setattr(prototypes, "prototypes_dir", lambda: tmp_path / "arts")
    P.reload_hints()
    try:
        # template resolves from the invented data (draft -> spa-sketch)
        assert P.resolve_template("journey-map", ["draft"]) == "spa-sketch"
        art = services.scaffold_artifact("jm1", "Onboarding Journey",
            {"title": "JM", "summary": "", "start": "h", "screens": [
                {"id": "h", "title": "H", "elements": [{"kind": "text", "id": "t", "label": "x"}]}]},
            type="journey-map", tags=["draft"], project_id="proj1", store=store)
        assert art["type"] == "journey-map" and "draft" in art["tags"]
        # the UI resolves label/color/glyph PURELY from the data
        ap = web._artifact_present(art)
        assert ap["label"] == "Journey Map"      # from presentation.label
        assert ap["color"] == "#abcdef"          # from presentation.color
        assert ap["glyph"] == "🗺"                # from presentation.glyph
        assert ap["disc"] == "Entwurf"           # discriminator short label from data
    finally:
        P.reload_hints()


# --------------------------------------------------------------------------- P3: structure

def test_step_tags_are_first_class_on_nodes(store):
    """A node carries its step's open tags so they are filterable like theme tags."""
    proj = M.start_methodology_project("DD", "g", "double_diamond", store=store)
    pid = proj["id"]
    store.insert_council_session({"id": "c1", "created_at": "2026-01-01T00:00:00+00:00", "prompt": "p",
        "persona_ids": ["p1"], "turns": [], "votes": [], "proposal": "", "summary": "",
        "exec_summary": "e", "selection_reason": "x"})
    M.record_node(pid, "A", ["c1"], {"gesamtbild": "a"}, store=store)
    graph = services.get_project_graph(pid, store=store)
    disc_node = next(n for n in graph["nodes"] if n.get("phase") == "discover")
    assert "explore" in disc_node["theme_tags"]          # capability tag is now filterable
    assert "problem-landscape" in disc_node["theme_tags"]  # role tag too


def test_empty_step_draws_no_diamond(store):
    """A declared fan with no nodes yet must NOT render an (empty) diamond silhouette."""
    proj = M.start_methodology_project("DD", "g", "double_diamond_deep", store=store)
    pid = proj["id"]
    store.insert_council_session({"id": "c1", "created_at": "2026-01-01T00:00:00+00:00", "prompt": "p",
        "persona_ids": ["p1"], "turns": [], "votes": [], "proposal": "", "summary": "",
        "exec_summary": "e", "selection_reason": "x"})
    store.insert_council_session({"id": "c2", "created_at": "2026-01-01T00:00:00+00:00", "prompt": "p",
        "persona_ids": ["p1"], "turns": [], "votes": [], "proposal": "", "summary": "",
        "exec_summary": "e", "selection_reason": "x"})
    M.record_node(pid, "A", ["c1"], {"gesamtbild": "a"}, store=store)
    M.record_node(pid, "B", ["c2"], {"gesamtbild": "b"}, store=store)
    graph = services.get_project_graph(pid, store=store)
    ml = web._methodology_layout(graph)
    # only `discover` has nodes → exactly one diamond, not one per declared diverge step
    assert len(ml["diamonds"]) == 1
