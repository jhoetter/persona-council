from __future__ import annotations

import json
from typing import Any


class PrototypesMixin:
    # ---- Prototype artifacts + recorded persona sessions ----
    def upsert_prototype(self, proto: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO prototypes (id, slug, project_id, version, data, created_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET slug=excluded.slug, project_id=excluded.project_id, "
            "version=excluded.version, data=excluded.data",
            (proto["id"], proto["slug"], proto.get("project_id"), proto.get("version", ""),
             json.dumps(proto, ensure_ascii=False), proto["created_at"]))
        self.conn.commit()

    def get_prototype(self, id_or_slug: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM prototypes WHERE id=? OR slug=?", (id_or_slug, id_or_slug)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_prototypes(self, project_id: str | None = None) -> list[dict[str, Any]]:
        if project_id:
            rows = self.conn.execute(
                "SELECT data FROM prototypes WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT data FROM prototypes ORDER BY created_at DESC").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def delete_prototype(self, prototype_id: str) -> int:
        cur = self.conn.execute("DELETE FROM prototypes WHERE id=? OR slug=?", (prototype_id, prototype_id))
        self.conn.commit()
        return cur.rowcount

    def insert_prototype_session(self, sess: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO prototype_sessions (id, persona_id, prototype_id, session_id, data, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (sess["id"], sess["persona_id"], sess["prototype_id"], sess.get("session_id"),
             json.dumps(sess, ensure_ascii=False), sess["created_at"]))
        self.conn.commit()

    def list_prototype_sessions(self, prototype_id: str | None = None,
                                persona_id: str | None = None) -> list[dict[str, Any]]:
        q, params = "SELECT data FROM prototype_sessions", []
        clauses = []
        if prototype_id:
            clauses.append("prototype_id=?"); params.append(prototype_id)
        if persona_id:
            clauses.append("persona_id=?"); params.append(persona_id)
        if clauses:
            q += " WHERE " + " AND ".join(clauses)
        q += " ORDER BY created_at DESC"
        return [json.loads(r["data"]) for r in self.conn.execute(q, params).fetchall()]
