"""List pagination components — the human-UI half of the shared cross-repo convention
(sonaloop-data docs/pagination.md; core adoption in this repo's docs/pagination.md):
numbered pages in the URL (?page=N) ALONGSIDE the filter params, ~25 rows per page,
totals over the full filtered set; changing the filter resets to page 1."""
from __future__ import annotations

from urllib.parse import quote as _urlquote

from ._html import h, raw, register_css
from ._i18n import t

LIST_PAGE_SIZE = 25


def _page_window(rows: list, page: int) -> tuple[list, int, int]:
    """Clamp `page` and slice one page out of the (already filtered) rows.
    Returns (visible rows, clamped page, page count)."""
    pages = max(1, -(-len(rows) // LIST_PAGE_SIZE))
    page = min(max(1, int(page or 1)), pages)
    return rows[(page - 1) * LIST_PAGE_SIZE: page * LIST_PAGE_SIZE], page, pages


def _pager(base: str, page: int, pages: int, q: str = "") -> str:
    """Prev/next page controls + 'page N of M'. Page state lives in the URL next to the
    search param, so any view is shareable and back/forward restores it."""
    if pages <= 1:
        return ""
    def url(n: int) -> str:
        return f"{base}?page={n}" + (f"&q={_urlquote(q)}" if q else "")
    def step(label: str, n: int, ok: bool) -> str:
        if ok:
            return h("a", {"class_": "sl-btn", "href": url(n)}, label)
        return h("span", {"class_": "sl-btn", "aria-disabled": "true"}, label)
    return h("nav", {"class_": "pager", "aria-label": t("page_of", n=page, m=pages)},
             step(t("pager_prev"), page - 1, page > 1),
             h("span", {"class_": "pager-n muted small"}, t("page_of", n=page, m=pages)),
             step(t("pager_next"), page + 1, page < pages))


def _list_filter_box(base: str, q: str) -> str:
    """The list search field (GET ?q=…). Submitting drops the page param by construction,
    so a changed filter always restarts at the first page (the convention's reset rule)."""
    from ._components import _icon
    return h("form", {"class_": "listsearch", "method": "get", "action": base},
             raw(_icon("search")),
             h("input", {"type": "text", "name": "q", "value": q,
                         "placeholder": t("list_search_ph"), "aria-label": t("list_search_ph")}))


register_css(r"""
/* ---- list pagination + filter (docs/pagination.md) ---- */
.pager{display:flex;align-items:center;justify-content:center;gap:12px;margin:16px 0 4px}
.pager .sl-btn[aria-disabled]{opacity:.45;pointer-events:none}
.pager-n{font-variant-numeric:tabular-nums}
.listsearch{display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:var(--radius);padding:5px 10px;background:var(--panel);max-width:320px;margin:0 0 12px}
.listsearch svg{width:15px;height:15px;color:var(--muted);flex:none}
.listsearch input{border:0;background:transparent;padding:2px 0;font-size:var(--t-body);color:var(--ink);width:100%}
.listsearch input:focus{outline:none}
""")
