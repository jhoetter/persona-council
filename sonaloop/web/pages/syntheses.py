"""Synthesis pages: list + detail (spec/roadmap.md R2)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)


def register_syntheses(app) -> None:
    @app.get("/syntheses", response_class=HTMLResponse)
    def syntheses() -> str:
        store = Store()
        rows = []
        for s in store.list_syntheses():
            done = s.get("status", "done") == "done"
            rows.append(h("a", {"class_": "row", "href": f'/syntheses/{s["id"]}'},
                          h("span", {"class_": "rico", "style": "color:var(--violet)"}, raw(_icon("syntheses"))),
                          h("span", {"class_": "title"}, s["title"]),
                          h("span", {"class_": "right"},
                            _label(t("done") if done else t("running"), "var(--green)" if done else "var(--amber)"),
                            h("span", {}, f'{len(s.get("council_ids", []))} {t("councils")}'),
                            h("span", {}, s["created_at"][:10]),
                            raw(_star("synthesis", s["id"], s["title"], f"/syntheses/{s['id']}")))))
        return _list_page(store, title=t("syntheses"), lead=t("syntheses_lead"), rows=rows,
                          empty_icon="syntheses", empty_msg=t("no_synthesis"), active="syntheses")

    @app.get("/syntheses/{synthesis_id}", response_class=HTMLResponse)
    def synthesis_detail(synthesis_id: str) -> str:
        store = Store()
        syn = store.get_synthesis(synthesis_id)
        if not syn:
            return _layout(t("not_found"), _empty_state(t("synthesis_not_found"), t("runtime_maybe_cleared")), store, active="syntheses")
        short_title = _display_title(syn["title"])             # short form for breadcrumb / tab / favourite only
        crumbs = [(t("projects"), "/projects")]
        proj = services.parent_project_of_synthesis(synthesis_id, store)
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((short_title, None))
        content, toc = _synthesis_html(store, syn)             # content carries its own hero (syn-head, full title)
        return detail_page(
            store, title=short_title, active="projects", crumbs=crumbs,
            hero="", body=raw(content), rail_sections=toc,
            prop_rows=[("check", t("status"), t("done") if syn.get("status", "done") == "done" else t("running")),
                       ("councils", t("councils"), str(len(syn.get("council_ids", [])))),
                       ("dot", t("created"), syn.get("created_at", "")[:10]),
                       ("projects", t("project"), (h("a", {"href": f'/projects/{proj["id"]}'}, proj["title"]) if proj else "—"))],
            rel_study_id=f"synthesis:{synthesis_id}", rel_proj_id=(proj["id"] if proj else None),
            star=("synthesis", synthesis_id, short_title, f"/syntheses/{synthesis_id}"))

