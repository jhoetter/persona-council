from __future__ import annotations

import json
from typing import Any

from ..config import utc_now_iso


class ResearchMixin:
    # ---- Research graph: projects / edges / open questions / meta-reports ----
    def upsert_research_project(self, project: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO research_projects (id, slug, title, data, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET slug=excluded.slug, title=excluded.title, data=excluded.data, updated_at=excluded.updated_at",
            (project["id"], project["slug"], project["title"], json.dumps(project, ensure_ascii=False),
             project["created_at"], project.get("updated_at", project["created_at"])),
        )
        self.conn.commit()

    def get_research_project(self, project_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM research_projects WHERE id=? OR slug=?", (project_id, project_id)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_research_projects(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT data FROM research_projects ORDER BY created_at DESC").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def insert_study_edge(self, edge: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO study_edges (id, project_id, from_study, to_study, type, data, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (edge["id"], edge["project_id"], edge["from_study"], edge["to_study"], edge["type"],
             json.dumps(edge, ensure_ascii=False), edge["created_at"]))
        self.conn.commit()

    def list_study_edges(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM study_edges WHERE project_id=? ORDER BY created_at", (project_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def upsert_open_question(self, oq: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO research_open_questions (id, project_id, study_id, status, data, created_at) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET status=excluded.status, study_id=excluded.study_id, data=excluded.data",
            (oq["id"], oq["project_id"], oq.get("study_id"), oq["status"],
             json.dumps(oq, ensure_ascii=False), oq["created_at"]))
        self.conn.commit()

    def list_open_questions(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM research_open_questions WHERE project_id=? ORDER BY created_at", (project_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def upsert_meta_report(self, report: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO meta_reports (id, project_id, title, data, created_at) VALUES (?, ?, ?, ?, ?)",
            (report["id"], report["project_id"], report["title"], json.dumps(report, ensure_ascii=False), report["created_at"]))
        self.conn.commit()

    def get_meta_report(self, report_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM meta_reports WHERE id=?", (report_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_meta_reports(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM meta_reports WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    # ---- ESV: the resumable run object ----
    def upsert_run(self, run: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, project_id, status, cursor, data, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run["run_id"], run["project_id"], run.get("status", "active"), int(run.get("cursor", 0)),
             json.dumps(run, ensure_ascii=False), run["created_at"], run.get("updated_at", run["created_at"])))
        self.conn.commit()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_runs(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM runs WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    # ---- Methodology engine: user-defined specs + per-phase judgments ----
    def upsert_methodology(self, spec: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO methodologies (key, name, data, created_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET name=excluded.name, data=excluded.data",
            (spec["key"], spec["name"], json.dumps(spec, ensure_ascii=False),
             spec.get("created_at", utc_now_iso())))
        self.conn.commit()

    def get_methodology(self, key: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM methodologies WHERE key=?", (key,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_methodologies(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT data FROM methodologies ORDER BY key").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def insert_methodology_judgment(self, j: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO methodology_judgments (id, project_id, phase_key, kind, decided, data, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (j["id"], j["project_id"], j["phase_key"], j["kind"], 1 if j.get("decided") else 0,
             json.dumps(j, ensure_ascii=False), j["created_at"]))
        self.conn.commit()

    def list_methodology_judgments(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM methodology_judgments WHERE project_id=? ORDER BY created_at", (project_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    # ---- Research plan (one per project) ----
    def upsert_research_plan(self, plan: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO research_plans (project_id, data, created_at, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(project_id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
            (plan["project_id"], json.dumps(plan, ensure_ascii=False),
             plan.get("created_at", ""), plan.get("updated_at", "")))
        self.conn.commit()

    def get_research_plan(self, project_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM research_plans WHERE project_id=?", (project_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    # ---- Granular deletes (D in CRUD; all via MCP/CLI, never the read-only UI) ----
    def delete_research_project(self, project_id: str) -> dict[str, int]:
        """Delete a project container + its graph metadata (edges, open questions,
        meta-reports). The syntheses themselves are independent studies and are kept."""
        p = self.get_research_project(project_id)
        if not p:
            return {}
        pid = p["id"]
        deleted: dict[str, int] = {}
        for table in ("study_edges", "research_open_questions", "meta_reports", "methodology_judgments"):
            cur = self.conn.execute(f"DELETE FROM {table} WHERE project_id=?", (pid,))
            deleted[table] = cur.rowcount
        cur = self.conn.execute("DELETE FROM research_projects WHERE id=?", (pid,))
        deleted["research_projects"] = cur.rowcount
        self.conn.commit()
        return deleted

    def delete_study_edges(self, project_id: str, from_study: str, to_study: str, type: str | None = None) -> int:
        if type:
            cur = self.conn.execute(
                "DELETE FROM study_edges WHERE project_id=? AND from_study=? AND to_study=? AND type=?",
                (project_id, from_study, to_study, type))
        else:
            cur = self.conn.execute(
                "DELETE FROM study_edges WHERE project_id=? AND from_study=? AND to_study=?",
                (project_id, from_study, to_study))
        self.conn.commit()
        return cur.rowcount

    def delete_edges_touching(self, project_id: str, study_id: str) -> int:
        cur = self.conn.execute(
            "DELETE FROM study_edges WHERE project_id=? AND (from_study=? OR to_study=?)",
            (project_id, study_id, study_id))
        self.conn.commit()
        return cur.rowcount

    def delete_open_question(self, question_id: str) -> int:
        cur = self.conn.execute("DELETE FROM research_open_questions WHERE id=?", (question_id,))
        self.conn.commit()
        return cur.rowcount

    def delete_meta_report(self, report_id: str) -> int:
        cur = self.conn.execute("DELETE FROM meta_reports WHERE id=?", (report_id,))
        self.conn.commit()
        return cur.rowcount
