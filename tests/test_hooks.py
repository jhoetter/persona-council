"""Lifecycle hooks: the event catalogue, in-process handlers, durable command
hooks, and the emission points (ticket sonaloop/lifecycle-hooks).

The contract under test: events fire AFTER persistence, payloads carry stable
ids, and a failing subscriber never breaks the emitting operation."""
from __future__ import annotations

import json

import pytest

from sonaloop import services
from sonaloop.services import _hooks

from conftest import create_persona


@pytest.fixture(autouse=True)
def _clean_handlers(monkeypatch):
    """Each test gets an empty in-process handler registry and no entry-point scan."""
    monkeypatch.setattr(_hooks, "_HANDLERS", {})
    monkeypatch.setattr(_hooks, "_ENTRY_POINTS_LOADED", True)
    yield


def _capture(events: list):
    def handler(envelope):
        events.append(envelope)
    return handler


def test_event_catalogue_is_documented():
    cat = services.list_lifecycle_events()
    assert "council.recorded" in cat["events"]
    assert cat["envelope"]["schema"] == _hooks.HOOK_ENVELOPE_VERSION
    for spec in cat["events"].values():
        assert spec["description"] and spec["payload"]


def test_persona_created_emits_with_stable_ids(store):
    seen: list = []
    services.add_hook_handler("persona.created", _capture(seen))
    pid = create_persona(store, "Hooked Persona")
    assert [e["event"] for e in seen] == ["persona.created"]
    assert seen[0]["data"]["persona_id"] == pid
    assert seen[0]["schema"] == 1 and seen[0]["emitted_at"]


def test_update_and_evidence_events(store):
    seen: list = []
    services.add_hook_handler("persona.*", _capture(seen))
    services.add_hook_handler("evidence.attached", _capture(seen))
    pid = create_persona(store, "Patch Target")
    services.update_persona(pid, {"goals": ["new goal"]}, "test patch", store=store)
    ev = services.attach_evidence(pid, "user_note", "observed in interview", store=store)
    names = [e["event"] for e in seen]
    assert names == ["persona.created", "persona.updated", "evidence.attached"]
    assert seen[1]["data"]["reason"] == "test patch"
    assert seen[2]["data"]["evidence_id"] == ev["id"]


def test_council_recorded_is_the_session_finished_event(store):
    seen: list = []
    services.add_hook_handler("council.recorded", _capture(seen))
    pid = create_persona(store, "Council Member")
    project = services.start_project("Hook study", "does it fire?", persona_ids=[pid], store=store)
    council = services.record_council(project["id"], "What changed?", [pid], store=store)
    assert len(seen) == 1
    data = seen[0]["data"]
    assert data["council_id"] == council["id"]
    assert data["project_id"] == project["id"]
    assert data["persona_ids"] == [pid]


def test_project_synthesis_and_run_events(store):
    seen: list = []
    services.add_hook_handler("*", _capture(seen))
    project = services.start_project("Full arc", "goal", store=store)
    services.record_synthesis("Answer", "goal", store=store)
    run = services.start_run(project["id"], store=store)
    services.finish_run(run["run_id"], "stopped", store=store)
    names = [e["event"] for e in seen]
    assert "project.created" in names
    assert "synthesis.recorded" in names
    assert names[-1] == "run.finished"
    finished = seen[-1]["data"]
    assert finished == {"run_id": run["run_id"], "project_id": project["id"],
                        "status": "stopped", "steps": 0}


def test_failing_handler_never_breaks_the_operation(store):
    def boom(_envelope):
        raise RuntimeError("subscriber bug")
    services.add_hook_handler("persona.created", boom)
    pid = create_persona(store, "Resilient")  # must not raise
    assert pid


def test_register_hook_validates_event_and_kind(store):
    with pytest.raises(ValueError):
        services.register_hook("no.such.event", "command", "true", store=store)
    with pytest.raises(ValueError):
        services.register_hook("council.recorded", "carrier-pigeon", "true", store=store)
    with pytest.raises(ValueError):
        services.register_hook("council.recorded", "command", "   ", store=store)


def test_durable_command_hook_receives_envelope_on_stdin(store, tmp_path):
    out = tmp_path / "envelope.json"
    hook = services.register_hook("council.recorded", "command", f"cat > {out}",
                                  label="capture", store=store)
    assert hook["id"] in {h["id"] for h in services.list_hooks(store=store)}
    pid = create_persona(store, "Sender")
    project = services.start_project("Delivery", "goal", persona_ids=[pid], store=store)
    services.record_council(project["id"], "ping", [pid], store=store)
    envelope = json.loads(out.read_text(encoding="utf-8"))
    assert envelope["event"] == "council.recorded"
    assert envelope["data"]["project_id"] == project["id"]


def test_register_is_idempotent_and_unregister_removes(store):
    h1 = services.register_hook("*", "command", "true", store=store)
    h2 = services.register_hook("*", "command", "true", store=store)
    assert h1["id"] == h2["id"]
    assert len(services.list_hooks(store=store)) == 1
    services.unregister_hook(h1["id"], store=store)
    assert services.list_hooks(store=store) == []
    with pytest.raises(KeyError):
        services.unregister_hook(h1["id"], store=store)


def test_test_hook_reports_delivery_outcome(store, tmp_path):
    ok_hook = services.register_hook("council.recorded", "command", "cat > /dev/null", store=store)
    bad_hook = services.register_hook("day.recorded", "command", "exit 3", store=store)
    assert services.test_hook(ok_hook["id"], store=store)["ok"] is True
    verdict = services.test_hook(bad_hook["id"], store=store)
    assert verdict["ok"] is False and verdict["envelope"]["data"] == {"test": True}


def test_disable_env_skips_external_delivery(store, tmp_path, monkeypatch):
    out = tmp_path / "should_not_exist"
    services.register_hook("persona.created", "command", f"touch {out}", store=store)
    monkeypatch.setenv("SONALOOP_DISABLE_HOOKS", "1")
    create_persona(store, "Silenced")
    assert not out.exists()


def test_wildcard_and_domain_patterns():
    assert _hooks._event_matches("*", "run.finished")
    assert _hooks._event_matches("persona.*", "persona.updated")
    assert not _hooks._event_matches("persona.*", "council.recorded")
    assert not _hooks._event_matches("persona.created", "persona.updated")
