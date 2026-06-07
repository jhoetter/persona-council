"""Synthesis pages: list + detail (spec/roadmap.md R2). A synthesis is scoped (spec/unified-synthesis-
report.md): scope=convergence renders the structured view (findings → 2×2); scope=project renders the
report (sections + figures). One detail route + one PDF export serve both."""
from __future__ import annotations

import re

from fastapi import Request
from fastapi.responses import Response

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._report import render_meta_report


def register_syntheses(app) -> None:
    @app.get("/syntheses", response_class=HTMLResponse)
    def syntheses() -> str:
        store = Store()
        rows = []
        for s in store.list_syntheses():
            is_report = s.get("scope") == "project"
            done = s.get("status", "done") == "done"
            scope_pill = (_label(t("meta_report"), "var(--accent)") if is_report
                          else _label(t("done") if done else t("running"), "var(--green)" if done else "var(--amber)"))
            meta_right = (h("span", {}, t("n_sections", n=len(s.get("sections", [])))) if is_report
                          else h("span", {}, f'{len(s.get("council_ids", []))} {t("councils")}'))
            rows.append(h("a", {"class_": "row", "href": f'/syntheses/{s["id"]}'},
                          h("span", {"class_": "rico", "style": "color:var(--violet)"},
                            raw(_icon("report" if is_report else "syntheses"))),
                          h("span", {"class_": "title"}, s["title"]),
                          h("span", {"class_": "right"}, scope_pill, meta_right,
                            h("span", {}, s["created_at"][:10]),
                            raw(_star("synthesis", s["id"], s["title"], f"/syntheses/{s['id']}")))))
        return _list_page(store, title=t("syntheses"), lead=t("syntheses_lead"), rows=rows,
                          empty_icon="syntheses", empty_msg=t("no_synthesis"), active="syntheses")

    @app.get("/syntheses/{synthesis_id}.pdf")
    def synthesis_pdf(synthesis_id: str, request: Request):
        """Proper PDF via headless Chromium — navigate to the live detail page, emulate print, page.pdf().
        Reuses the EXACT page HTML (spec/unified-synthesis-report.md; meta-report Phase 3)."""
        store = Store()
        syn = store.get_synthesis(synthesis_id)
        if not syn:
            return Response(t("not_found"), status_code=404)
        from playwright.sync_api import sync_playwright
        url = str(request.base_url).rstrip("/") + f"/syntheses/{synthesis_id}"
        _hf = "font-size:8px;color:#9aa0a6;width:100%;padding:0 16mm"
        header = h("div", {"style": _hf}, syn.get("title", ""))
        footer = h("div", {"style": _hf + ";text-align:center;padding:0"},
                   h("span", {"class_": "pageNumber"}), " / ", h("span", {"class_": "totalPages"}))
        with sync_playwright() as pw:
            b = pw.chromium.launch()
            pg = b.new_page()
            pg.goto(url, wait_until="networkidle")
            pg.emulate_media(media="print")
            pg.wait_for_timeout(200)
            pdf = pg.pdf(format="A4", print_background=True,
                         margin={"top": "18mm", "bottom": "16mm", "left": "16mm", "right": "16mm"},
                         display_header_footer=True, header_template=header, footer_template=footer)
            b.close()
        fn = (re.sub(r"[^\w\-]+", "-", syn.get("title", "")).strip("-").lower() or "synthesis") + ".pdf"
        return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{fn}"'})

    @app.get("/syntheses/{synthesis_id}", response_class=HTMLResponse)
    def synthesis_detail(synthesis_id: str) -> str:
        store = Store()
        syn = store.get_synthesis(synthesis_id)
        if not syn:
            return _layout(t("not_found"), _empty_state(t("synthesis_not_found"), t("runtime_maybe_cleared"), icon="syntheses"), store, active="syntheses")
        # project-scope synthesis = the report → report-grade renderer + PDF export.
        if syn.get("scope") == "project":
            proj = store.get_research_project(syn.get("project_id")) if syn.get("project_id") else None
            crumbs = ([(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (syn["title"], None)]
                      if proj else [(t("syntheses"), "/syntheses"), (syn["title"], None)])
            body = h("div", {"class_": "page"}, raw(render_meta_report(syn, store)))
            actions = h("a", {"class_": "btn", "href": f"/syntheses/{synthesis_id}.pdf"}, t("export_pdf"))
            return _layout(syn["title"], body, store, crumbs=crumbs, active="syntheses", actions=actions)
        # convergence synthesis = the structured analysis view (findings → 2×2, voices).
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
