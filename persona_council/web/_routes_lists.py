"""Index/list-page builders, split out of _routes_pages (spec/component-ssr-architecture.md C5 — keep
route modules small). Each renders rows through the shared _list_page() shell."""
from __future__ import annotations

from .. import services
from ..storage import Store
from ._i18n import t
from ._components import _esc, _icon, _avatar, _label, _star, _list_page


def _projects_page() -> str:
    """The Projects list — the app's home (project-centric IA)."""
    store = Store()
    rows = []
    for p in services.list_research_projects(store=store):
        meta = ((f'<span>{p["studies"]} {t("syntheses")}</span>' if p["studies"] else "")   # non-zero only (no "0 Themes")
                + (f'<span>{p["edges"]} {t("build_order_h")}</span>' if p["edges"] else "")
                + (f'<span>{len(p["themes"])} {t("themes_h")}</span>' if p.get("themes") else ""))
        rows.append(f'<a class="row" href="/projects/{_esc(p["id"])}">'
                    f'<span class="rico" style="color:var(--accent)">{_icon("projects")}</span>'
                    f'<span class="title">{_esc(p["title"])}</span><span class="right">{meta}</span></a>')
    return _list_page(store, title=t("projects"), lead=t("projects_lead"), rows=rows,
                      empty_icon="projects", empty_msg=t("no_projects"), active="projects")


def _persona_row(p: dict, store: Store) -> str:
    pid = p["id"]
    try:
        proj = services.list_active_projects(pid, store=store)
    except Exception:
        proj = []
    loops = len(store.list_threads(pid, "open"))
    meta = []
    if proj:
        meta.append(_label(t("n_projects", n=len(proj)), "var(--accent)"))
    if loops:
        meta.append(_label(t("n_open", n=loops), "var(--amber)"))
    return (
        f'<a class="row" href="/personas/{_esc(pid)}">{_avatar(p, 22)}'
        f'<span class="title">{_esc(p["display_name"])}'
        f'<span class="muted small"> · {_esc(p["role"]["title"])}</span></span>'
        f'<span class="right"><span class="muted small">{_esc(p["company_context"]["industry"])}</span>{"".join(meta)}'
        f'{_star("persona", pid, p["display_name"], f"/personas/{pid}")}</span></a>'
    )
