"""Persona-catalog MCP tools — thin wrappers over services/_catalog.py (where the
browse/recommend/status/pull logic lives so core can use the catalog natively;
ticket sonaloop/catalog-sync-status-drift-safe-pull-refresh). The three pull
paths, documented for hosts: (a) in-process `load_into(store)` from a checkout
(sonaloop-data), (b) `sonaloop-data pull` CLI / `pull_remote` without a
checkout, (c) these MCP tools — search → recommend → pull, with
`catalog_status` as the fetch/status half of the git analogy."""
from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_catalog(mcp):
    # ================= Persona catalog (sonaloop-data) =================
    @mcp.tool()
    def catalog_search(query: str | None = None, facets: dict[str, list[str]] | None = None,
                       limit: int = 25, cursor: str | None = None, ref: str = "main") -> dict[str, Any]:
        """Browse the curated persona catalog (github:jhoetter/sonaloop-data): slugs, names,
        roles + a facet summary over the filtered set. `query` is a free-text filter; `facets`
        ({facet -> [values]}, e.g. {"lebensphase": ["schichtarbeit"]}) needs the sonaloop-data
        package with a local catalog. Paginated per the shared convention (docs/pagination.md):
        `limit` (default 25) + opaque `cursor`; answers {items, total, has_more, next_cursor}.
        Works WITHOUT the sonaloop-data package via the published manifest at git `ref`."""
        t = time.perf_counter()
        return _env("catalog_search", services.catalog_search(query, facets, limit, cursor, ref), t)

    @mcp.tool()
    def catalog_recommend(spec: dict[str, Any]) -> dict[str, Any]:
        """Deterministic, explainable persona-SET recommendation over the catalog (no LLM):
        spec = {keywords?: [...], facets?: {facet -> [values]}, n?: int, seed_pack?: id,
        min_coverage?: int}. Returns ranked picks with human-readable rationales, the set's
        facet coverage, gap warnings and a ready pull list. Needs the sonaloop-data package
        + a local catalog (answers in-band with an install note otherwise)."""
        t = time.perf_counter()
        return _env("catalog_recommend", services.catalog_recommend(spec), t)

    @mcp.tool()
    def catalog_status(persona_slugs: list[str] | None = None, ref: str = "main") -> dict[str, Any]:
        """The `git fetch && git status` of the catalog: for every catalog-pulled persona in
        the CURRENT store (optionally filtered by `persona_slugs`), report freshness against
        the catalog — `up_to_date`, `behind` (catalog updated since the pull), `possibly_behind`
        (coarse: the catalog index has no per-persona timestamp at this ref), `locally_modified`
        (the persona lived on here after the pull), `diverged` (both) or `removed_upstream`.
        Compares against the local checkout when sonaloop-data is installed, else the
        published manifest at git `ref`. Plain catalog_pull refreshes `behind` personas;
        locally_modified/diverged need catalog_pull(force=True)."""
        t = time.perf_counter()
        return _env("catalog_status", services.catalog_status(persona_slugs, ref), t)

    @mcp.tool()
    def catalog_pull(persona_slugs: list[str] | None = None, pack: str | None = None,
                     ref: str = "main", embed: bool = False, force: bool = False) -> dict[str, Any]:
        """Pull catalog personas (by slug and/or archetype `pack`) into the CURRENT store —
        profiles, SOUL/MEMORY, lived memories, avatars — with `provenance.catalog` stamped on
        each persona; re-pulls are idempotent (stable ids, upserts) and DRIFT-SAFE: personas
        modified locally after their last pull are skipped and reported
        (`skipped_locally_modified`) instead of silently overwritten — pass `force=True` to
        overwrite them (catalog_status shows the drift first). Uses sonaloop-data when
        installed (local checkout for the default ref, else the published catalog at `ref`);
        without it a built-in stdlib fallback pulls from the published catalog directly.
        `embed=True` re-derives embedding vectors (needs a configured provider; skipped
        gracefully otherwise). Returns what landed (slug, id, provenance)."""
        t = time.perf_counter()
        return _env("catalog_pull", services.catalog_pull(persona_slugs, pack, ref, embed, force), t)
