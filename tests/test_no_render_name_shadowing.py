"""Guard: never shadow the render/i18n names in web modules (spec/roadmap.md R1).

`h` / `raw` / `fragment` / `esc` / `Safe` are the HTML builder (from ._html) and `t` is the i18n function
(from ._i18n). A local binding with one of those names — a loop var (`for h in …`), an unpack
(`x, y, w, h = …`), an assignment (`raw = lines[i]`), a param, a walrus, or a with/except as-name —
silently shadows the import and is a latent bug (it bit the C4 conversion ~4×). These names are ALWAYS
the import inside web modules, so the rule is absolute: don't rebind them.
"""
from __future__ import annotations

import ast
from pathlib import Path

from sonaloop import web

FORBIDDEN = {"h", "raw", "fragment", "esc", "Safe", "t"}
# _html.py defines the builder; _i18n.py defines t — they own the names, so they're exempt.
SKIP = {"_html.py", "_i18n.py"}


def _binding_names(node: ast.AST):
    """Yield (name, lineno) for every local binding target in a single statement/expr node."""
    targets: list[ast.AST] = []
    if isinstance(node, (ast.For, ast.AsyncFor)):
        targets = [node.target]
    elif isinstance(node, ast.Assign):
        targets = list(node.targets)
    elif isinstance(node, (ast.AugAssign, ast.AnnAssign, ast.NamedExpr)):
        targets = [node.target]
    elif isinstance(node, ast.comprehension):
        targets = [node.target]
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        targets = [it.optional_vars for it in node.items if it.optional_vars]
    elif isinstance(node, ast.ExceptHandler) and node.name:
        yield node.name, node.lineno
        return
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        a = node.args
        for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs, a.vararg, a.kwarg):
            if arg:
                yield arg.arg, arg.lineno
        return
    for tgt in targets:
        for n in ast.walk(tgt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                yield n.id, n.lineno


def test_no_render_name_shadowing():
    web_dir = Path(web.__file__).parent
    offenders = []
    for f in sorted(web_dir.rglob("*.py")):          # rglob: also covers the web/pages/ package (R2)
        if f.name in SKIP:
            continue
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            for name, lineno in _binding_names(node):
                if name in FORBIDDEN:
                    offenders.append(f"{f.name}:{lineno} rebinds '{name}' (shadows the render/i18n import)")
    assert not offenders, (
        "render/i18n names must not be shadowed by locals in web modules — rename them:\n  "
        + "\n  ".join(sorted(set(offenders)))
    )
