from __future__ import annotations

import json
from typing import Any


class UsabilitySessionsMixin:
    # ---- Usability sessions: the durable, replayable per-step trace ----
    def insert_usability_session(self, sess: dict[str, Any]) -> None:
        subject = sess.get("subject") or {}
        self.conn.execute(
            "INSERT OR REPLACE INTO usability_sessions "
            "(id, project_id, persona_id, subject_kind, subject_key, fidelity, data, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (sess["id"], sess.get("project_id"), sess["persona_id"], subject.get("kind", ""),
             subject.get("id") or subject.get("url") or "", sess.get("fidelity", ""),
             json.dumps(sess, ensure_ascii=False), sess["created_at"]))
        self.conn.commit()

    def get_usability_session(self, session_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM usability_sessions WHERE id=?", (session_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_usability_sessions(self, project_id: str | None = None, persona_id: str | None = None,
                                subject_kind: str | None = None,
                                subject_key: str | None = None) -> list[dict[str, Any]]:
        q, params = "SELECT data FROM usability_sessions", []
        clauses = []
        if project_id:
            clauses.append("project_id=?"); params.append(project_id)
        if persona_id:
            clauses.append("persona_id=?"); params.append(persona_id)
        if subject_kind:
            clauses.append("subject_kind=?"); params.append(subject_kind)
        if subject_key:
            clauses.append("subject_key=?"); params.append(subject_key)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY created_at DESC"
        return [json.loads(r["data"]) for r in self.conn.execute(q, params).fetchall()]

    def delete_usability_session(self, session_id: str) -> int:
        cur = self.conn.execute("DELETE FROM usability_sessions WHERE id=?", (session_id,))
        self.conn.commit()
        return cur.rowcount
