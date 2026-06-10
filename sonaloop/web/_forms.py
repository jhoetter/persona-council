"""Shared write-path helpers for the inspector's CRUD forms (ticket web-crud-structure).

The inspector grew a WRITE path for structural/metadata operations (projects, notes,
sections, persona metadata, deletes). The boundary stays HOST-AUTHORS-ALL-TEXT:
generated/authored prose (council statements, synthesis prose, memories, SOUL
content) is never editable here — see docs/web-mutations.md for the full contract.

The ONE pattern every write route follows:
  GET  /thing/new | /thing/{id}/edit  -> plain HTML form (this module's components)
  POST same URL                       -> write_gate (CSRF + access guard)
                                         -> validate -> service call -> 303 See Other
Failure codes: 400 validation (form re-rendered with inline errors), 403 CSRF or
guard denial, 404 unknown id. All mutations go through sonaloop.services — never
the Store directly — so lifecycle events / hooks / cloud guards keep working.

CSRF: DOUBLE-SUBMIT COOKIE (stateless — the app has no session store, and a signed
token would need a key to manage; the cookie comparison needs neither). The
middleware issues a random token in an `sl_csrf` cookie (SameSite=Lax, HttpOnly)
and every form embeds the same token in a hidden field (csrf_field()). A POST is
accepted only when cookie and field match (constant-time compare). A cross-site
attacker can make the browser SEND the cookie but can neither read it nor set a
cookie on this origin, so it cannot forge the matching field.
"""
from __future__ import annotations

import contextvars
import hmac
import json
import secrets

from .. import services
from ..storage import Store
from ._i18n import t
from ._components import _icon, _layout, _empty_state
from ._html import h, raw, fragment, register_css

CSRF_COOKIE = "sl_csrf"
_CSRF: contextvars.ContextVar[str] = contextvars.ContextVar("csrf_token", default="")


def install_forms(app) -> None:
    """Install the CSRF middleware: every response is guaranteed a double-submit
    cookie, and the per-request token is exposed to csrf_field() via a contextvar
    (the same pattern as the UI-language middleware)."""

    @app.middleware("http")
    async def _csrf_cookie_middleware(request, call_next):
        token = request.cookies.get(CSRF_COOKIE) or ""
        fresh = not token
        if fresh:
            token = secrets.token_urlsafe(32)
        ctx = _CSRF.set(token)
        try:
            response = await call_next(request)
        finally:
            _CSRF.reset(ctx)
        if fresh:
            response.set_cookie(CSRF_COOKIE, token, max_age=60 * 60 * 24 * 365,
                                samesite="lax", httponly=True)
        return response


def csrf_field() -> str:
    """The hidden token field — embed in EVERY mutating <form>."""
    return h("input", {"type": "hidden", "name": "csrf_token", "value": _CSRF.get()})


def csrf_ok(form) -> bool:
    """Double-submit check: the posted hidden field must equal the request cookie."""
    cookie, field = _CSRF.get(), str(form.get("csrf_token") or "")
    return bool(cookie) and bool(field) and hmac.compare_digest(cookie, field)


def write_gate(form, operation: str, resource: dict | None = None):
    """The shared front door of every POST route: CSRF first, then the cloud
    access-guard seam (services.check_access -> register_access_guard). Returns an
    error response to send back, or None to proceed. Operations are namespaced
    `web.<action>` so a tenancy guard can hold one editor+ rule for all web writes."""
    if not csrf_ok(form):
        return forbidden(t("csrf_invalid"))
    try:
        services.check_access("web." + operation, resource or {})
    except PermissionError:
        return forbidden(t("write_forbidden"))
    return None


def forbidden(message: str):
    from fastapi.responses import HTMLResponse
    store = Store()
    return HTMLResponse(_layout(t("not_allowed"), _empty_state(t("not_allowed"), message,
                                                               icon="warning"), store),
                        status_code=403)


def not_found(icon: str = "projects", active: str = "projects"):
    """The write-path 404 — same calm empty-state as read routes, but with a real
    404 status (forms post to ids that can vanish under them)."""
    from fastapi.responses import HTMLResponse
    store = Store()
    return HTMLResponse(_layout(t("not_found"), _empty_state(t("not_found"), t("runtime_maybe_cleared"),
                                                             icon=icon), store, active=active),
                        status_code=404)


def see_other(url: str):
    """POST-redirect-GET: every successful mutation answers 303 to the entity page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url, status_code=303)


# --------------------------------------------------------------------- components

def field(name: str, label: str, value: str = "", *, error: str = "", required: bool = False,
          textarea: bool = False, hint: str = "") -> str:
    """One labeled form control (design-system .sl-field), with the inline error
    rendered under the control when server-side validation re-renders the form."""
    ctrl = (h("textarea", {"class_": "sl-textarea", "id": f"f-{name}", "name": name, "rows": "5"}, value)
            if textarea else
            h("input", {"class_": "sl-input", "id": f"f-{name}", "name": name, "type": "text",
                        "value": value}))
    return h("div", {"class_": "sl-field" + (" sl-field--invalid" if error else "")},
             h("label", {"class_": "sl-field__label", "for": f"f-{name}"}, label,
               h("span", {"class_": "sl-field__req"}, " *") if required else None),
             ctrl,
             h("p", {"class_": "sl-field__error"}, error) if error else None,
             h("p", {"class_": "sl-field__hint"}, hint) if hint else None)


def form_page(store, *, title: str, crumbs: list, active: str, action: str,
              fields: list, submit_label: str, cancel_href: str, lead: str = "",
              danger: str = "") -> str:
    """The shared form-page shell: heading, the POST form (CSRF field included),
    submit/cancel, and an optional danger zone below."""
    body = h("div", {"class_": "page"},
             h("h1", {"class_": "h1"}, title),
             h("p", {"class_": "lead"}, lead) if lead else None,
             h("form", {"class_": "wform", "method": "post", "action": action},
               raw(csrf_field()), fragment(*fields),
               h("div", {"class_": "wform-actions"},
                 h("button", {"class_": "sl-btn sl-btn--primary", "type": "submit"}, submit_label),
                 h("a", {"class_": "sl-btn", "href": cancel_href}, t("cancel")))),
             raw(danger))
    return _layout(title, body, store, crumbs=crumbs, active=active)


def danger_zone(*forms) -> str:
    """The ONE destructive-actions area — same red-bordered block on every page
    that can delete something."""
    return h("div", {"class_": "danger-zone"},
             h("h2", {}, raw(_icon("warning")), " ", t("danger_zone")), fragment(*forms))


def confirm_delete_modal(action: str, expected: str, button_label: str, *,
                         error: str = "", dialog_id: str = "del-dialog") -> str:
    """Typed-confirmation delete (projects/personas): a native <dialog> modal asking
    the user to type the entity name; the SERVER re-checks `confirm` == name (the JS
    is convenience, never the protection). On mismatch the form page re-renders with
    the inline error and the dialog re-opened."""
    dlg = h("dialog", {"class_": "danger-dialog", "id": dialog_id},
            h("form", {"method": "post", "action": action},
              raw(csrf_field()),
              h("h3", {}, button_label),
              raw(field("confirm", t("confirm_type_name", name=expected),
                        error=error, required=True)),
              h("div", {"class_": "wform-actions"},
                h("button", {"class_": "sl-btn btn-danger", "type": "submit"}, button_label),
                h("button", {"class_": "sl-btn", "type": "button",
                             "onclick": f"document.getElementById('{dialog_id}').close()"},
                  t("cancel")))))
    opener = h("button", {"class_": "sl-btn btn-danger", "type": "button",
                          "onclick": f"document.getElementById('{dialog_id}').showModal()"},
               raw(_icon("trash")), " ", button_label)
    reopen = (raw("<script>document.getElementById(" + json.dumps(dialog_id)
                  + ").showModal()</script>") if error else "")
    return fragment(opener, h("p", {"class_": "sl-field__hint"}, t("delete_hint")), dlg, reopen)


def delete_button_form(action: str, button_label: str) -> str:
    """One-click delete with a JS confirm (notes/sections/councils/syntheses/
    prototypes — structural rows without a typed-confirmation requirement)."""
    return h("form", {"method": "post", "action": action, "class_": "danger-row",
                      "onsubmit": f"return confirm({json.dumps(t('delete_confirm_q'))})"},
             raw(csrf_field()),
             h("button", {"class_": "sl-btn btn-danger", "type": "submit"},
               raw(_icon("trash")), " ", button_label),
             h("span", {"class_": "sl-field__hint"}, t("delete_hint")))


def edit_button(href: str) -> str:
    """The topbar Edit affordance every editable detail page shows."""
    return h("a", {"class_": "sl-btn", "href": href}, raw(_icon("pencil")), " ", t("edit"))


# Co-located CSS (spec/roadmap.md R3): the write-form shell + the danger area/modal.
register_css(r"""
/* ---- write forms (web CRUD) ---- */
.wform{max-width:560px;display:flex;flex-direction:column;gap:14px;margin-top:10px}
.wform-actions{display:flex;gap:10px;margin-top:6px}
.btn-danger{border-color:var(--red,#ea4335);color:var(--red,#ea4335)}
.btn-danger:hover{background:var(--red,#ea4335);border-color:var(--red,#ea4335);color:#fff}
.danger-zone{max-width:560px;margin-top:34px;border:1px solid var(--red,#ea4335);border-radius:var(--radius);padding:14px 16px}
.danger-zone h2{display:flex;align-items:center;gap:7px;color:var(--red,#ea4335);font-size:var(--t-md);margin:0 0 10px}
.danger-zone h2 svg{width:16px;height:16px}
.danger-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:8px 0 0}
.danger-zone .sl-field{margin-top:8px}
.danger-dialog{border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);color:var(--ink);padding:18px;max-width:420px}
.danger-dialog h3{margin:0 0 12px}
.danger-dialog::backdrop{background:rgba(0,0,0,.45)}
""")
