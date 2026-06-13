"""The storage backend seam (Phase 1 of the cloud-data-model redesign).

Pins that the Store opens through a pluggable backend, that open-core stays SQLite with
unchanged behaviour, and that a postgresql:// URL fails LOUDLY rather than silently
falling back to SQLite (a silent fallback once served the cloud app off the wrong store)."""
from __future__ import annotations

import sqlite3

import pytest

from sonaloop.storage import Store
from sonaloop.storage._backend import SqliteBackend, StorageBackend, make_backend


def test_store_opens_through_the_sqlite_backend(store):
    assert isinstance(store.backend, SqliteBackend)
    assert store.backend.dialect == "sqlite"
    assert store.path is not None and store.path.suffix == ".db"
    # the connection is the real sqlite3 one, schema applied, version stamped
    assert isinstance(store.conn, sqlite3.Connection)
    assert store.schema_version() >= 1


def test_make_backend_defaults_to_sqlite_at_database_path():
    b = make_backend()
    assert isinstance(b, SqliteBackend) and b.path is not None


def test_postgres_url_raises_loudly_not_a_silent_sqlite_fallback(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user@host/db")
    with pytest.raises(NotImplementedError, match="Postgres backend not implemented"):
        make_backend()
    monkeypatch.setenv("DATABASE_URL", "postgres://user@host/db")
    with pytest.raises(NotImplementedError):
        make_backend()


def test_store_accepts_an_explicit_backend(tmp_path):
    """The seam is injectable — the Postgres backend will arrive this way without
    touching StoreBase."""
    backend = SqliteBackend(tmp_path / "explicit.db")
    s = Store(backend=backend)
    assert s.backend is backend and (tmp_path / "explicit.db").exists()
    s.close()


def test_backend_interface_is_abstract():
    b = StorageBackend()
    with pytest.raises(NotImplementedError):
        b.connect()
    with pytest.raises(NotImplementedError):
        b.apply_schema(None)
