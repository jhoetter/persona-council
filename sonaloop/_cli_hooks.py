"""The grounding + automation CLI surface: lifecycle hooks and evidence attachment.

Split out of cli.py to keep it under the LOC bar (tests/test_loc_budget.py). The
hook commands mirror the MCP tools 1:1 (docs/lifecycle-hooks.md); evidence-attach
lives here too — attaching evidence emits `evidence.attached`, so the seam that
produces events and the seam that subscribes to them stay together."""
from __future__ import annotations

from typing import Any

from . import services

COMMANDS = ("evidence-attach", "hooks-events", "hooks-list",
            "hook-register", "hook-remove", "hook-test")


def add_hook_parsers(sub) -> None:
    p = sub.add_parser("evidence-attach")
    p.add_argument("persona_id")
    p.add_argument("source_type")
    p.add_argument("content_or_path")
    p.add_argument("--notes")

    sub.add_parser("hooks-events", help="The documented lifecycle-event catalogue (names + payload contracts).")
    sub.add_parser("hooks-list", help="All durable hook registrations.")
    p = sub.add_parser("hook-register", help="Subscribe a command/webhook to a lifecycle event.")
    p.add_argument("event", help="Exact event name, 'domain.*', or '*' (see hooks-events).")
    p.add_argument("kind", choices=["command", "webhook"])
    p.add_argument("target", help="Shell command (envelope JSON on stdin) or URL to POST to.")
    p.add_argument("--label")
    p = sub.add_parser("hook-remove")
    p.add_argument("hook_id")
    p = sub.add_parser("hook-test", help="Fire a sample envelope through one hook to verify delivery.")
    p.add_argument("hook_id")


def run_hook_command(args) -> Any:
    if args.command == "evidence-attach":
        return services.attach_evidence(args.persona_id, args.source_type, args.content_or_path, args.notes)
    if args.command == "hooks-events":
        return services.list_lifecycle_events()
    if args.command == "hooks-list":
        return services.list_hooks()
    if args.command == "hook-register":
        return services.register_hook(args.event, args.kind, args.target, args.label or "")
    if args.command == "hook-remove":
        return services.unregister_hook(args.hook_id)
    return services.test_hook(args.hook_id)
