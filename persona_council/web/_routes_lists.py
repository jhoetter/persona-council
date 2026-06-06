"""Index/list-page builders, split out of _routes_pages (spec/component-ssr-architecture.md C5 — keep
route modules small). Each renders rows through the shared _list_page() shell."""
from __future__ import annotations

from .. import services
from ..storage import Store
from ._i18n import t
from ._components import _esc, _icon, _avatar, _label, _star, _list_page, _artifact_present


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
            right = ((f'<span class="muted small">{_esc(proj["title"])}</span>' if proj else "") + (f'<span>{t("sessions")} {nsess}</span>' if nsess else "") + (f'<span class="muted small">{_esc(p["version"])}</span>' if p.get("version") else ""))
            rows.append(f'<a class="row" href="/prototypes/{_esc(p["slug"])}"><span class="rico" style="color:{ap["color"]}">{_icon("prototype")}</span>'
                        f'<span class="title">{_esc(p["name"])}<span class="muted small"> · {_esc(ap["disc"] or ap["label"])}</span></span>'
                        f'<span class="right">{right}{_star("prototype", p["id"], p["name"], f"/prototypes/{p["slug"]}")}</span></a>')
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
                rows.append(f'<a class="row" href="/concepts/{_esc(n["id"])}"><span class="rico" style="color:#ea4335">{_icon("bulb")}</span>'
                            f'<span class="title">{_esc(n.get("title", ""))}</span>'
                            f'<span class="right"><span class="muted small">{_esc(proj["title"])}</span>'
                            f'{_star("concept", n["id"], n.get("title", ""), f"/concepts/{n['id']}")}</span></a>')
        return _list_page(store, title=t("concepts"), lead=t("concepts_lead"), rows=rows,
                          empty_icon="bulb", empty_msg=t("no_concepts"), active="concept")
