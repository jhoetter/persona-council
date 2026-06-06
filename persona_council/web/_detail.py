"""Detail-page building blocks: the Linear-style Relations + Properties panels.

Split out of _routes_pages.py to keep it under the LOC bar. Pure render helpers."""
from __future__ import annotations

from .. import services
from ._i18n import t
from ._components import _esc, _icon  # noqa: F401  (_esc kept for any callers)
from ._html import h, raw, fragment


def _relations_html(store, study_id: str, proj_id: str | None,
                    extra_in: list | None = None, extra_out: list | None = None, aside: bool = False) -> str:
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
        rows = fragment(*(
            h("a", {"class_": "relrow", "href": n.get("href", "")},
              h("span", {"class_": "ol-dot", "style": f"background:{n.get('color', '#9aa0a6')}"}),
              h("span", {"class_": "relt"}, n.get("title", "")),
              h("span", {"class_": "muted small"}, n.get("kind_label", n.get("kind", ""))))
            for n in ns))
        return h("div", {"class_": "relgrp"}, h("div", {"class_": "rellbl"}, label), rows)

    blocks = fragment(grp(t("rel_based_on"), incoming), grp(t("rel_feeds_into"), outgoing))
    if not blocks:
        return ""
    if aside:                                                  # plain uppercase header, uniform with Properties
        return fragment(h("h4", {"id": "sec-relations"}, t("relations")), blocks)
    return h("div", {"class_": "card relcard", "id": "sec-relations"},
             h("div", {"class_": "relh"}, raw(_icon("link")), " ", t("relations")), blocks)


# Reaction keys that are meta/internal (shown via the badge/header), not user-facing content.
_SESSION_SKIP = {"persona", "fidelity", "version", "observed_state_refs", "self_authored", "session_id"}


def _session_card(store, sess: dict) -> str:
    """One prototype/persona session, rendered generically. The reaction schema is agent-authored
    and varies widely (9+ shapes across the corpus), so we resolve the persona's display name and
    render every substantive field — never cherry-pick fixed keys (which silently hides content)."""
    r = sess.get("reaction") if isinstance(sess.get("reaction"), dict) else {}
    pid = sess.get("persona_id", "") or ""
    name = r.get("persona") or ""
    if not name and pid:                                   # data is matched — resolve slug/id → name
        p = store.get_persona(pid)
        name = (p or {}).get("display_name") or pid
    gv = fragment(raw(_icon("check") if sess.get("grounded_verified") else _icon("circle")), " ",
                  t("grounded_yes") if sess.get("grounded_verified") else t("grounded_no"))
    fields = []
    for k, v in r.items():
        if k in _SESSION_SKIP or v in (None, "", [], {}):
            continue
        if isinstance(v, bool):
            val = raw(_icon("check") if v else _icon("circle"))
        elif isinstance(v, list):
            val = h("ul", {"class_": "small", "style": "margin:2px 0 0 16px"}, [h("li", {}, str(x)) for x in v])
        else:
            val = h("div", {"class_": "small"}, str(v))
        label = k.replace("_", " ").capitalize()
        fields.append(h("div", {"style": "margin:7px 0"},
                        h("div", {"class_": "muted small", "style": "text-transform:uppercase;letter-spacing:.04em"}, label),
                        val))
    inner = fragment(*fields) if fields else h("div", {"class_": "muted small"}, "—")
    return h("div", {"class_": "strow"}, h("b", {}, name or pid or "—"), " ",
             h("span", {"class_": "muted small"}, gv), h("div", {"style": "margin-top:4px"}, inner))


def _properties_html(rows, aside: bool = False) -> str:
    """Linear-style Properties panel: an icon + label + value per row (skips empty values).
    aside=True renders a bare section (h4 + rows) to sit inside the _doc right rail."""
    proprows = [h("div", {"class_": "prop"},
                  h("span", {"class_": "prop-k"}, raw(_icon(ic)), lbl),
                  h("span", {"class_": "prop-v"}, val))                # text auto-escaped; h-built links (Safe) kept
                for ic, lbl, val in rows if val not in (None, "", "—")]
    if not proprows:
        return ""
    inner = fragment(*proprows)
    if aside:
        return fragment(h("h4", {"id": "sec-properties"}, t("properties")), inner)
    return h("div", {"class_": "card propcard", "id": "sec-properties"},
             h("div", {"class_": "relh"}, t("properties")), inner)
