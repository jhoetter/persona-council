from __future__ import annotations

import json
from typing import Any


class HypothesesMixin:
    # ---- Hypotheses: falsifiable predictions stamped before reality answers, scored when it does ----
    def upsert_hypothesis(self, hyp: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO hypotheses "
            "(id, project_id, status, data, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (hyp["id"], hyp["project_id"], hyp.get("status", "open"),
             json.dumps(hyp, ensure_ascii=False), hyp["created_at"], hyp["updated_at"]))
        self.conn.commit()

    def get_hypothesis(self, hypothesis_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM hypotheses WHERE id=?", (hypothesis_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_hypotheses(self, project_id: str | None = None,
                        status: str | None = None) -> list[dict[str, Any]]:
        q, params, clauses = "SELECT data FROM hypotheses", [], []
        if project_id:
            clauses.append("project_id=?"); params.append(project_id)
        if status:
            clauses.append("status=?"); params.append(status)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY created_at DESC"
        return [json.loads(r["data"]) for r in self.conn.execute(q, params).fetchall()]

    def delete_hypothesis(self, hypothesis_id: str) -> int:
        cur = self.conn.execute("DELETE FROM hypotheses WHERE id=?", (hypothesis_id,))
        self.conn.commit()
        return cur.rowcount
