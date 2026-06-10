"""Lifecycle hooks: documented events the core emits + the subscription seams.

Three ways to listen, layered cheapest-first (docs/lifecycle-hooks.md):

1. In-process handlers — ``add_hook_handler(event, fn)``. For code living in the
   same process (tests, embedded hosts).
2. Entry-point extensions — the ``sonaloop.hooks`` entry-point group, the hooks
   counterpart of ``sonaloop.web.extensions``: each entry point resolves to a
   ``setup()`` callable that registers in-process handlers. This is the seam
   sonaloop-cloud / sonaloop-research plug their connectors into.
3. Durable hooks — ``register_hook(event, kind, target)`` persists a
   command/webhook subscription in the DB; every matching event runs the command
   (envelope JSON on stdin) or POSTs the envelope to the URL. This is how a USER
   wires "session finished → notify me" with no Python involved.

Emission is best-effort by contract: a failing handler/hook is logged and never
breaks the core operation that emitted the event. The envelope is the stable
surface cloud connectors consume — version-stamped, ids + summaries only."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import urllib.request
from typing import Any, Callable

from ..config import utc_now_iso
from ..storage import Store
from ._common import stable_id

log = logging.getLogger("sonaloop.hooks")

HOOK_ENVELOPE_VERSION = 1

# The documented event catalogue: every event the core emits, with the payload
# contract cloud connectors can rely on (ids + lean summaries, never authored text).
LIFECYCLE_EVENTS: dict[str, dict[str, Any]] = {
    "persona.created": {
        "description": "A host-authored persona profile was validated and persisted.",
        "payload": {"persona_id": "id", "slug": "slug", "display_name": "name"},
    },
    "persona.updated": {
        "description": "A persona profile was patched (reason carries the audit trail).",
        "payload": {"persona_id": "id", "reason": "why the patch happened"},
    },
    "evidence.attached": {
        "description": "A real-world source (doc/url/note) was attached to a persona.",
        "payload": {"persona_id": "id", "evidence_id": "id", "source_type": "doc|url|user_note|…"},
    },
    "persona.grounded": {
        "description": "A persona was grounded in real source material (provenance recorded).",
        "payload": {"persona_id": "id", "corpus_ids": ["corpus ids"], "claims": "new claim count"},
    },
    "prediction.scored": {
        "description": "A real outcome was matched to a predicted behavior (Brier derived).",
        "payload": {"project_id": "id", "outcome_id": "id", "brier": "0..1", "hit": "bool"},
    },
    "calibration.round_recorded": {
        "description": "A correction round was stamped after calibration misses (docs/calibration.md).",
        "payload": {"scope": "project id or 'global'", "corrections": "count", "mean_brier": "0..1|null"},
    },
    "asset.attached": {
        "description": "A file/image/screenshot was attached to a project as evidence.",
        "payload": {"project_id": "id", "asset_id": "id", "kind": "image|screenshot|document|file",
                    "filename": "name"},
    },
    "chat.recorded": {
        "description": "A persona chat exchange was persisted (one authored turn pair).",
        "payload": {"chat_id": "id", "persona_id": "id", "turns": "total turn count"},
    },
    "day.recorded": {
        "description": "One simulated day was persisted (calendar + experience + summary).",
        "payload": {"persona_id": "id", "date": "YYYY-MM-DD", "events": "experience-event count"},
    },
    "council.recorded": {
        "description": "A council session finished and was persisted inside its project. "
                       "This is the 'session finished' moment.",
        "payload": {"council_id": "id", "project_id": "id", "prompt": "the council prompt",
                    "persona_ids": ["id"], "statements": "count", "votes": "count"},
    },
    "synthesis.recorded": {
        "description": "A synthesis (answer/report node) was created or updated.",
        "payload": {"synthesis_id": "id", "title": "title", "status": "status",
                    "council_ids": ["referenced council ids"]},
    },
    "project.created": {
        "description": "A research project was created and its plan seeded.",
        "payload": {"project_id": "id", "title": "title", "goal": "goal",
                    "methodology": "framework key or ''"},
    },
    "project.updated": {
        "description": "A project's structural metadata (title/goal/description/status) was patched.",
        "payload": {"project_id": "id", "title": "title"},
    },
    "run.finished": {
        "description": "A governed run ended (status finished|stopped) — the study completed.",
        "payload": {"run_id": "id", "project_id": "id", "status": "finished|stopped",
                    "steps": "checkpointed step count"},
    },
}

HOOK_KINDS = ("command", "webhook")

# In-process handlers: event pattern -> [callable(envelope), ...]
_HANDLERS: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
_ENTRY_POINTS_LOADED = False


def _hooks_disabled() -> bool:
    return os.getenv("SONALOOP_DISABLE_HOOKS", "").lower() in {"1", "true", "yes"}


def _hook_timeout() -> float:
    try:
        return max(1.0, min(120.0, float(os.getenv("SONALOOP_HOOK_TIMEOUT", 10.0))))
    except (TypeError, ValueError):
        return 10.0


def _event_matches(pattern: str, event: str) -> bool:
    """Exact match, '*' (everything), or 'domain.*' (one domain's events)."""
    if pattern == "*" or pattern == event:
        return True
    return pattern.endswith(".*") and event.startswith(pattern[:-1])


def _validate_event_pattern(pattern: str) -> str:
    p = (pattern or "").strip()
    if p == "*" or p in LIFECYCLE_EVENTS:
        return p
    if p.endswith(".*") and any(e.startswith(p[:-1]) for e in LIFECYCLE_EVENTS):
        return p
    raise ValueError(
        f"Unknown lifecycle event pattern: {pattern!r}. "
        f"Valid: {sorted(LIFECYCLE_EVENTS)} (or '*' / '<domain>.*')")


def load_hook_extensions() -> int:
    """Load the ``sonaloop.hooks`` entry-point group (idempotent). Each entry point
    is a ``setup()`` callable that registers in-process handlers. A broken extension
    is logged and skipped — same graceful contract as the web extension seam."""
    global _ENTRY_POINTS_LOADED
    if _ENTRY_POINTS_LOADED:
        return 0
    _ENTRY_POINTS_LOADED = True
    loaded = 0
    try:
        from importlib.metadata import entry_points
        for ep in entry_points(group="sonaloop.hooks"):
            try:
                ep.load()()
                loaded += 1
            except Exception as exc:
                log.warning("hook extension %r failed to load: %s", ep.name, exc)
    except Exception as exc:
        log.warning("hook entry-point discovery failed: %s", exc)
    return loaded


def add_hook_handler(event: str, handler: Callable[[dict[str, Any]], None]) -> None:
    """Register an in-process handler. ``event`` accepts the same patterns as
    durable hooks ('*' / 'domain.*' / exact). The handler receives the envelope."""
    _HANDLERS.setdefault(_validate_event_pattern(event), []).append(handler)


def remove_hook_handler(event: str, handler: Callable[[dict[str, Any]], None]) -> None:
    if event in _HANDLERS:
        _HANDLERS[event] = [h for h in _HANDLERS[event] if h is not handler]


def list_lifecycle_events() -> dict[str, Any]:
    """The documented event catalogue (names, payload contracts, envelope shape)."""
    return {
        "envelope": {"event": "<name>", "schema": HOOK_ENVELOPE_VERSION,
                     "emitted_at": "ISO-8601 UTC", "data": "<payload per event>"},
        "events": LIFECYCLE_EVENTS,
        "patterns": "subscribe with an exact name, 'domain.*', or '*'",
    }


def register_hook(event: str, kind: str, target: str, label: str = "",
                  store: Store | None = None) -> dict[str, Any]:
    """Persist a durable hook: ``kind='command'`` runs ``target`` as a shell command
    with the event envelope as JSON on stdin (+ SONALOOP_EVENT in its env);
    ``kind='webhook'`` POSTs the envelope to ``target`` as JSON. Registration is
    idempotent on (event, kind, target)."""
    store = store or Store()
    event = _validate_event_pattern(event)
    if kind not in HOOK_KINDS:
        raise ValueError(f"Unknown hook kind: {kind!r}. Valid: {list(HOOK_KINDS)}")
    if not (target or "").strip():
        raise ValueError("Hook target must be a non-empty command or URL.")
    hook = {
        "id": stable_id("hook", event, kind, target),
        "event": event, "kind": kind, "target": target.strip(),
        "label": label or "", "enabled": True, "created_at": utc_now_iso(),
    }
    store.upsert_lifecycle_hook(hook)
    return hook


def unregister_hook(hook_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    deleted = store.delete_lifecycle_hook(hook_id)
    if not deleted:
        raise KeyError(f"Unknown hook: {hook_id}")
    return {"id": hook_id, "deleted": True}


def list_hooks(store: Store | None = None) -> list[dict[str, Any]]:
    """All durable hook registrations (the persisted subscriptions)."""
    store = store or Store()
    return store.list_lifecycle_hooks()


def _deliver_command(target: str, envelope: dict[str, Any]) -> tuple[bool, str]:
    proc = subprocess.run(
        target, shell=True, input=json.dumps(envelope, ensure_ascii=False),
        capture_output=True, text=True, timeout=_hook_timeout(),
        env={**os.environ, "SONALOOP_EVENT": envelope["event"]},
    )
    detail = (proc.stderr or proc.stdout or "").strip()[:500]
    return proc.returncode == 0, detail or f"exit {proc.returncode}"


def _deliver_webhook(target: str, envelope: dict[str, Any]) -> tuple[bool, str]:
    req = urllib.request.Request(
        target, data=json.dumps(envelope, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "X-Sonaloop-Event": envelope["event"]},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_hook_timeout()) as resp:
        return 200 <= resp.status < 300, f"HTTP {resp.status}"


def _deliver(hook: dict[str, Any], envelope: dict[str, Any]) -> tuple[bool, str]:
    try:
        if hook.get("kind") == "webhook":
            return _deliver_webhook(hook["target"], envelope)
        return _deliver_command(hook["target"], envelope)
    except Exception as exc:
        return False, str(exc)[:500]


def deliver_notification(kind: str, target: str, envelope: dict[str, Any]) -> tuple[bool, str]:
    """PUBLIC one-shot delivery on the hook transport: run a command (envelope JSON on
    stdin) or POST to a webhook, returning (ok, detail). The seam connectors and cloud
    automations (recurring-jobs alerts) send through, so every notification in the
    system uses ONE transport with the same timeout/disable knobs."""
    if _hooks_disabled():
        return False, "hooks disabled (SONALOOP_DISABLE_HOOKS)"
    if kind not in HOOK_KINDS:
        raise ValueError(f"Unknown notification kind: {kind!r}. Valid: {list(HOOK_KINDS)}")
    return _deliver({"kind": kind, "target": target}, envelope)


def test_hook(hook_id: str, store: Store | None = None) -> dict[str, Any]:
    """Fire a sample envelope through one registered hook and report the outcome —
    the verification step after register_hook."""
    store = store or Store()
    hook = store.get_lifecycle_hook(hook_id)
    if not hook:
        raise KeyError(f"Unknown hook: {hook_id}")
    sample_event = hook["event"] if hook["event"] in LIFECYCLE_EVENTS else "council.recorded"
    envelope = {"event": sample_event, "schema": HOOK_ENVELOPE_VERSION,
                "emitted_at": utc_now_iso(), "data": {"test": True}}
    ok, detail = _deliver(hook, envelope)
    return {"id": hook_id, "ok": ok, "detail": detail, "envelope": envelope}


def emit_lifecycle_event(event: str, data: dict[str, Any],
                         store: Store | None = None) -> None:
    """Emit one lifecycle event to every subscriber. Called by the service layer
    AFTER the state is persisted. Best-effort by contract: never raises."""
    try:
        envelope = {"event": event, "schema": HOOK_ENVELOPE_VERSION,
                    "emitted_at": utc_now_iso(), "data": data}
        load_hook_extensions()
        for pattern, handlers in list(_HANDLERS.items()):
            if not _event_matches(pattern, event):
                continue
            for handler in list(handlers):
                try:
                    handler(envelope)
                except Exception as exc:
                    log.warning("hook handler for %r failed: %s", event, exc)
        if _hooks_disabled():
            return
        store = store or Store()
        for hook in store.list_lifecycle_hooks():
            if not hook.get("enabled", True) or not _event_matches(hook["event"], event):
                continue
            ok, detail = _deliver(hook, envelope)
            if not ok:
                log.warning("hook %s (%s -> %s) failed: %s",
                            hook["id"], hook["event"], hook["kind"], detail)
    except Exception as exc:
        log.warning("emit_lifecycle_event(%r) failed: %s", event, exc)
