"""The sanctioned presentation-composition layer (spec/ux-contract.md C9 + §3.7).

This module is the ONLY way pages compose presentation: every helper is a thin, 1:1
Python counterpart of a design-system class contract (styles/components.css, vendored
as sonaloop/_components_css.py) and mirrors the React wrapper of the same name in
sonaloop-design/src/components.tsx — so the SSR app and the React surfaces can never
drift. Pages call these helpers (or emit bare `sl-*` classes); they do NOT invent
inline `style=` attributes or new CSS classes — tests/test_ux_contract.py gates both
(ratchet: existing violations may only burn down).

Helpers return Safe html strings via the h()/raw()/fragment() element builder
(web/_html.py), so everything is auto-escaped and composes with the page components.
"""
from __future__ import annotations

import re as _re
from typing import Any, Iterable

from ._html import Safe, h, raw, fragment
from ._i18n import t

# Long authored bodies (ADRs, exec summaries) clamp above this many characters; shorter
# text renders plain — no toggle chrome for three lines of prose (UX contract C6).
CLAMP_THRESHOLD = 420
# Detail pages dose prose at higher thresholds (ux-contract §3.6 / P4): a SECTION of a
# report/synthesis/council detail reads naturally up to ~900 chars and collapses beyond
# (genuinely long authored sections), a council TURN clamps at ~600 so a round of voices
# scans as rows. Rows/peeks keep the tight CLAMP_THRESHOLD.
SECTION_CLAMP = 900
TURN_CLAMP = 600


def scaffold(body: Any, *, head: Any = "", bar: Any = "", cls: str = "") -> Safe:
    """The page layout contract (`sl-scaffold`, ux-contract §3.1): a column filling its
    container with a fixed `__head` (breadcrumb/title/actions) and optional `__bar`
    (filters, tabs), and `__body` — THE one scroll container on the page. Children of
    the body must never bring their own overflow/flex:1 (two nested scroll traps = bug;
    see the P0 outline-squeeze). Mirrors React <Scaffold>."""
    return h("div", {"class_": f"sl-scaffold {cls}".strip()},
             h("div", {"class_": "sl-scaffold__head"}, head) if head else None,
             h("div", {"class_": "sl-scaffold__bar"}, bar) if bar else None,
             h("div", {"class_": "sl-scaffold__body"}, body))


def section(title: Any, *content: Any, id: str | None = None) -> Safe:
    """A quiet, content-sized section (`sl-section`, ux-contract §3.7) for below-content
    groups (decision records, assets, open questions): the page's centered 900px
    measure, plain document flow — never flexed, never internally scrolled; anchor
    arrivals clear sticky phase headers via scroll-margin. Group labels inside a
    section use the `sl-section__h` idiom (the old app-local `.oqp-h`). Mirrors
    React <Section>."""
    return h("section", {"class_": "sl-section", "id": id},
             h("h2", {}, title) if title is not None else None,
             fragment(*content))


def clamp(text: Any, *, threshold: int = CLAMP_THRESHOLD, id: str | None = None) -> Safe:
    """Dosed long-form text (`sl-clamp`, ux-contract C6): authored prose at/below the
    threshold renders plain; longer text clamps to 5 lines with an accent "more/less"
    toggle that reveals it in place. Accepts plain text (escaped, a <p>) or pre-rendered
    Safe html — e.g. a _md() body — which keeps block children legal in a <div> and
    measures the threshold on the VISIBLE characters (tags stripped). The localized
    labels ride data-more/data-less so the tiny inline handler stays i18n-clean.
    Mirrors React <Clamp> (which holds the open state in React instead)."""
    is_html = isinstance(text, Safe)
    content: Any = text if is_html else ("" if text is None else str(text))
    visible = _re.sub(r"<[^>]+>", "", content) if is_html else content
    tag = "div" if is_html else "p"
    if len(visible) <= threshold:
        return h(tag, {"id": id}, content)
    return fragment(
        h(tag, {"class_": "sl-clamp", "id": id}, content),
        h("button", {"class_": "sl-clamp-toggle", "type": "button",
                     "data-more": t("more"), "data-less": t("less"),
                     "onclick": "var p=this.previousElementSibling;p.classList.toggle('open');"
                                "this.textContent=p.classList.contains('open')?this.dataset.less:this.dataset.more;"},
          t("more")))


def entity_row(title: Any, *, href: str | None = None, visual: Any = "", badges: Iterable[Any] = (),
               meta: Iterable[Any] = (), desc: Any = "", id: str | None = None,
               peek_url: str | None = None) -> Safe:
    """THE row atom (`sl-entity`, ux-contract §3.2 / C1): leading `visual` (icon/avatar,
    pass Safe html) · one-line ellipsized `title` with its status `badges` · optional
    muted `desc` line · right-aligned `meta` (counts, date, persona chips) in the
    trailing slot. Identical anatomy in the outline, the library, and search.

    Implementation over the vendored `.sl-entity` contract (visual / content(title,
    desc) / trailing): badges lead the trailing slot so a long, ellipsized title can
    never clip a status pill (the title span owns the overflow). `href` makes the row
    a link (`--button` hover affordance); `peek_url` additionally opens the target in
    the shared drawer peek (see peek()). The per-kind visual/badge/meta mapping lives
    in primitive_row (the §3.2 table)."""
    badges = list(badges)
    meta = list(meta)
    content = h("div", {"class_": "sl-entity__content"},
                h("div", {"class_": "sl-entity__title"}, title),
                h("div", {"class_": "sl-entity__desc"}, desc) if desc else None)
    trailing = badges + meta
    inner = fragment(
        h("span", {"class_": "sl-entity__visual"}, visual) if visual else None,
        content,
        h("span", {"class_": "sl-entity__trailing"}, fragment(*trailing)) if trailing else None)
    if href:
        return h("a", {"class_": "sl-entity sl-entity--button", "id": id, "href": href,
                       "data-drawer": peek_url, "data-drawer-title": None}, inner)
    return h("div", {"class_": "sl-entity", "id": id}, inner)


def primitive_row(kind: str, record: dict, store: Any = None, *, href: str | None = None,
                  peek_url: str | None = None, desc: Any = None) -> Safe:
    """THE per-kind row vocabulary (ux-contract §3.2 — one table, used everywhere): maps a
    primitive's record onto the entity_row anatomy (leading visual · title · status badges ·
    right meta). Library lists, search and the peek headers render through this; the dense
    project outline renders the SAME vocabulary through its olrow variant (_graph_outline's
    kind icons + the _outline_chips registry — both read this table).

    | kind            | visual                | badges                  | meta right            |
    | council         | councils icon         | mode/round tag          | participants · date   |
    | report/synthesis| report icon           | `Report`                | sources count · date  |
    | decision        | flag                  | status pill             | evidence count · date |
    | survey          | plan icon             | lifecycle pill          | n questions · n resp. |
    | session         | activity icon         | verified check          | persona · steps · date|
    | prototype       | prototype icon        | fidelity tag            | sessions count        |
    | asset           | thumb / file icon     | kind + direction pill   | size · date           |
    | note / hypothesis| panel / target icon  | — / status pill         | date                  |

    Late imports keep this module's import graph a leaf (pages → ui, never the reverse). The
    per-kind dispatch + icon map use dict() kwargs / `in (…)` membership — the kind-vocabulary
    grep gates ban kind-literal dict heads and `== "<kind>"` comparisons in web/*.py.

    `desc` overrides the muted description line — cross-project lists (the Library) pass
    the owning project's title here; in a project-scoped context the per-kind default
    stands (e.g. the session's walked subject)."""
    from .. import presentation as _pres
    from ._components import _avatar, _display_title, _icon, _label
    from ._presence import (asset_direction, decision_status_pill, hypothesis_status_pill,
                            survey_status_pill)
    rec = record or {}
    date = _fmt_day(rec.get("created_at") or "")
    icons = dict(council="councils", synthesis="syntheses", report="syntheses", decision="flag",
                 survey="plan", session="activity", prototype="prototype", note="panel",
                 hypothesis="target", open_question="help")
    visual: Any = raw(_icon(icons.get(kind, "square")))
    title: Any = rec.get("title") or rec.get("text") or rec.get("name") or rec.get("id", "")
    kind_desc: Any = ""
    badges: list[Any] = []
    meta: list[Any] = [date] if date else []
    if kind in ("council",):
        title = _display_title(rec.get("prompt") or rec.get("title") or "")
        mode = rec.get("mode") or ""
        if mode in ("discovery", "evaluation", "decision"):
            badges.append(raw(_label(t("council_mode_" + mode), "var(--blue)")))
        pids = list(dict.fromkeys(s.get("persona_id", "") for s in rec.get("statements") or []))
        if store is not None and pids:
            avatars = fragment(*(raw(_avatar(store.get_persona(p) or {}, 18)) for p in pids[:4] if p))
            meta.insert(0, h("span", {"class_": "ol-crew"}, avatars))
    elif kind in ("synthesis", "report"):
        badges.append(raw(_label(t("synthesis_kind"), "var(--violet)")))
        if rec.get("sections") is not None:
            meta.insert(0, raw(_label(t("n_sections", n=len(rec.get("sections") or [])))))
        else:
            meta.insert(0, raw(_label(t("chip_sources_n", n=len(rec.get("council_ids") or [])))))
    elif kind == "decision":
        badges.append(raw(decision_status_pill(rec.get("status", "proposed"))))
        meta.insert(0, raw(_label(t("chip_evidence_n", n=len(rec.get("based_on") or [])))))
    elif kind == "survey":
        badges.append(raw(survey_status_pill(rec.get("status", "draft"))))
        meta = [raw(_label(t("n_questions", n=len(rec.get("questions") or [])))),
                raw(_label(t("n_responses", n=int(rec.get("response_count") or 0))))]
    elif kind == "session":
        persona = (store.get_persona(rec.get("persona_id", "")) or {}) if store is not None else {}
        title = persona.get("display_name") or rec.get("persona_id", "")
        # The subject walked (prototype/flow label): in the outline a session nests under its
        # subject row, but in a flat list (Library) the persona name alone says nothing.
        kind_desc = (rec.get("subject") or {}).get("label", "")
        if rec.get("grounded_verified"):
            badges.append(raw(_label(t("grounded_yes"), "var(--green)")))
        meta = [raw(_avatar(persona, 18)) if persona else None,
                raw(_label(t("chip_steps_n", n=len(rec.get("steps") or []))))] + meta
    elif kind == "prototype":
        if rec.get("fidelity"):
            badges.append(raw(_label(_pres.present(rec["fidelity"])["short"], "#00897b")))
        meta = [raw(_label(t("sessions_n", n=int(rec.get("n_sessions") or 0))))]
    elif kind == "asset":
        if rec.get("kind") in ("image", "screenshot") and rec.get("url"):
            visual = h("img", {"class_": "sl-avatar", "src": rec["url"], "alt": "", "loading": "lazy"})
        else:
            visual = raw(_icon("download" if asset_direction(rec) == "out" else "file"))
        title = rec.get("title") or rec.get("filename", "")
        badges.append(raw(_label(t("asset_kind_" + (rec.get("kind") or "file")))))
        badges.append(raw(_label(t("asset_dir_out"), "var(--green)") if asset_direction(rec) == "out"
                          else _label(t("asset_dir_in"))))
        size_kb = f'{max(1, int(rec.get("bytes") or 0) // 1024)} KB'   # a unit, not a UI string
        meta.insert(0, size_kb)
    elif kind == "hypothesis":
        badges.append(raw(hypothesis_status_pill(rec.get("status", "open"))))
    return entity_row(title, href=href, visual=visual, badges=badges,
                      desc=desc if desc is not None else kind_desc,
                      meta=[m for m in meta if m], peek_url=peek_url)


def _fmt_day(iso: str) -> str:
    """'11 Jun' — the same compact day the outline rows show (_graph_outline._fmt_ts), so a
    primitive carries ONE date format in every surface (library, peek, outline — C5/C10).
    Falls back to the raw YYYY-MM-DD prefix for non-ISO input."""
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return f"{dt.day} {dt:%b}"
    except Exception:
        return iso[:10]


def peek(url: str, trigger: Any, *, title: str = "") -> Safe:
    """Peek before page (`sl-drawer`, ux-contract C2 / §3.3): wrap `trigger` so a click
    opens `url` in the shared right slide-over drawer (the persistent `#drawer` root +
    DRAWER_JS wiring in web/_components.py fetch the page and re-execute its scripts);
    the plain href keeps the deep link, so peeks are navigation sugar, never the only
    address (middle-click / Esc / outside-click behave as expected).

    The per-kind peek BODIES (decision essence, survey stance strip, session verdict —
    §3.3) are served by the /peek/{kind}/{id} fragments (web/pages/peek.py), which
    compose primitive_row()/clamp()/section() server-side behind these same URLs."""
    return h("a", {"href": url, "data-drawer": url, "data-drawer-title": title or None}, trigger)


def tabs(items: Iterable[dict[str, Any]], active: str) -> Safe:
    """Underline tabs (`sl-tabs`) for in-page surface switching (the Library browser,
    detail bodies). `items`: dicts with `key`, `label`, `href` (+ optional `icon`,
    Safe html); `active` selects by key. Mirrors React <Tabs variant="underline">."""
    return h("div", {"class_": "sl-tabs", "role": "tablist"},
             fragment(*(h("a", {"class_": "sl-tab" + (" is-active" if it["key"] == active else ""),
                                "href": it["href"], "role": "tab",
                                "aria-selected": "true" if it["key"] == active else "false"},
                          raw(it["icon"]) if it.get("icon") else None, it["label"])
                        for it in items)))
