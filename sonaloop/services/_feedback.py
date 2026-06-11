"""User feedback (ticket feedback-button): submit, list, unread count, webhook fan-out.

The web inspector's Feedback modal posts here; `sonaloop feedback` and the /feedback
admin page read here. Submissions carry a transparent context (the page path the user
was on + the app version — shown to the user before sending, never collected silently).

Rate limit: a NAIVE per-DB recent-count cap (no auth/session store exists) —
at most RATE_LIMIT_MAX submissions per RATE_LIMIT_WINDOW_MIN minutes across the DB,
enough to stop a stuck retry loop or a prankster tab without bookkeeping.

Webhook: when SONALOOP_FEEDBACK_WEBHOOK is set, every submission also POSTs a JSON
envelope to that URL — through the ONE durable-hook transport
(services._hooks.deliver_notification, same timeout/disable knobs), best-effort:
a dead webhook never blocks or fails the user's submission."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from ..config import utc_now_iso
from ..storage import Store
from ._common import stable_id

log = logging.getLogger("sonaloop.feedback")

FEEDBACK_WEBHOOK_ENV = "SONALOOP_FEEDBACK_WEBHOOK"
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW_MIN = 10


class FeedbackRateLimited(Exception):
    """Raised when the naive per-DB submission cap is hit (try again later)."""


def app_version() -> str:
    """The installed package version (the transparent context line + `sonaloop info`)."""
    try:
        from importlib.metadata import version
        return version("sonaloop")
    except Exception:
        return "0.0.0+local"


def _deliver_feedback_webhook(fb: dict) -> None:
    """Best-effort fan-out to SONALOOP_FEEDBACK_WEBHOOK — never raises."""
    url = (os.getenv(FEEDBACK_WEBHOOK_ENV) or "").strip()
    if not url:
        return
    try:
        from . import _hooks
        envelope = {"event": "feedback.submitted", "schema": _hooks.HOOK_ENVELOPE_VERSION,
                    "emitted_at": utc_now_iso(), "data": dict(fb)}
        ok, detail = _hooks.deliver_notification("webhook", url, envelope)
        if not ok:
            log.warning("feedback webhook %s failed: %s", url, detail)
    except Exception as exc:                       # the user's submission already succeeded
        log.warning("feedback webhook delivery error: %s", exc)


def submit_feedback(message: str, email: str = "", page: str = "",
                    store: Store | None = None) -> dict:
    """Validate -> rate-limit -> persist -> (best-effort) webhook. Returns the row."""
    store = store or Store()
    message = (message or "").strip()
    if not message:
        raise ValueError("Feedback message must not be empty.")
    window_start = (datetime.now(timezone.utc)
                    - timedelta(minutes=RATE_LIMIT_WINDOW_MIN)).isoformat()
    if store.count_feedback_since(window_start) >= RATE_LIMIT_MAX:
        raise FeedbackRateLimited(
            f"More than {RATE_LIMIT_MAX} submissions in {RATE_LIMIT_WINDOW_MIN} minutes.")
    created = utc_now_iso()
    fb = {
        "id": stable_id("feedback", created, message[:80]),
        "message": message[:5000],
        "email": (email or "").strip()[:200],
        "page": (page or "").strip()[:300],
        "app_version": app_version(),
        "created_at": created,
    }
    store.add_feedback(fb)
    _deliver_feedback_webhook(fb)
    return fb


def list_feedback(limit: int = 50, *, mark_read: bool = False,
                  store: Store | None = None) -> list[dict]:
    """Recent submissions, newest first. mark_read=True stamps them read (the
    /feedback page and `sonaloop feedback` are the read events)."""
    store = store or Store()
    rows = store.list_feedback(limit)
    if mark_read:
        store.mark_feedback_read()
    return rows


def unread_feedback_count(store: Store | None = None) -> int:
    return (store or Store()).unread_feedback_count()
