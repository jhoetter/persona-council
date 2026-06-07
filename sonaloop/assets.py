"""Asset store for embeddable media — prototype screenshots, uploaded images
(spec/meta-report-presentation-and-pdf.md §2).

Files live under `data/assets/`, which the web app already serves statically at `/data/assets/…`, so
no extra route is needed. An asset id is the content hash + extension (`assets/<hash>.png`); the URL is
`/data/<id>`. `capture_prototype_shot` uses the Playwright harness to screenshot a static prototype —
the harness CAPTURES, it does not generate text, so the no-in-process-LLM invariant is preserved.
"""
from __future__ import annotations

import hashlib

from .config import DATA_DIR, prototypes_dir

ASSETS_DIR = DATA_DIR / "assets"


def put_asset(data: bytes, ext: str = "png") -> str:
    """Write bytes to the content-addressed store; return the asset id (`assets/<hash>.<ext>`)."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    aid = hashlib.sha1(data).hexdigest()[:16]
    name = f"{aid}.{ext.lstrip('.')}"
    (ASSETS_DIR / name).write_bytes(data)
    return f"assets/{name}"


def asset_url(asset_id: str) -> str:
    """The static URL for an asset id (served from the /data mount)."""
    return f"/data/{asset_id}"


def capture_prototype_shot(prototype_id: str, store=None, width: int = 1120, height: int = 720) -> str:
    """Screenshot a STATIC prototype (its entry HTML via file://) into an asset; record the asset id on
    the prototype (`shot`) so the report can embed it. Uses the Playwright harness (a hard dependency)."""
    from .storage import Store
    store = store or Store()
    p = store.get_prototype(prototype_id)
    if not p:
        raise KeyError(f"Unknown prototype: {prototype_id}")
    entry = prototypes_dir() / p["slug"] / p.get("entry", "index.html")
    if not entry.exists():
        raise FileNotFoundError(f"Prototype has no entry file to screenshot: {entry}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": width, "height": height}, device_scale_factor=2)
        pg.goto(entry.resolve().as_uri(), wait_until="networkidle")
        pg.wait_for_timeout(300)
        png = pg.screenshot()
        b.close()
    aid = put_asset(png, "png")
    rec = dict(p)
    rec["shot"] = aid
    store.upsert_prototype(rec)
    return aid
