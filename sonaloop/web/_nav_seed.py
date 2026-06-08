"""Seed the core sidebar through the SAME public registry an extension uses.

There is no privileged path for the core's own nav: it registers its sections and
items via register_nav_section/register_nav_item exactly as sonaloop-cloud or
sonaloop-research would, so downstream sections sit beside these (ordered by `order`).
Imported for its side effects by _components (the render side lives in _nav there).

Workspace = the inputs/containers; Library = the methodology-agnostic primitives any
methodology produces (council/concept/prototype/synthesis). Labels are lambdas so they
resolve per request (i18n). Within a section, item order follows list order.
"""
from __future__ import annotations

from ._i18n import t
from ._ext import register_nav_section, register_nav_item

register_nav_section("workspace", label=None, order=0)
register_nav_section("library", label=lambda: t("library_h"), order=10)

_CORE_NAV = {
    "workspace": [
        ("/projects", "projects", "projects", lambda: t("projects")),
        ("/personas", "personas", "personas", lambda: t("personas")),
        ("/documentation", "docs", "overview", lambda: t("documentation")),
    ],
    "library": [
        ("/notes", "note", "panel", lambda: t("notes")),
        ("/councils", "councils", "councils", lambda: t("councils")),
        ("/prototypes", "prototype", "prototype", lambda: t("prototypes_h")),
        ("/syntheses", "syntheses", "report", lambda: t("syntheses")),
    ],
}

for _section, _items in _CORE_NAV.items():
    for _order, (_href, _key, _icon, _label) in enumerate(_items):
        register_nav_item(_section, _href, _key, _icon, _label, _order)
