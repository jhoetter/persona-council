"""Extension seams for downstream private packages (sonaloop-cloud, sonaloop-research).

The public core stays FULLY runnable with zero extensions installed, and renders
bit-identically to before — every seam is additive and no-op when unused. Downstream
packages plug in WITHOUT the core ever importing them, via four seams:

  1. Routes  — entry_points(group="sonaloop.web.extensions"); each entry resolves to a
               callable invoked as `setup(app)` during create_app(), after core routes.
  2. Nav     — register_nav_section() / register_nav_item(); the sidebar iterates the
               registry. The core seeds its OWN defaults through the same API — there is
               no privileged path, so an extension's items sit beside the core's.
  3. Slots   — register_slot(name, fn); _layout() renders named insertion points
               ("head_extra", "sidebar_extra", "body_end"). fn(store) -> HTML string.
  4. Theme   — set_theme_overrides(mapping): a per-request contextvar (mirrors the
               i18n _UI_LANG pattern). _layout() injects a SANITIZED :root override so a
               tenant/project can carry its own design-system colors. Pure SSR — the
               override is plain CSS custom properties; nothing leaks into JS or data-*.

Labels are `str | Callable[[], str]`: pass a literal, or a lambda that resolves the
label per request when it must (i18n) — e.g. one that returns t(<your-key>). Slot/route callables are trusted
code (they ship inside a private package), so their returned HTML is emitted as-is.
"""
from __future__ import annotations

import contextvars
import re
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Nav registry
# ---------------------------------------------------------------------------
# A nav section is a heading + an ordered group of items. label=None => no heading
# (the core's "workspace" group). Sections and items are sorted by `order`; ties keep
# insertion order (stable sort), so registration order is the tie-break.

_LabelLike = "str | Callable[[], str] | None"

_NAV_SECTIONS: list[dict[str, Any]] = []
_NAV_ITEMS: list[dict[str, Any]] = []


def register_nav_section(section_id: str, label: Any = None, order: int = 0) -> None:
    """Register (or update) a sidebar section. Idempotent by section_id."""
    for s in _NAV_SECTIONS:
        if s["id"] == section_id:
            s["label"], s["order"] = label, order
            return
    _NAV_SECTIONS.append({"id": section_id, "label": label, "order": order})


def register_nav_item(section: str, href: str, key: str, icon: str,
                      label: Any, order: int = 0) -> None:
    """Register (or replace) a sidebar link. Idempotent by href so a re-import or an
    extension overriding a core entry does not duplicate the row."""
    for it in _NAV_ITEMS:
        if it["href"] == href:
            it.update(section=section, key=key, icon=icon, label=label, order=order)
            return
    _NAV_ITEMS.append({"section": section, "href": href, "key": key,
                       "icon": icon, "label": label, "order": order})


def resolve_label(label: Any) -> str:
    return label() if callable(label) else (label or "")


def nav_model() -> list[tuple[dict[str, Any], list[dict[str, Any]]]]:
    """Ordered [(section, [items])] for the sidebar to render. Empty sections are
    dropped (a heading with no links would render as a dangling label)."""
    out: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    for sec in sorted(_NAV_SECTIONS, key=lambda s: s["order"]):
        items = sorted((i for i in _NAV_ITEMS if i["section"] == sec["id"]),
                       key=lambda i: i["order"])
        if items:
            out.append((sec, items))
    return out


# ---------------------------------------------------------------------------
# Layout slots
# ---------------------------------------------------------------------------

_SLOTS: dict[str, list[Callable[[Any], str]]] = {}


def register_slot(name: str, fn: Callable[[Any], str]) -> None:
    """Register a render function for a named layout slot. Multiple registrations
    accumulate (rendered in registration order)."""
    _SLOTS.setdefault(name, []).append(fn)


def render_slot(name: str, store: Any) -> str:
    fns = _SLOTS.get(name)
    if not fns:
        return ""
    return "".join(fn(store) for fn in fns)


# ---------------------------------------------------------------------------
# Per-request theme overrides (design-system-per-tenant/project)
# ---------------------------------------------------------------------------

_THEME_OVERRIDES: contextvars.ContextVar[dict[str, str] | None] = contextvars.ContextVar(
    "theme_overrides", default=None)

# CSS-injection guard: a key must be a custom property; a value must be a small,
# safe subset (colors / numeric tokens). No `;`, `{`, `}`, or `:` to break out of the
# declaration block. Anything off-shape is silently dropped — the page still renders.
_VAR_RE = re.compile(r"^--[a-z0-9-]+$")
_VAL_RE = re.compile(r"^[#a-zA-Z0-9_.,%()\s/-]+$")


def set_theme_overrides(mapping: dict[str, str] | None) -> contextvars.Token:
    """Set per-request CSS custom-property overrides (e.g. {'--accent': '#0a7'}).
    Returns a token; pass it to reset_theme_overrides() in a finally block. Designed
    to be called from middleware once the active tenant/project is known."""
    return _THEME_OVERRIDES.set(dict(mapping) if mapping else None)


def reset_theme_overrides(token: contextvars.Token) -> None:
    _THEME_OVERRIDES.reset(token)


def theme_override_css() -> str:
    """A `<style>` block re-declaring the active overrides on :root, or "" when none.
    Emitted by _layout() AFTER the base stylesheet so it wins by cascade order."""
    ov = _THEME_OVERRIDES.get() or {}
    decls = [f"{k}:{v}" for k, v in ov.items()
             if _VAR_RE.match(str(k)) and _VAL_RE.match(str(v))]
    if not decls:
        return ""
    return '<style id="theme-overrides">:root{' + ";".join(decls) + "}</style>"


# ---------------------------------------------------------------------------
# Entry-point loader
# ---------------------------------------------------------------------------

def load_extensions(app: Any) -> list[str]:
    """Discover and run installed web extensions. Each entry in the
    `sonaloop.web.extensions` group resolves to a callable run as `setup(app)`.
    A broken extension is skipped (logged) rather than taking down the core."""
    from importlib.metadata import entry_points

    loaded: list[str] = []
    try:
        eps = entry_points(group="sonaloop.web.extensions")
    except TypeError:  # pragma: no cover - Python <3.10 selectable-API shim
        eps = entry_points().get("sonaloop.web.extensions", [])
    for ep in eps:
        try:
            ep.load()(app)
            loaded.append(ep.name)
        except Exception as exc:  # noqa: BLE001 - never let one extension break boot
            import logging
            logging.getLogger("sonaloop.web").warning(
                "extension %r failed to load: %s", ep.name, exc)
    return loaded
