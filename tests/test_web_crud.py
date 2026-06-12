"""Web CRUD write path (ticket web-crud-structure): POST + 303, double-submit CSRF,
validation re-render, 404s, and the cloud access-guard seam.

Per route family: happy path / validation failure / CSRF rejection / 404 — plus the
write-requires-editor check through services.register_access_guard (the same seam
sonaloop-cloud's tenancy guard registers on). The boundary itself (structural writes
only, generated prose never editable) is documented in docs/web-mutations.md; the
absence of any text-edit route for councils/syntheses/SOUL is asserted here too."""
from __future__ import annotations

import pytest

from sonaloop import services, web
from sonaloop.services import _substrate
from conftest import create_persona


def _client():
    from starlette.testclient import TestClient
    client = TestClient(web.create_app())
    client.get("/projects?lang=en")            # primes the sl_csrf double-submit cookie
    return client


def _post(client, url: str, **data):
    """POST a form with the matching CSRF token; never follow the 303."""
    payload = {"csrf_token": client.cookies.get("sl_csrf"), **data}
    return client.post(url, data=payload, follow_redirects=False)


@pytest.fixture(autouse=True)
def _no_leftover_guards():
    yield
    _substrate.clear_access_guards()


# ------------------------------------------------------------------- CSRF plumbing

def test_csrf_cookie_is_issued_and_forms_embed_it(store):
    proj = services.create_research_project("P", store=store)
    client = _client()
    token = client.cookies.get("sl_csrf")
    assert token
    html = client.get(f'/projects/{proj["id"]}/edit?lang=en').text
    assert f'name="csrf_token" value="{token}"' in html


def test_post_without_or_with_wrong_csrf_token_is_403():
    client = _client()
    assert client.post("/projects/new", data={"title": "x"}).status_code == 403
    r = client.post("/projects/new", data={"title": "x", "csrf_token": "forged"})
    assert r.status_code == 403
    assert not services.list_research_projects()


# ------------------------------------------------------------------------ projects

def test_project_create_happy_path_redirects_303(store):
    client = _client()
    r = _post(client, "/projects/new", title="Pricing study", goal="WTP", description="desc")
    assert r.status_code == 303
    pid = r.headers["location"].rsplit("/", 1)[1]
    proj = services.get_research_project(pid, store=store)
    assert (proj["title"], proj["goal"], proj["description"]) == ("Pricing study", "WTP", "desc")


def test_project_create_empty_title_rerenders_form_with_inline_error():
    client = _client()
    r = _post(client, "/projects/new", title="   ", goal="kept goal")
    assert r.status_code == 400
    assert "This field is required." in r.text          # inline error …
    assert "kept goal" in r.text                        # … and the submitted values survive
    assert not services.list_research_projects()


def test_project_edit_happy_validation_and_404(store):
    proj = services.create_research_project("Old title", store=store)
    client = _client()
    assert "Old title" in client.get(f'/projects/{proj["id"]}/edit?lang=en').text
    r = _post(client, f'/projects/{proj["id"]}/edit', title="New title", goal="g2", description="")
    assert r.status_code == 303 and r.headers["location"] == f'/projects/{proj["id"]}'
    assert services.get_research_project(proj["id"], store=store)["title"] == "New title"
    assert _post(client, f'/projects/{proj["id"]}/edit', title="").status_code == 400
    assert client.get("/projects/nope/edit").status_code == 404
    assert _post(client, "/projects/nope/edit", title="x").status_code == 404


def test_project_delete_requires_typed_confirmation(store):
    proj = services.create_research_project("Keep me safe", store=store)
    client = _client()
    r = _post(client, f'/projects/{proj["id"]}/delete', confirm="wrong name")
    assert r.status_code == 400
    assert "The typed name does not match." in r.text
    assert services.get_research_project(proj["id"], store=store)
    r = _post(client, f'/projects/{proj["id"]}/delete', confirm="Keep me safe")
    assert r.status_code == 303 and r.headers["location"] == "/projects"
    with pytest.raises(KeyError):
        services.get_research_project(proj["id"], store=store)


def test_project_delete_404():
    assert _post(_client(), "/projects/nope/delete", confirm="x").status_code == 404


# ------------------------------------------------------------------------ personas

def test_persona_metadata_edit_happy_validation_csrf_404(store):
    pid = create_persona(store, "Anna Architect")
    client = _client()
    assert "Anna Architect" in client.get(f"/personas/{pid}/edit?lang=en").text
    r = _post(client, f"/personas/{pid}/edit", display_name="Anna Renamed",
              role_title="CTO", customer_type="SMB", industry="Construction")
    assert r.status_code == 303
    p = store.get_persona(pid)
    assert p["display_name"] == "Anna Renamed" and p["role"]["title"] == "CTO"
    assert p["segment"]["customer_type"] == "SMB"
    assert _post(client, f"/personas/{pid}/edit", display_name=" ").status_code == 400
    assert client.post(f"/personas/{pid}/edit",
                       data={"display_name": "x"}).status_code == 403
    assert client.get("/personas/nope/edit").status_code == 404


def test_persona_delete_typed_confirmation_and_404(store):
    pid = create_persona(store, "Bert Builder")
    client = _client()
    assert _post(client, f"/personas/{pid}/delete", confirm="Bart").status_code == 400
    assert store.get_persona(pid)
    r = _post(client, f"/personas/{pid}/delete", confirm="Bert Builder")
    assert r.status_code == 303 and r.headers["location"] == "/personas"
    assert store.get_persona(pid) is None
    assert _post(client, "/personas/nope/delete", confirm="x").status_code == 404


def test_persona_create_stays_mcp_only():
    # No browser create path (docs/web-mutations.md): record_persona needs the full
    # host-authored profile from brief_persona — the web offers metadata edit + delete only.
    client = _client()
    # no create route: /personas/new falls through to the detail route's not-found state
    html = client.get("/personas/new?lang=en").text
    assert 'action="/personas/new"' not in html and "Not found" in html
    assert "/personas/new" not in client.get("/personas?lang=en").text


# --------------------------------------------------------------------------- notes

def test_note_create_edit_delete_roundtrip(store):
    proj = services.create_research_project("P", store=store)
    client = _client()
    # no GET create form (U9) — the POST route stays as API surface
    assert client.get(f'/projects/{proj["id"]}/notes/new?lang=en').status_code == 405
    r = _post(client, f'/projects/{proj["id"]}/notes/new', title="Obs", text="saw a thing")
    assert r.status_code == 303
    nid = r.headers["location"].rsplit("/", 1)[1]
    assert services.get_note(nid, store=store)["note"]["text"] == "saw a thing"
    r = _post(client, f"/notes/{nid}/edit", title="Obs2", text="updated thing")
    assert r.status_code == 303 and r.headers["location"] == f"/notes/{nid}"
    assert services.get_note(nid, store=store)["note"]["title"] == "Obs2"
    r = _post(client, f"/notes/{nid}/delete")
    assert r.status_code == 303 and r.headers["location"] == f'/projects/{proj["id"]}'
    with pytest.raises(KeyError):
        services.get_note(nid, store=store)


def test_note_validation_csrf_and_404(store):
    proj = services.create_research_project("P", store=store)
    client = _client()
    r = _post(client, f'/projects/{proj["id"]}/notes/new', title="t", text="  ")
    assert r.status_code == 400 and "This field is required." in r.text
    assert client.post(f'/projects/{proj["id"]}/notes/new',
                       data={"text": "x"}).status_code == 403
    assert _post(client, "/projects/nope/notes/new", text="x").status_code == 404
    assert client.get("/notes/nope/edit").status_code == 404
    assert _post(client, "/notes/nope/edit", text="x").status_code == 404
    assert _post(client, "/notes/nope/delete").status_code == 404


# ------------------------------------------------------------------------ sections

def test_section_create_edit_delete_roundtrip(store):
    proj = services.create_research_project("P", store=store)
    client = _client()
    r = _post(client, f'/projects/{proj["id"]}/sections/new', title="Theme A", kind="theme", note="")
    assert r.status_code == 303
    sid = r.headers["location"].rsplit("/", 1)[1]
    r = _post(client, f"/sections/{sid}/edit", title="Theme B", kind="phase", note="why")
    assert r.status_code == 303
    sec = services.get_section(sid, store=store)
    assert (sec["title"], sec["kind"], sec["note"]) == ("Theme B", "phase", "why")
    r = _post(client, f"/sections/{sid}/delete")
    assert r.status_code == 303 and r.headers["location"] == f'/projects/{proj["id"]}'
    with pytest.raises(KeyError):
        services.get_section(sid, store=store)


def test_section_validation_and_404(store):
    proj = services.create_research_project("P", store=store)
    client = _client()
    r = _post(client, f'/projects/{proj["id"]}/sections/new', title=" ", kind="theme")
    assert r.status_code == 400 and "This field is required." in r.text
    assert _post(client, "/projects/nope/sections/new", title="x").status_code == 404
    assert client.get("/sections/nope/edit").status_code == 404
    assert _post(client, "/sections/nope/edit", title="x").status_code == 404
    assert _post(client, "/sections/nope/delete").status_code == 404


# ------------------------------------- councils / syntheses / prototypes: delete-only

def test_council_delete_happy_csrf_404(store):
    pid = create_persona(store, "Cara Council")
    proj = services.create_research_project("P", persona_ids=[pid], store=store)
    council = services.record_council(proj["id"], "Would you pay?", [pid],
                                      statements=[], store=store)
    cid = council["id"]
    client = _client()
    assert client.post(f"/councils/{cid}/delete", data={}).status_code == 403
    r = _post(client, f"/councils/{cid}/delete")
    assert r.status_code == 303 and r.headers["location"] == "/councils"
    assert store.get_council_session(cid) is None
    assert _post(client, f"/councils/{cid}/delete").status_code == 404


def test_synthesis_delete_happy_and_404(store):
    pid = create_persona(store, "Sara Synth")
    proj = services.create_research_project("P", persona_ids=[pid], store=store)
    syn = services.record_synthesis("Finding", "what did we learn?", [], {}, store=store)
    client = _client()
    r = _post(client, f'/syntheses/{syn["id"]}/delete')
    assert r.status_code == 303 and r.headers["location"] == "/syntheses"
    assert store.get_synthesis(syn["id"]) is None
    assert _post(client, f'/syntheses/{syn["id"]}/delete').status_code == 404


def test_prototype_delete_happy_and_404(store):
    proj = services.create_research_project("P", store=store)
    from sonaloop import prototypes
    p = prototypes.register_artifact("signup-flow", "Signup flow", "prototypes/signup-flow",
                                     project_id=proj["id"], store=store)
    client = _client()
    r = _post(client, f'/prototypes/{p["slug"]}/delete')
    assert r.status_code == 303 and r.headers["location"] == "/prototypes"
    assert store.get_prototype(p["id"]) is None
    assert _post(client, f'/prototypes/{p["slug"]}/delete').status_code == 404


# --------------------------------------------------------------- cloud guard seam

def test_web_writes_pass_the_access_guard_seam(store):
    """The write-requires-editor check: a guard (as sonaloop-cloud registers for its
    tenancy/role rules) sees every web write as `web.<action>` and can deny it."""
    seen = []

    def viewer_guard(operation, resource):
        seen.append(operation)
        if operation.startswith("web."):
            raise PermissionError("viewer role: read-only")

    proj = services.create_research_project("Guarded", store=store)
    client = _client()
    services.register_access_guard(viewer_guard)
    try:
        assert _post(client, "/projects/new", title="x").status_code == 403
        assert _post(client, f'/projects/{proj["id"]}/edit', title="x").status_code == 403
        assert _post(client, f'/projects/{proj["id"]}/delete', confirm="Guarded").status_code == 403
        assert _post(client, f'/projects/{proj["id"]}/notes/new', text="x").status_code == 403
    finally:
        _substrate.clear_access_guards()
    assert {"web.create_project", "web.update_project",
            "web.delete_project", "web.create_note"} <= set(seen)
    # nothing was written while the guard denied
    assert services.get_research_project(proj["id"], store=store)["title"] == "Guarded"
    assert len(services.list_research_projects(store=store)) == 1


def test_guard_denial_renders_a_403_page_not_a_traceback(store):
    services.register_access_guard(
        lambda op, res: (_ for _ in ()).throw(PermissionError()) if op.startswith("web.") else None)
    client = _client()
    r = _post(client, "/projects/new", title="x")
    assert r.status_code == 403
    assert "permission" in r.text


# ------------------------------------------------------------------- affordances (U9)

def test_no_create_affordances_anywhere_in_the_ui(store):
    """U9 (ux-contract §8.4): the UI inspects + edits — creation belongs to the MCP/CLI
    host. No "New …" button, no create-form link, no GET create form."""
    client = _client()
    html = client.get("/?lang=en").text             # empty DB -> first-steps checklist
    assert "/projects/new" not in html              # the checklist TELLS, it never links a form
    services.create_research_project("P", store=store)
    proj = services.list_research_projects(store=store)[0]
    assert "/projects/new" not in client.get("/projects?lang=en").text
    html = client.get(f'/projects/{proj["id"]}?lang=en').text
    assert f'/projects/{proj["id"]}/notes/new' not in html
    assert f'/projects/{proj["id"]}/sections/new' not in html
    # the GET create forms are gone; the POST routes stay as API surface
    assert client.get(f'/projects/{proj["id"]}/notes/new').status_code == 405
    assert client.get(f'/projects/{proj["id"]}/sections/new').status_code == 405


def test_edit_affordances_stay_and_delete_is_the_header_overflow(store):
    """U9: editing is unchanged; every delete lives in the subtle header overflow ("…")
    with the confirm <dialog> — zero danger zones render anywhere."""
    pid = create_persona(store, "Edith Editor")
    proj = services.create_research_project("P", persona_ids=[pid], store=store)
    client = _client()
    html = client.get(f'/projects/{proj["id"]}?lang=en').text
    assert f'/projects/{proj["id"]}/edit' in html
    assert f"/personas/{pid}/edit" in client.get(f"/personas/{pid}?lang=en").text
    edit_html = client.get(f'/projects/{proj["id"]}/edit?lang=en').text
    assert "danger-zone" not in edit_html and "Danger zone" not in edit_html
    assert "sl-overflow" in edit_html                       # the overflow menu …
    assert f'/projects/{proj["id"]}/delete' in edit_html    # … holds the delete action
    assert "danger-dialog" in edit_html                     # … which opens the confirm modal
    assert "Type the name to confirm" in edit_html          # typed confirm (server-checked)


def test_every_delete_surface_uses_the_overflow_pattern(store):
    """One consistent pattern (U9): council/synthesis/prototype detail pages and the
    note/section/persona edit pages all carry the overflow + dialog, no danger zone."""
    pid = create_persona(store, "Cara Council")
    proj = services.create_research_project("P", persona_ids=[pid], store=store)
    council = services.record_council(proj["id"], "Would you pay?", [pid],
                                      statements=[], store=store)
    syn = services.record_synthesis("Finding", "what did we learn?", [], {}, store=store)
    from sonaloop import prototypes
    proto = prototypes.register_artifact("signup-flow", "Signup flow", "prototypes/signup-flow",
                                         project_id=proj["id"], store=store)
    note = services.create_note(proj["id"], "saw a thing", title="Obs", store=store)
    sec = services.create_section(proj["id"], "Theme A", kind="theme", store=store)
    client = _client()
    surfaces = [
        (f'/councils/{council["id"]}', f'/councils/{council["id"]}/delete'),
        (f'/syntheses/{syn["id"]}', f'/syntheses/{syn["id"]}/delete'),
        (f'/prototypes/{proto["slug"]}', f'/prototypes/{proto["slug"]}/delete'),
        (f'/notes/{note["id"]}/edit', f'/notes/{note["id"]}/delete'),
        (f'/sections/{sec["id"]}/edit', f'/sections/{sec["id"]}/delete'),
        (f'/personas/{pid}/edit', f'/personas/{pid}/delete'),
    ]
    for page_url, delete_action in surfaces:
        html = client.get(f"{page_url}?lang=en").text
        assert "danger-zone" not in html, page_url
        assert "sl-overflow" in html and "danger-dialog" in html, page_url
        assert delete_action in html, page_url


def test_forms_render_in_german_too(store):
    proj = services.create_research_project("P", store=store)
    client = _client()
    html = client.get(f'/projects/{proj["id"]}/edit?lang=de').text
    assert "Titel" in html and "Speichern" in html
    assert "Gefahrenzone" not in html and "Projekt löschen" in html
