"""Report pages: list + detail (spec/roadmap.md R2). A report IS a synthesis — one concept, short or
exhaustive. Internally scope=convergence renders the structured view (findings → 2×2) and
scope=project the narrative sections + figures; one detail route serves both. The web is READ-ONLY:
PDF / PPTX export is an MCP tool (export_synthesis) + the CLI, not a UI action."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._report import render_report


def register_syntheses(app) -> None:
    @app.get("/syntheses", response_class=HTMLResponse)
    def syntheses() -> str:
        store = Store()
        rows = []
        for s in store.list_syntheses():
            # ONE concept — a Report. It can be short or exhaustive; that's just block count, not a type.
            done = s.get("status", "done") == "done"
            status_pill = _label(t("done") if done else t("running"),
                                 "var(--green)" if done else "var(--amber)")
            n_sec = len(s.get("sections", []))
            blocks = (t("n_sections", n=n_sec) if n_sec
                      else f'{len(s.get("council_ids", []))} {t("councils")}')
            rows.append(h("a", {"class_": "row", "href": f'/syntheses/{s["id"]}'},
                          h("span", {"class_": "rico", "style": "color:var(--violet)"},
                            raw(_icon("report"))),
                          h("span", {"class_": "title"}, s["title"]),
                          h("span", {"class_": "right"}, status_pill, h("span", {}, blocks),
                            h("span", {}, s["created_at"][:10]),
                            raw(_star("synthesis", s["id"], s["title"], f"/syntheses/{s['id']}")))))
        return _list_page(store, title=t("syntheses"), lead=t("syntheses_lead"), rows=rows,
                          empty_icon="syntheses", empty_msg=t("no_synthesis"), active="syntheses")

    @app.get("/syntheses/{synthesis_id}", response_class=HTMLResponse)
    def synthesis_detail(synthesis_id: str) -> str:
        store = Store()
        syn = store.get_synthesis(synthesis_id)
        if not syn:
            return _layout(t("not_found"), _empty_state(t("synthesis_not_found"), t("runtime_maybe_cleared"), icon="syntheses"), store, active="syntheses")
        # ONE renderer for every scope (spec/unified-synthesis-report.md §3): the report shell — a
        # convergence synthesis shows its structured analysis (findings → 2×2, voices), a project report
        # its narrative sections; both report-grade + PDF-exportable.
        is_project = syn.get("scope") == "project"
        proj = (store.get_research_project(syn.get("project_id")) if (is_project and syn.get("project_id"))
                else services.parent_project_of_synthesis(synthesis_id, store))
        short_title = _display_title(syn["title"])
        crumbs = [(t("projects"), "/projects")]
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((short_title, None))
        body = h("div", {"class_": "page"}, raw(render_report(syn, store)))
        actions = raw(_star("synthesis", synthesis_id, short_title, f"/syntheses/{synthesis_id}"))
        return _layout(short_title, body, store, crumbs=crumbs, active="syntheses", actions=actions)
