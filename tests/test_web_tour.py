"""Opt-in product tour (web/_tour.py): chrome presence, the quiet sidebar-footer offer
(ux-contract §9 V7 — it retired the one-time floating toast), i18n'd copy, and THE
CANARY — every step's selector must keep existing in the rendered chrome (the
palette-canary spirit: the tour cannot rot silently when the chrome changes)."""
from __future__ import annotations

import re

from starlette.testclient import TestClient

from sonaloop import services, web
from sonaloop.web._i18n import STRINGS, _UI_LANG
from sonaloop.web._tour import tour_steps


def _client():
    return TestClient(web.create_app())


def test_tour_chrome_is_injected_on_every_page(store):
    client = _client()
    for path in ("/?lang=en", "/personas", "/documentation"):
        html = client.get(path).text
        assert 'id="tourov"' in html, f"tour overlay missing on {path}"
        assert 'id="tour-cfg"' in html, f"tour config missing on {path}"
        assert "data-tour-start" in html, f"no tour trigger on {path}"


def test_tour_offer_is_a_sidebar_footer_row_not_a_toast(store):
    """V7: the floating offer toast retired; the quiet always-available offer is ONE row
    in the sidebar footer's `.sl-nav` cluster (exactly the nav-row idiom, like Feedback
    and the `?` shortcuts hint) — and the tour still never auto-starts."""
    first = _client().get("/?lang=en")
    assert 'id="tour-offer"' not in first.text                   # the toast is gone …
    assert "tour-offer" not in first.headers.get("set-cookie", "")  # … and so is its cookie
    foot = first.text.split('class="sl-nav sl-sb-foot"')[1].split("</nav>")[0]
    assert STRINGS["en"]["tour_take"] in foot and "data-tour-start" in foot
    # the footer rows share ONE row contract: Feedback, the tour, the ? hint
    assert STRINGS["en"]["feedback_h"] in foot and "data-km-open" in foot
    assert foot.count('class="pi-hover"') == 3
    # never auto-start: the overlay ships hidden; only [data-tour-start] opens it
    assert re.search(r'id="tourov"[^>]*hidden', first.text)


def test_tour_has_six_localized_steps():
    assert len(tour_steps()) == 6
    for lang in ("de", "en"):
        token = _UI_LANG.set(lang)
        try:
            for s in tour_steps():
                assert s["title"].strip() and s["body"].strip()
                # localized through the catalog, not raw keys leaking into the UI
                assert not s["title"].startswith("tour_") and not s["body"].startswith("tour_")
        finally:
            _UI_LANG.reset(token)
    de = dict((s["sel"], s["title"]) for s in _steps_in("de"))
    en = dict((s["sel"], s["title"]) for s in _steps_in("en"))
    assert de.keys() == en.keys() and de != en                   # same steps, different copy


def _steps_in(lang: str):
    token = _UI_LANG.set(lang)
    try:
        return tour_steps()
    finally:
        _UI_LANG.reset(token)


def test_canary_every_step_selector_exists_in_the_rendered_chrome(store):
    """THE CANARY: each step anchors to the persistent chrome. A selector is either
    `<scope> a[href="…"]` (assert the link exists in the sidebar) or a bare `.class`
    (assert the class is rendered). Fails naming the dead selector when the chrome
    drops or renames a target — fix the step, don't let it rot."""
    # seed one project so the canary also holds on the NON-empty home (the normal case)
    services.create_research_project("Tour canary", goal="g", store=store)
    client = _client()
    html = client.get("/?lang=en").text
    sidebar = html.split('class="sl-sidebar"')[1].split("</aside>")[0]
    dead = []
    for s in tour_steps():
        m = re.search(r'a\[href="([^"]+)"\]$', s["sel"])
        if m:
            if f'href="{m.group(1)}"' not in sidebar:
                dead.append(s["sel"])
        else:
            cls = s["sel"].lstrip(".")
            assert re.fullmatch(r"[a-z-]+", cls), f"unsupported selector shape: {s['sel']}"
            if cls not in html:
                dead.append(s["sel"])
    assert not dead, f"tour steps point at chrome that no longer renders: {dead}"


def test_take_the_tour_link_on_home_both_states(store):
    client = _client()
    # empty DB: prominent on the first-steps card, beside the example loader
    empty = client.get("/?lang=en").text
    assert STRINGS["en"]["first_steps_h"] in empty
    assert STRINGS["en"]["tour_take"] in empty and "data-tour-start" in empty
    # populated home (projects list): exactly ONE entry point — the sidebar footer row
    # (V7); the old floating link under the list is gone (round-3 craft pass, C10).
    services.create_research_project("Tour link", goal="g", store=store)
    home = client.get("/?lang=en").text
    assert "tour-take-row" not in home
    assert STRINGS["en"]["tour_take"] in home and "data-tour-start" in home
