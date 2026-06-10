from __future__ import annotations

import json
from typing import Any


class HooksMixin:
    """Durable lifecycle-hook registrations (spec: docs/lifecycle-hooks.md).

    A hook row is the SUBSCRIPTION (event pattern + delivery target), not the
    event itself — events are emitted in-process by the service layer and only
    pass through here to find their registered subscribers."""

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
