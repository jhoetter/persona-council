from __future__ import annotations

import contextvars  # noqa: F401  (public surface preserved)
from datetime import date, timedelta  # noqa: F401  (public surface preserved)

from ..config import DATA_DIR, load_env, set_ui_language
from ..config import SUPPORTED_LANGUAGES, ui_language  # noqa: F401  (public surface preserved)
from ._i18n import (  # noqa: F401  (public surface preserved)
    STRINGS, _UI_LANG, _lang, t, _resolve_request_language,
)
from ._components import *  # noqa: F401,F403  (re-export render helpers / assets)
from ._components import (  # noqa: F401  (explicit names used by callers/tests)
    CSS, HEAD_JS, _RGRAPH_JS,
    _esc, _icon, _avatar, _artifact_present, _proto_tags,
    _EDGE_COLORS, _theme_color,
)
from ._synthesis import *  # noqa: F401,F403  (re-export synthesis/voices/charts helpers)
from ._synthesis import (  # noqa: F401  (public surface preserved)
    _sentiment_section, _synthesis_html, _persona_voices_html,
)
from ._graph import (  # noqa: F401  (public surface preserved)
    _graph_layout, _graph_interactive, _graph_svg, _methodology_layout,
    _convex_hull, _expand_hull, _plan_html, _NW, _NH, _LAYOUT_VERSION,
)
from .pages import (  # noqa: F401  (public surface preserved; routes split into web/pages/ — R2)
    register_pages, _projects_page, _calendar_tabs,
    _event_chip, _period_calendar_html, _memory_html,
)
from ._routes_api import register_api  # noqa: F401
from ._ext import (  # noqa: F401  (public extension surface for sonaloop-cloud / sonaloop-research)
    register_nav_section, register_nav_item, register_slot,
    set_theme_overrides, reset_theme_overrides, set_brand, load_extensions,
)
from ._components import _layout as _layout  # noqa: F401  (wrapped publicly as render_page)


def render_page(title: str, body: str, store, *, crumbs=None, active: str = "",
                actions: str = "") -> str:
    """Render `body` inside the full core shell (sidebar, topbar, theme, command
    palette). The STABLE public entry point for downstream extension pages — use this
    instead of reaching into web._components. `body` is emitted as-is (extensions are
    trusted code); build it with the exported h()/raw()/fragment() helpers to get the
    same auto-escaping and component CSS as core pages."""
    return _layout(title, body, store, crumbs=crumbs, active=active, actions=actions)
from ._routes_lists import register_lists  # noqa: F401


def create_app():
    load_env()
    try:
        from fastapi import FastAPI, Query  # noqa: F401
        from fastapi.responses import HTMLResponse, JSONResponse  # noqa: F401
        from fastapi.staticfiles import StaticFiles
    except ImportError as exc:
        raise RuntimeError("Install web dependencies first: uv sync") from exc

    DATA_DIR.mkdir(parents=True, exist_ok=True)   # cold start: create the whole chain on first touch
    app = FastAPI(title="Sonaloop")
    # Absolute path (not cwd-relative "data"): downstream apps (sonaloop-cloud/-research)
    # call create_app() from their own working directory, so the mount must not depend on cwd.
    app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")
    # Serve prototype apps so they can be viewed directly in the inspector (read-only).
    from ..config import prototypes_dir as _proto_dir
    _pd = _proto_dir()
    _pd.mkdir(parents=True, exist_ok=True)
    app.mount("/proto-files", StaticFiles(directory=str(_pd), html=True), name="proto-files")

    @app.middleware("http")
    async def _ui_language_middleware(request, call_next):
        """Resolve the UI language per request (?lang= -> cookie -> setting), expose
        it to the render helpers via the contextvar, and persist an explicit choice."""
        lang, persist = _resolve_request_language(
            request.query_params.get("lang"), request.cookies.get("ui_lang"))
        token = _UI_LANG.set(lang)
        try:
            response = await call_next(request)
        finally:
            _UI_LANG.reset(token)
        if persist:
            response.set_cookie("ui_lang", lang, max_age=60 * 60 * 24 * 365, samesite="lax")
            set_ui_language(lang)
        return response

    # Write-path support (web CRUD): the double-submit CSRF cookie middleware. The
    # form/validation helpers live in web/_forms.py; routes in web/pages/edit.py.
    from ._forms import install_forms
    install_forms(app)

    register_pages(app)
    register_lists(app)
    register_api(app)
    # Discover installed web extensions (sonaloop-cloud / sonaloop-research). No-op when
    # none are installed, so the public core stays fully runnable on its own.
    load_extensions(app)
    return app


def main() -> None:
    import os
    import uvicorn

    host = os.getenv("PERSONA_COUNCIL_WEB_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("PERSONA_COUNCIL_WEB_PORT", "8787"))
    except ValueError:
        port = 8787
    url = f"http://{host}:{port}"
    print(
        "\n" + "─" * 56 + "\n"
        "  Sonaloop inspector is ready.\n"
        f"  → Open {url} in your browser.\n"
        + "─" * 56 + "\n",
        flush=True,
    )
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    main()
