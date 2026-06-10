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


def suggest_section_kinds() -> dict[str, Any]:
    """Suggested Section kinds (theme/phase/research/problem/solution, …) + presentation."""
    return _load("section_kinds")


def suggest_stances() -> dict[str, Any]:
    """The CANONICAL stance scale (suggestions/stance_scale.json) in scale order (+2 → −2) — unlike the
    other suggest_* vocabularies this one IS the closed set every stance resolves onto. Each item:
    {term, value, label_key, aliases} (label_key = the i18n key the UI renders; the engine stays
    label-free, the host authors display text itself). Derived live via artifacts.stance_terms() so the
    JSON is the single source — no term is hardcoded here."""
    from . import artifacts
    raw = _load("stance_scale")
    alias_of: dict[str, list[str]] = {}
    for alias, term in (raw.get("aliases") or {}).items():
        alias_of.setdefault(term, []).append(alias)
    items = [{"term": r["term"], "value": r["value"], "label_key": r["label_key"],
              "aliases": sorted(alias_of.get(r["term"], []), key=str.lower)}
             for r in artifacts.stance_terms()]
    return {"kind": "stance_scale", "items": items,
            "note": "Author a stance as {value -2..2, label?: " + "|".join(i["term"] for i in items)
                    + "}. `label` is optional when `value` is given; any other label resolves via the "
                      "aliases, and an unknown one buckets at neutral but survives as `label_raw` "
                      "(never silently dropped). Council votes use the same terms."}


def suggest_blocker_themes() -> dict[str, Any]:
    """Suggested starter `theme` labels for red-team objections (suggestions/blocker_themes.json) — the
    common blocker families (price / trust / switching cost / …). Recommendations only: brief_red_team
    surfaces them next to the project's own prior themes; any free-text theme is always accepted."""
    return _load("blocker_themes")


def suggest_finding_kinds() -> dict[str, Any]:
    """Suggested Finding kinds (suggestions/finding_kinds.json) — summary/key_problem/pain_solver/… with
    the section id + label_key each renders under. Recommendations: an invented kind still renders
    (artifacts.finding_kind has a generic fallback)."""
    return _load("finding_kinds")


def suggest_chart_kinds() -> dict[str, Any]:
    """Suggested report chart kinds — which `of` to use when, + each one's author payload shape.
    The single source of truth is charts_catalogue.py (also drives the report renderer)."""
    from .charts_catalogue import chart_kinds
    return chart_kinds()


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
