"""Sections — methodology-INDEPENDENT overlay groupings of graph nodes.

A Section references nodes by id (explicit, set-based, overlap allowed) and is a VIEW, never a
container: it never owns/moves/mutates nodes, and deleting it never deletes nodes. Geometry is
derived at render time. `kind` is an OPEN tag resolved for display via presentation/suggestions.
Spec: spec/sections-and-composable-graph.md. Cross-module helpers (get_project_graph,
_require_research_project, stable_id, utc_now_iso, Store) are bound into this module's globals by
the services package __init__ (same shared-namespace mechanism as the rest of the split).
"""
from __future__ import annotations

from typing import Any

from ..config import utc_now_iso
from ..models import Section
from ..storage import Store


def _valid_node_ids(project_id: str, store) -> set[str]:
    """Every node id a section may reference in this project's graph (+ prototype slugs)."""
    g = get_project_graph(project_id, store=store)  # noqa: F821 (bound by package __init__)
    ids = {n["study_id"] for n in g.get("nodes", [])}
    for p in (g.get("prototypes") or []):
        ids.add(p["id"])
        if p.get("slug"):
            ids.add(p["slug"])
    return ids


def _sections(project: dict) -> list[dict]:
    secs = project.get("sections")
    if not isinstance(secs, list):
        secs = []
        project["sections"] = secs
    return secs


def _find(store, section_id: str) -> tuple[dict, dict]:
    """Locate (project, section) by section id across projects."""
    for project in store.list_research_projects():
        for s in _sections(project):
            if s.get("id") == section_id:
                return project, s
    raise KeyError(f"Unknown section: {section_id}")


def _validate_members(project_id: str, member_ids: list[str], store) -> list[str]:
    ids = [str(m).strip() for m in (member_ids or []) if str(m).strip()]
    valid = _valid_node_ids(project_id, store)
    unknown = [m for m in ids if m not in valid]
    if unknown:
        raise ValueError(f"section member_ids not present as nodes in project {project_id}: {unknown}")
    # de-dupe, preserve order
    return list(dict.fromkeys(ids))


def create_section(project_id: str, title: str, kind: str = "theme", member_ids: list[str] | None = None,
                   parent_id: str | None = None, order: int | None = None,
                   presentation: dict[str, Any] | None = None, note: str = "",
                   store=None) -> dict[str, Any]:
    """Create a labeled overlay grouping of graph nodes. `member_ids` must reference real nodes.
    `kind` is a free tag (theme|phase|invented). A section is a view; it never owns nodes."""
    store = store or Store()  # noqa: F821
    project = _require_research_project(store, project_id)  # noqa: F821
    if not str(title).strip():
        raise ValueError("a section needs a non-empty title")
    members = _validate_members(project["id"], member_ids or [], store)
    secs = _sections(project)
    now = utc_now_iso()  # noqa: F821
    sec = Section(
        id=stable_id("section", project["id"], title, now),  # noqa: F821
        project_id=project["id"], title=str(title).strip()[:160], kind=str(kind).strip() or "theme",
        member_ids=members, parent_id=(parent_id or None),
        order=(order if order is not None else len(secs)),
        presentation=presentation or None, note=str(note or "")[:2000],
        created_at=now, updated_at=now,
    ).to_dict()
    secs.append(sec)
    project["updated_at"] = now
    store.upsert_research_project(project)
    return sec


def update_section(section_id: str, patch: dict[str, Any], store=None) -> dict[str, Any]:
    store = store or Store()  # noqa: F821
    project, sec = _find(store, section_id)
    for k in ("title", "kind", "parent_id", "note"):
        if k in patch and patch[k] is not None:
            sec[k] = str(patch[k])[:2000] if k in ("note",) else str(patch[k])[:160]
    if "order" in patch and patch["order"] is not None:
        sec["order"] = int(patch["order"])
    if "presentation" in patch:
        sec["presentation"] = patch["presentation"] or None
    if "member_ids" in patch and patch["member_ids"] is not None:
        sec["member_ids"] = _validate_members(project["id"], patch["member_ids"], store)
    sec["updated_at"] = utc_now_iso()  # noqa: F821
    project["updated_at"] = sec["updated_at"]
    store.upsert_research_project(project)
    return sec


def add_to_section(section_id: str, node_ids: list[str], store=None) -> dict[str, Any]:
    store = store or Store()  # noqa: F821
    project, sec = _find(store, section_id)
    add = _validate_members(project["id"], node_ids, store)
    sec["member_ids"] = list(dict.fromkeys(list(sec.get("member_ids", [])) + add))
    sec["updated_at"] = utc_now_iso()  # noqa: F821
    store.upsert_research_project(project)
    return sec


def remove_from_section(section_id: str, node_ids: list[str], store=None) -> dict[str, Any]:
    store = store or Store()  # noqa: F821
    project, sec = _find(store, section_id)
    drop = {str(n).strip() for n in (node_ids or [])}
    sec["member_ids"] = [m for m in sec.get("member_ids", []) if m not in drop]
    sec["updated_at"] = utc_now_iso()  # noqa: F821
    store.upsert_research_project(project)
    return sec


def set_section_members(section_id: str, node_ids: list[str], store=None) -> dict[str, Any]:
    """Bulk-set membership (the 'promote this cluster into a named section' affordance)."""
    return update_section(section_id, {"member_ids": node_ids}, store=store)


def reorder_sections(project_id: str, ordered_ids: list[str], store=None) -> dict[str, Any]:
    store = store or Store()  # noqa: F821
    project = _require_research_project(store, project_id)  # noqa: F821
    rank = {sid: i for i, sid in enumerate(ordered_ids)}
    for s in _sections(project):
        if s["id"] in rank:
            s["order"] = rank[s["id"]]
    project["updated_at"] = utc_now_iso()  # noqa: F821
    store.upsert_research_project(project)
    return {"project_id": project["id"], "sections": list_sections(project["id"], store=store)}


def list_sections(project_id: str, store=None) -> list[dict[str, Any]]:
    store = store or Store()  # noqa: F821
    project = _require_research_project(store, project_id)  # noqa: F821
    return sorted(_sections(project), key=lambda s: (s.get("order", 0), s.get("created_at", "")))


def get_section(section_id: str, store=None) -> dict[str, Any]:
    store = store or Store()  # noqa: F821
    _project, sec = _find(store, section_id)
    return sec


def delete_section(section_id: str, store=None) -> dict[str, Any]:
    """Delete the section only — its member nodes are untouched (reference, not containment)."""
    store = store or Store()  # noqa: F821
    project, sec = _find(store, section_id)
    project["sections"] = [s for s in _sections(project) if s["id"] != section_id]
    project["updated_at"] = utc_now_iso()  # noqa: F821
    store.upsert_research_project(project)
    return {"deleted": section_id, "nodes_kept": len(sec.get("member_ids", []))}
