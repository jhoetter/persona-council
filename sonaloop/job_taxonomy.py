"""Job / Framework / Format taxonomy — the canonical three-layer model.

The single source of truth is the data file `taxonomy.json` (this module just loads it) and
its human-readable companion `docs/job-framework-format.md`. The three orthogonal layers:

  - Job        — what the user wants / the use case they buy ("how is my positioning?").
  - Framework  — the process the run follows (a methodology key under methodologies/*.json).
  - Format     — a single move inside a run (council, prototype_test, head_to_head, red_team).

A Job runs THROUGH a Framework USING Formats. Consumers (the website IA, the
`sharpen-question-helper` presets, the methodology surface) should import from here rather than
re-reading the raw JSON, so the ids/labels stay aligned across repos.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import taxonomy_path


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    """The full taxonomy document (layers, frameworks, formats, jobs)."""
    return json.loads(taxonomy_path().read_text(encoding="utf-8"))


def layers() -> dict[str, dict[str, Any]]:
    """The three layer definitions, keyed by id (job / framework / format)."""
    return load_taxonomy()["layers"]


def frameworks() -> list[dict[str, Any]]:
    """Frameworks in the taxonomy, each pointing at a real methodology `key`."""
    return load_taxonomy()["frameworks"]


def formats() -> list[dict[str, Any]]:
    """Formats (council, prototype_test, head_to_head, red_team) with implementation status."""
    return load_taxonomy()["formats"]


def jobs() -> list[dict[str, Any]]:
    """The named Jobs the product sells, each resolving to framework(s) + formats + coverage."""
    return load_taxonomy()["jobs"]


def get_job(job_id: str) -> dict[str, Any]:
    """One Job by stable id (e.g. 'positioning'). Raises KeyError if unknown."""
    for job in jobs():
        if job["id"] == job_id:
            return job
    raise KeyError(f"No taxonomy job '{job_id}'")


def framework_keys() -> set[str]:
    """The methodology keys referenced by the taxonomy — for cross-checking against the registry."""
    return {fw["methodology_key"] for fw in frameworks()}


def format_ids() -> set[str]:
    """All known Format ids (implemented or planned)."""
    return {fmt["id"] for fmt in formats()}
