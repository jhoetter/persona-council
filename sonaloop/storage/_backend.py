"""Storage backend seam — the one place the Store's DB dialect lives.

Phase 1 of the cloud data-model redesign (tracker: sonaloop/storage-backend-abstraction;
page: cloud-data-model). Open-core uses SQLite; cloud will add a Postgres backend with
row-level tenancy (sonaloop/storage-row-tenancy-and-rls). The Store and its mixins talk to
a DB-API-2.0-shaped connection and use `?` placeholders uniformly — a backend is free to
translate those (Postgres uses `%s`) so the mixins stay dialect-agnostic.

This module ships SQLite ONLY, routed through the seam with zero behaviour change. A
`postgresql://` DATABASE_URL is an explicit, loud error here — never a silent fallback —
until the Postgres backend lands.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from ._schema import SCHEMA


class StorageBackend:
    """Owns connection creation + schema application for one SQL dialect."""

    dialect: str = "abstract"
    #: the on-disk DB path for file backends (SQLite); None for server backends (Postgres).
    path: Path | None = None

    def connect(self) -> Any:                       # pragma: no cover - interface
        raise NotImplementedError

    def apply_schema(self, conn: Any) -> None:      # pragma: no cover - interface
        raise NotImplementedError


class SqliteBackend(StorageBackend):
    """The open-core / default backend: one local SQLite file, `sqlite3.Row` rows."""

    dialect = "sqlite"

    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def apply_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(SCHEMA)


def make_backend(path: Path | None = None) -> StorageBackend:
    """Select the Store's backend. Default / open-core: SQLite at `path` (or the
    partition-resolved `database_path()`). A `postgresql://` DATABASE_URL selects the
    Postgres backend once it exists — for now it raises rather than silently falling
    back to SQLite (a silent fallback once served the cloud app off the wrong store)."""
    import os

    url = os.getenv("DATABASE_URL", "")
    if url.startswith(("postgres://", "postgresql://")):
        raise NotImplementedError(
            "Postgres backend not implemented yet — Phase 1 ships SQLite through the "
            "backend seam; Postgres lands in tracker: sonaloop/storage-row-tenancy-and-rls."
        )
    from ..config import database_path
    return SqliteBackend(path or database_path())
