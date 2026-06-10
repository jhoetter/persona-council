"""Decision records: the cross-project list page + the shared row renderers.

A decision LIVES on its project page — the decisions section there (projects.py) renders through
the helpers below, and the canonical Ref route /decisions/{id} (registered in projects.py)
redirects into that anchor. This module owns the rendering shared by the section and the global
/decisions index: the lifecycle pills and the decision card (evidence chips via render_ref,
rejected alternatives with why-not notes, supersede links in both directions). READ-ONLY like
every page; list rows deep-link into their project's section. The card's `.hyp` CSS is
co-located with its primary owner in hypotheses.py. /decisions and /decisions/{id} have distinct
path shapes, so the list route never shadows the redirect (registered after projects' routes
anyway — see pages/__init__)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._render import render_ref

# Decision lifecycle pill colors (proposed → adopted → superseded; labels are i18n keys below).
_DEC_STATUS_COLORS = {"proposed": "var(--accent)", "adopted": "var(--green)",
                      "superseded": "var(--muted)"}


def _dec_status_label(status: str) -> str:
    """Resolved per request so the labels follow the active UI language."""
    labels = {"proposed": t("dec_status_proposed"), "adopted": t("dec_status_adopted"),
              "superseded": t("dec_status_superseded")}
    return labels.get(status, status)


def _decision_row(d: dict, store, by_id: dict, *, title_href: str | None = None,
                  project_title: str | None = None) -> str:
    """One decision: status pill + title, the decision text, evidence chips (render_ref deep-links
    into the source studies), rejected alternatives with their why-not notes, and the supersede
    links in both directions. On the project page the card is the anchor target (plain bold
    title); on the cross-project list `title_href` links the title into that anchor and
    `project_title` names where the decision lives."""
    based = h("p", {"class_": "muted small turn-refs", "style": "margin:4px 0 0"},
              t("rel_based_on"), ": ",
              fragment(*(raw(render_ref(r, store)) for r in d.get("based_on") or [])))
    rejected = fragment(*(
        h("p", {"class_": "muted small turn-refs", "style": "margin:4px 0 0"},
          t("dec_rejected"), ": ", raw(render_ref(r, store)),
          (f' — {r["note"]}' if r.get("note") else ""))
        for r in d.get("rejected") or []))
    def _link(oid: str, label: str) -> str:
        return h("p", {"class_": "muted small", "style": "margin:4px 0 0"}, label, ": ",
                 h("a", {"href": f"#dec-{oid}"}, (by_id.get(oid) or {}).get("title", oid)))

    links = []
    if d.get("superseded_by"):
        links.append(_link(d["superseded_by"], t("dec_superseded_by")))
    if d.get("supersedes"):
        links.append(_link(d["supersedes"], t("dec_supersedes")))
    status = d.get("status", "proposed")
    title = h("b", {}, d.get("title", ""))
    if title_href:
        title = h("a", {"href": title_href}, title)
    proj = (h("span", {"class_": "muted small", "style": "margin-left:8px"}, project_title)
            if project_title else None)
    return h("div", {"class_": "hyp", "id": f'dec-{d["id"]}'},
             h("div", {}, raw(_label(_dec_status_label(status),
                                     _DEC_STATUS_COLORS.get(status, "var(--muted)"))),
               " ", title, proj),
             h("p", {"style": "margin:4px 0 0"}, d.get("decision", "")),
             based, rejected, fragment(*links))


def _decisions_html(project_id: str, store) -> str:
    """The project's decision records, grouped adopted / proposed / superseded — what the research
    led to, on which evidence, rejecting what (ticket decision-record-artifact)."""
    decs = services.list_decisions(project_id, store=store)
    if not decs:
        return ""
    by_id = {d["id"]: d for d in decs}
    groups = []
    for status in ("adopted", "proposed", "superseded"):
        rows = [d for d in decs if d.get("status") == status]
        if not rows:
            continue
        groups.append(h("div", {"class_": "oqp-h", "style": "margin-top:10px"},
                        f'{_dec_status_label(status)} ({len(rows)})'))
        groups += [_decision_row(d, store, by_id) for d in rows]
    return h("div", {"class_": "outlinecard", "id": "decisions", "style": "margin-top:14px"},
             h("h2", {"style": "margin:0 0 6px"}, f'{t("decisions_h")} ({len(decs)})'),
             fragment(*groups))


def register_decisions(app) -> None:
    @app.get("/decisions", response_class=HTMLResponse)
    def decisions_list() -> str:
        """Every decision record across all projects, grouped adopted / proposed / superseded —
        the audit trail of what the research changed."""
        store = Store()
        decs = services.list_decisions(store=store)
        projects = {p["id"]: p["title"] for p in store.list_research_projects()}
        by_id = {d["id"]: d for d in decs}
        rows: list = []
        for status in ("adopted", "proposed", "superseded"):
            group = [d for d in decs if d.get("status") == status]
            if not group:
                continue
            rows.append(h("div", {"class_": "group"}, _dec_status_label(status),
                          h("span", {"class_": "cnt"}, str(len(group)))))
            rows += [_decision_row(d, store, by_id,
                                   title_href=f'/projects/{d["project_id"]}#dec-{d["id"]}',
                                   project_title=projects.get(d["project_id"]))
                     for d in group]
        return _list_page(store, title=t("decisions_h"), lead=t("decisions_lead"), rows=rows,
                          empty_icon="flag", empty_msg=t("no_decisions"), active="decisions",
                          count=len(decs))
