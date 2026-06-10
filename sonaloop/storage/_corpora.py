from __future__ import annotations

import json
from typing import Any


class CorporaMixin:
    """Real source material (docs/grounding.md): a corpus row per ingested document,
    its deduped chunks as addressable rows — the citable units personas ground in."""

    def upsert_corpus(self, corpus: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO corpora (id, data) VALUES (?, ?)",
            (corpus["id"], json.dumps(corpus, ensure_ascii=False)),
        )
        self.conn.commit()

    def get_corpus(self, corpus_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM corpora WHERE id=?", (corpus_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_corpora(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT data FROM corpora ORDER BY id").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def insert_corpus_chunks(self, chunks: list[dict[str, Any]]) -> None:
        self.conn.executemany(
            "INSERT OR REPLACE INTO corpus_chunks (id, corpus_id, idx, text, data) VALUES (?, ?, ?, ?, ?)",
            [(c["id"], c["corpus_id"], c["idx"], c["text"], json.dumps(c, ensure_ascii=False))
             for c in chunks],
        )
        self.conn.commit()

    def get_corpus_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT data FROM corpus_chunks WHERE id=?", (chunk_id,)).fetchone()
        return json.loads(row["data"]) if row else None

    def list_corpus_chunks(self, corpus_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT data FROM corpus_chunks WHERE corpus_id=? ORDER BY idx", (corpus_id,)).fetchall()
        return [json.loads(r["data"]) for r in rows]

    def all_corpus_chunks(self, corpus_ids: list[str] | None = None) -> list[dict[str, Any]]:
        if corpus_ids:
            marks = ",".join("?" for _ in corpus_ids)
            rows = self.conn.execute(
                f"SELECT data FROM corpus_chunks WHERE corpus_id IN ({marks}) ORDER BY corpus_id, idx",
                tuple(corpus_ids)).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT data FROM corpus_chunks ORDER BY corpus_id, idx").fetchall()
        return [json.loads(r["data"]) for r in rows]
