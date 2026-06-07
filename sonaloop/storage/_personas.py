from __future__ import annotations

import json
from typing import Any


class PersonasMixin:
    def upsert_persona(self, persona: dict[str, Any], reason: str = "upsert") -> None:
        self.conn.execute(
            """
            INSERT INTO personas (id, slug, data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              slug=excluded.slug,
              data=excluded.data,
              updated_at=excluded.updated_at
            """,
            (
                persona["id"],
                persona["slug"],
                json.dumps(persona, ensure_ascii=False),
                persona["created_at"],
                persona["updated_at"],
            ),
        )
        self.audit("persona", persona["id"], "upsert", reason, persona)
        self.conn.commit()

    def get_persona(self, persona_id_or_slug: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM personas WHERE id=? OR slug=?",
            (persona_id_or_slug, persona_id_or_slug),
        ).fetchone()
        return json.loads(row["data"]) if row else None

    def list_personas(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT data FROM personas ORDER BY created_at").fetchall()
        return [json.loads(r["data"]) for r in rows]

    # ---- Persona revisions -------------------------------------------
    def insert_persona_revision(self, revision: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO persona_revisions (id, persona_id, effective_on, data, created_at) VALUES (?, ?, ?, ?, ?)",
            (revision["id"], revision["persona_id"], revision["effective_on"],
             json.dumps(revision, ensure_ascii=False), revision["created_at"]))

    def list_persona_revisions(self, persona_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM persona_revisions WHERE persona_id=? ORDER BY effective_on", (persona_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]
