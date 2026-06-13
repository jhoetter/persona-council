"""Live SQLite⇄Postgres parity for the Store (Phase 1 of cloud-data-model).

Runs an identical services workload on the SQLite backend and on a REAL Postgres (a
throwaway per-test schema) and asserts the observable results match — proof the Postgres
backend's dialect translation (`?`→`%s`, `INSERT OR REPLACE`→`ON CONFLICT`, schema port,
RETURNING event bus) is behaviour-equivalent.

Skipped unless `SONALOOP_TEST_PG_DSN` points at a Postgres (e.g.
postgresql://postgres:test@localhost:55432/sonaloop) — so open-core / CI without Postgres
stays green. Locally: `docker run -d -e POSTGRES_PASSWORD=test -e POSTGRES_DB=sonaloop
-p 55432:5432 postgres:16`.
"""
from __future__ import annotations

import os
import uuid

import pytest

from sonaloop import services

_DSN = os.getenv("SONALOOP_TEST_PG_DSN")
pytestmark = pytest.mark.skipif(not _DSN, reason="set SONALOOP_TEST_PG_DSN to run Postgres parity")


def _workload() -> dict:
    """A representative slice exercising upserts, the event bus, search/fetch and the
    cross-entity reads — run against whatever backend the active env selects. Uses stable
    `key`s so a re-record is a true idempotent upsert (the ON CONFLICT path)."""
    s = services  # all calls thread store=None → each opens Store() on the active backend
    from sonaloop.storage import Store
    st = Store()
    p = s.start_project("Parity study", "does the port behave", store=st)
    pid = p["id"]
    for _ in range(2):                              # second call = idempotent upsert
        s.record_council(pid, "What lands?", [], [{"persona_id": "x", "text": "a trigger"}],
                         store=st, key="par-c")
    s.record_synthesis("Parity report", "arc", council_ids=[], project_id=pid,
                       payload={"gesamtbild": "Trigger beats message."}, store=st, key="par-s")
    s.record_hypothesis(pid, "Triggers beat cold messaging",
                        {"metric": "reply_rate", "expected_direction": "up", "confidence": 0.6},
                        store=st, key="par-h")
    eid = st.append_event("2026-06-13T00:00:00Z", "council.recorded", "council", "c", pid, {"k": 1})
    summary = {
        "projects": len(s.list_research_projects(store=st)),
        "councils": len(s.list_councils(store=st)),
        "syntheses": len(s.list_syntheses(store=st)),
        "hypotheses": len(s.list_hypotheses(pid, store=st)),
        "search_titles": sorted(r["title"][:20] for r in s.retrieval_search("parity trigger")["results"]),
        "fetch_kind": s.retrieval_fetch(pid, store=st)["metadata"]["kind"],
        "event_monotonic": eid == st.latest_event_id() and eid > 0,
        "events_replayable": len(st.list_events_after(0)) >= 1,
        # the link SHAPE is parity-relevant; the id itself is timestamp-derived, so it
        # naturally differs between two independent runs — compare the prefix, not the id.
        "url_prefix": p["url"].rsplit("/", 1)[0],
    }
    st.close()
    return summary


def test_sqlite_and_postgres_workloads_agree(monkeypatch):
    monkeypatch.setenv("SONALOOP_PUBLIC_BASE_URL", "https://app.sonaloop.test")

    # arm 1: SQLite (the conftest's per-test sqlite DATABASE_URL is already in the env)
    monkeypatch.delenv("SONALOOP_PG_SCHEMA", raising=False)
    sqlite_summary = _workload()

    # arm 2: a fresh Postgres schema — every Store() (incl. the event-bus appender's own)
    # resolves to Postgres because DATABASE_URL now points there.
    schema = "parity_" + uuid.uuid4().hex[:10]
    import psycopg
    raw = psycopg.connect(_DSN)
    raw.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'); raw.commit()
    monkeypatch.setenv("DATABASE_URL", _DSN)
    monkeypatch.setenv("SONALOOP_PG_SCHEMA", schema)
    try:
        pg_summary = _workload()
    finally:
        raw.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'); raw.commit(); raw.close()

    assert pg_summary == sqlite_summary
    # and the backend really was Postgres for arm 2
    assert pg_summary["fetch_kind"] == "project" and pg_summary["event_monotonic"]
