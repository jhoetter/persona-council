"""`sonaloop feedback` — list recent web-feedback submissions (ticket feedback-button).

Split out of cli.py to keep it under the LOC bar (the _cli_data.py pattern). Listing
marks the shown submissions read by default (the CLI is a read surface like the
/feedback page; `sonaloop info` reports the remaining unread count) — pass
`--keep-unread` to peek without consuming."""
from __future__ import annotations

from typing import Any

from . import services

COMMANDS = ("feedback",)


def add_feedback_parsers(sub) -> None:
    p = sub.add_parser("feedback", help="List recent feedback submitted through the web "
                                        "inspector (newest first; marks them read).")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--keep-unread", action="store_true",
                   help="Don't mark the listed submissions as read.")


def run_feedback_command(args) -> Any:
    rows = services.list_feedback(limit=args.limit, mark_read=not args.keep_unread)
    return {
        "unread_remaining": services.unread_feedback_count(),
        "feedback": [{k: r.get(k) for k in
                      ("created_at", "message", "email", "page", "app_version", "read_at")}
                     for r in rows],
    }
