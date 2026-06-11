from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_examples(mcp):
    # ===== Shipped example projects — loadable demo data (ticket loadable-example-projects) =====
    # Two flagship projects ship inside the wheel as committed fixtures and replay through the
    # real record_* layer: validated shapes, server-side aggregates, lifecycle events. Loading is
    # idempotent (stable example-namespaced ids -> keyed upserts); removal deletes exactly the
    # example's entities (ids re-derived from the fixture + provenance.example on personas).
    @mcp.tool()
    def list_examples() -> dict[str, Any]:
        """The example projects shipped with Sonaloop: slug, title, one-line tagline, and
        whether each is currently loaded into this database. Load one with load_example(slug)
        to populate a complete, polished demo project (personas, councils incl. a price ladder /
        head-to-head / red team / ideation run, hypotheses, a synthesis, decisions, notes and
        sections)."""
        t = time.perf_counter()
        return _env("list_examples", {"examples": services.list_examples()}, t)

    @mcp.tool()
    def load_example(slug: str = "") -> dict[str, Any]:
        """Load one shipped example project end-to-end (empty slug = list what's available).
        Idempotent: re-loading updates the same stable ids — no duplicates. Returns the loaded
        project id, the inspector URL, and per-entity counts."""
        t = time.perf_counter()
        if not slug:
            return _env("load_example", {"examples": services.list_examples()}, t)
        return _env("load_example", services.load_example(slug), t)

    @mcp.tool()
    def remove_example(slug: str) -> dict[str, Any]:
        """Remove ONE example project's entities — and nothing else. Every id is re-derived
        from the shipped fixture; personas are matched by their provenance.example stamp, so
        user-created data is never touched."""
        t = time.perf_counter()
        return _env("remove_example", services.remove_example(slug), t)
