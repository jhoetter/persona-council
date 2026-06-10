"""Provider-agnostic embeddings (ticket provider-agnostic-embeddings).

Embeddings power recall/memory retrieval but were welded to OpenAI — blocking
EU / on-prem / local users and coupling the free core to one vendor's keys.
This module makes the provider a CONFIG choice:

    SONALOOP_EMBEDDINGS_PROVIDER = openai | ollama | none

- **openai** — the previous behavior (urllib REST, no SDK); model via
  OPENAI_EMBEDDING_MODEL (default text-embedding-3-small). Stored model ids
  stay un-namespaced for this provider, so existing vectors remain valid.
- **ollama** — local/open: POSTs to OLLAMA_HOST (default
  http://localhost:11434) /api/embed; model via SONALOOP_OLLAMA_EMBED_MODEL
  (default nomic-embed-text). Stored model ids are namespaced
  ("ollama:<model>") so the vector space never silently mixes with OpenAI's.
- **none** — explicit off; recall degrades to keyword/recency/importance.

Unset, the provider resolves to openai when OPENAI_API_KEY is present, else
none — existing setups keep working, keyless setups simply run without
semantics until they opt into a provider. Everything is fail-soft: any
provider error returns None and recall falls back to keyword retrieval.
Vector-space safety lives at the call sites: rows persist with their
provider-qualified model id, recall only scores rows from the ACTIVE space,
and the backfill re-embeds per space (memory.py)."""

from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

PROVIDERS = ("openai", "ollama", "none")


def _disabled() -> bool:
    return os.getenv("PERSONA_COUNCIL_DISABLE_EMBEDDINGS", "").lower() in {"1", "true", "yes"}


def active_provider() -> str:
    """The resolved provider name. Explicit env wins; default = openai when a key
    is present, else none (never auto-probe a local server)."""
    if _disabled():
        return "none"
    explicit = os.getenv("SONALOOP_EMBEDDINGS_PROVIDER", "").strip().lower()
    if explicit:
        if explicit not in PROVIDERS:
            raise ValueError(f"SONALOOP_EMBEDDINGS_PROVIDER={explicit!r} — valid: {PROVIDERS}")
        return explicit
    return "openai" if os.getenv("OPENAI_API_KEY") else "none"


def provider_model() -> str:
    """The model id persisted with every vector — the VECTOR-SPACE key. OpenAI ids
    stay un-namespaced (existing rows keep matching); other providers namespace."""
    p = active_provider()
    if p == "openai":
        return os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    if p == "ollama":
        return f"ollama:{os.getenv('SONALOOP_OLLAMA_EMBED_MODEL', 'nomic-embed-text')}"
    return "none"


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **headers},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _embed_openai(texts: list[str]) -> list[list[float]] | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    data = _post_json("https://api.openai.com/v1/embeddings",
                      {"model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
                       "input": texts},
                      {"Authorization": f"Bearer {api_key}"})
    rows = sorted(data["data"], key=lambda d: d["index"])
    return [r["embedding"] for r in rows]


def _embed_ollama(texts: list[str]) -> list[list[float]] | None:
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    model = os.getenv("SONALOOP_OLLAMA_EMBED_MODEL", "nomic-embed-text")
    data = _post_json(f"{host}/api/embed", {"model": model, "input": texts}, {})
    vecs = data.get("embeddings")
    return vecs if isinstance(vecs, list) and len(vecs) == len(texts) else None


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """One vector per text via the active provider, or None when embeddings are
    off/unavailable. Fail-soft by contract: errors degrade to keyword retrieval."""
    if not texts:
        return None
    provider = active_provider()
    if provider == "none":
        return None
    try:
        if provider == "openai":
            return _embed_openai(texts)
        return _embed_ollama(texts)
    except Exception:  # noqa: BLE001 — fail-soft to keyword-only retrieval
        return None
