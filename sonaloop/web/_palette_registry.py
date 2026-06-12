"""Cmd+K coverage registry — ONE source of truth for what the palette can reach
(ticket cmdk-registry-driven-coverage).

Two enumerations, consumed by BOTH /api/search and the palette's static commands, and
guarded by the canary (tests/test_palette_coverage.py — the "palette fell behind" gate,
the house pattern of the presence contract / i18n parity):

  - SEARCH_SOURCES: every searchable entity type — its localized group label, icon,
    palette dot color, the detail-route prefix its results link to, and a rows(store)
    reader yielding (title, subtitle, url). /api/search iterates THIS; the palette's
    group labels/icons/order are generated from it. Adding an entity type here is the
    whole job — search, grouping and styling follow.
  - nav_commands(): the palette's jump commands, derived from the NAV REGISTRY
    (web/_ext.nav_model — core seeds + extension items, so a downstream package's nav
    entry becomes a palette command automatically), plus the chrome surfaces that have
    no route of their own (the ? cheat sheet, the settings popover — '#'-href commands
    the chrome JS handles).

The explicit, reasoned opt-outs the canary honors — silence is never an excuse:

  - NON_SEARCHABLE_ROUTES: detail routes (/{prefix}/{id}) that are deliberately not
    entity search targets, each with the reason.
  - KIND_SEARCH: every presence-contract kind (web/_presence.REGISTRY) mapped to its
    search source — or to NotSearchable(reason) when it has no detail route to land on.

The entity kinds deliberately REUSE the presence contract's inventory rather than
inventing a second registry: _presence.REGISTRY stays the list of what exists,
KIND_SEARCH only declares how each kind reaches the palette."""
from __future__ import annotations

from typing import Any, Callable, Iterator

from ..storage import Store
from ._i18n import t

Row = tuple[str, str, str]   # (title, subtitle, url)


class SearchSource:
    """One searchable entity type. `label` is a lambda (resolves per request — i18n);
    `rows(store)` yields (title, subtitle, url); `url_prefix` is the detail-route
    prefix the canary maps routes onto."""

    def __init__(self, label: Callable[[], str], icon: str, color: str,
                 url_prefix: str, rows: Callable[[Store], Iterator[Row]]):
        self.label, self.icon, self.color = label, icon, color
        self.url_prefix, self.rows = url_prefix, rows


class NotSearchable:
    """Explicit 'this kind has no palette search target' declaration, with the reason
    (where its signal lives instead)."""

    def __init__(self, reason: str):
        self.reason = reason


# ------------------------------------------------------------------ the row readers

def _project_rows(store: Store) -> Iterator[Row]:
    for p in store.list_research_projects():
        yield p.get("title", ""), (p.get("goal", "") or "")[:90], f'/projects/{p["id"]}'


def _persona_rows(store: Store) -> Iterator[Row]:
    for p in store.list_personas():
        role = p.get("role")
        role_t = role.get("title", "") if isinstance(role, dict) else (role or "")
        yield p.get("display_name", ""), role_t, f'/personas/{p["id"]}'


def _council_rows(store: Store) -> Iterator[Row]:
    for c in store.list_council_sessions():
        yield c.get("prompt", ""), "", f'/councils/{c["id"]}'


def _synthesis_rows(store: Store) -> Iterator[Row]:
    for sy in store.list_syntheses():
        yield sy.get("title", ""), "", f'/syntheses/{sy["id"]}'


def _prototype_rows(store: Store) -> Iterator[Row]:
    for pr in store.list_prototypes():
        yield pr.get("name", ""), pr.get("version", "") or "", f'/prototypes/{pr["slug"]}'


def _section_rows(store: Store) -> Iterator[Row]:
    from .. import services
    for proj in store.list_research_projects():
        for sec in services.list_sections(proj["id"], store=store):
            yield sec.get("title", ""), proj.get("title", ""), f'/sections/{sec["id"]}'


def _note_rows(store: Store) -> Iterator[Row]:
    # ONE note entity — observations, concepts AND idea notes (kind discriminators on
    # the note primitive), so /notes/{id} ideas are searchable without a second source.
    from .. import services
    for proj in store.list_research_projects():
        for nt in services.list_notes(proj["id"], store=store):
            yield nt.get("title", ""), proj.get("title", ""), f'/notes/{nt["id"]}'


def _session_rows(store: Store) -> Iterator[Row]:
    for s in store.list_usability_sessions():
        subj = s.get("subject") or {}
        yield (subj.get("label") or s.get("id", "")), (s.get("date") or "")[:10], f'/sessions/{s["id"]}'


def _hypothesis_rows(store: Store) -> Iterator[Row]:
    for hx in store.list_hypotheses():
        yield hx.get("text", ""), hx.get("status", "") or "", f'/hypotheses/{hx["id"]}'


def _decision_rows(store: Store) -> Iterator[Row]:
    for d in store.list_decisions():
        yield d.get("title", ""), d.get("status", "") or "", f'/decisions/{d["id"]}'


def _survey_rows(store: Store) -> Iterator[Row]:
    for sv in store.list_surveys():
        yield sv.get("title", ""), sv.get("status", "") or "", f'/surveys/{sv["id"]}'


def _asset_rows(store: Store) -> Iterator[Row]:
    # Assets ride the project record (no global list read) — the same scan the /assets/{id}
    # route resolves through (web/pages/assets.find_asset).
    for proj in store.list_research_projects():
        for a in proj.get("assets") or []:
            yield (a.get("title") or a.get("filename", "")), proj.get("title", ""), f'/assets/{a["id"]}'


# ------------------------------------------------- the searchable entity types (ordered)

SEARCH_SOURCES: dict[str, SearchSource] = {
    "project": SearchSource(lambda: t("projects"), "projects", "#7a5ed1", "/projects", _project_rows),
    "persona": SearchSource(lambda: t("personas"), "personas", "#3d7fc4", "/personas", _persona_rows),
    "council": SearchSource(lambda: t("councils"), "councils", "var(--accent)", "/councils", _council_rows),
    "synthesis": SearchSource(lambda: t("syntheses"), "syntheses", "#9a8cff", "/syntheses", _synthesis_rows),
    "prototype": SearchSource(lambda: t("prototypes_h"), "prototype", "#00897b", "/prototypes", _prototype_rows),
    "session": SearchSource(lambda: t("sessions"), "activity", "#4a7d7d", "/sessions", _session_rows),
    "survey": SearchSource(lambda: t("surveys_h"), "clipboard", "#00798c", "/surveys", _survey_rows),
    "hypothesis": SearchSource(lambda: t("hypotheses_h"), "target", "#c0760a", "/hypotheses", _hypothesis_rows),
    "decision": SearchSource(lambda: t("decisions_h"), "flag", "#d81b60", "/decisions", _decision_rows),
    "section": SearchSource(lambda: t("sections"), "squareGrid", "#3d9b6b", "/sections", _section_rows),
    "note": SearchSource(lambda: t("notes_h"), "panel", "#b87a25", "/notes", _note_rows),
    "asset": SearchSource(lambda: t("assets_h"), "file", "#8a6d3b", "/assets", _asset_rows),
}


def search_rows(q: str, store: Store | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """The /api/search read: title-substring match across every SEARCH_SOURCES type.
    A broken source is skipped (fail-soft) — the canary, not the request, polices gaps."""
    ql = (q or "").strip().lower()
    if not ql:
        return []
    store = store or Store()
    out: list[dict[str, Any]] = []
    for typ, src in SEARCH_SOURCES.items():
        try:
            rows = list(src.rows(store))
        except Exception:  # noqa: BLE001
            continue
        for title, subtitle, url in rows:
            if title and ql in title.lower():
                out.append({"type": typ, "title": title,
                            "subtitle": subtitle if isinstance(subtitle, str) else "", "url": url})
    out.sort(key=lambda r: (0 if r["title"].lower().startswith(ql) else 1, len(r["title"])))
    return out[:limit]


# ----------------------------------------------------------------- the jump commands

def nav_commands() -> list[dict[str, str]]:
    """Every registered nav item (core seeds AND extension registrations — the nav
    registry is the source of truth) as a palette jump command, plus the surfaces the
    4-item sidebar deliberately does NOT carry (ux-contract §3.5) but that stay one
    keystroke away: the Library tabs under their canonical routes, the /runs journal
    and the documentation hub — and the chrome overlays without a route: the ? cheat
    sheet (web/_keymap.py opens the overlay on #shortcuts) and the settings popover
    (web/_palette.py opens it on #settings)."""
    from ._ext import nav_model, resolve_label
    from .pages.library import LIBRARY_TABS   # late: pages import web modules, not vice versa
    cmds = [{"title": resolve_label(it["label"]), "url": it["href"], "type": "go"}
            for _sec, items in nav_model() for it in items]
    cmds += [{"title": label(), "url": route, "type": "go"}
             for _k, route, _i, label, *_rest in LIBRARY_TABS]
    cmds.append({"title": t("runs_h"), "url": "/runs", "type": "go"})
    cmds.append({"title": t("documentation"), "url": "/documentation", "type": "go"})
    cmds.append({"title": t("kbd_cheatsheet_h"), "url": "#shortcuts", "type": "go"})
    cmds.append({"title": t("settings"), "url": "#settings", "type": "go"})
    return cmds


# ------------------------------------------------------- the canary's reasoned opt-outs

# Detail routes (GET /{prefix}/{param}) that are deliberately NOT entity-search targets.
NON_SEARCHABLE_ROUTES: dict[str, str] = {
    "/activities": "one simulated calendar activity of one persona — reached from the persona's "
                   "calendar; far too granular for a global jump target",
    "/documentation": "the curated docs hub — the nav-derived 'Documentation' jump command covers "
                      "it; full-text doc search is not entity search",
    "/sessions-files": "static passthrough for recorded session assets (screenshots), not an entity",
}

# Every presence-contract kind (web/_presence.REGISTRY — the existing entity-kind
# inventory, reused instead of duplicated) → its search source, or why it has none.
KIND_SEARCH: dict[str, str | NotSearchable] = {
    "council": "council",
    "synthesis": "synthesis",
    "report": "synthesis",       # a report IS a project-scope synthesis; list_syntheses carries it
    "note": "note",              # observations/concepts/ideas — kind discriminators on one primitive
    "prototype": "prototype",
    "session": "session",
    "section": "section",
    "hypothesis": "hypothesis",
    "decision": "decision",
    "survey": "survey",
    "flow": NotSearchable("no detail route — a flow surfaces as its sessions' subject; the "
                          "sessions source reaches those traces"),
    "url_artifact": NotSearchable("no detail route — A/B captures render as outline rows on "
                                  "their project page (reachable via the project source)"),
    "open_question": NotSearchable("no detail route — lives in the project page's "
                                   "#open-questions section (reachable via the project source)"),
    "asset": "asset",            # the U8 detail surface: /assets/{id}, global id resolution
}
