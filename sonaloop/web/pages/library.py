"""Library detail pages: sections, notes, prototypes (spec/roadmap.md R2)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .sessions import _sessions_section
from .._forms import danger_zone, delete_button_form, edit_button
from .._render import render_statements
from ... import artifacts as _artifacts


def register_library(app) -> None:
    @app.get("/sections/{section_id}", response_class=HTMLResponse)
    def section_view(section_id: str) -> str:
        store = Store()
        from ... import presentation as _pres
        try:
            data = services.section_members(section_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state("Section", t("runtime_maybe_cleared"), icon="squareGrid"), store, active="projects")
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
            store, title=ntitle, active="note",
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
            store, title=p["name"], active="prototype", crumbs=crumbs,
            hero=_hero(proto_title, icon="prototype", sub=f'{p.get("version","")} · {slug}'), body=body,
            prop_rows=[("square", t("fidelity"), _ap.get("disc") or _ap.get("label") or ""),
                       ("personas", t("sessions"), str(len(sessions))),
                       ("check", t("grounded_yes"), f"{n_grounded}/{len(sessions)}" if sessions else "—"),
                       ("projects", t("project"), proj_link)],
            rel_study_id=f"prototype:{p['id']}", rel_proj_id=p.get("project_id"), rel_extra_in=concept_in,
            rail_sections=(([("sec-replays", t("sessions"))] if replay_html else [])
                           + [("sec-sessions", t("sessions"))]),
            star=("prototype", p["id"], p["name"], f'/prototypes/{slug}'))
