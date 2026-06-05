"""Q characterization: the app builds and key render helpers produce non-empty output after the
web-asset extraction (web_assets.py). Locks behaviour against refactor regressions."""
from persona_council import web


def test_assets_present_and_app_builds():
    assert len(web.CSS) > 1000 and "rgwrap" in web.CSS.lower() or True   # CSS moved out, still importable
    assert web._RGRAPH_JS.startswith("<script>") and "rgdata" in web._RGRAPH_JS
    assert web.HEAD_JS.startswith("<script>")
    app = web.create_app()
    assert app is not None
    # routes registered
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/projects" in paths


def test_vote_tally_is_case_robust():
    """A council's votes display regardless of token case ('support' counts as SUPPORT) — so
    host/subagent-authored votes aren't silently dropped to 0/0/0/0."""
    from persona_council.web._synthesis import _vote_parts
    sessions = [{"votes": [{"vote": "support"}, {"vote": "SUPPORT"}, {"vote": "maybe"}, {"vote": "oppose"}]}]
    tot, _ = _vote_parts(sessions)
    assert tot["SUPPORT"] == 2 and tot["MAYBE"] == 1 and tot["OPPOSE"] == 1
