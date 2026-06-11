"""Report pages: list + detail (spec/roadmap.md R2). A report IS a synthesis — one concept, short or
exhaustive. Internally scope=convergence renders the structured view (findings → 2×2) and
scope=project the narrative sections + figures; one detail route serves both. The web is READ-ONLY:
PDF / PPTX export is an MCP tool (export_synthesis) + the CLI, not a UI action."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._keymap import sibling_attrs, sibling_urls
from .._render import render_ref
from .._report import render_report


def _informed_decisions_html(synthesis_id: str, store) -> str:
    """The reverse edge of a decision's based_on/rejected refs: the decisions THIS synthesis
    informed, as chips deep-linking into the project's decisions section (ticket
    decision-record-artifact). Empty when nothing cites the synthesis."""
    informed = [d for d in store.list_decisions()
                if any(r.get("kind") == "synthesis" and r.get("id") == synthesis_id
                       for r in (d.get("based_on") or []) + (d.get("rejected") or []))]
    if not informed:
        return ""
    chips = fragment(*(raw(render_ref({"kind": "decision", "id": d["id"]}, store))
                       for d in informed))
    return h("p", {"class_": "muted small turn-refs", "style": "margin:14px 0 0"},
             t("dec_informed_h"), ": ", chips)


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
        from .._forms import danger_zone, delete_button_form
        body = h("div", {"class_": "page"}, raw(render_report(syn, store)),
                 raw(_informed_decisions_html(synthesis_id, store)),
                 # server-provided prev/next sibling URLs for the keymap's [ / ] bindings
                 raw(sibling_attrs(*sibling_urls(
                     [f'/syntheses/{x["id"]}' for x in store.list_syntheses()],
                     f'/syntheses/{synthesis_id}'))),
                 # delete-only (no content editing): report prose is authored/generated
                 raw(danger_zone(raw(delete_button_form(f'/syntheses/{synthesis_id}/delete',
                                                        t("delete_synthesis"))))))
        actions = raw(_star("synthesis", synthesis_id, short_title, f"/syntheses/{synthesis_id}"))
        return _layout(short_title, body, store, crumbs=crumbs, active="syntheses", actions=actions)
