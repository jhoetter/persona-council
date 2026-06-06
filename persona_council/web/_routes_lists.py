"""Index/list-page builders, split out of _routes_pages (spec/component-ssr-architecture.md C5 — keep
route modules small). Each renders rows through the shared _list_page() shell. Markup via h()."""
from __future__ import annotations

from .. import services
from ..storage import Store
from ._i18n import t
from ._components import _icon, _avatar, _label, _star, _list_page, _artifact_present
from ._html import h, raw, fragment


def _row(href: str, ric, title, right=None, *, color: str | None = None, sub=None) -> str:
    """A list row: leading icon/avatar (`ric`), title (+ optional muted `sub`), right-aligned meta."""
    lead = ric if color is None else h("span", {"class_": "rico", "style": f"color:{color}"}, raw(_icon(ric)))
    return h("a", {"class_": "row", "href": href}, lead,
             h("span", {"class_": "title"}, title,
               h("span", {"class_": "muted small"}, f" · {sub}") if sub else None),
             h("span", {"class_": "right"}, right))


def _projects_page() -> str:
    """The Projects list — the app's home (project-centric IA)."""
    store = Store()
    rows = []
    for p in services.list_research_projects(store=store):
        meta = fragment(                                       # non-zero counts only (no "0 Themes" noise)
            h("span", {}, f'{p["studies"]} {t("syntheses")}') if p["studies"] else None,
            h("span", {}, f'{p["edges"]} {t("build_order_h")}') if p["edges"] else None,
            h("span", {}, f'{len(p["themes"])} {t("themes_h")}') if p.get("themes") else None)
        rows.append(_row(f'/projects/{p["id"]}', "projects", p["title"], meta, color="var(--accent)"))
    return _list_page(store, title=t("projects"), lead=t("projects_lead"), rows=rows,
                      empty_icon="projects", empty_msg=t("no_projects"), active="projects")


def _persona_row(p: dict, store: Store) -> str:
    pid = p["id"]
    try:
        proj = services.list_active_projects(pid, store=store)
    except Exception:
        proj = []
    loops = len(store.list_threads(pid, "open"))
    meta = fragment(
        _label(t("n_projects", n=len(proj)), "var(--accent)") if proj else None,
        _label(t("n_open", n=loops), "var(--amber)") if loops else None)
    right = fragment(h("span", {"class_": "muted small"}, p["company_context"]["industry"]), meta,
                     raw(_star("persona", pid, p["display_name"], f"/personas/{pid}")))
    return _row(f'/personas/{pid}', _avatar(p, 22), p["display_name"], right, sub=p["role"]["title"])


def register_lists(app) -> None:
    """Library/index routes that aren't project-scoped: the global Prototypes and Concepts lists."""
    from fastapi.responses import HTMLResponse

    @app.get("/prototypes", response_class=HTMLResponse)
    def prototypes_list() -> str:
        store = Store()
        rows = []
        for p in store.list_prototypes():
            ap = _artifact_present(p)
            proj = store.get_research_project(p["project_id"]) if p.get("project_id") else None
            nsess = len(store.list_prototype_sessions(prototype_id=p["id"]))
            right = fragment(
                h("span", {"class_": "muted small"}, proj["title"]) if proj else None,
                h("span", {}, f'{t("sessions")} {nsess}') if nsess else None,
                h("span", {"class_": "muted small"}, p["version"]) if p.get("version") else None,
                raw(_star("prototype", p["id"], p["name"], f'/prototypes/{p["slug"]}')))
            rows.append(_row(f'/prototypes/{p["slug"]}', "prototype", p["name"], right,
                             color=ap["color"], sub=ap["disc"] or ap["label"]))
        return _list_page(store, title=t("prototypes_h"), lead=t("prototypes_lead"), rows=rows,
                          empty_icon="prototype", empty_msg=t("no_prototypes"), active="prototype")

    @app.get("/concepts", response_class=HTMLResponse)
    def concepts_list() -> str:
        store = Store()
        rows = []
        for proj in store.list_research_projects():
            for n in services.list_notes(proj["id"], store=store):
                if (n.get("kind") or "note") != "concept":
                    continue
                right = fragment(h("span", {"class_": "muted small"}, proj["title"]),
                                 raw(_star("concept", n["id"], n.get("title", ""), f'/concepts/{n["id"]}')))
                rows.append(_row(f'/concepts/{n["id"]}', "bulb", n.get("title", ""), right, color="#ea4335"))
        return _list_page(store, title=t("concepts"), lead=t("concepts_lead"), rows=rows,
                          empty_icon="bulb", empty_msg=t("no_concepts"), active="concept")
