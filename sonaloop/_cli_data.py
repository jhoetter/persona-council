"""The portable-data CLI surface: snapshot export/import + shipped example projects.

Split out of cli.py to keep it under the LOC bar (tests/test_loc_budget.py). One
seam for data that moves in and out of the DB wholesale: `export-snapshot` /
`import-snapshot` (the portable local-only artifact), and the example projects
(ticket loadable-example-projects) whose commands mirror the MCP tools 1:1 —
`load-example` with no slug lists what ships, with a slug loads one project
idempotently, `--all` loads both; `remove-example` deletes exactly one example's
entities (or every loaded one with `--all`)."""
from __future__ import annotations

from typing import Any

from . import services

COMMANDS = ("export-snapshot", "import-snapshot", "load-example", "remove-example")


def add_data_parsers(sub) -> None:
    p = sub.add_parser("export-snapshot")
    p.add_argument("--out")
    p = sub.add_parser("import-snapshot")
    p.add_argument("--in", dest="in_dir")
    p.add_argument("--no-embed", action="store_true")
    p = sub.add_parser("load-example", help="Load a shipped example project (no slug = list available; --all = load every example).")
    p.add_argument("slug", nargs="?")
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("remove-example", help="Remove a loaded example project's data — and nothing else (no slug = list; --all = remove all loaded).")
    p.add_argument("slug", nargs="?")
    p.add_argument("--all", action="store_true")


def run_data_command(args) -> Any:
    if args.command == "export-snapshot":
        return services.export_snapshot(args.out)
    if args.command == "import-snapshot":
        return services.import_snapshot(args.in_dir, embed=not args.no_embed)
    if args.command == "load-example":
        if args.all:
            return [services.load_example(e["slug"]) for e in services.list_examples()]
        return services.load_example(args.slug) if args.slug else services.list_examples()
    if args.command == "remove-example":
        if args.all:
            return [services.remove_example(e["slug"])
                    for e in services.list_examples() if e["loaded"]]
        return services.remove_example(args.slug) if args.slug else services.list_examples()
    raise SystemExit(f"unknown data command: {args.command}")
