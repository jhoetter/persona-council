from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ..config import DATA_DIR, database_path, utc_now_iso
from ._schema import SCHEMA


class StoreBase:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or database_path()
        DATA_DIR.mkdir(exist_ok=True)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._stamp_schema_version()

    def _stamp_schema_version(self) -> None:
        from ..config import MEMORY_SCHEMA_VERSION

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
            "research_plans",
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
            "research_plans",
            "study_edges",
            "research_open_questions",
            "meta_reports",
            "methodology_judgments",
            "prototypes",
            "prototype_sessions",
            "runs",
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
