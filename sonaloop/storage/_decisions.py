from __future__ import annotations

import json
from typing import Any


class DecisionsMixin:
    # ---- Decision records: what was decided, on which evidence, rejecting what (ADR-style) ----
    def upsert_decision(self, dec: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO decision_records "
            "(id, project_id, status, data, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (dec["id"], dec["project_id"], dec.get("status", "proposed"),
             json.dumps(dec, ensure_ascii=False), dec["created_at"], dec["updated_at"]))
        self.conn.commit()

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM decision_records WHERE id=?", (decision_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_decisions(self, project_id: str | None = None,
                       status: str | None = None) -> list[dict[str, Any]]:
        q, params, clauses = "SELECT data FROM decision_records", [], []
        if project_id:
            clauses.append("project_id=?"); params.append(project_id)
        if status:
            clauses.append("status=?"); params.append(status)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY created_at DESC"
        return [json.loads(r["data"]) for r in self.conn.execute(q, params).fetchall()]

    def delete_decision(self, decision_id: str) -> int:
        cur = self.conn.execute("DELETE FROM decision_records WHERE id=?", (decision_id,))
        self.conn.commit()
        return cur.rowcount
