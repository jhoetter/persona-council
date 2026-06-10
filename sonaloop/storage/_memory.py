from __future__ import annotations

import json
from typing import Any


class MemoryMixin:
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

    def count_memory_for_personas(self, persona_ids: list[str]) -> dict[str, int]:
        """Cheap aggregate (one query each) of memory depth across a cohort — ESV6 memory_depth."""
        if not persona_ids:
            return {"facts": 0, "events": 0}
        q = ",".join("?" * len(persona_ids))
        facts = self.conn.execute(f"SELECT COUNT(*) AS c FROM entity_facts WHERE persona_id IN ({q})",
                                  tuple(persona_ids)).fetchone()["c"]
        events = self.conn.execute(f"SELECT COUNT(*) AS c FROM experience_events WHERE persona_id IN ({q})",
                                   tuple(persona_ids)).fetchone()["c"]
        return {"facts": int(facts), "events": int(events)}

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
                "SELECT obj_type, obj_id, persona_id, model, dim, vector, text FROM embeddings WHERE persona_id=? AND obj_type=?",
                (persona_id, obj_type)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT obj_type, obj_id, persona_id, model, dim, vector, text FROM embeddings WHERE persona_id=?",
                (persona_id,)).fetchall()
        return [dict(r) for r in rows]

    def has_embedding(self, obj_type: str, obj_id: str, model: str | None = None) -> bool:
        if model:
            return self.conn.execute(
                "SELECT 1 FROM embeddings WHERE obj_type=? AND obj_id=? AND model=?",
                (obj_type, obj_id, model)).fetchone() is not None
        return self.conn.execute(
            "SELECT 1 FROM embeddings WHERE obj_type=? AND obj_id=?", (obj_type, obj_id)).fetchone() is not None

    def embedding_models(self) -> list[str]:
        """The distinct vector spaces present (provider-qualified model ids)."""
        rows = self.conn.execute("SELECT DISTINCT model FROM embeddings ORDER BY model").fetchall()
        return [r["model"] for r in rows]

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
