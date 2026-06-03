"""M3 — Playwright harness: a persona-agent drives the REAL running app.

Live when chromium is installed; otherwise asserts graceful PLAYWRIGHT_UNAVAILABLE
(per spec: harness tests skip the live path when chromium is absent).
"""
from __future__ import annotations

import pytest

from persona_council import browser, prototypes, services


_CONCEPT = {
    "title": "Übergabe-Check", "summary": "Was hat sich geändert?", "start": "home",
    "screens": [
        {"id": "home", "title": "Start", "elements": [
            {"kind": "button", "id": "go", "label": "Vergleichen", "goto": "result"}]},
        {"id": "result", "title": "Ergebnis", "elements": [
            {"kind": "text", "id": "t2", "label": "W-12 (tragende Wand) entfernt."}]},
    ],
}


def _proto(store, tmp_path, monkeypatch, slug):
    monkeypatch.setattr(prototypes, "prototypes_dir", lambda: tmp_path)
    return prototypes.scaffold_prototype(slug, "Übergabe-Check", _CONCEPT, store=store)


def test_unavailable_is_graceful(store, tmp_path, monkeypatch):
    if browser.available():
        pytest.skip("playwright present; covered by the live test")
    with pytest.raises(browser.HarnessError) as e:
        browser.open_session("http://127.0.0.1:1/x")
    assert e.value.code == "PLAYWRIGHT_UNAVAILABLE"


@pytest.mark.skipif(not browser.available(), reason="chromium not installed")
def test_agent_drives_real_app(store, tmp_path, monkeypatch):
    _proto(store, tmp_path, monkeypatch, "harness-live")
    info = prototypes.run_prototype("harness-live", store=store)
    try:
        opened = browser.open_session(info["url"], prototype_id="harness-live")
        sid = opened["session_id"]
        # the start screen exposes the "Vergleichen" button with a ref
        refs = _refs(opened["snapshot"])
        go = next(r for r, spec in refs.items() if "Vergleichen" in spec["name"])
        out = browser.act(sid, {"type": "click", "ref": go})
        # clicking navigated to the result screen -> real observed state change
        assert "W-12" in out["snapshot"]["text"]
        # a stale/fabricated ref is rejected
        with pytest.raises(browser.HarnessError) as e:
            browser.act(sid, {"type": "click", "ref": "e999"})
        assert e.value.code == "STALE_REF"
        # groundedness: a reaction citing a real observed state is accepted...
        res = services.record_prototype_session(
            "pX", "harness-live", sid, "2026-06-03",
            {"summary": "tried it", "liked": ["catches W-12"], "observed_state_refs": ["W-12"]}, store=store)
        assert res["grounded_verified"] is True
        # ...one citing a never-seen state is rejected
        with pytest.raises(ValueError):
            services.record_prototype_session(
                "pX", "harness-live", sid, "2026-06-03",
                {"summary": "x", "observed_state_refs": ["NONEXISTENT-STATE-XYZ"]}, store=store)
    finally:
        try:
            browser.close(opened["session_id"])
        except Exception:
            pass
        prototypes.stop_prototype("harness-live", store=store)


def _refs(snapshot):
    tree = snapshot["tree"]
    nodes = tree if isinstance(tree, list) else [tree]
    return {n["ref"]: {"role": n["role"], "name": n["name"]} for n in nodes if n.get("ref")}
