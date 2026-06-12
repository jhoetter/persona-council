"""Decision records: the cross-project list page + the shared row renderers.

A decision LIVES on its project page — an outline row in the phase whose gate it decided (UX P2,
spec/ux-contract.md §3.4); the canonical Ref route /decisions/{id} (registered in projects.py)
redirects into that row's anchor. This module owns the decision CARD shared by the global
/decisions index and the decision peek (web/pages/peek.py): evidence chips via render_ref,
rejected alternatives with why-not notes, supersede links in both directions. READ-ONLY like
every page; list rows deep-link into their project's row. The card's `.hyp` CSS is co-located
with its primary owner in hypotheses.py; the status pills live in web/_presence (shared with the
outline chips). /decisions and /decisions/{id} have distinct path shapes, so the list route
never shadows the redirect (registered after projects' routes anyway — see pages/__init__)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .. import ui
from .._presence import decision_status_pill
from .._render import render_ref


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
    # ADR bodies are LONG by design (ranking rationales, shortlist, must-haves) — ui.clamp keeps
    # the record scanning like a row: 5 lines + an expand toggle above the threshold, a plain
    # paragraph below it (no toggle chrome for three lines of text). UX contract C6.
    body = ui.clamp(d.get("decision", ""))
    return h("div", {"class_": "hyp", "id": f'dec-{d["id"]}'},
             h("div", {}, raw(decision_status_pill(status)), " ", title, proj),
             body,
             based, rejected, fragment(*links))


def register_decisions(app) -> None:
    @app.get("/decisions", response_class=HTMLResponse)
    def decisions_list() -> str:
        """Every decision record across all projects — the Library's Decisions tab
        (ux-contract §3.5): one status-pilled row per record, the audit trail of what
        the research changed; the full ADR card lives in the peek and on the project."""
        from .library import library_page
        return library_page("decisions")
