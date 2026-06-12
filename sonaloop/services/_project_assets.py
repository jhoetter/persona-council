"""Project assets: files, images & screenshots as first-class, citable evidence
(ticket attach-evidence-files-mcp — the generic multimodal Assets foundation the
council-artifacts module points at).

An asset is REAL MATERIAL on a project — stored once in the content-addressed
binary store (ROOT/data/assets, the same dir the web app serves at
/data/assets/…) and recorded on the project (`project["assets"]`, the same
JSON-blob-per-row model artifacts use; no new table). Ids are stable
(content-addressed per project) so personas/councils can cite them and
re-attaching the same bytes is idempotent.

Direction (ticket project-assets-direction-deliverables-page-section): an asset
flows `in` (evidence brought INTO the project — a screenshot, a PDF, an
interview note; the default, and what every pre-direction record means) or
`out` (a deliverable PRODUCED from the project — the exported PPTX/PDF a
synthesis renders; attached by export_synthesis_deliverable with
source `synthesis:<id>`). No migration: a record without the field is `in`.

Multimodal contract: image assets are not merely stored — `get_asset_content`
hands back the bytes, and the MCP `view_asset` tool returns them as an actual
image so the HOST looks at the evidence before authoring persona reactions
(no in-process vision; the host's eyes are the vision model). Text documents
carry an inline excerpt so councils can quote them directly."""

from __future__ import annotations

import base64
import hashlib
import mimetypes
from pathlib import Path
from typing import Any

from ..config import ROOT, utc_now_iso
from ..storage import Store

from ._common import *  # noqa: F401,F403  (stable_id, _require_research_project, …)


IMAGE_EXTS = {"png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"}
DOCUMENT_EXTS = {"pdf", "md", "txt", "csv", "json", "html", "docx", "rtf"}
TEXT_EXCERPT_EXTS = {"md", "txt", "csv", "json", "html", "rtf"}
ASSET_KINDS = ("image", "screenshot", "document", "file")
ASSET_DIRECTIONS = ("in", "out")   # in = evidence brought into the project · out = deliverable produced from it
MAX_ASSET_BYTES = 25 * 1024 * 1024
_EXCERPT_CHARS = 4000


def _assets_dir() -> Path:
    # ROOT-relative like SOUL/avatars (and = DATA_DIR/assets in a source checkout,
    # which the web app serves statically at /data/assets/…); tests monkeypatch ROOT.
    return Path(ROOT) / "data" / "assets"


def _project_assets(project: dict[str, Any]) -> list[dict[str, Any]]:
    return project.setdefault("assets", [])


def _infer_kind(ext: str, declared: str | None) -> str:
    if declared in ASSET_KINDS:
        return declared
    if ext in IMAGE_EXTS:
        return "image"
    if ext in DOCUMENT_EXTS:
        return "document"
    return "file"


def _text_excerpt(data: bytes, ext: str) -> str:
    if ext not in TEXT_EXCERPT_EXTS or len(data) > 512 * 1024:
        return ""
    try:
        return data.decode("utf-8", errors="ignore")[:_EXCERPT_CHARS].strip()
    except Exception:
        return ""


def attach_asset(project_id: str, path: str | None = None, content_base64: str | None = None,
                 filename: str | None = None, kind: str | None = None, title: str = "",
                 notes: str = "", source: str = "", direction: str | None = None,
                 store: Store | None = None) -> dict[str, Any]:
    """Attach a file/image/screenshot to a project as a citable asset. Pass EITHER
    `path` (a local file — e.g. a screenshot captured during the project) OR
    `content_base64` (+ `filename` for the extension). The binary lands in the
    content-addressed store; the record (stable id, kind, media type, excerpt for
    text documents) lands on the project. `direction` is `in` (evidence, the
    default) or `out` (a deliverable produced from the project). Re-attaching
    identical bytes is an idempotent upsert (title/notes/direction refresh).
    Emits `asset.attached`."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # noqa: F821 (bound)
    if direction is not None and direction not in ASSET_DIRECTIONS:
        raise ValueError(f"direction must be one of {ASSET_DIRECTIONS}, got {direction!r}")
    if bool(path) == bool(content_base64):
        raise ValueError("Pass exactly one of `path` or `content_base64`.")
    if path:
        src = Path(path).expanduser()
        if not src.is_file():
            raise FileNotFoundError(f"No such file: {path}")
        data = src.read_bytes()
        name = filename or src.name
        source = source or str(src)
    else:
        data = base64.b64decode(content_base64, validate=True)
        if not filename:
            raise ValueError("`filename` is required with content_base64 (it carries the extension).")
        name = filename
    if not data:
        raise ValueError("Asset is empty.")
    if len(data) > MAX_ASSET_BYTES:
        raise ValueError(f"Asset exceeds the {MAX_ASSET_BYTES // (1024 * 1024)}MB cap.")
    ext = (Path(name).suffix.lstrip(".") or "bin").lower()
    sha = hashlib.sha1(data).hexdigest()[:16]
    adir = _assets_dir()
    adir.mkdir(parents=True, exist_ok=True)
    (adir / f"{sha}.{ext}").write_bytes(data)
    assets = _project_assets(project)
    aid = stable_id("asset", project["id"], sha)  # noqa: F821 (bound)
    existing = next((a for a in assets if a["id"] == aid), None)
    record = {
        "id": aid,
        "kind": _infer_kind(ext, kind),
        "filename": name,
        "title": (title or (existing or {}).get("title") or name).strip(),
        "notes": notes or (existing or {}).get("notes", ""),
        "source": source or (existing or {}).get("source", ""),
        # in (evidence; also every pre-direction record) | out (deliverable). Kept on re-attach.
        "direction": direction or (existing or {}).get("direction") or "in",
        "media_type": mimetypes.guess_type(name)[0] or "application/octet-stream",
        "bytes": len(data),
        "asset_path": f"data/assets/{sha}.{ext}",
        "url": f"/data/assets/{sha}.{ext}",
        "text_excerpt": _text_excerpt(data, ext),
        "created_at": (existing or {}).get("created_at") or utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    if (existing or {}).get("supersedes"):       # the provenance chain survives a re-attach upsert
        record["supersedes"] = existing["supersedes"]
    if existing:
        assets[assets.index(existing)] = record
    else:
        assets.append(record)
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    emit_lifecycle_event("asset.attached", {"project_id": project["id"], "asset_id": aid,  # noqa: F821 (bound)
                                            "kind": record["kind"], "filename": name}, store)
    return record


def attach_prototype_shot(project_id: str, prototype_id: str, title: str = "",
                          notes: str = "", store: Store | None = None) -> dict[str, Any]:
    """The capture path for artifacts PRODUCED during a project: screenshot a
    registered prototype (Playwright harness) and attach the shot as image evidence."""
    from .. import assets as _assets
    store = store or Store()
    shot = _assets.capture_prototype_shot(prototype_id, store=store)  # "assets/<hash>.png"
    shot_file = _assets.ASSETS_DIR / Path(shot).name
    return attach_asset(project_id, path=str(shot_file), kind="screenshot",
                        title=title or f"Prototype shot: {prototype_id}",
                        notes=notes, source=f"prototype:{prototype_id}", store=store)


def list_assets(project_id: str, store: Store | None = None) -> list[dict[str, Any]]:
    """Every asset attached to a project (lean records; bytes via get_asset_content)."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # noqa: F821 (bound)
    return [{k: v for k, v in a.items() if k != "text_excerpt"} for a in _project_assets(project)]


def get_asset(project_id: str, asset_id: str, store: Store | None = None) -> dict[str, Any]:
    """One asset record by id (or filename) — includes the text excerpt for documents."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # noqa: F821 (bound)
    for a in _project_assets(project):
        if a["id"] == asset_id or a.get("filename") == asset_id:
            return a
    raise KeyError(f"Unknown asset '{asset_id}' in project {project_id}")


def record_asset_supersession(project_id: str, asset_id: str, replaced: list[dict[str, Any]],
                              store: Store | None = None) -> dict[str, Any]:
    """Record the supersede chain on a SURVIVING asset record (UX U8 — provenance: which earlier
    version this file replaced). `replaced` entries are lean `{id, filename, created_at}` stubs:
    the stale records themselves are already detached (remove_asset — a deliverable re-export
    keeps exactly one live record per (synthesis, format)), so the chain keeps enough of each to
    read honestly on the asset's provenance block. Idempotent per replaced id."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # noqa: F821 (bound)
    for a in _project_assets(project):
        if a["id"] == asset_id:
            seen = {s.get("id") for s in a.get("supersedes") or []}
            new = [r for r in replaced if r.get("id") and r["id"] not in seen and r["id"] != asset_id]
            if new:
                a["supersedes"] = (a.get("supersedes") or []) + new
                a["updated_at"] = utc_now_iso()
                project["updated_at"] = utc_now_iso()
                store.upsert_research_project(project)
            return a
    raise KeyError(f"Unknown asset '{asset_id}' in project {project_id}")


def get_asset_content(project_id: str, asset_id: str,
                      store: Store | None = None) -> tuple[bytes, dict[str, Any]]:
    """The asset's bytes + its record — the multimodal feed (MCP view_asset wraps this).
    The read is contained to the asset store, never an arbitrary path from the record."""
    record = get_asset(project_id, asset_id, store=store)
    target = (Path(ROOT) / record["asset_path"]).resolve()
    if not target.is_relative_to(_assets_dir().resolve()):
        raise ValueError(f"Asset path escapes the asset store: {record['asset_path']}")
    if not target.exists():
        raise FileNotFoundError(f"Asset binary missing: {record['asset_path']} (re-attach or import-snapshot)")
    return target.read_bytes(), record


def remove_asset(project_id: str, asset_id: str, store: Store | None = None) -> dict[str, Any]:
    """Detach an asset from a project (by id or filename). The binary stays in the
    content-addressed store — it may be shared by other projects and is cheap."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # noqa: F821 (bound)
    assets = _project_assets(project)
    keep = [a for a in assets if a["id"] != asset_id and a.get("filename") != asset_id]
    deleted = len(assets) - len(keep)
    if deleted:
        project["assets"] = keep
        project["updated_at"] = utc_now_iso()
        store.upsert_research_project(project)
    return {"deleted": deleted}


def project_asset_briefs(project_id: str, asset_ids: list[str] | None = None,
                         store: Store | None = None) -> list[dict[str, Any]]:
    """The assets to put IN the council room, as compact evidence briefs.
    `asset_ids` selects a subset (by id or filename); None = every project asset."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # noqa: F821 (bound)
    assets = _project_assets(project)
    if asset_ids:
        want = {str(x) for x in asset_ids}
        assets = [a for a in assets if a["id"] in want or a.get("filename") in want]
    return [{"id": a["id"], "project_id": project["id"], "kind": a.get("kind"),
             "title": a.get("title"), "filename": a.get("filename"), "notes": a.get("notes", ""),
             "media_type": a.get("media_type"), "is_image": a.get("kind") in ("image", "screenshot"),
             "text_excerpt": a.get("text_excerpt", ""), "source": a.get("source", "")}
            for a in assets]


def render_assets_context(briefs: list[dict[str, Any]]) -> str:
    """Render the evidence assets as one labelled block for persona contexts. Image
    assets instruct the HOST to view_asset them first — the host's eyes feed the
    persona an honest description of what is actually there; text documents are
    quoted inline via their excerpt."""
    if not briefs:
        return ""
    parts = ["EVIDENCE ASSETS IN THE ROOM — ground reactions in this real material, not in "
             "assumptions about it."]
    for b in briefs:
        lines = [f"--- ASSET: {b.get('title') or b.get('filename')} ({b.get('kind')}, id {b['id']}) ---"]
        if b.get("notes"):
            lines.append(f"Notes: {b['notes']}")
        if b.get("is_image"):
            lines.append(f"IMAGE EVIDENCE: call view_asset('{b['project_id']}', '{b['id']}') and LOOK at it "
                         "before authoring any reaction; relay only what is actually visible.")
        elif b.get("text_excerpt"):
            lines.append("Content (excerpt):\n" + b["text_excerpt"])
        else:
            lines.append(f"Binary evidence ({b.get('media_type')}); cite it by id — do not invent its contents.")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
