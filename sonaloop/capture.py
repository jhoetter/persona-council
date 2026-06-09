"""Server-side artifact capture (ticket artifacts-into-council).

A council can be pointed at a REAL artifact — a live URL/website or a prototype link — instead of a
mere textual description. To let personas "see" it without server-side text-LLM calls (the
host-authors-all-text contract), we capture a lightweight, grounded TEXT snapshot of the page: its
title, meta description, headings and visible copy. That snapshot is the representation the council
reads.

Capture degrades gracefully: a URL that can't be fetched still yields a snapshot stub (the ref + the
error) so a council is never hard-failed by a dead link. We reuse `httpx` (already a transitive dep
via fastapi/mcp) and a stdlib HTML parser — NO new dependency, NO browser launch. If a richer image
snapshot is ever wanted, the existing Playwright harness (sonaloop/browser.py) can be layered on; the
text snapshot is the portable default.
"""
from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from typing import Any

from .config import utc_now_iso

# Keep the captured text bounded so a single artifact can't bloat the council context.
MAX_SNAPSHOT_CHARS = 6000
_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_BLOCK_TAGS = {"p", "li", "div", "section", "article", "header", "footer", "main", "br", "tr"}


class _TextExtractor(HTMLParser):
    """Pull the title, meta description, headings and visible text out of an HTML document with the
    stdlib parser (no bs4 dependency). Hidden/non-content tags are skipped; headings are kept distinct
    so the council sees the page's structure, not just a wall of text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.headings: list[str] = []
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._heading_tag: str | None = None
        self._heading_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            a = {k.lower(): (v or "") for k, v in attrs}
            if a.get("name", "").lower() in ("description", "og:description") or a.get("property", "").lower() == "og:description":
                if a.get("content") and not self.description:
                    self.description = a["content"].strip()
        elif tag in _HEADING_TAGS:
            self._heading_tag = tag
            self._heading_buf = []
        elif tag in _BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "title":
            self._in_title = False
        elif tag in _HEADING_TAGS and self._heading_tag == tag:
            text = " ".join("".join(self._heading_buf).split())
            if text:
                self.headings.append(text)
                self._chunks.append("\n" + text + "\n")
            self._heading_tag = None
            self._heading_buf = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title += data
            return
        if self._heading_tag:
            self._heading_buf.append(data)
            return
        if data.strip():
            self._chunks.append(data)

    def visible_text(self) -> str:
        text = "".join(self._chunks)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n[ \t]+", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def _content_hash(*parts: str) -> str:
    return hashlib.sha256("".join(parts).encode("utf-8")).hexdigest()[:16]


def capture_url(url: str, *, timeout: float = 12.0) -> dict[str, Any]:
    """Fetch `url` and return a grounded TEXT snapshot the council can read:

        {ok, mode, url, final_url, status, title, description, headings, text, content_hash,
         captured_at, bytes, error?}

    `mode` is 'text' on success, 'unavailable' when the fetch failed. Never raises — a dead/blocked
    link yields ok=False with the error recorded, so the caller still stores a reproducible reference
    (url + captured_at) and the council degrades instead of hard-failing."""
    captured_at = utc_now_iso()
    base = {"url": url, "captured_at": captured_at, "title": "", "description": "",
            "headings": [], "text": "", "status": None, "final_url": url, "bytes": 0}
    try:
        import httpx
    except Exception as exc:  # pragma: no cover - httpx is a transitive dep, present in practice
        return {**base, "ok": False, "mode": "unavailable",
                "content_hash": _content_hash(url, "no-httpx"),
                "error": f"http client unavailable: {exc}"}
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Sonaloop-Council/1.0; +artifact-capture)"}
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers) as client:
            resp = client.get(url)
        body = resp.text or ""
        parser = _TextExtractor()
        try:
            parser.feed(body)
        except Exception:
            pass  # malformed HTML: keep whatever was parsed so far
        title = " ".join(parser.title.split()).strip()
        text = parser.visible_text()[:MAX_SNAPSHOT_CHARS]
        return {
            **base,
            "ok": resp.is_success,
            "mode": "text",
            "status": resp.status_code,
            "final_url": str(resp.url),
            "title": title,
            "description": parser.description,
            "headings": parser.headings[:30],
            "text": text,
            "bytes": len(body.encode("utf-8", "ignore")),
            "content_hash": _content_hash(str(resp.url), title, text),
        }
    except Exception as exc:
        return {**base, "ok": False, "mode": "unavailable",
                "content_hash": _content_hash(url, repr(exc)),
                "error": f"{type(exc).__name__}: {exc}"}
