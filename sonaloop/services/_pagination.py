"""Shared pagination — the core implementation of the cross-repo convention
(sonaloop-data: docs/pagination.md; referenced from this repo's docs/pagination.md).

Machine surfaces (MCP tools, machine-readable CLI output) paginate with
`limit` (default 25) + an OPAQUE `cursor` over a stable sort key, and answer in
the shared envelope::

    {"items": [...], "total": 311, "has_more": true, "next_cursor": "..."}

- `next_cursor` is present exactly when `has_more` is true.
- The cursor encodes the position (the last item's sort key) AND a fingerprint
  of the filter set it was issued under — reusing it with different filters is
  rejected instead of silently paging the wrong list.
- Backward compatible by construction: a call with no pagination params gets
  the first page plus the `has_more` hint, so existing callers keep working.

Clients must treat the cursor as opaque (the encoding may change at any time).
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
from typing import Any, Callable

DEFAULT_PAGE_LIMIT = 25
MAX_PAGE_LIMIT = 200


def _fingerprint(filters: dict[str, Any] | None) -> str:
    """A short stable digest of the filter set a cursor was issued under."""
    canon = json.dumps(filters or {}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(canon.encode("utf-8")).hexdigest()[:10]


def encode_cursor(position: str, filters: dict[str, Any] | None = None) -> str:
    """Opaque cursor: the last-seen sort key + the filter fingerprint, b64-packed."""
    raw = json.dumps({"k": position, "f": _fingerprint(filters)}, ensure_ascii=False)
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(cursor: str | None, filters: dict[str, Any] | None = None) -> str | None:
    """The sort-key position inside `cursor` — or None when no cursor was given.

    Raises ValueError for a malformed cursor and for a cursor issued under a
    DIFFERENT filter set (filters always compose with pagination; a stale cursor
    must not silently page a differently-filtered list).
    """
    if not cursor:
        return None
    try:
        pad = "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(cursor + pad))
        position, fp = data["k"], data["f"]
    except (ValueError, KeyError, TypeError, binascii.Error) as exc:
        raise ValueError("Invalid pagination cursor — treat cursors as opaque and pass back "
                         "exactly the next_cursor a previous call returned") from exc
    if fp != _fingerprint(filters):
        raise ValueError("This cursor was issued under a different filter set — "
                         "restart from the first page (omit the cursor) after changing filters")
    return str(position)


def paginate(items: list[Any], key: Callable[[Any], str], *,
             limit: int | None = DEFAULT_PAGE_LIMIT, cursor: str | None = None,
             filters: dict[str, Any] | None = None, reverse: bool = False) -> dict[str, Any]:
    """Page `items` (ALREADY sorted by `key`; descending when `reverse`) into the envelope.

    Cursor-based, not offset-based: the cursor remembers the last item's sort
    key, so inserts/deletes between calls never skip or repeat existing items.
    `total` counts the whole (filtered) set, never just the page.
    """
    limit = max(1, min(MAX_PAGE_LIMIT, int(limit or DEFAULT_PAGE_LIMIT)))
    after = decode_cursor(cursor, filters)
    start = 0
    if after is not None:
        later = (lambda k: k < after) if reverse else (lambda k: k > after)
        start = next((i for i, it in enumerate(items) if later(key(it))), len(items))
    window = items[start:start + limit]
    has_more = start + limit < len(items)
    out: dict[str, Any] = {"items": window, "total": len(items), "has_more": has_more}
    if has_more:
        out["next_cursor"] = encode_cursor(key(window[-1]), filters)
    return out
