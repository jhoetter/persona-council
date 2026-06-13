from __future__ import annotations

import json
from typing import Any

# The event bus keeps only the newest ~1000 rows — enough for SSE replay after a
# reconnect and the Activity feed, never an unbounded log (audit_log holds history).
EVENTS_CAP = 1000


class HooksMixin:
    """Durable lifecycle-hook registrations + the cross-process event bus
    (spec: docs/lifecycle-hooks.md).

    A hook row is the SUBSCRIPTION (event pattern + delivery target), not the
    event itself — events are emitted in-process by the service layer and only
    pass through here to find their registered subscribers. An `events` row is
    one EMITTED event: the services-layer '*' subscriber appends it so the web
    inspector (a separate process on the same SQLite DB) can tail it live."""

    def upsert_lifecycle_hook(self, hook: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO lifecycle_hooks (id, event, data) VALUES (?, ?, ?)",
            (hook["id"], hook["event"], json.dumps(hook, ensure_ascii=False)),
        )
        self.audit("lifecycle_hook", hook["id"], "register", hook.get("label"), hook)
        self.conn.commit()

    def get_lifecycle_hook(self, hook_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM lifecycle_hooks WHERE id=?", (hook_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_lifecycle_hooks(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT data FROM lifecycle_hooks ORDER BY id").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def delete_lifecycle_hook(self, hook_id: str) -> int:
        cur = self.conn.execute("DELETE FROM lifecycle_hooks WHERE id=?", (hook_id,))
        self.conn.commit()
        return cur.rowcount

    # ---- event bus rows (appended by services._events, tailed by web /api/events) ----

    def append_event(self, ts: str, event: str, entity_type: str, entity_id: str,
                     project_id: str | None, data: dict[str, Any],
                     cap: int = EVENTS_CAP) -> int:
        """Append one bus row and trim to the newest `cap`. AUTOINCREMENT ids never
        recycle, so `id <= lastrowid - cap` is exactly 'everything but the newest cap'."""
        cur = self.conn.execute(
            "INSERT INTO events (ts, event, entity_type, entity_id, project_id, data) "
            "VALUES (?, ?, ?, ?, ?, ?) RETURNING id",      # RETURNING works on both dialects
            (ts, event, entity_type, entity_id, project_id,  # (sqlite >= 3.35); Postgres has no
             json.dumps(data, ensure_ascii=False)))          # lastrowid for IDENTITY columns
        event_id = int(cur.fetchone()["id"])
        self.conn.execute("DELETE FROM events WHERE id <= ?", (event_id - cap,))
        self.conn.commit()
        return event_id

    def list_events_after(self, after_id: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        """Bus rows with id > after_id, oldest first — the SSE tail/replay query."""
        rows = self.conn.execute(
            "SELECT * FROM events WHERE id > ? ORDER BY id LIMIT ?",
            (after_id, limit)).fetchall()
        return [{**dict(r), "data": json.loads(r["data"])} for r in rows]

    def list_recent_events(self, limit: int = 200) -> list[dict[str, Any]]:
        """Newest bus rows first — the Activity feed query."""
        rows = self.conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{**dict(r), "data": json.loads(r["data"])} for r in rows]

    def latest_event_id(self) -> int:
        """The bus high-water mark — a fresh SSE connection tails from here."""
        row = self.conn.execute("SELECT MAX(id) AS top FROM events").fetchone()
        return int(row["top"] or 0)
