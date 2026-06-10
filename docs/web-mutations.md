# Web mutations — the inspector's write boundary

The web inspector started as a strictly read-only SSR surface. It now carries a
**structural write path**: metadata and container operations are editable in the
browser, while every piece of authored or generated text stays host-authored
(the HOST-AUTHORS-ALL-TEXT invariant). This page documents the boundary, the
write-path pattern, and why some operations remain MCP-only.

## The mutation boundary

| Entity | Create | Edit | Delete | Notes |
| --- | --- | --- | --- | --- |
| Project | ✅ web (`/projects/new`) | ✅ title/goal/description | ✅ typed-confirmation (type the project title) | container metadata only; the graph/plan stays agent-driven |
| Persona | ❌ MCP-only (`brief_persona` → `record_persona`) | ✅ metadata: name, role title, segment, industry | ✅ typed-confirmation (type the display name) | see "Why persona create is MCP-only" |
| Note | ✅ web (`/projects/{id}/notes/new`) | ✅ title/text | ✅ | notes are *user/host-authored observations*, not generated prose — typing one in the browser **is** authoring |
| Section | ✅ web (`/projects/{id}/sections/new`) | ✅ title/kind/note | ✅ (member nodes untouched) | a section is a view; membership editing stays MCP (`add_to_section` …) |
| Council | ❌ | ❌ | ✅ delete only | statements are generated prose — never editable |
| Synthesis / report | ❌ | ❌ | ✅ delete only | report prose is authored/generated — never editable |
| Prototype | ❌ | ❌ | ✅ delete only | recorded artifacts |
| Memories, SOUL, evidence, councils' content, calendar days | ❌ | ❌ | ❌ | host-authored / generated — MCP/CLI only |

Everything in the ✅ columns goes through the **existing service layer**
(`sonaloop.services`) — the web routes never touch the `Store` for writes, so
lifecycle events, hooks, the event bus (SSE/activity feed) and cloud guards all
keep firing. Two service functions were added for the web path and are equally
available to MCP/CLI: `update_research_project(project_id, patch)` and
`update_note(note_id, patch)`.

## Why persona create is MCP-only

`record_persona` (the only create path) requires the **complete host-authored
profile JSON** produced by the `brief_persona` protocol: goals, pain points,
personality, relationships, success criteria, … — prose authored by the agent
against the briefing instructions, validated by `validate_profile_payload`. The
generated SOUL is then derived from that profile. There is no meaningful
"structural shell" subset that passes validation, and a web form that asked a
human to hand-type the full profile would bypass the briefing protocol that
keeps personas evidence-shaped. The web therefore offers **metadata edit +
delete** only; creation stays with the agent.

## The write-path pattern (web/_forms.py)

Every mutating route follows one shape:

1. `GET /thing/new` or `/thing/{id}/edit` renders a plain HTML form
   (`form_page`/`field`, design-system `.sl-field` markup, no JS required).
2. `POST` to the same URL runs `write_gate(form, operation, resource)`:
   - **CSRF** check first (403 on failure),
   - then the **cloud access-guard seam** (403 on `PermissionError`).
3. Server-side validation; on failure the SAME form re-renders with inline
   errors and HTTP **400**.
4. The service call, then **303 See Other** to the entity page
   (POST-redirect-GET — a refresh never re-submits).
5. Unknown ids answer HTTP **404** (the calm empty-state page).

Destructive actions live in one consistent **danger zone** (red-bordered block).
Projects and personas use a typed-confirmation modal (a native `<dialog>`; the
server re-checks `confirm == name` — the JS is convenience, not protection).
The other entities use a one-click delete form with a JS `confirm()`.

### CSRF: double-submit cookie

The app has no server-side session store, so CSRF protection is stateless: a
middleware issues a random token in an `sl_csrf` cookie (`SameSite=Lax`,
`HttpOnly`), every form embeds the same token in a hidden `csrf_token` field
(`csrf_field()`), and a POST is accepted only when cookie and field match
(constant-time compare). A cross-site attacker can make the browser *send* the
cookie but can neither read it nor set a cookie for this origin, so it cannot
produce the matching field. Chosen over a signed token because it needs no key
management and is equally robust for a same-origin SSR app.

### The cloud guard seam

`services.check_access(operation, resource)` runs the SAME guard list that
`register_access_guard` feeds for substrate queries (`services/_substrate.py`).
Web writes call it with namespaced operations — `web.create_project`,
`web.update_persona`, `web.delete_council`, … — so sonaloop-cloud's tenancy
guard can enforce its editor+ write rule for every browser mutation with one
registration, without core importing anything cloud-specific. Locally the guard
list is empty and every call passes.
