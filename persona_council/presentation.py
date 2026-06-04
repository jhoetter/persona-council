"""Presentation-from-data resolver (spec/methodology-presentation-from-data.md).

The UI must render a methodology ENTIRELY from data. This module is the single resolver: given a
tag (capability/role/artifact-type/discriminator) and an optional object-level `presentation` block,
it returns {label, short, color, icon, glyph} from one of three sources only:

  (S1) verbatim     — the raw tag string
  (S2) data hint    — a `presentation` block authored via MCP (object-level, or in suggestions/*.json)
  (S3) generic fn   — hash(tag)->palette color; raw string label; no icon/glyph

There is NO code map keyed to a specific value (no {"lofi": ...}, no {"prototype": ...}). All such
hints live in suggestions/*.json (authored via MCP) and are looked up by tag here.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import suggestions_dir

# A fixed, value-agnostic palette (colors are assigned by HASHING the tag, not by name).
PALETTE = ["#6b7cff", "#34a853", "#f29900", "#a142f4", "#ea4335", "#00897b", "#5f6368", "#d81b60"]

# Structural default glyphs (keyed to the geometric fan/waist BOOLEAN, never to a value string).
FAN_GLYPH, WAIST_GLYPH = "◇", "◆"  # ◇ hollow (fan) / ◆ filled (waist)

# The conventional artifact type for legacy records that predate the `type` field. A single
# back-compat default (not a value-keyed table); the real type list lives in artifact_types.json.
DEFAULT_ARTIFACT_TYPE = "prototype"


def hash_color(tag: str, palette: list[str] | None = None) -> str:
    pal = palette or PALETTE
    if not tag:
        return "#9aa0a6"
    return pal[sum(ord(c) for c in tag) % len(pal)]


@lru_cache(maxsize=1)
def _hints() -> dict[str, dict[str, Any]]:
    """Flatten all suggestions/*.json into a tag -> presentation(+meta) map. Includes nested
    artifact-type discriminators. Pure data; reloadable by clearing the cache."""
    out: dict[str, dict[str, Any]] = {}
    d = suggestions_dir()
    if not d.exists():
        return out
    for path in sorted(d.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in data.get("items", []) or []:
            tag = item.get("tag")
            if not tag:
                continue
            entry = dict(item.get("presentation") or {})
            for k in ("renderer", "default_template"):
                if item.get(k):
                    entry[k] = item[k]
            out.setdefault(tag, {}).update(entry)
            # nested discriminators (e.g. an artifact type's lofi/midfi) are tags too
            for disc in item.get("discriminators", []) or []:
                dtag = disc.get("tag")
                if not dtag:
                    continue
                dentry = dict(disc.get("presentation") or {})
                if disc.get("template"):
                    dentry["template"] = disc["template"]
                dentry["_parent"] = tag
                out.setdefault(dtag, {}).update(dentry)
    return out


def reload_hints() -> None:
    _hints.cache_clear()


def present(tag: str, own: dict[str, Any] | None = None) -> dict[str, Any]:
    """Resolve display fields for a tag. own = an object-level `presentation` block (highest
    priority, S2); then suggestions hints (S2); then generic fallbacks (S3)."""
    hint = _hints().get(tag, {})
    merged = {**hint, **(own or {})}
    label = merged.get("label") or (tag or "")
    return {
        "label": label,
        "short": merged.get("short") or label,
        "color": merged.get("color") or hash_color(tag),
        "icon": merged.get("icon") or "",
        "glyph": merged.get("glyph") or "",
    }


def step_glyph(is_fan: bool, own: dict[str, Any] | None = None) -> str:
    """The strip glyph is a function of the STRUCTURAL fan/waist boolean (S3), or a data override (S2)."""
    g = (own or {}).get("glyph")
    return g or (FAN_GLYPH if is_fan else WAIST_GLYPH)


# ---- artifact-type registry helpers (data-driven; replaces the TEMPLATES code map) ----

def artifact_type_meta(type_tag: str) -> dict[str, Any]:
    return _hints().get(type_tag, {})


def discriminator_tags(type_tag: str) -> list[str]:
    """Tags declared as discriminators of an artifact type (data-driven; e.g. the fidelity
    ladder lofi/midfi/hifi under `prototype`). No fidelity vocabulary is hardcoded in code."""
    return [t for t, v in _hints().items() if v.get("_parent") == type_tag]


def resolve_template(type_tag: str, tags: list[str] | None = None,
                     explicit: str | None = None) -> str | None:
    """Resolve a renderer template for an artifact from DATA: an explicit template wins; else a
    discriminator tag that maps to a template; else the type's default_template; else None."""
    if explicit:
        return explicit
    hints = _hints()
    for tg in (tags or []):
        tmpl = (hints.get(tg) or {}).get("template")
        if tmpl:
            return tmpl
    return (hints.get(type_tag) or {}).get("default_template")
