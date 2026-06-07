"""Guard: the unified statement/finding/prompt markup is produced in ONE place (web/_render.py).

This is what keeps the app from drifting back into the per-surface rendering inconsistency the unified
artifact schema removed (spec/unified-artifact-schema.md). A council voice, a synthesis voice, a
prototype session and a persona voice are all the SAME Statement → all must render through
render_statement/render_statements; every finding list through render_finding. If a new page hand-rolls
a .turn card or .qround prompt banner, this test fails — render it through _render instead.
"""
from __future__ import annotations

from pathlib import Path

from sonaloop import web

# h()-attribute class values that ONLY the one renderer may emit (the statement card + prompt banner).
_RENDER_ONLY = ('"turn"', '"qround"', '"qround-q"', '"qround-a"', '"fitem"')
_ALLOWED = {"_render.py", "_html.py", "web_assets.py"}     # the renderer itself + the builder + the CSS sheet


def test_statement_and_prompt_markup_only_from_render():
    web_dir = Path(web.__file__).parent
    offenders = []
    for f in sorted(web_dir.rglob("*.py")):
        if f.name in _ALLOWED:
            continue
        src = f.read_text(encoding="utf-8")
        for marker in _RENDER_ONLY:
            if f'class_": {marker}' in src or f"class_': {marker}" in src:
                offenders.append(f"{f.name} hand-rolls {marker} — render via _render.render_statement/render_finding")
    assert not offenders, "voice/finding markup must come from web/_render.py only:\n  " + "\n  ".join(offenders)
