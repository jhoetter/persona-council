"""Selective live actuation (rung 2): owned-surface scoping, tightened caps,
fail-soft without the browser, and the evidence-quality gate."""
from __future__ import annotations

import pytest

from sonaloop import services
from sonaloop.services import _actuation

from conftest import create_persona


@pytest.fixture
def persona(store):
    return create_persona(store, "Driver")


# --- owned-surface scoping -----------------------------------------------------------

def test_owned_origins_default_to_loopback_plus_declared(monkeypatch):
    monkeypatch.delenv("SONALOOP_OWNED_ORIGINS", raising=False)
    assert any("localhost" in o for o in services.owned_origins())
    assert not _actuation._is_owned("https://example.com/app")
    assert _actuation._is_owned("http://localhost:8123/x")
    monkeypatch.setenv("SONALOOP_OWNED_ORIGINS", "https://staging.sonaloop.dev")
    assert _actuation._is_owned("https://staging.sonaloop.dev/login")


def test_walk_own_refuses_unowned_surfaces(store, persona, monkeypatch):
    monkeypatch.setattr(_actuation._browser, "available", lambda: True)
    with pytest.raises(ValueError, match="rung 3"):
        services.walk_own(persona, url="https://thirdparty.example.com", store=store)
    with pytest.raises(ValueError):
        services.walk_own(persona, store=store)                      # neither id nor url
    with pytest.raises(ValueError):
        services.walk_own(persona, prototype_id="p", url="http://localhost:1", store=store)


def test_walk_own_locks_origin_and_clamps_caps(store, persona, monkeypatch):
    captured = {}

    def fake_walk_open(url, persona_id, policy=None, project_id=None, store=None):
        captured.update({"url": url, "policy": policy, "project_id": project_id})
        return {"session_id": "sess_1", "snapshot": {}, "fidelity": "live", "policy": policy}

    monkeypatch.setattr(_actuation._browser, "available", lambda: True)
    monkeypatch.setattr(_actuation, "walk_open", fake_walk_open)     # bound cross-module name
    out = services.walk_own(persona, url="http://localhost:9001/start",
                            policy={"max_actions": 500, "max_duration_s": 9999},
                            project_id="proj-x", store=store)
    assert out["rung"] == "owned" and captured["project_id"] == "proj-x"
    assert captured["policy"]["allowed_origins"] == ["http://localhost:9001"]
    assert captured["policy"]["max_actions"] == _actuation.OWNED_MAX_ACTIONS      # clamped DOWN
    assert captured["policy"]["max_duration_s"] == _actuation.OWNED_MAX_DURATION_S


def test_walk_own_runs_the_prototype_first(store, persona, monkeypatch):
    monkeypatch.setattr(_actuation._browser, "available", lambda: True)
    monkeypatch.setattr(_actuation, "run_prototype",
                        lambda pid, store=None: {"prototype_id": pid, "url": "http://127.0.0.1:8222"})
    monkeypatch.setattr(_actuation, "walk_open",
                        lambda url, persona_id, policy=None, project_id=None, store=None:
                        {"session_id": "s", "fidelity": "live", "policy": policy, "url": url})
    out = services.walk_own(persona, prototype_id="proto-1", store=store)
    assert out["prototype_id"] == "proto-1" and out["rung"] == "owned"
    assert out["policy"]["allowed_origins"] == ["http://127.0.0.1:8222"]


def test_fail_soft_without_browser(store, persona, monkeypatch):
    """Core stays fully functional without Playwright — rung 2 degrades, never crashes."""
    monkeypatch.setattr(_actuation._browser, "available", lambda: False)
    out = services.walk_own(persona, url="http://localhost:9001", store=store)
    assert out["ok"] is False and out["unavailable"] is True
    assert "brief_flow_walkthrough" in out["fallback"]               # the artifact rung


# --- the evidence-quality gate ---------------------------------------------------------

def _record(store, persona_id, project_id, fidelity, key, *, monologues, screenshots, verified):
    steps = []
    for i in range(3):
        state = {"screen": f"screen {i}"}
        if screenshots:
            state["title"] = f"t{i}"
        steps.append({"index": i, "action": {"type": "look", "target": "", "detail": ""},
                      "monologue": monologues[i], "state": state,
                      "friction": {"level": ["none", "hesitation", "confusion"][i], "note": ""},
                      "verdict": {"would_continue": i < 2, "reason": "lost" if i == 2 else "ok"}})
    out = {"completed": False, "dropoff_step": 2, "summary": "dropped",
           "predicted_behaviors": [{"action": "gives up", "step": 2, "likelihood": "likely"}]}
    res = services.record_usability_session(
        persona_id, {"kind": "flow", "id": "flow-x", "label": "Signup"}, fidelity,
        "2026-06-10", steps, out, project_id=project_id, key=key, store=store)
    sess_id = res["usability_session"]["id"]
    if verified:                                  # simulate the browser-verified live trace
        sess = store.get_usability_session(sess_id)
        sess["grounded_verified"] = True
        store.insert_usability_session(sess)
    return sess_id


def test_gate_derives_winner_and_persists(store, persona, monkeypatch):
    project = services.start_project("Gate study", "rung 1 vs rung 2", persona_ids=[persona], store=store)
    art = _record(store, persona, project["id"], "artifact", "a1",
                  monologues=["short", "short", "short"], screenshots=False, verified=False)
    live = _record(store, persona, project["id"], "live", "l1",
                   monologues=["a much longer concurrent think-aloud line"] * 3,
                   screenshots=False, verified=True)
    report = services.record_actuation_gate(project["id"], art, live,
                                            note="live verified + denser monologue", store=store)
    assert report["winner"] == "live" and report["green"] is True
    assert report["same_subject"] is True
    assert "verified" in report["wins"]["live"]
    assert "monologue_chars_per_step" in report["wins"]["live"]
    stored = [r for r in store.list_eval_reports() if r.get("kind") == "actuation_gate"]
    assert stored and stored[0]["winner"] == "live"                  # the recorded head-to-head
    with pytest.raises(KeyError):
        services.record_actuation_gate(project["id"], "sess_missing", live, store=store)
