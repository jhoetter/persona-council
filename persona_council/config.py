from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "persona-council.db"


def load_env(path: Path | None = None) -> None:
    """Load a simple .env file without requiring python-dotenv at import time."""
    env_path = path or ROOT / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def database_path() -> Path:
    url = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
    if url.startswith("sqlite:///"):
        return Path(url.removeprefix("sqlite:///")).expanduser()
    if url.startswith("sqlite://"):
        return Path(url.removeprefix("sqlite://")).expanduser()
    raise ValueError("Only sqlite DATABASE_URL values are supported in this build.")


def utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Memory & simulation settings (spec/memory-and-simulation-architecture.md) ---

MEMORY_SCHEMA_VERSION = 2


def embedding_model() -> str:
    return os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def embeddings_enabled() -> bool:
    """Semantic retrieval is on when an OpenAI key is present and not disabled."""
    if os.getenv("PERSONA_COUNCIL_DISABLE_EMBEDDINGS", "").lower() in {"1", "true", "yes"}:
        return False
    return bool(os.getenv("OPENAI_API_KEY"))


def retrieval_weights() -> dict[str, float]:
    """Hybrid recall weights: semantic, keyword/entity, recency, importance."""
    def _w(name: str, default: float) -> float:
        try:
            return float(os.getenv(name, default))
        except (TypeError, ValueError):
            return default

    return {
        "semantic": _w("PERSONA_COUNCIL_W_SEMANTIC", 0.45),
        "keyword": _w("PERSONA_COUNCIL_W_KEYWORD", 0.25),
        "recency": _w("PERSONA_COUNCIL_W_RECENCY", 0.15),
        "importance": _w("PERSONA_COUNCIL_W_IMPORTANCE", 0.15),
    }


def recency_halflife_days() -> float:
    try:
        return float(os.getenv("PERSONA_COUNCIL_RECENCY_HALFLIFE_DAYS", 30.0))
    except (TypeError, ValueError):
        return 30.0


def default_sample_days_per_month() -> int:
    try:
        return int(os.getenv("PERSONA_COUNCIL_SAMPLE_DAYS_PER_MONTH", 4))
    except (TypeError, ValueError):
        return 4

