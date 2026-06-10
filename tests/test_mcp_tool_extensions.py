"""The sonaloop.mcp.tools entry-point seam + the public notification transport —
the two core hooks sonaloop-cloud's recurring jobs build on."""
from __future__ import annotations

import anyio
import pytest

from sonaloop import services
from sonaloop import mcp_server


def test_tool_extensions_are_loaded_onto_the_server(monkeypatch):
    registered = []

    class _EP:
        name = "fake-cloud"
        def load(self):
            def register(mcp):
                registered.append(mcp)
                @mcp.tool()
                def cloud_fake_tool() -> dict:
                    """A tool contributed by an extension package."""
                    return {"ok": True}
            return register

    class _Broken:
        name = "broken-ext"
        def load(self):
            raise RuntimeError("bad extension")

    monkeypatch.setattr("importlib.metadata.entry_points",
                        lambda group=None: [_EP(), _Broken()] if group == "sonaloop.mcp.tools" else [])
    mcp = mcp_server.build_server()
    names = {t.name for t in anyio.run(mcp.list_tools)}
    assert "cloud_fake_tool" in names          # the extension's tool is on the SAME server
    assert registered and registered[0] is mcp  # called with the live server
    # the broken extension was skipped, not fatal — build_server returned normally


def test_no_extensions_is_the_quiet_default(monkeypatch):
    monkeypatch.setattr("importlib.metadata.entry_points", lambda group=None: [])
    mcp = mcp_server.build_server()
    assert "record_persona" in {t.name for t in anyio.run(mcp.list_tools)}


def test_deliver_notification_command_roundtrip(tmp_path):
    out = tmp_path / "note.json"
    ok, detail = services.deliver_notification(
        "command", f"cat > {out}", {"event": "cloud.job", "data": {"job": "j1"}})
    assert ok, detail
    assert '"job": "j1"' in out.read_text()


def test_deliver_notification_validates_and_respects_disable(monkeypatch, tmp_path):
    with pytest.raises(ValueError):
        services.deliver_notification("carrier-pigeon", "x", {})
    out = tmp_path / "silenced"
    monkeypatch.setenv("SONALOOP_DISABLE_HOOKS", "1")
    ok, detail = services.deliver_notification("command", f"touch {out}", {})
    assert not ok and "disabled" in detail and not out.exists()


def test_failed_delivery_reports_not_raises():
    ok, detail = services.deliver_notification("command", "exit 7", {"event": "x"})
    assert ok is False and detail
