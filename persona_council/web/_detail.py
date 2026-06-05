"""Detail-page building blocks: the Linear-style Relations + Properties panels.

Split out of _routes_pages.py to keep it under the LOC bar. Pure render helpers."""
from __future__ import annotations

from .. import services
from ._i18n import t
from ._components import _esc, _icon


def _relations_html(store, study_id: str, proj_id: str | None,
                    extra_in: list | None = None, extra_out: list | None = None) -> str:
    """Linear-style RELATIONS block for a detail page (progressive disclosure: precise links live HERE,
    not in the list). Built from the project graph's real plan-evidence edges — what this was BASED ON
    (incoming) and what it FEEDS INTO (outgoing) — plus any caller-supplied extra links (e.g. a prototype's
    concept). Returns "" when there's nothing to show."""
    incoming, outgoing = list(extra_in or []), list(extra_out or [])
    if proj_id:
        try:
            g = services.get_project_graph(proj_id, store=store)
        except Exception:
            g = None
        if g:
            nmap = {n["study_id"]: n for n in g["nodes"]}
            for e in g.get("edges", []):
                if e.get("to_study") == study_id and e.get("from_study") in nmap:
                    incoming.append(nmap[e["from_study"]])
                elif e.get("from_study") == study_id and e.get("to_study") in nmap:
                    outgoing.append(nmap[e["to_study"]])
            cur = nmap.get(study_id)
            if cur and cur.get("prototype_id"):               # concept → its prototype (not a graph edge)
                pr = next((p for p in g.get("prototypes", []) if p["id"] == cur["prototype_id"]), None)
                if pr:
                    outgoing.append({"href": f'/prototypes/{pr["slug"]}', "title": pr["name"],
                                     "color": "#00897b", "kind_label": t("prototypes_h")})

    def grp(label, ns):
        if not ns:
            return ""
        rows = "".join(
            f'<a class="relrow" href="{_esc(n.get("href", ""))}">'
            f'<span class="ol-dot" style="background:{n.get("color", "#9aa0a6")}"></span>'
            f'<span class="relt">{_esc(n.get("title", ""))}</span>'
            f'<span class="muted small">{_esc(n.get("kind_label", n.get("kind", "")))}</span></a>'
            for n in ns)
        return f'<div class="relgrp"><div class="rellbl">{_esc(label)}</div>{rows}</div>'

    blocks = grp(t("rel_based_on"), incoming) + grp(t("rel_feeds_into"), outgoing)
    return (f'<div class="card relcard" id="sec-relations"><div class="relh">{_icon("link")} {t("relations")}</div>{blocks}</div>'
            if blocks else "")


def _properties_html(rows) -> str:
    """Linear-style Properties panel: an icon + label + value per row (skips empty values)."""
    inner = "".join(
        f'<div class="prop"><span class="prop-k">{_icon(ic)}{_esc(lbl)}</span>'
        f'<span class="prop-v">{val}</span></div>'
        for ic, lbl, val in rows if val not in (None, "", "—"))
    return f'<div class="card propcard" id="sec-properties"><div class="relh">{t("properties")}</div>{inner}</div>' if inner else ""
