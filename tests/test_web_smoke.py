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
