"""The Library — ONE browser over every produced primitive (spec/ux-contract.md §3.5) —
plus the library detail pages: sections, notes, prototypes (spec/roadmap.md R2).

/library renders `ui.tabs` across the 8 produced kinds; every tab is the SAME shape:
the kind's existing list read rendered as `ui.primitive_row` rows (deep-link href +
peek data-drawer) through the shared _list_page shell. The old list routes (/councils,
/syntheses, /prototypes, /sessions, /surveys, /hypotheses, /decisions, /notes) stay
registered — their handlers render the library with that tab active, so deep links and
`next_recommended_tool` hints survive without redirects; the tab links use the
canonical routes, ?tab= addresses a tab on /library itself. Detail routes unchanged."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .sessions import _sessions_section
from .. import ui
from .._forms import danger_zone, delete_button_form, edit_button
from .._render import render_statements
from ... import artifacts as _artifacts

# (key, canonical route, icon, label, empty-state msg, lead) — labels are lambdas so they
# resolve per request (i18n, the _nav_seed idiom). Tab order is the methodology arc:
# debate → synthesis → build → test → measure → bet → decide → note.
LIBRARY_TABS: tuple = (
    ("councils", "/councils", "councils",
     lambda: t("councils"), lambda: t("no_councils"), lambda: t("councils_lead")),
    ("reports", "/syntheses", "syntheses",
     lambda: t("syntheses"), lambda: t("no_synthesis"), lambda: t("syntheses_lead")),
    ("prototypes", "/prototypes", "prototype",
     lambda: t("prototypes_h"), lambda: t("no_prototypes"), lambda: t("prototypes_lead")),
    ("sessions", "/sessions", "activity",
     lambda: t("sessions"), lambda: t("no_sessions"), lambda: t("sessions_lead")),
    ("surveys", "/surveys", "plan",
     lambda: t("surveys_h"), lambda: t("no_surveys"), lambda: t("surveys_lead")),
    ("hypotheses", "/hypotheses", "target",
     lambda: t("hypotheses_h"), lambda: t("no_hypotheses"), lambda: t("hypotheses_lead")),
    ("decisions", "/decisions", "flag",
     lambda: t("decisions_h"), lambda: t("no_decisions"), lambda: t("decisions_lead")),
    ("notes", "/notes", "panel",
     lambda: t("notes"), lambda: t("no_notes"), lambda: t("notes_lead")),
)


def _tab_rows(key: str, store: Store, sessions: list | None = None) -> list:
    """The active tab's rows: the kind's EXISTING list read mapped through the one row
    vocabulary (ui.primitive_row — §3.2), with the owning project's title as the muted
    desc line (this is a CROSS-project browser — the row must say where it lives; the
    library mockup in §4 shows exactly this). Hypotheses/decisions deep-link into their
    project's outline anchor (their canonical home); everything else to its detail page."""
    projects = {p["id"]: p["title"] for p in store.list_research_projects()}
    in_proj = lambda rec: projects.get(rec.get("project_id") or "", "")
    if key == "councils":
        return [ui.primitive_row("council", {**c, "mode": services.council_mode(c)}, store,
                                 href=f'/councils/{c["id"]}', peek_url=f'/peek/council/{c["id"]}',
                                 desc=in_proj(c))
                for c in store.list_council_sessions()]
    if key == "reports":
        return [ui.primitive_row("synthesis", s, store, href=f'/syntheses/{s["id"]}',
                                 peek_url=f'/peek/synthesis/{s["id"]}', desc=in_proj(s))
                for s in store.list_syntheses()]
    if key == "prototypes":
        return [ui.primitive_row(
                    "prototype",
                    {**p, "n_sessions": len(store.list_prototype_sessions(prototype_id=p["id"]))},
                    store, href=f'/prototypes/{p["slug"]}', peek_url=f'/peek/prototype/{p["id"]}',
                    desc=in_proj(p))
                for p in store.list_prototypes()]
    if key == "sessions":
        if sessions is None:
            sessions = services.list_usability_sessions(store=store)
        # desc stays the per-kind default: the walked subject says more than the project here.
        return [ui.primitive_row("session", s, store, href=f'/sessions/{s["id"]}',
                                 peek_url=f'/peek/session/{s["id"]}')
                for s in sessions]
    if key == "surveys":
        return [ui.primitive_row("survey", s, store, href=f'/surveys/{s["id"]}',
                                 peek_url=f'/peek/survey/{s["id"]}', desc=in_proj(s))
                for s in services.list_surveys(store=store)]
    if key == "hypotheses":
        return [ui.primitive_row("hypothesis", x, store,
                                 href=f'/projects/{x["project_id"]}#hyp-{x["id"]}',
                                 peek_url=f'/peek/hypothesis/{x["id"]}', desc=in_proj(x))
                for x in services.list_hypotheses(store=store)]
    if key == "decisions":
        return [ui.primitive_row("decision", d, store,
                                 href=f'/projects/{d["project_id"]}#dec-{d["id"]}',
                                 peek_url=f'/peek/decision/{d["id"]}', desc=in_proj(d))
                for d in services.list_decisions(store=store)]
    if key == "notes":
        return [ui.primitive_row("note", n, store, href=f'/notes/{n["id"]}',
                                 peek_url=f'/peek/note/{n["id"]}', desc=proj["title"])
                for proj in store.list_research_projects()
                for n in services.list_notes(proj["id"], store=store)]
    return []


def library_page(tab: str = "councils", store: Store | None = None, *,
                 sessions: list | None = None, pre_extra: str = "") -> str:
    """The one Library browser. `sessions` lets the /sessions route keep its honest
    project/subject query filters; `pre_extra` carries a tab's extra read (the sessions
    funnel, the hypotheses hit-rate strip) between the tab bar and the rows."""
    store = store or Store()
    keys = [k for k, *_ in LIBRARY_TABS]
    if tab not in keys:
        tab = keys[0]
    tabs_html = ui.tabs([{"key": k, "label": label(), "href": route}
                         for k, route, _icon_, label, _e, _l in LIBRARY_TABS], tab)
    _k, _route, icon, _label, empty_msg, lead = next(
        row for row in LIBRARY_TABS if row[0] == tab)
    rows = _tab_rows(tab, store, sessions=sessions)
    return _list_page(store, title=t("library_h"), lead=lead(), rows=rows,
                      empty_icon=icon, empty_msg=empty_msg(), active="library",
                      pre=str(tabs_html) + pre_extra, count=len(rows))


def register_library(app) -> None:
    @app.get("/library", response_class=HTMLResponse)
    def library(tab: str = Query(default="councils")) -> str:
        return library_page(tab)

    @app.get("/sections/{section_id}", response_class=HTMLResponse)
    def section_view(section_id: str) -> str:
        store = Store()
        from ... import presentation as _pres
        try:
            data = services.section_members(section_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("section"), t("runtime_maybe_cleared"), icon="squareGrid"), store, active="projects")
        sec, proj, members = data["section"], data["project"], data["members"]
        pr = _pres.present(sec.get("kind", "theme"), sec.get("presentation"))
        chip = h("span", {"class_": "pill", "style": f'border-color:{pr["color"]};color:{pr["color"]}'},
                 ((pr.get("glyph") + " ") if pr.get("glyph") else ""), pr.get("short", sec.get("kind", "")))
        rows = []
        for m in members:
            head = h("a", {"href": m["href"]}, m["title"]) if m["href"] else m["title"]
            rows.append(h("div", {"class_": "strow"}, h("b", {}, head), " ", h("span", {"class_": "muted small"}, m["kind"]),
                          h("div", {"class_": "muted small", "style": "margin-top:3px"}, (m["summary"] or "")[:240])))
        note_sub = h("p", {"class_": "sub"}, sec.get("note", "")) if sec.get("note") else ""
        sec_sub = fragment(chip, " ", h("span", {"class_": "muted small"}, t("n_nodes", n=len(members))))
        body = fragment(note_sub, h("div", {"style": "margin-top:8px"},
                        fragment(*rows) if rows else raw(_empty_state(t("section"), t("no_members"), icon="squareGrid"))))
        return detail_page(
            store, title=sec["title"], active="projects",
            crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (sec["title"], None)],
            icon="squareGrid", sub=sec_sub, body=body,
            prop_rows=[("dot", t("type_h"), pr.get("short", sec.get("kind", ""))),
                       ("projects", t("project"), h("a", {"href": f'/projects/{proj["id"]}'}, proj["title"]))],
            star=("section", sec["id"], sec["title"], f'/sections/{sec["id"]}'),
            actions=edit_button(f'/sections/{sec["id"]}/edit'))

    @app.get("/notes/{note_id}", response_class=HTMLResponse)
    def note_view(note_id: str) -> str:
        store = Store()
        try:
            data = services.get_note(note_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("not_found"), t("runtime_maybe_cleared"), icon="panel"), store, active="projects")
        note, proj = data["note"], data["project"]
        klabel = t("notes_h")                                          # ONE note entity (concepts merged in)
        ntitle = note.get("title") or klabel
        return detail_page(
            store, title=ntitle, active="library",
            crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (ntitle, None)],
            icon="panel", sub=klabel, hid="sec-content",
            body=h("div", {"class_": "sl-prose", "style": "margin-top:4px"}, raw(_md(note.get("text", "")))),
            prop_rows=[("dot", t("created"), note.get("created_at", "")[:10]),
                       ("projects", t("project"), h("a", {"href": f'/projects/{proj["id"]}'}, proj["title"]))],
            rel_study_id=f"note:{note_id}", rel_proj_id=proj["id"],
            rail_sections=[("sec-content", klabel)],
            star=("note", note_id, ntitle, f'/notes/{note_id}'),
            actions=edit_button(f'/notes/{note_id}/edit'))

    @app.get("/prototypes/{slug}", response_class=HTMLResponse)
    def prototype_view(slug: str) -> str:
        store = Store()
        try:
            p = services.get_prototype_artifact(slug, store=store)
        except Exception:
            return _layout(t("not_found"), _empty_state(t("prototypes_h"), t("runtime_maybe_cleared"), icon="prototype"), store, active="projects")
        crumbs = [(t("projects"), "/projects")]
        proj = store.get_research_project(p["project_id"]) if p.get("project_id") else None
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((p["name"], None))
        _ap = _artifact_present(p)
        fid = h("span", {"class_": "pill"}, _ap["disc"] or _ap["label"])
        src = f'/proto-files/{slug}/{p.get("entry", "index.html")}'
        # Sessions render through the SAME statement renderer as council/synthesis voices: the test
        # `focus` is the prompt BANNER above the persona cards (not a line inside each), with a grounded
        # chip per card — one uniform "prompt → responses" structure across all detail pages.
        sessions = store.list_prototype_sessions(prototype_id=p["id"])
        sess_statements = [_artifacts.session_statements(s)[0] for s in sessions]
        focus = next((f for f in (_artifacts.session_focus(s) for s in sessions) if f), "")
        fp = _artifacts.prompt(focus, kind="focus", id="focus") if focus else None
        if sess_statements:
            sessions_html = (render_statements(sess_statements, store, group_by="prompt", prompts=[fp]) if fp
                             else render_statements(sess_statements, store, group_by="persona"))
        else:
            sessions_html = h("div", {"class_": "muted small"}, f'— {t("prototypes_h")}: {t("no_sessions")} —')
        proto_title = fragment(p["name"], " ", fid)
        # Replayable usability sessions of THIS prototype (subject.id is the prototype id or slug) —
        # each row deep-links into the session replay view.
        useen, usess = set(), []
        for key in (p["id"], p.get("slug")):
            for s in (services.list_usability_sessions(subject=key, store=store) if key else []):
                if s["id"] not in useen:
                    useen.add(s["id"]); usess.append(s)
        replay_html = _sessions_section(store, usess, sid="sec-replays")
        body = fragment(
            h("p", {"style": "margin:8px 0 16px"},
              h("a", {"class_": "sl-btn", "href": src, "target": "_blank"},
                raw(_icon("projects")), " ", t("open_in_new_tab"), " ", raw(_icon("external")))),
            h("div", {"class_": "protoframe"}, h("iframe", {"src": src, "title": p["name"], "loading": "lazy"})),
            raw(replay_html),
            h("div", {"class_": "sec", "id": "sec-sessions", "style": "margin-top:22px"},
              h("h2", {}, f'{t("prototypes_h")} · {t("sessions")} ({len(sessions)})'),
              h("div", {"style": "margin-top:8px"}, sessions_html)),
            # delete-only (no content editing): prototypes are recorded artifacts
            raw(danger_zone(raw(delete_button_form(f'/prototypes/{slug}/delete',
                                                   t("delete_prototype"))))))
        concept_in = []
        if proj:                                              # the concept that realises this prototype
            try:
                g = services.get_project_graph(p["project_id"], store=store)
                concept_in = [n for n in g["nodes"] if p["id"] in (n.get("prototype_ids") or [])]
            except Exception:
                concept_in = []
        n_grounded = sum(1 for s in sessions if s.get("grounded_verified"))
        proj_link = (h("a", {"href": f'/projects/{proj["id"]}'}, proj["title"]) if proj else "—")
        return detail_page(
            store, title=p["name"], active="library", crumbs=crumbs,
            hero=_hero(proto_title, icon="prototype", sub=f'{p.get("version","")} · {slug}'), body=body,
            prop_rows=[("square", t("fidelity"), _ap.get("disc") or _ap.get("label") or ""),
                       ("personas", t("sessions"), str(len(sessions))),
                       ("check", t("grounded_yes"), f"{n_grounded}/{len(sessions)}" if sessions else "—"),
                       ("projects", t("project"), proj_link)],
            rel_study_id=f"prototype:{p['id']}", rel_proj_id=p.get("project_id"), rel_extra_in=concept_in,
            rail_sections=(([("sec-replays", t("sessions"))] if replay_html else [])
                           + [("sec-sessions", t("sessions"))]),
            star=("prototype", p["id"], p["name"], f'/prototypes/{slug}'))
