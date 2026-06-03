from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import DATA_DIR, database_path, utc_now_iso


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS personas (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar_events (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  start TEXT NOT NULL,
  end TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experience_events (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  event_type TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_summaries (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  date TEXT NOT NULL,
  data TEXT NOT NULL,
  UNIQUE(persona_id, date)
);

CREATE TABLE IF NOT EXISTS reflections (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pain_points (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  issue TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS council_sessions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS syntheses (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  reason TEXT,
  created_at TEXT NOT NULL,
  data TEXT
);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Memory layer 2: entities (project|person|org|building|authority|topic)
CREATE TABLE IF NOT EXISTS entities (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  status TEXT,
  data TEXT NOT NULL,
  first_seen TEXT,
  last_seen TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_entities_persona ON entities(persona_id, kind);

-- Memory layer 2: bi-temporal facts (valid-time intervals = time-travel)
CREATE TABLE IF NOT EXISTS entity_facts (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  fact TEXT NOT NULL,
  status TEXT,
  t_valid TEXT NOT NULL,
  t_invalid TEXT,
  importance INTEGER DEFAULT 3,
  source_event_id TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_facts_entity ON entity_facts(entity_id);
CREATE INDEX IF NOT EXISTS idx_facts_persona ON entity_facts(persona_id);

-- Episode <-> entity links
CREATE TABLE IF NOT EXISTS event_entities (
  event_id TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  persona_id TEXT NOT NULL,
  role TEXT,
  PRIMARY KEY (event_id, entity_id)
);
CREATE INDEX IF NOT EXISTS idx_event_entities_entity ON event_entities(entity_id);

-- Open loops with identity
CREATE TABLE IF NOT EXISTS threads (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  entity_id TEXT,
  text TEXT NOT NULL,
  status TEXT NOT NULL,
  opened_on TEXT,
  closed_on TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_threads_persona ON threads(persona_id, status);

-- Plans across resolutions: day|week|month|quarter|year
CREATE TABLE IF NOT EXISTS plans (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(persona_id, scope, period_start)
);

-- Layer 3: consolidated digests
CREATE TABLE IF NOT EXISTS memory_digests (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  scope TEXT NOT NULL,
  period_start TEXT NOT NULL,
  period_end TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(persona_id, scope, period_start)
);

-- Embeddings for hybrid semantic retrieval
CREATE TABLE IF NOT EXISTS embeddings (
  obj_type TEXT NOT NULL,
  obj_id TEXT NOT NULL,
  persona_id TEXT NOT NULL,
  model TEXT NOT NULL,
  dim INTEGER NOT NULL,
  vector BLOB NOT NULL,
  text TEXT,
  created_at TEXT NOT NULL,
  PRIMARY KEY (obj_type, obj_id)
);
CREATE INDEX IF NOT EXISTS idx_embeddings_persona ON embeddings(persona_id, obj_type);

-- Slow, evidence-backed persona identity drift
CREATE TABLE IF NOT EXISTS persona_revisions (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  effective_on TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_revisions_persona ON persona_revisions(persona_id, effective_on);

-- Exogenous world backdrop (not shared persona knowledge)
CREATE TABLE IF NOT EXISTS world_context (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  fact TEXT NOT NULL,
  t_valid TEXT NOT NULL,
  t_invalid TEXT,
  relevance_tags TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Consistency / quality anomalies (non-blocking, visible)
CREATE TABLE IF NOT EXISTS memory_anomalies (
  id TEXT PRIMARY KEY,
  persona_id TEXT,
  kind TEXT NOT NULL,
  severity INTEGER DEFAULT 2,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Evaluation reports (how we measure "top")
CREATE TABLE IF NOT EXISTS eval_reports (
  id TEXT PRIMARY KEY,
  persona_id TEXT,
  period_start TEXT,
  period_end TEXT,
  green INTEGER NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- Research graph: a Project groups studies (syntheses) into a themed graph,
-- with typed edges between studies, promotable open questions, and meta-reports.
-- (Distinct from the memory "project" entity, which is a persona's own work project.)
CREATE TABLE IF NOT EXISTS research_projects (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS study_edges (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  from_study TEXT NOT NULL,
  to_study TEXT NOT NULL,
  type TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_study_edges_project ON study_edges(project_id);

CREATE TABLE IF NOT EXISTS research_open_questions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  study_id TEXT,
  status TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_roq_project ON research_open_questions(project_id);

CREATE TABLE IF NOT EXISTS meta_reports (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  title TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_meta_reports_project ON meta_reports(project_id);

-- Methodology engine (spec/methodology-engine-and-prototyping.md): user-defined
-- methodology specs + the LLM-judged gate decisions recorded per phase.
CREATE TABLE IF NOT EXISTS methodologies (
  key TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS methodology_judgments (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  phase_key TEXT NOT NULL,
  kind TEXT NOT NULL,
  decided INTEGER NOT NULL,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mjudge_project ON methodology_judgments(project_id);

-- Prototype artifacts (real, minimal, locally-runnable apps) + recorded persona use.
CREATE TABLE IF NOT EXISTS prototypes (
  id TEXT PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  project_id TEXT,
  version TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prototypes_project ON prototypes(project_id);

CREATE TABLE IF NOT EXISTS prototype_sessions (
  id TEXT PRIMARY KEY,
  persona_id TEXT NOT NULL,
  prototype_id TEXT NOT NULL,
  session_id TEXT,
  data TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_protosess_proto ON prototype_sessions(prototype_id);
"""


class Store:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or database_path()
        DATA_DIR.mkdir(exist_ok=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._stamp_schema_version()

    def _stamp_schema_version(self) -> None:
        from .config import MEMORY_SCHEMA_VERSION

        self.conn.execute(
            "INSERT INTO meta (key, value) VALUES ('schema_version', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(MEMORY_SCHEMA_VERSION),),
        )
        self.conn.commit()

    def schema_version(self) -> int:
        row = self.conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        return int(row["value"]) if row else 0

    def close(self) -> None:
        self.conn.close()

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

    def insert_calendar_event(self, event: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO calendar_events (id, persona_id, start, end, data) VALUES (?, ?, ?, ?, ?)",
            (event["id"], event["persona_id"], event["start"], event["end"], json.dumps(event, ensure_ascii=False)),
        )

    def insert_experience_event(self, event: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO experience_events (id, persona_id, timestamp, event_type, data) VALUES (?, ?, ?, ?, ?)",
            (event["id"], event["persona_id"], event["timestamp"], event["event_type"], json.dumps(event, ensure_ascii=False)),
        )

    def upsert_daily_summary(self, summary: dict[str, Any]) -> None:
        self.conn.execute(
            """
            INSERT INTO daily_summaries (id, persona_id, date, data)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(persona_id, date) DO UPDATE SET data=excluded.data
            """,
            (summary["id"], summary["persona_id"], summary["date"], json.dumps(summary, ensure_ascii=False)),
        )

    def insert_reflection(self, reflection: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO reflections (id, persona_id, period_start, period_end, data) VALUES (?, ?, ?, ?, ?)",
            (
                reflection["id"],
                reflection["persona_id"],
                reflection["period_start"],
                reflection["period_end"],
                json.dumps(reflection, ensure_ascii=False),
            ),
        )

    def upsert_pain_point(self, pain: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO pain_points (id, persona_id, issue, data) VALUES (?, ?, ?, ?)",
            (pain["id"], pain["persona_id"], pain["issue"], json.dumps(pain, ensure_ascii=False)),
        )

    def insert_council_session(self, session: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO council_sessions (id, created_at, data) VALUES (?, ?, ?)",
            (session["id"], session["created_at"], json.dumps(session, ensure_ascii=False)),
        )
        self.conn.commit()

    def insert_evidence(self, evidence: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO evidence (id, persona_id, source_type, data) VALUES (?, ?, ?, ?)",
            (evidence["id"], evidence["persona_id"], evidence["source_type"], json.dumps(evidence, ensure_ascii=False)),
        )
        self.audit("evidence", evidence["id"], "attach", evidence.get("notes"), evidence)
        self.conn.commit()

    def list_evidence(self, persona_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM evidence WHERE persona_id=? ORDER BY id", (persona_id,)
        ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def list_calendar_events(self, persona_id: str, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT data FROM calendar_events WHERE persona_id=?"
        params: list[Any] = [persona_id]
        if start:
            query += " AND start>=?"
            params.append(start)
        if end:
            query += " AND start<=?"
            params.append(end)
        query += " ORDER BY start"
        return [json.loads(r["data"]) for r in self.conn.execute(query, params).fetchall()]

    def list_experience_events(self, persona_id: str, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT data FROM experience_events WHERE persona_id=?"
        params: list[Any] = [persona_id]
        if start:
            query += " AND timestamp>=?"
            params.append(start)
        if end:
            query += " AND timestamp<=?"
            params.append(end)
        query += " ORDER BY timestamp"
        return [json.loads(r["data"]) for r in self.conn.execute(query, params).fetchall()]

    def get_experience_event(self, event_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM experience_events WHERE id=?", (event_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_daily_summaries(self, persona_id: str, start: str | None = None, end: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT data FROM daily_summaries WHERE persona_id=?"
        params: list[Any] = [persona_id]
        if start:
            query += " AND date>=?"
            params.append(start)
        if end:
            query += " AND date<=?"
            params.append(end)
        query += " ORDER BY date"
        return [json.loads(r["data"]) for r in self.conn.execute(query, params).fetchall()]

    def list_reflections(self, persona_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM reflections WHERE persona_id=? ORDER BY period_end",
            (persona_id,),
        ).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def list_pain_points(self, persona_id: str | None = None) -> list[dict[str, Any]]:
        if persona_id:
            rows = self.conn.execute(
                "SELECT data FROM pain_points WHERE persona_id=? ORDER BY issue",
                (persona_id,),
            ).fetchall()
        else:
            rows = self.conn.execute("SELECT data FROM pain_points ORDER BY issue").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def list_council_sessions(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT data FROM council_sessions ORDER BY created_at DESC").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def get_council_session(self, session_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM council_sessions WHERE id=?", (session_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def upsert_synthesis(self, synthesis: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO syntheses (id, title, data, created_at) VALUES (?, ?, ?, ?)",
            (synthesis["id"], synthesis["title"], json.dumps(synthesis, ensure_ascii=False), synthesis["created_at"]),
        )
        self.conn.commit()

    def get_synthesis(self, synthesis_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM syntheses WHERE id=?", (synthesis_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_syntheses(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT data FROM syntheses ORDER BY created_at DESC").fetchall()
        return [json.loads(r["data"]) for r in rows]

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

    def delete_synthesis(self, synthesis_id: str) -> int:
        cur = self.conn.execute("DELETE FROM syntheses WHERE id=?", (synthesis_id,))
        self.conn.commit()
        return cur.rowcount

    def delete_council_session(self, session_id: str) -> int:
        cur = self.conn.execute("DELETE FROM council_sessions WHERE id=?", (session_id,))
        self.conn.commit()
        return cur.rowcount

    def delete_persona_cascade(self, persona_id: str) -> dict[str, int]:
        """Delete a persona and all of its persona-scoped rows (memory, simulation,
        evidence, eval). Council/synthesis rows reference personas only inside JSON and
        are left intact."""
        deleted: dict[str, int] = {}
        scoped = ["calendar_events", "experience_events", "daily_summaries", "reflections",
                  "pain_points", "entities", "entity_facts", "event_entities", "threads",
                  "plans", "memory_digests", "embeddings", "persona_revisions", "evidence",
                  "eval_reports", "memory_anomalies"]
        for table in scoped:
            cur = self.conn.execute(f"DELETE FROM {table} WHERE persona_id=?", (persona_id,))
            deleted[table] = cur.rowcount
        cur = self.conn.execute("DELETE FROM personas WHERE id=?", (persona_id,))
        deleted["personas"] = cur.rowcount
        self.conn.commit()
        return deleted

    # ---- Memory layer: entities ---------------------------------------
    def upsert_entity(self, entity: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO entities (id, persona_id, kind, name, status, data, first_seen, last_seen, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              kind=excluded.kind, name=excluded.name, status=excluded.status,
              data=excluded.data, last_seen=excluded.last_seen, updated_at=excluded.updated_at""",
            (entity["id"], entity["persona_id"], entity["kind"], entity["name"], entity.get("status"),
             json.dumps(entity, ensure_ascii=False), entity.get("first_seen"), entity.get("last_seen"),
             entity["created_at"], entity["updated_at"]),
        )

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM entities WHERE id=?", (entity_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_entities(self, persona_id: str, kind: str | None = None) -> list[dict[str, Any]]:
        if kind:
            rows = self.conn.execute(
                "SELECT data FROM entities WHERE persona_id=? AND kind=? ORDER BY last_seen DESC",
                (persona_id, kind)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT data FROM entities WHERE persona_id=? ORDER BY last_seen DESC", (persona_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def insert_entity_fact(self, fact: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO entity_facts
            (id, persona_id, entity_id, fact, status, t_valid, t_invalid, importance, source_event_id, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (fact["id"], fact["persona_id"], fact["entity_id"], fact["fact"], fact.get("status"),
             fact["t_valid"], fact.get("t_invalid"), int(fact.get("importance", 3)),
             fact.get("source_event_id"), json.dumps(fact, ensure_ascii=False), fact["created_at"]),
        )

    def invalidate_entity_fact(self, fact_id: str, t_invalid: str) -> None:
        row = self.conn.execute("SELECT data FROM entity_facts WHERE id=?", (fact_id,)).fetchone()
        if not row:
            return
        data = json.loads(row["data"])
        data["t_invalid"] = t_invalid
        self.conn.execute("UPDATE entity_facts SET t_invalid=?, data=? WHERE id=?",
                          (t_invalid, json.dumps(data, ensure_ascii=False), fact_id))

    def list_entity_facts(self, entity_id: str, as_of: str | None = None, valid_only: bool = False) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM entity_facts WHERE entity_id=? ORDER BY t_valid", (entity_id,)).fetchall()
        facts = [json.loads(r["data"]) for r in rows]
        if as_of:
            facts = [f for f in facts if f["t_valid"] <= as_of and (not f.get("t_invalid") or f["t_invalid"] > as_of)]
        elif valid_only:
            facts = [f for f in facts if not f.get("t_invalid")]
        return facts

    def list_persona_facts(self, persona_id: str, valid_only: bool = False) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM entity_facts WHERE persona_id=? ORDER BY t_valid", (persona_id,)).fetchall()
        facts = [json.loads(r["data"]) for r in rows]
        return [f for f in facts if not f.get("t_invalid")] if valid_only else facts

    def link_event_entity(self, event_id: str, entity_id: str, persona_id: str, role: str | None = None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO event_entities (event_id, entity_id, persona_id, role) VALUES (?, ?, ?, ?)",
            (event_id, entity_id, persona_id, role))

    def list_entity_events(self, entity_id: str) -> list[str]:
        rows = self.conn.execute("SELECT event_id FROM event_entities WHERE entity_id=?", (entity_id,)).fetchall()
        return [r["event_id"] for r in rows]

    def list_event_entities(self, persona_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT event_id, entity_id, persona_id, role FROM event_entities WHERE persona_id=?", (persona_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ---- Memory layer: threads (open loops with identity) -------------
    def upsert_thread(self, thread: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO threads (id, persona_id, entity_id, text, status, opened_on, closed_on, data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              entity_id=excluded.entity_id, text=excluded.text, status=excluded.status,
              closed_on=excluded.closed_on, data=excluded.data, updated_at=excluded.updated_at""",
            (thread["id"], thread["persona_id"], thread.get("entity_id"), thread["text"], thread["status"],
             thread.get("opened_on"), thread.get("closed_on"), json.dumps(thread, ensure_ascii=False),
             thread["created_at"], thread["updated_at"]),
        )

    def list_threads(self, persona_id: str, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            rows = self.conn.execute(
                "SELECT data FROM threads WHERE persona_id=? AND status=? ORDER BY opened_on", (persona_id, status)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT data FROM threads WHERE persona_id=? ORDER BY opened_on", (persona_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    # ---- Plans -------------------------------------------------------
    def upsert_plan(self, plan: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO plans (id, persona_id, scope, period_start, period_end, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(persona_id, scope, period_start) DO UPDATE SET
              period_end=excluded.period_end, data=excluded.data, created_at=excluded.created_at""",
            (plan["id"], plan["persona_id"], plan["scope"], plan["period_start"], plan["period_end"],
             json.dumps(plan, ensure_ascii=False), plan["created_at"]),
        )

    def get_plan(self, persona_id: str, scope: str, period_start: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM plans WHERE persona_id=? AND scope=? AND period_start=?",
            (persona_id, scope, period_start)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_plans(self, persona_id: str, scope: str | None = None) -> list[dict[str, Any]]:
        if scope:
            rows = self.conn.execute(
                "SELECT data FROM plans WHERE persona_id=? AND scope=? ORDER BY period_start", (persona_id, scope)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT data FROM plans WHERE persona_id=? ORDER BY period_start", (persona_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def find_covering_plan(self, persona_id: str, scope: str, day: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT data FROM plans WHERE persona_id=? AND scope=? AND period_start<=? AND period_end>=? "
            "ORDER BY period_start DESC LIMIT 1",
            (persona_id, scope, day, day)).fetchone()
        return json.loads(row["data"]) if row else None

    # ---- Digests -----------------------------------------------------
    def upsert_digest(self, digest: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT INTO memory_digests (id, persona_id, scope, period_start, period_end, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(persona_id, scope, period_start) DO UPDATE SET
              period_end=excluded.period_end, data=excluded.data, created_at=excluded.created_at""",
            (digest["id"], digest["persona_id"], digest["scope"], digest["period_start"], digest["period_end"],
             json.dumps(digest, ensure_ascii=False), digest["created_at"]),
        )

    def list_digests(self, persona_id: str, scope: str | None = None) -> list[dict[str, Any]]:
        if scope:
            rows = self.conn.execute(
                "SELECT data FROM memory_digests WHERE persona_id=? AND scope=? ORDER BY period_start", (persona_id, scope)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT data FROM memory_digests WHERE persona_id=? ORDER BY period_start", (persona_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    # ---- Embeddings --------------------------------------------------
    def upsert_embedding(self, obj_type: str, obj_id: str, persona_id: str, model: str, vector: bytes, dim: int, text: str, created_at: str) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO embeddings (obj_type, obj_id, persona_id, model, dim, vector, text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (obj_type, obj_id, persona_id, model, dim, vector, text, created_at))

    def get_embedding(self, obj_type: str, obj_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT obj_type, obj_id, persona_id, model, dim, vector, text FROM embeddings WHERE obj_type=? AND obj_id=?",
            (obj_type, obj_id)).fetchone()
        return dict(row) if row else None

    def list_embeddings(self, persona_id: str, obj_type: str | None = None) -> list[dict[str, Any]]:
        if obj_type:
            rows = self.conn.execute(
                "SELECT obj_type, obj_id, persona_id, dim, vector, text FROM embeddings WHERE persona_id=? AND obj_type=?",
                (persona_id, obj_type)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT obj_type, obj_id, persona_id, dim, vector, text FROM embeddings WHERE persona_id=?",
                (persona_id,)).fetchall()
        return [dict(r) for r in rows]

    def has_embedding(self, obj_type: str, obj_id: str) -> bool:
        return self.conn.execute(
            "SELECT 1 FROM embeddings WHERE obj_type=? AND obj_id=?", (obj_type, obj_id)).fetchone() is not None

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

    # ---- World context -----------------------------------------------
    def insert_world_context(self, item: dict[str, Any]) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO world_context (id, category, fact, t_valid, t_invalid, relevance_tags, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (item["id"], item["category"], item["fact"], item["t_valid"], item.get("t_invalid"),
             json.dumps(item.get("relevance_tags", []), ensure_ascii=False),
             json.dumps(item, ensure_ascii=False), item["created_at"]))

    def list_world_context(self, as_of: str | None = None) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT data FROM world_context ORDER BY t_valid").fetchall()
        items = [json.loads(r["data"]) for r in rows]
        if as_of:
            items = [i for i in items if i["t_valid"] <= as_of and (not i.get("t_invalid") or i["t_invalid"] > as_of)]
        return items

    # ---- Anomalies & eval --------------------------------------------
    def insert_anomaly(self, anomaly: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO memory_anomalies (id, persona_id, kind, severity, data, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (anomaly["id"], anomaly.get("persona_id"), anomaly["kind"], int(anomaly.get("severity", 2)),
             json.dumps(anomaly, ensure_ascii=False), anomaly["created_at"]))

    def list_anomalies(self, persona_id: str | None = None) -> list[dict[str, Any]]:
        if persona_id:
            rows = self.conn.execute(
                "SELECT data FROM memory_anomalies WHERE persona_id=? ORDER BY created_at", (persona_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT data FROM memory_anomalies ORDER BY created_at").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def insert_eval_report(self, report: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO eval_reports (id, persona_id, period_start, period_end, green, data, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (report["id"], report.get("persona_id"), report.get("period_start"), report.get("period_end"),
             1 if report.get("green") else 0, json.dumps(report, ensure_ascii=False), report["created_at"]))

    def list_eval_reports(self, persona_id: str | None = None) -> list[dict[str, Any]]:
        if persona_id:
            rows = self.conn.execute(
                "SELECT data FROM eval_reports WHERE persona_id=? ORDER BY created_at DESC", (persona_id,)).fetchall()
        else:
            rows = self.conn.execute("SELECT data FROM eval_reports ORDER BY created_at DESC").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def clear_simulation_state(self) -> dict[str, int]:
        tables = [
            "calendar_events",
            "experience_events",
            "daily_summaries",
            "reflections",
            "pain_points",
            "council_sessions",
            "syntheses",
            "entities",
            "entity_facts",
            "event_entities",
            "threads",
            "plans",
            "memory_digests",
            "embeddings",
            "persona_revisions",
            "memory_anomalies",
            "eval_reports",
            "research_projects",
            "study_edges",
            "research_open_questions",
            "meta_reports",
        ]
        deleted: dict[str, int] = {}
        for table in tables:
            count = self.conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
            self.conn.execute(f"DELETE FROM {table}")
            deleted[table] = int(count)
        self.audit("simulation_state", "all", "clear", "cleared generated simulation state", deleted)
        self.conn.commit()
        return deleted

    def purge_runtime_state(self) -> dict[str, int]:
        tables = [
            "calendar_events",
            "experience_events",
            "daily_summaries",
            "reflections",
            "pain_points",
            "council_sessions",
            "syntheses",
            "evidence",
            "entities",
            "entity_facts",
            "event_entities",
            "threads",
            "plans",
            "memory_digests",
            "embeddings",
            "persona_revisions",
            "world_context",
            "memory_anomalies",
            "eval_reports",
            "research_projects",
            "study_edges",
            "research_open_questions",
            "meta_reports",
            "methodology_judgments",
            "prototypes",
            "prototype_sessions",
            "personas",
            "audit_log",
        ]
        deleted: dict[str, int] = {}
        for table in tables:
            count = self.conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"]
            self.conn.execute(f"DELETE FROM {table}")
            deleted[table] = int(count)
        self.conn.commit()
        return deleted

    def audit(self, entity_type: str, entity_id: str, action: str, reason: str | None, data: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            "INSERT INTO audit_log (entity_type, entity_id, action, reason, created_at, data) VALUES (?, ?, ?, ?, ?, ?)",
            (entity_type, entity_id, action, reason, utc_now_iso(), json.dumps(data or {}, ensure_ascii=False)),
        )

    def commit(self) -> None:
        self.conn.commit()
