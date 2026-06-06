"""Detail-page building blocks: the shared detail_page() shell + the Linear-style Relations / Properties
panels (spec/design-system.md). Every artifact detail page (council, synthesis, concept/note, section,
prototype) is assembled by detail_page(), so the structure — hero, content column, Properties→Relations
aside, section minimap, topbar star — is identical by construction instead of duplicated per route."""
from __future__ import annotations

from .. import services
from ._i18n import t
from ._components import _esc, _icon, _hero, _doc, _layout, _star, _prose, _avatar, _label  # noqa: F401
from ._rail import _page_rail
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
_SESSION_SKIP = {"persona", "fidelity", "version", "observed_state_refs", "self_authored", "session_id",
                 "grounded_verified", "grounded"}   # grounded shows once as the header badge (session is the source)


def _session_card(store, sess: dict) -> str:
    """One prototype/persona session — rendered as the SAME statement card as a council voice (avatar +
    name + grounded badge + meta), so sessions and councils read as one product. The reaction schema is
    agent-authored and varies (9+ shapes), so we render every substantive field generically through the
    shared _prose() renderer (Markdown + citations) — never cherry-pick fixed keys, never raw text."""
    r = sess.get("reaction") if isinstance(sess.get("reaction"), dict) else {}
    pid = sess.get("persona_id", "") or ""
    p = store.get_persona(pid) if pid else None
    name = r.get("persona") or (p or {}).get("display_name") or pid or "—"
    grounded = bool(sess.get("grounded_verified"))         # SINGLE source of truth (the session, not the reaction)
    badge = _label(t("grounded_yes") if grounded else t("grounded_no"), "var(--green)" if grounded else "var(--muted)")
    meta = " · ".join(x for x in [r.get("fidelity"), r.get("version")] if x)
    fields = []
    for k, v in r.items():
        if k in _SESSION_SKIP or v in (None, "", [], {}):  # _SESSION_SKIP now also drops the redundant grounded_verified
            continue
        if isinstance(v, bool):
            val = raw(_icon("check") if v else _icon("circle"))
        elif isinstance(v, list):
            val = h("ul", {"class_": "es-prose sm", "style": "margin:2px 0 0 18px"},
                    [h("li", {}, raw(_prose(x))) for x in v])
        else:
            val = h("div", {"class_": "es-prose sm"}, raw(_prose(v)))
        fields.append(h("div", {"class_": "sfield"}, h("div", {"class_": "eyebrow"}, k.replace("_", " ")), val))
    head = fragment(
        h("div", {"class_": "turn-who"}, (_avatar(p, 26) if p else None), h("b", {}, name), " ", badge),
        h("div", {"class_": "muted small turn-ctx"}, meta) if meta else None)
    body = fragment(*fields) if fields else h("div", {"class_": "muted small"}, "—")
    return h("div", {"class_": "turn"}, h("div", {"class_": "hd"}, head), body)


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


def detail_page(store, *, title: str, active: str, crumbs: list, body,
                hero=None, icon: str | None = None, sub=None, hid: str | None = None,
                prop_rows: list | None = None,
                rel_study_id: str | None = None, rel_proj_id: str | None = None,
                rel_extra_in: list | None = None, rel_extra_out: list | None = None,
                rail_sections: list | None = None, star: tuple | None = None) -> str:
    """The ONE detail-page shell every artifact page extends — consistency by construction.

    Assembles: hero · content column (`body`) · Properties→Relations aside (always that order) · the
    section minimap (`rail_sections` + auto Properties/Relations anchors) · a topbar favourite star.

    - `hero`: a pre-built hero (Safe) — e.g. the synthesis syn-head, or "" to omit. If None, the
      component builds `_hero(title, icon=, sub=, hid=)`.
    - `body`: the content after the hero (Safe).
    - `prop_rows`: `[(icon, label, value), …]` for Properties (empty values are skipped).
    - `rel_study_id`/`rel_proj_id`/`rel_extra_*`: build the Relations panel from the project graph.
    - `star`: `(kind, ident, label, href)` for the topbar favourite.
    """
    hero_html = hero if hero is not None else _hero(title, icon=icon, sub=sub, hid=hid)
    main = fragment(raw(hero_html), body)
    props = _properties_html(prop_rows, aside=True) if prop_rows else ""
    rel = ""
    if rel_study_id:
        rel = _relations_html(store, rel_study_id, rel_proj_id, extra_in=rel_extra_in,
                              extra_out=rel_extra_out, aside=True)
    rail = list(rail_sections or [])
    if props:
        rail.append(("sec-properties", t("properties")))
    if rel:
        rail.append(("sec-relations", t("relations")))
    page = _doc(main, rail=raw(props) + raw(rel)) + _page_rail(rail)
    actions = raw(_star(*star)) if star else ""
    return _layout(title, page, store, crumbs=crumbs, active=active, actions=actions)
