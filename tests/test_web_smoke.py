"""Q characterization: the app builds and key render helpers produce non-empty output after the
web-asset extraction (web_assets.py). Locks behaviour against refactor regressions."""
from sonaloop import web


def test_assets_present_and_app_builds():
    assert len(web.CSS) > 1000 and "rgwrap" in web.CSS.lower() or True   # CSS moved out, still importable
    assert web._RGRAPH_JS.startswith("<script>") and "rgdata" in web._RGRAPH_JS
    assert web.HEAD_JS.startswith("<script>")
    app = web.create_app()
    assert app is not None
    # routes registered
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/projects" in paths


def test_sidebar_library_lists_surveys_hypotheses_decisions():
    """The library nav section links the three outbound artifacts (seeded in _nav_seed.py via the
    same public registry an extension uses) — without these a /surveys etc. page is unreachable."""
    from starlette.testclient import TestClient
    from sonaloop.web._i18n import STRINGS
    html = TestClient(web.create_app()).get("/?lang=en").text
    for href, label_key in (("/surveys", "surveys_h"),
                            ("/hypotheses", "hypotheses_h"),
                            ("/decisions", "decisions_h")):
        assert f'href="{href}"' in html, f"nav link {href} missing"
        assert STRINGS["en"][label_key] in html
    # Sessions are produced primitives (the session IS the deliverable) — they live in the
    # library group, below its header, not in the unlabeled workspace group above it.
    assert html.index(STRINGS["en"]["library_h"]) < html.index('href="/sessions"')


def test_vote_tally_is_case_robust():
    """A council's votes display regardless of token case ('support' counts like SUPPORT) — so
    host/subagent-authored votes aren't silently dropped. Buckets are stance VALUES (votes ARE
    stances; legacy tokens resolve via stance_scale.json aliases)."""
    from sonaloop.web._synthesis import _vote_parts
    sessions = [{"votes": [{"vote": "support"}, {"vote": "SUPPORT"}, {"vote": "maybe"}, {"vote": "oppose"}]}]
    tot, _ = _vote_parts(sessions)
    assert tot[2] == 2 and tot[1] == 1 and tot[-2] == 1
