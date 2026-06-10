from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_assets(mcp):
    # ============ Project assets: files/images/screenshots as evidence ============
    @mcp.tool()
    def attach_asset(project_id: str, path: str | None = None, content_base64: str | None = None,
                     filename: str | None = None, kind: str | None = None, title: str = "",
                     notes: str = "", source: str = "") -> dict[str, Any]:
        """Attach a file/image/screenshot to a project as citable evidence. Pass EITHER `path`
        (a local file, e.g. a screenshot you just captured) OR `content_base64` + `filename`.
        `kind` (image|screenshot|document|file) is inferred from the extension when omitted.
        Idempotent on content. The asset gets a stable id personas/councils cite in refs;
        brief_council automatically puts every project asset in the room."""
        t = time.perf_counter()
        return _env("attach_asset", services.attach_asset(
            project_id, path, content_base64, filename, kind, title, notes, source), t)

    @mcp.tool()
    def attach_prototype_shot(project_id: str, prototype_id: str, title: str = "",
                              notes: str = "") -> dict[str, Any]:
        """Screenshot a registered prototype (Playwright) and attach the shot to the project
        as image evidence — the capture path for artifacts produced during the project."""
        t = time.perf_counter()
        return _env("attach_prototype_shot",
                    services.attach_prototype_shot(project_id, prototype_id, title, notes), t)

    @mcp.tool()
    def list_assets(project_id: str) -> dict[str, Any]:
        """Every asset attached to a project (lean records; excerpt via get_asset, pixels via
        view_asset)."""
        t = time.perf_counter()
        return _env("list_assets", services.list_assets(project_id), t)

    @mcp.tool()
    def get_asset(project_id: str, asset_id: str) -> dict[str, Any]:
        """One asset record (by id or filename) — includes the text excerpt for documents."""
        t = time.perf_counter()
        return _env("get_asset", services.get_asset(project_id, asset_id), t)

    @mcp.tool()
    def view_asset(project_id: str, asset_id: str):
        """LOOK at an asset. For an image/screenshot this returns the actual image — view it
        before authoring persona reactions so they are grounded in what is really there. For a
        text document it returns the full excerpt; other binaries return their metadata."""
        data, record = services.get_asset_content(project_id, asset_id)
        if record.get("kind") in ("image", "screenshot"):
            from mcp.server.fastmcp import Image
            fmt = (record.get("media_type") or "image/png").split("/")[-1]
            return Image(data=data, format=fmt)
        t = time.perf_counter()
        if record.get("text_excerpt"):
            return _env("view_asset", {"id": record["id"], "title": record.get("title"),
                                       "content": record["text_excerpt"]}, t)
        return _env("view_asset", {"id": record["id"], "title": record.get("title"),
                                   "media_type": record.get("media_type"), "bytes": record.get("bytes"),
                                   "note": "binary asset — cite it by id; no inline preview"}, t)

    @mcp.tool()
    def remove_asset(project_id: str, asset_id: str) -> dict[str, Any]:
        """Detach an asset from a project (by id or filename)."""
        t = time.perf_counter()
        return _env("remove_asset", services.remove_asset(project_id, asset_id), t)
