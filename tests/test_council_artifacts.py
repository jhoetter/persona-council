"""Artifacts into a council (ticket artifacts-into-council): a council can be pointed at a REAL
artifact — a live URL/website, a prototype link, or two A/B variants — so personas react to what is
actually there. Covers: add/list/persistence round-trip, capture degradation (a URL that can't be
fetched still stores a reproducible reference), and that captured artifact content reaches the council
context (single artifact + two labelled variants compared in one run).

Capture is stubbed (no network) by monkeypatching sonaloop.capture.capture_url, mirroring how the
rest of the suite supplies host/IO output inline."""
from __future__ import annotations

from sonaloop import services
from sonaloop import capture as _capture
from conftest import create_persona


def _fake_capture(mapping):
    """Return a capture_url stub that serves canned snapshots by url (and degrades for unknown urls)."""
    def _cap(url, *, timeout=12.0):
        snap = mapping.get(url)
        if snap is None:
            return {"ok": False, "mode": "unavailable", "url": url, "captured_at": "2026-06-09T00:00:00Z",
                    "title": "", "description": "", "headings": [], "text": "", "status": None,
                    "final_url": url, "bytes": 0, "content_hash": "deadbeef", "error": "ConnectError: boom"}
        return {"ok": True, "mode": "text", "url": url, "final_url": url, "status": 200,
                "captured_at": "2026-06-09T00:00:00Z", "bytes": len(snap["text"]),
                "content_hash": snap["hash"], "title": snap["title"], "description": snap.get("desc", ""),
                "headings": snap.get("headings", []), "text": snap["text"]}
    return _cap


def _project(store):
    p = create_persona(store, "Alpha")
    proj = services.create_research_project("Positioning study", goal="how's my positioning",
                                            persona_ids=[p], store=store)
    return proj["id"], p


def test_add_list_persistence_round_trip(store, monkeypatch):
    monkeypatch.setattr(_capture, "capture_url", _fake_capture({
        "https://example.com": {"title": "Example Home", "text": "We sell widgets fast.",
                                 "hash": "h1", "headings": ["Widgets"], "desc": "Best widgets"}}))
    pid, _ = _project(store)

    art = services.add_artifact(pid, "https://example.com", kind="url", store=store)
    assert art["kind"] == "url" and art["url"] == "https://example.com"
    assert art["label"] == "A"
    assert art["title"] == "Example Home"               # captured title fills in
    assert art["content_hash"] == "h1" and art["captured_at"]
    assert art["snapshot"]["ok"] is True

    # Persisted on the PROJECT snapshot (same model as council_ids) — survives a fresh read.
    proj = services.get_research_project(pid, store=store)
    assert [a["id"] for a in proj["artifacts"]] == [art["id"]]
    listed = services.list_artifacts(pid, store=store)
    assert len(listed) == 1 and listed[0]["id"] == art["id"]
    assert services.get_artifact(pid, "A", store=store)["id"] == art["id"]   # addressable by label too

    # Re-adding the same url re-captures (idempotent id, fresh snapshot) — not a duplicate.
    again = services.add_artifact(pid, "https://example.com", kind="url", store=store)
    assert again["id"] == art["id"]
    assert len(services.list_artifacts(pid, store=store)) == 1

    assert services.delete_artifact(pid, art["id"], store=store)["deleted"] == 1
    assert services.list_artifacts(pid, store=store) == []


def test_capture_degrades_but_still_stores_reference(store, monkeypatch):
    # No mapping entry -> the stub returns an "unavailable" snapshot (a dead/blocked link).
    monkeypatch.setattr(_capture, "capture_url", _fake_capture({}))
    pid, _ = _project(store)

    art = services.add_artifact(pid, "https://does-not-resolve.invalid", kind="url", store=store)
    # The artifact is still stored with a reproducible reference (url + captured_at + hash), not dropped.
    assert art["url"] == "https://does-not-resolve.invalid"
    assert art["captured_at"] and art["content_hash"]
    assert art["snapshot"]["ok"] is False
    assert services.list_artifacts(pid, store=store)[0]["id"] == art["id"]


def test_capture_url_never_raises_on_bad_url():
    # The real capture path (no stub) must degrade, never raise — host-authored-text contract.
    snap = _capture.capture_url("http://127.0.0.1:1/definitely-down", timeout=0.5)
    assert snap["ok"] is False and snap["mode"] == "unavailable"
    assert snap["content_hash"] and "error" in snap


def test_artifact_content_reaches_the_council_context(store, monkeypatch):
    monkeypatch.setattr(_capture, "capture_url", _fake_capture({
        "https://site-a.test": {"title": "Variant A", "text": "Calm minimalist landing page.",
                                 "hash": "ha", "headings": ["Hero A"]},
        "https://site-b.test": {"title": "Variant B", "text": "Loud high-contrast landing page.",
                                "hash": "hb", "headings": ["Hero B"]}}))
    pid, persona = _project(store)
    a = services.add_artifact(pid, "https://site-a.test", kind="variant", store=store)
    b = services.add_artifact(pid, "https://site-b.test", kind="variant", store=store)
    assert {a["label"], b["label"]} == {"A", "B"}       # auto A/B labelling for side-by-side compare

    brief = services.brief_council(pid, "Which landing page positions us better?", [persona], store=store)
    # Both variants are present, labelled, and their CAPTURED copy is in the participant's context.
    assert len(brief["artifacts"]) == 2
    ctx = brief["participants"][0]["agent_context"]
    assert "VARIANT A" in ctx and "VARIANT B" in ctx
    assert "Calm minimalist landing page." in ctx
    assert "Loud high-contrast landing page." in ctx
    assert "site-a.test" in ctx and "site-b.test" in ctx
    # The instructions tell the host to ground reactions in the real artifacts.
    assert "ARTIFACTS ARE IN THE ROOM" in brief["instructions"]

    # Selecting a single artifact by label scopes the council to just that one (no A/B framing).
    one = services.brief_council(pid, "Rate variant A", [persona], artifact_ids=["A"], store=store)
    assert len(one["artifacts"]) == 1 and one["artifacts"][0]["label"] == "A"
    assert "Calm minimalist landing page." in one["participants"][0]["agent_context"]
    assert "Loud high-contrast landing page." not in one["participants"][0]["agent_context"]


def test_no_artifacts_means_no_artifact_context(store, monkeypatch):
    monkeypatch.setattr(_capture, "capture_url", _fake_capture({}))
    pid, persona = _project(store)
    brief = services.brief_council(pid, "Open discovery", [persona], store=store)
    assert brief["artifacts"] == []
    assert brief["artifacts_context"] == ""
    assert "ARTIFACTS ARE IN THE ROOM" not in brief["instructions"]
