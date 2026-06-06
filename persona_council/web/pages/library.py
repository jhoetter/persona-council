"""Library detail pages: sections, notes/concepts, prototypes (spec/roadmap.md R2)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)


def register_library(app) -> None:
    @app.get("/sections/{section_id}", response_class=HTMLResponse)
    def section_view(section_id: str) -> str:
        store = Store()
        from ... import presentation as _pres
        try:
            data = services.section_members(section_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state("Section", t("runtime_maybe_cleared")), store, active="projects")
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
        sprops = _properties_html([
            ("dot", t("type_h"), pr.get("short", sec.get("kind", ""))),
            ("projects", t("project"), h("a", {"href": f'/projects/{proj["id"]}'}, proj["title"])),
        ], aside=True)
        sec_sub = fragment(chip, " ", h("span", {"class_": "muted small"}, t("n_nodes", n=len(members))))
        main = fragment(raw(_hero(sec["title"], sub=sec_sub)), note_sub,
                        h("div", {"style": "margin-top:8px"},
                          fragment(*rows) if rows else raw(_empty_state(t("section"), t("no_members")))))
        return _layout(sec["title"], _doc(main, rail=sprops), store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (sec["title"], None)],
                       active="projects")

    @app.get("/notes/{note_id}", response_class=HTMLResponse)
    @app.get("/concepts/{note_id}", response_class=HTMLResponse)        # a concept is a note with kind=concept
    def note_view(note_id: str) -> str:
        store = Store()
        from ... import presentation as _pres
        try:
            data = services.get_note(note_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("not_found"), t("runtime_maybe_cleared")), store, active="projects")
        note, proj = data["note"], data["project"]
        kind = note.get("kind") or "note"                              # present by the record's OWN kind
        pr = _pres.present(kind)
        klabel = t("concept_h") if kind == "concept" else (t("notes_h") if kind == "note" else (pr.get("label") or kind))
        active = "concept" if kind == "concept" else "projects"
        proj_link = h("a", {"href": f'/projects/{proj["id"]}'}, proj["title"])
        nprops = _properties_html([
            ("dot", t("created"), note.get("created_at", "")[:10]),
            ("projects", t("project"), proj_link),
        ], aside=True)
        nrel = _relations_html(store, f"note:{note_id}", proj["id"], aside=True)
        pill = h("div", {"style": "margin-bottom:6px"},
                 h("span", {"class_": "pill", "style": f'border-color:{pr["color"]};color:{pr["color"]}'},
                   ((pr.get("glyph") + " ") if pr.get("glyph") else ""), klabel))
        main = fragment(raw(_hero(note.get("title", ""), hid="sec-content", top=pill)),
                        h("div", {"class_": "es-prose", "style": "margin-top:4px"}, raw(_md(note.get("text", "")))))
        nrail = [("sec-content", klabel)]
        if nprops:
            nrail.append(("sec-properties", t("properties")))
        if nrel:
            nrail.append(("sec-relations", t("relations")))
        body = _doc(main, rail=nprops + nrel) + _page_rail(nrail)
        return _layout(note.get("title") or klabel, body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (klabel, None)],
                       active=active)

    @app.get("/prototypes/{slug}", response_class=HTMLResponse)
    def prototype_view(slug: str) -> str:
        store = Store()
        try:
            p = services.get_prototype_artifact(slug, store=store)
        except Exception:
            return _layout(t("not_found"), _empty_state(t("prototypes_h"), t("runtime_maybe_cleared")), store, active="projects")
        crumbs = [(t("projects"), "/projects")]
        proj = store.get_research_project(p["project_id"]) if p.get("project_id") else None
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((p["name"], None))
        _ap = _artifact_present(p)
        fid = h("span", {"class_": "pill"}, _ap["disc"] or _ap["label"])
        src = f'/proto-files/{slug}/{p.get("entry", "index.html")}'
        sessions = store.list_prototype_sessions(prototype_id=p["id"])
        sessions_html = (fragment(*(_session_card(store, s) for s in sessions))
                         or h("div", {"class_": "muted small"}, f'— {t("prototypes_h")}: {t("no_sessions")} —'))
        proto_title = fragment(p["name"], " ", fid)
        proto_sub = f'{p.get("version","")} · {slug}'
        main = fragment(
            raw(_hero(proto_title, icon="prototype", sub=proto_sub)),
            h("p", {"style": "margin:8px 0 16px"},
              h("a", {"class_": "btn", "href": src, "target": "_blank"},
                raw(_icon("projects")), " ", t("open_in_new_tab"), " ", raw(_icon("external")))),
            h("div", {"class_": "protoframe"}, h("iframe", {"src": src, "title": p["name"], "loading": "lazy"})),
            h("div", {"class_": "sec", "id": "sec-sessions", "style": "margin-top:22px"},
              h("h2", {}, f'{t("prototypes_h")} · {t("sessions")} ({len(sessions)})'),
              h("div", {"style": "margin-top:8px"}, sessions_html)))
        concept_in = []
        if proj:                                              # the concept that realises this prototype
            try:
                g = services.get_project_graph(p["project_id"], store=store)
                concept_in = [n for n in g["nodes"] if n.get("prototype_id") == p["id"]]
            except Exception:
                concept_in = []
        n_grounded = sum(1 for s in sessions if s.get("grounded_verified"))
        proj_link = (h("a", {"href": f'/projects/{proj["id"]}'}, proj["title"]) if proj else "—")
        prop_html = _properties_html([
            ("square", t("fidelity"), _ap.get("disc") or _ap.get("label") or ""),
            ("personas", t("sessions"), str(len(sessions))),
            ("check", t("grounded_yes"), f"{n_grounded}/{len(sessions)}" if sessions else "—"),
            ("projects", t("project"), proj_link),
        ], aside=True)
        rel_html = _relations_html(store, f"prototype:{p['id']}", p.get("project_id"), extra_in=concept_in, aside=True)
        rail = [("sec-sessions", t("sessions"))]
        if prop_html:
            rail.append(("sec-properties", t("properties")))
        if rel_html:
            rail.append(("sec-relations", t("relations")))
        body = _doc(main, rail=prop_html + rel_html) + _page_rail(rail)
        return _layout(p["name"], body, store, crumbs=crumbs, active="prototype")
