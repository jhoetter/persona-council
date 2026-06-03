"""Methodology building-block SUGGESTIONS (spec/methodology-constellations.md §2.3).

The common capabilities, roles, artifact-types and whole-methodology templates are EDITABLE
DATA under suggestions/*.json. The MCP/CLI *offer* them so the host has good defaults and
reuse — they are recommendations, NEVER constraints. The engine (methodology.py) is tag-agnostic
and never consults this module to decide what is allowed: you may adopt a suggested tag, tweak
it, or invent a brand-new one.
"""
from __future__ import annotations

import json
from typing import Any

from .config import suggestions_dir
from .storage import Store


def _load(name: str) -> dict[str, Any]:
    path = suggestions_dir() / f"{name}.json"
    if not path.exists():
        return {"kind": name, "items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def suggest_capabilities() -> dict[str, Any]:
    """Suggested capability tags (explore/cluster/decide/build/test/synthesize, …)."""
    return _load("capabilities")


def suggest_roles() -> dict[str, Any]:
    """Suggested role tags for produces.role."""
    return _load("roles")


def suggest_artifact_types() -> dict[str, Any]:
    """Suggested artifact-type tags for produces.artifact_type / requires.*_tags."""
    return _load("artifact_types")


def suggest_methodologies(store: Store | None = None) -> dict[str, Any]:
    """Full constellation templates to start from — the registered methodologies themselves,
    plus any extra templates under suggestions/methodologies/*.json."""
    from . import methodology as M
    store = store or Store()
    items = []
    for spec in M.registry(store).values():
        items.append({
            "key": spec["key"], "name": spec["name"], "description": spec["description"],
            "when_to_use": spec["when_to_use"],
            "steps": [{"id": s["id"], "name": s["name"], "tags": s["tags"],
                       "consumes": s["consumes"], "produces": s["produces"], "requires": s["requires"]}
                      for s in spec["steps"]],
        })
    extra_dir = suggestions_dir() / "methodologies"
    if extra_dir.exists():
        for path in sorted(extra_dir.glob("*.json")):
            try:
                items.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                pass
    return {"kind": "methodologies", "note": "Constellation templates — copy and adapt; tags are free.",
            "items": items}
