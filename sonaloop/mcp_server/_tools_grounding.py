from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_grounding(mcp):
    # ======== Grounding in real material (docs/grounding.md) ========
    @mcp.tool()
    def ingest_corpus(content_or_path: str, source_type: str, title: str | None = None,
                      notes: str | None = None) -> dict[str, Any]:
        """Ingest one REAL document (interview transcript, support-ticket export, review
        dump, survey verbatims) as a corpus of citable chunks. `content_or_path` is a
        file path or the raw text itself. Idempotent on content; near-duplicate chunks
        are dropped. Then: brief_grounding to author a persona from it."""
        t = time.perf_counter()
        return _env("ingest_corpus", services.ingest_corpus(content_or_path, source_type, title, notes), t)

    @mcp.tool()
    def list_corpora() -> dict[str, Any]:
        """Every ingested corpus (id, title, source_type, chunk count)."""
        t = time.perf_counter()
        return _env("list_corpora", services.list_corpora(), t)

    @mcp.tool()
    def get_corpus(corpus_id: str, include_chunks: bool = False) -> dict[str, Any]:
        """One corpus record; include_chunks=True returns the full chunk list (large)."""
        t = time.perf_counter()
        return _env("get_corpus", services.get_corpus(corpus_id, include_chunks), t)

    @mcp.tool()
    def search_corpus(query: str, corpus_ids: list[str] | None = None,
                      limit: int = 12) -> dict[str, Any]:
        """Keyword search over corpus chunks — pull the real signal relevant to a task
        (deterministic token-hit scoring, no embeddings needed)."""
        t = time.perf_counter()
        return _env("search_corpus", services.search_corpus(query, corpus_ids, limit), t)

    @mcp.tool()
    def brief_grounding(corpus_ids: list[str], persona_id: str | None = None,
                        focus: str | None = None) -> dict[str, Any]:
        """Gather the chunks + authoring contract to ground a persona in real material.
        WITHOUT persona_id: author a NEW persona from the corpora (description + profile
        + provenance), then record_persona → record_grounding. WITH persona_id: author a
        patch refreshing the existing profile against the material. Either way you build
        `provenance` = [{claim, chunk_ids}] — the traceability record_grounding persists."""
        t = time.perf_counter()
        return _env("brief_grounding", services.brief_grounding(corpus_ids, persona_id, focus), t)

    @mcp.tool()
    def record_grounding(persona_id: str, corpus_ids: list[str],
                         provenance: list[dict[str, Any]],
                         patch: dict[str, Any] | None = None,
                         reason: str = "grounded from real material") -> dict[str, Any]:
        """Persist authored grounding: optional profile patch + the provenance map
        (claim → chunk ids; validated against the corpora). Links the corpora as persona
        evidence and emits `persona.grounded`. Sessions then carry the task-relevant
        chunks automatically and cite them as refs {kind:'evidence', id, quote}."""
        t = time.perf_counter()
        return _env("record_grounding",
                    services.record_grounding(persona_id, corpus_ids, provenance, patch, reason), t)

    @mcp.tool()
    def trace_evidence(chunk_id: str) -> dict[str, Any]:
        """Resolve a cited evidence chunk id back to its source: the chunk text, its
        corpus, and every persona claim grounded on it — how synthesis claims trace to
        real signal."""
        t = time.perf_counter()
        return _env("trace_evidence", services.trace_evidence(chunk_id), t)
