"""Page route modules (spec/roadmap.md R2 — split out of the old monolithic _routes_pages.py).

`register_pages(app)` wires every page-group's routes. Each group lives in its own module with a
`register_<group>(app)`. Calendar/memory helpers are re-exported here to preserve the public surface
that `web/__init__` and tests import."""
from __future__ import annotations

from ._calendar import _calendar_tabs, _event_chip, _period_calendar_html  # noqa: F401
from .personas import _memory_html, register_personas  # noqa: F401
from .councils import register_councils
from .syntheses import register_syntheses
from .projects import register_projects
from .library import register_library
from .surveys import register_surveys
from .hypotheses import register_hypotheses
from .decisions import register_decisions
from .sessions import register_sessions
from .activity import register_activity
from .._routes_lists import _projects_page  # noqa: F401  (re-export preserved)


def register_pages(app) -> None:
    register_projects(app)      # owns "/" (home = projects index)
    register_personas(app)
    register_councils(app)
    register_syntheses(app)
    register_library(app)
    register_surveys(app)
    register_hypotheses(app)   # the /hypotheses list — after projects' /hypotheses/{id} redirect
    register_decisions(app)    # the /decisions list — after projects' /decisions/{id} redirect
    register_sessions(app)
    register_activity(app)
