"""`sonaloop catalog-*` — browse / recommend / status / pull over the curated persona
catalog (sonaloop-data). Split out of cli.py to keep it under the LOC bar (the
_cli_data.py / _cli_feedback.py pattern); the service surface is services.catalog_*."""
from __future__ import annotations

from typing import Any

from . import services

COMMANDS = ("catalog-search", "catalog-recommend", "catalog-status", "catalog-pull")


def add_catalog_parsers(sub) -> None:
    p = sub.add_parser("catalog-search", help="Browse the curated persona catalog (300+ ready-made personas).")
    p.add_argument("--query")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--cursor")
    p.add_argument("--ref", default="main")

    p = sub.add_parser("catalog-recommend", help="Deterministic persona-SET recommendation over the catalog.")
    p.add_argument("--keywords", help="comma-separated keywords")
    p.add_argument("-n", type=int, default=5)
    p.add_argument("--facet", action="append", help="facet=value (repeatable)")
    p.add_argument("--seed-pack")

    p = sub.add_parser("catalog-status", help="The `git fetch && git status` of the catalog: freshness of "
                                              "every pulled persona (behind / locally_modified / ...).")
    p.add_argument("--personas", help="comma-separated slugs (default: all pulled)")
    p.add_argument("--ref", default="main")

    p = sub.add_parser("catalog-pull", help="Pull catalog personas/packs into the store "
                                            "(drift-safe: locally modified personas are skipped; --force overwrites).")
    p.add_argument("--personas", help="comma-separated slugs")
    p.add_argument("--pack")
    p.add_argument("--ref", default="main")
    p.add_argument("--embed", action="store_true")
    p.add_argument("--force", action="store_true")


def run_catalog_command(args) -> Any:
    if args.command == "catalog-search":
        return services.catalog_search(args.query, None, args.limit, args.cursor, args.ref)
    if args.command == "catalog-recommend":
        spec: dict[str, Any] = {"n": args.n}
        if args.keywords:
            spec["keywords"] = [k.strip() for k in args.keywords.split(",") if k.strip()]
        facets: dict[str, list[str]] = {}
        for f in args.facet or []:
            key, _, value = f.partition("=")
            facets.setdefault(key, []).append(value)
        if facets:
            spec["facets"] = facets
        if args.seed_pack:
            spec["seed_pack"] = args.seed_pack
        return services.catalog_recommend(spec)
    if args.command == "catalog-status":
        slugs = [s.strip() for s in (args.personas or "").split(",") if s.strip()]
        return services.catalog_status(slugs or None, args.ref)
    # catalog-pull
    slugs = [s.strip() for s in (args.personas or "").split(",") if s.strip()]
    return services.catalog_pull(slugs or None, args.pack, args.ref, args.embed, args.force)
