"""Write routes: the inspector's structural CRUD (ticket web-crud-structure).

Every route follows the ONE write-path pattern from web/_forms.py — GET form,
POST -> write_gate (CSRF + cloud access guard) -> validate -> SERVICE call -> 303.
The mutation boundary (docs/web-mutations.md): structural/metadata operations only;
authored/generated prose stays host-authored (persona CREATE is therefore MCP-only —
record_persona requires the full host-authored profile JSON from brief_persona)."""
from __future__ import annotations

from fastapi import Request

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from ...prototypes import PrototypeError
from .._forms import (
    confirm_delete_modal, danger_zone, delete_button_form, field, form_page,
    not_found, see_other, write_gate,
)


def _s(form, name: str) -> str:
    return str(form.get(name) or "").strip()


# ------------------------------------------------------------------- projects

def _project_form(store, proj: dict | None, values: dict, errors: dict,
                  confirm_error: str = "") -> str:
    """New + edit share one form; edit adds the danger zone (typed-confirm delete)."""
    new = proj is None
    title = t("new_project") if new else f'{proj["title"]} — {t("edit")}'
    action = "/projects/new" if new else f'/projects/{proj["id"]}/edit'
    cancel = "/projects" if new else f'/projects/{proj["id"]}'
    crumbs = ([(t("projects"), "/projects"), (t("new_project"), None)] if new else
              [(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (t("edit"), None)])
    danger = "" if new else danger_zone(confirm_delete_modal(
        f'/projects/{proj["id"]}/delete', proj["title"], t("delete_project"), error=confirm_error))
    return form_page(
        store, title=title, crumbs=crumbs, active="projects", action=action,
        lead=t("project_form_lead"),
        fields=[raw(field("title", t("f_title"), values.get("title", ""),
                          error=errors.get("title", ""), required=True)),
                raw(field("goal", t("f_goal"), values.get("goal", ""))),
                raw(field("description", t("f_description"), values.get("description", ""),
                          textarea=True))],
        submit_label=t("create") if new else t("save"), cancel_href=cancel, danger=danger)


def _persona_form(store, p: dict, values: dict, errors: dict, confirm_error: str = "") -> str:
    """Persona METADATA only (name/role/segment/industry) — the profile prose and the
    generated SOUL stay host-authored (docs/web-mutations.md)."""
    danger = danger_zone(confirm_delete_modal(
        f'/personas/{p["id"]}/delete', p["display_name"], t("delete_persona"), error=confirm_error))
    return form_page(
        store, title=f'{p["display_name"]} — {t("edit")}', active="personas",
        crumbs=[(t("personas"), "/personas"), (p["display_name"], f'/personas/{p["id"]}'), (t("edit"), None)],
        action=f'/personas/{p["id"]}/edit', lead=t("persona_form_lead"),
        fields=[raw(field("display_name", t("f_name"), values.get("display_name", ""),
                          error=errors.get("display_name", ""), required=True)),
                raw(field("role_title", t("f_role_title"), values.get("role_title", ""))),
                raw(field("customer_type", t("f_segment"), values.get("customer_type", ""))),
                raw(field("industry", t("f_industry"), values.get("industry", "")))],
        submit_label=t("save"), cancel_href=f'/personas/{p["id"]}', danger=danger)


def _note_form(store, proj: dict, note: dict | None, values: dict, errors: dict) -> str:
    new = note is None
    title = t("new_note") if new else f'{note.get("title") or t("notes_h")} — {t("edit")}'
    action = f'/projects/{proj["id"]}/notes/new' if new else f'/notes/{note["id"]}/edit'
    cancel = f'/projects/{proj["id"]}' if new else f'/notes/{note["id"]}'
    danger = "" if new else danger_zone(raw(
        delete_button_form(f'/notes/{note["id"]}/delete', t("delete_note"))))
    return form_page(
        store, title=title, active="library",
        crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (title, None)],
        action=action,
        fields=[raw(field("title", t("f_title"), values.get("title", ""))),
                raw(field("text", t("f_text"), values.get("text", ""),
                          error=errors.get("text", ""), required=True, textarea=True))],
        submit_label=t("create") if new else t("save"), cancel_href=cancel, danger=danger)


def _section_form(store, proj: dict, sec: dict | None, values: dict, errors: dict) -> str:
    new = sec is None
    title = t("new_section") if new else f'{sec["title"]} — {t("edit")}'
    action = f'/projects/{proj["id"]}/sections/new' if new else f'/sections/{sec["id"]}/edit'
    cancel = f'/projects/{proj["id"]}' if new else f'/sections/{sec["id"]}'
    danger = "" if new else danger_zone(raw(
        delete_button_form(f'/sections/{sec["id"]}/delete', t("delete_section"))))
    return form_page(
        store, title=title, active="projects",
        crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (title, None)],
        action=action, lead=t("section_form_lead"),
        fields=[raw(field("title", t("f_title"), values.get("title", ""),
                          error=errors.get("title", ""), required=True)),
                raw(field("kind", t("type_h"), values.get("kind", "theme"))),
                raw(field("note", t("f_note"), values.get("note", ""), textarea=True))],
        submit_label=t("create") if new else t("save"), cancel_href=cancel, danger=danger)


def register_edit(app) -> None:  # noqa: C901  (route table — one block per entity)
    from fastapi.responses import HTMLResponse

    # ---------------------------------------------------------------- projects
    @app.get("/projects/new", response_class=HTMLResponse)
    def project_new_form() -> str:
        return _project_form(Store(), None, {}, {})

    @app.post("/projects/new")
    async def project_create(request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "create_project")) is not None:
            return gate
        values = {k: _s(form, k) for k in ("title", "goal", "description")}
        if not values["title"]:
            return HTMLResponse(_project_form(store, None, values, {"title": t("field_required")}),
                                status_code=400)
        p = services.create_research_project(values["title"], goal=values["goal"],
                                             description=values["description"], store=store)
        return see_other(f'/projects/{p["id"]}')

    @app.get("/projects/{project_id}/edit", response_class=HTMLResponse)
    def project_edit_form(project_id: str):
        store = Store()
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return not_found()
        return _project_form(store, proj, {"title": proj["title"], "goal": proj.get("goal", ""),
                                           "description": proj.get("description", "")}, {})

    @app.post("/projects/{project_id}/edit")
    async def project_update(project_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "update_project", {"project_id": project_id})) is not None:
            return gate
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return not_found()
        values = {k: _s(form, k) for k in ("title", "goal", "description")}
        if not values["title"]:
            return HTMLResponse(_project_form(store, proj, values, {"title": t("field_required")}),
                                status_code=400)
        services.update_research_project(project_id, values, store=store)
        return see_other(f"/projects/{project_id}")

    @app.post("/projects/{project_id}/delete")
    async def project_delete(project_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "delete_project", {"project_id": project_id})) is not None:
            return gate
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return not_found()
        if _s(form, "confirm") != proj["title"]:
            values = {"title": proj["title"], "goal": proj.get("goal", ""),
                      "description": proj.get("description", "")}
            return HTMLResponse(_project_form(store, proj, values, {},
                                              confirm_error=t("confirm_mismatch")), status_code=400)
        services.delete_research_project(project_id, store=store)
        return see_other("/projects")

    # ---------------------------------------------------------------- personas
    @app.get("/personas/{persona_id}/edit", response_class=HTMLResponse)
    def persona_edit_form(persona_id: str):
        store = Store()
        p = store.get_persona(persona_id)
        if not p:
            return not_found(icon="personas", active="personas")
        return _persona_form(store, p, {
            "display_name": p["display_name"], "role_title": p.get("role", {}).get("title", ""),
            "customer_type": p.get("segment", {}).get("customer_type", ""),
            "industry": p.get("company_context", {}).get("industry", "")}, {})

    @app.post("/personas/{persona_id}/edit")
    async def persona_update(persona_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "update_persona", {"persona_id": persona_id})) is not None:
            return gate
        p = store.get_persona(persona_id)
        if not p:
            return not_found(icon="personas", active="personas")
        values = {k: _s(form, k) for k in ("display_name", "role_title", "customer_type", "industry")}
        if not values["display_name"]:
            return HTMLResponse(_persona_form(store, p, values,
                                              {"display_name": t("field_required")}), status_code=400)
        services.update_persona(persona_id, {
            "display_name": values["display_name"],
            "role": {"title": values["role_title"]},
            "segment": {"customer_type": values["customer_type"]},
            "company_context": {"industry": values["industry"]},
        }, reason="web metadata edit", store=store)
        return see_other(f"/personas/{persona_id}")

    @app.post("/personas/{persona_id}/delete")
    async def persona_delete(persona_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "delete_persona", {"persona_id": persona_id})) is not None:
            return gate
        p = store.get_persona(persona_id)
        if not p:
            return not_found(icon="personas", active="personas")
        if _s(form, "confirm") != p["display_name"]:
            values = {"display_name": p["display_name"], "role_title": p.get("role", {}).get("title", ""),
                      "customer_type": p.get("segment", {}).get("customer_type", ""),
                      "industry": p.get("company_context", {}).get("industry", "")}
            return HTMLResponse(_persona_form(store, p, values, {},
                                              confirm_error=t("confirm_mismatch")), status_code=400)
        services.delete_persona(persona_id, store=store)
        return see_other("/personas")

    # ------------------------------------------------------------------- notes
    @app.get("/projects/{project_id}/notes/new", response_class=HTMLResponse)
    def note_new_form(project_id: str):
        store = Store()
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return not_found()
        return _note_form(store, proj, None, {}, {})

    @app.post("/projects/{project_id}/notes/new")
    async def note_create(project_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "create_note", {"project_id": project_id})) is not None:
            return gate
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return not_found()
        values = {k: _s(form, k) for k in ("title", "text")}
        if not values["text"]:
            return HTMLResponse(_note_form(store, proj, None, values, {"text": t("field_required")}),
                                status_code=400)
        note = services.create_note(project_id, values["text"], title=values["title"], store=store)
        return see_other(f'/notes/{note["id"]}')

    @app.get("/notes/{note_id}/edit", response_class=HTMLResponse)
    def note_edit_form(note_id: str):
        store = Store()
        try:
            data = services.get_note(note_id, store=store)
        except KeyError:
            return not_found(icon="panel", active="library")
        return _note_form(store, data["project"], data["note"],
                          {"title": data["note"].get("title", ""), "text": data["note"].get("text", "")}, {})

    @app.post("/notes/{note_id}/edit")
    async def note_update(note_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "update_note", {"note_id": note_id})) is not None:
            return gate
        try:
            data = services.get_note(note_id, store=store)
        except KeyError:
            return not_found(icon="panel", active="library")
        values = {k: _s(form, k) for k in ("title", "text")}
        if not values["text"]:
            return HTMLResponse(_note_form(store, data["project"], data["note"], values,
                                           {"text": t("field_required")}), status_code=400)
        services.update_note(note_id, values, store=store)
        return see_other(f"/notes/{note_id}")

    @app.post("/notes/{note_id}/delete")
    async def note_delete(note_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "delete_note", {"note_id": note_id})) is not None:
            return gate
        try:
            data = services.get_note(note_id, store=store)
        except KeyError:
            return not_found(icon="panel", active="library")
        services.delete_note(data["project"]["id"], note_id, store=store)
        return see_other(f'/projects/{data["project"]["id"]}')

    # ---------------------------------------------------------------- sections
    @app.get("/projects/{project_id}/sections/new", response_class=HTMLResponse)
    def section_new_form(project_id: str):
        store = Store()
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return not_found()
        return _section_form(store, proj, None, {}, {})

    @app.post("/projects/{project_id}/sections/new")
    async def section_create(project_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "create_section", {"project_id": project_id})) is not None:
            return gate
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return not_found()
        values = {k: _s(form, k) for k in ("title", "kind", "note")}
        if not values["title"]:
            return HTMLResponse(_section_form(store, proj, None, values,
                                              {"title": t("field_required")}), status_code=400)
        sec = services.create_section(project_id, values["title"], kind=values["kind"] or "theme",
                                      note=values["note"], store=store)
        return see_other(f'/sections/{sec["id"]}')

    @app.get("/sections/{section_id}/edit", response_class=HTMLResponse)
    def section_edit_form(section_id: str):
        store = Store()
        try:
            data = services.section_members(section_id, store=store)
        except KeyError:
            return not_found(icon="squareGrid")
        sec = data["section"]
        return _section_form(store, data["project"], sec,
                             {"title": sec["title"], "kind": sec.get("kind", "theme"),
                              "note": sec.get("note", "")}, {})

    @app.post("/sections/{section_id}/edit")
    async def section_update(section_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "update_section", {"section_id": section_id})) is not None:
            return gate
        try:
            data = services.section_members(section_id, store=store)
        except KeyError:
            return not_found(icon="squareGrid")
        values = {k: _s(form, k) for k in ("title", "kind", "note")}
        if not values["title"]:
            return HTMLResponse(_section_form(store, data["project"], data["section"], values,
                                              {"title": t("field_required")}), status_code=400)
        services.update_section(section_id, values, store=store)
        return see_other(f"/sections/{section_id}")

    @app.post("/sections/{section_id}/delete")
    async def section_delete(section_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "delete_section", {"section_id": section_id})) is not None:
            return gate
        try:
            sec = services.get_section(section_id, store=store)
        except KeyError:
            return not_found(icon="squareGrid")
        services.delete_section(section_id, store=store)
        return see_other(f'/projects/{sec["project_id"]}')

    # ------------------------------- studies/artifacts: DELETE only (no content editing)
    @app.post("/councils/{session_id}/delete")
    async def council_delete(session_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "delete_council", {"council_id": session_id})) is not None:
            return gate
        if not store.get_council_session(session_id):
            return not_found(icon="councils", active="library")
        services.delete_council(session_id, store=store)
        return see_other("/councils")

    @app.post("/syntheses/{synthesis_id}/delete")
    async def synthesis_delete(synthesis_id: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "delete_synthesis", {"synthesis_id": synthesis_id})) is not None:
            return gate
        if not store.get_synthesis(synthesis_id):
            return not_found(icon="syntheses", active="library")
        services.delete_synthesis(synthesis_id, store=store)
        return see_other("/syntheses")

    @app.post("/prototypes/{slug}/delete")
    async def prototype_delete(slug: str, request: Request):
        store = Store()
        form = await request.form()
        if (gate := write_gate(form, "delete_prototype", {"prototype": slug})) is not None:
            return gate
        try:
            p = services.get_prototype_artifact(slug, store=store)
        except PrototypeError:  # UNKNOWN_PROTOTYPE — the lookup's only input-triggered raise
            return not_found(icon="prototype", active="library")
        services.delete_prototype_artifact(p["id"], store=store)
        return see_other("/prototypes")
