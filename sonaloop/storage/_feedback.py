from __future__ import annotations

from typing import Any

from ..config import utc_now_iso


class FeedbackMixin:
    # ---- User feedback (ticket feedback-button): web-submitted free text + context ----

    def add_feedback(self, fb: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO feedback (id, message, email, page, app_version, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (fb["id"], fb["message"], fb.get("email") or "", fb.get("page") or "",
             fb.get("app_version") or "", fb["created_at"]))
        self.conn.commit()

    def list_feedback(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT * FROM feedback ORDER BY created_at DESC, id DESC LIMIT ?",
            (limit,)).fetchall()
        return [dict(r) for r in rows]

    def count_feedback_since(self, ts: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM feedback WHERE created_at >= ?", (ts,)).fetchone()
        return int(row["n"])

    def unread_feedback_count(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM feedback WHERE read_at IS NULL").fetchone()
        return int(row["n"])

    def mark_feedback_read(self) -> int:
        """Stamp every unread submission as read (viewing the list IS the read)."""
        cur = self.conn.execute(
            "UPDATE feedback SET read_at=? WHERE read_at IS NULL", (utc_now_iso(),))
        self.conn.commit()
        return cur.rowcount
