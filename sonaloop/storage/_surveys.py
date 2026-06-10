from __future__ import annotations

import json
from typing import Any


class SurveysMixin:
    # ---- Surveys: the outbound instrument document + its (never-embedded) response rows ----
    def upsert_survey(self, survey: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO surveys "
            "(id, slug, project_id, status, data, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (survey["id"], survey["slug"], survey.get("project_id"), survey.get("status", "draft"),
             json.dumps(survey, ensure_ascii=False), survey["created_at"], survey["updated_at"]))
        self.conn.commit()

    def get_survey(self, survey_id_or_slug: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM surveys WHERE id=? OR slug=?",
            (survey_id_or_slug, survey_id_or_slug)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_surveys(self, project_id: str | None = None) -> list[dict[str, Any]]:
        q, params = "SELECT data FROM surveys", []
        if project_id:
            q += " WHERE project_id=?"; params.append(project_id)
        q += " ORDER BY created_at DESC"
        return [json.loads(r["data"]) for r in self.conn.execute(q, params).fetchall()]

    def delete_survey(self, survey_id: str) -> int:
        self.conn.execute("DELETE FROM survey_responses WHERE survey_id=?", (survey_id,))
        cur = self.conn.execute("DELETE FROM surveys WHERE id=?", (survey_id,))
        self.conn.commit()
        return cur.rowcount

    def insert_survey_response(self, resp: dict[str, Any]) -> None:
        # INSERT OR REPLACE on the deterministic id → re-importing the same batch is idempotent.
        self.conn.execute(
            "INSERT OR REPLACE INTO survey_responses "
            "(id, survey_id, respondent_key, submitted_at, data, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (resp["id"], resp["survey_id"], resp.get("respondent_key", ""),
             resp.get("submitted_at", ""), json.dumps(resp, ensure_ascii=False), resp["created_at"]))
        self.conn.commit()

    def list_survey_responses(self, survey_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM survey_responses WHERE survey_id=? ORDER BY submitted_at",
            (survey_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def count_survey_responses(self, survey_id: str) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM survey_responses WHERE survey_id=?", (survey_id,)).fetchone()
        return int(row["n"]) if row else 0
