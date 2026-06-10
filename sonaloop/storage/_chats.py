from __future__ import annotations

import json
from typing import Any


class ChatsMixin:
    """Durable persona chats (docs/substrate.md): one row per conversation, the
    turns living inside the JSON blob like every other artifact body."""

    def upsert_persona_chat(self, chat: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO persona_chats (id, persona_id, updated_at, data) VALUES (?, ?, ?, ?)",
            (chat["id"], chat["persona_id"], chat["updated_at"], json.dumps(chat, ensure_ascii=False)),
        )
        self.conn.commit()

    def get_persona_chat(self, chat_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM persona_chats WHERE id=?", (chat_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_persona_chats(self, persona_id: str | None = None) -> list[dict[str, Any]]:
        if persona_id:
            rows = self.conn.execute(
                "SELECT data FROM persona_chats WHERE persona_id=? ORDER BY updated_at DESC, id",
                (persona_id,)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT data FROM persona_chats ORDER BY updated_at DESC, id").fetchall()
        return [json.loads(r["data"]) for r in rows]
