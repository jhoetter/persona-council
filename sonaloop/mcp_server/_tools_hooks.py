from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_hooks(mcp):
    # ================= Lifecycle hooks (docs/lifecycle-hooks.md) =================
    @mcp.tool()
    def list_lifecycle_events() -> dict[str, Any]:
        """The documented lifecycle-event catalogue the core emits (persona.created,
        council.recorded = 'session finished', run.finished, …) with each event's stable
        payload contract and the envelope shape — read this before register_hook."""
        t = time.perf_counter()
        return _env("list_lifecycle_events", services.list_lifecycle_events(), t)

    @mcp.tool()
    def register_hook(event: str, kind: str, target: str, label: str = "") -> dict[str, Any]:
        """Subscribe a durable hook to a lifecycle event. `event` is an exact name,
        'domain.*', or '*'. `kind='command'` runs `target` as a shell command with the
        event envelope as JSON on stdin (+ SONALOOP_EVENT env); `kind='webhook'` POSTs
        the envelope to `target`. Idempotent on (event, kind, target); delivery failures
        are logged and never break the emitting operation."""
        t = time.perf_counter()
        return _env("register_hook", services.register_hook(event, kind, target, label), t)

    @mcp.tool()
    def unregister_hook(hook_id: str) -> dict[str, Any]:
        """Remove one durable hook registration by id."""
        t = time.perf_counter()
        return _env("unregister_hook", services.unregister_hook(hook_id), t)

    @mcp.tool()
    def list_hooks() -> dict[str, Any]:
        """All durable hook registrations (id, event pattern, kind, target, label)."""
        t = time.perf_counter()
        return _env("list_hooks", services.list_hooks(), t)

    @mcp.tool()
    def test_hook(hook_id: str) -> dict[str, Any]:
        """Fire a sample envelope through one registered hook and report delivery
        success — the verification step right after register_hook."""
        t = time.perf_counter()
        return _env("test_hook", services.test_hook(hook_id), t)
