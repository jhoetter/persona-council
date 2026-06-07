"""Auto-generated tool CATALOGUE — a browsable, by-domain index of the MCP surface.

Derived from the live tool modules (AST-parsed at request time), so it can never drift from the real
registry: every `@mcp.tool` / `@mcp.resource` / `@mcp.prompt` in a `_tools_*.py` file appears here,
grouped by its module's domain. Exposed as the `sonaloop://guide/catalogue` resource.
"""
from __future__ import annotations

import ast
import pathlib

# Friendly domain labels + a useful reading ORDER (the ESV happy path first, plumbing last).
_DOMAIN_LABELS = {
    "plan": "Plan engine & run loop (the core ESV path)",
    "council": "Councils & syntheses",
    "prototypes": "Prototypes & proband sessions",
    "sections": "Sections, notes & organization",
    "research": "Research projects, graph & meta-report",
    "methodology": "Methodologies (plan seeds)",
    "personas": "Personas (profiles + evidence)",
    "simulation": "Simulation & memory (days/months/recall/timeline)",
    "eval": "Evaluation & critics",
}
_ORDER = ["plan", "council", "prototypes", "sections", "research", "methodology",
          "personas", "simulation", "eval"]


def _deco_name(d: ast.expr) -> str:
    """The decorator's attribute name: @mcp.tool() -> 'tool', @mcp.resource(...) -> 'resource'."""
    target = d.func if isinstance(d, ast.Call) else d
    return target.attr if isinstance(target, ast.Attribute) else ""


def _entries_in_file(path: pathlib.Path) -> list[tuple[str, str, str]]:
    """(name, kind, one-line) for every mcp.tool/resource/prompt-decorated def in a module file."""
    out: list[tuple[str, str, str]] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return out
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        kinds = [k for k in (_deco_name(d) for d in node.decorator_list) if k in ("tool", "resource", "prompt")]
        if not kinds:
            continue
        doc = ast.get_docstring(node) or ""
        first = " ".join(doc.strip().split())[:150] if doc else ""
        out.append((node.name, kinds[0], first))
    return out


def catalogue_md() -> str:
    base = pathlib.Path(__file__).parent
    by_domain: dict[str, list[tuple[str, str, str]]] = {}
    extras: list[tuple[str, str, str]] = []          # resources + prompts (not domain tools)
    for f in sorted(base.glob("_tools_*.py")):
        domain = f.stem.replace("_tools_", "")
        for name, kind, first in _entries_in_file(f):
            if kind == "tool":
                by_domain.setdefault(domain, []).append((name, kind, first))
            else:
                extras.append((name, kind, first))
    total = sum(len(v) for v in by_domain.values())
    ndomains = sum(1 for v in by_domain.values() if v)
    lines = [
        "# Sonaloop — tool catalogue (by domain)",
        "",
        f"_{total} tools across {ndomains} domains — auto-generated from the live modules._",
        "",
        "Start with the **`sonaloop://guide/research`** resource for the canonical path "
        "(personas → start_project → start_run → loop run_step → finish). This is the full browsable "
        "index; every tool's response also carries a `next_recommended_tool` hint.",
        "",
    ]
    ordered = _ORDER + [d for d in sorted(by_domain) if d not in _ORDER]
    for d in ordered:
        items = by_domain.get(d) or []
        if not items:
            continue
        lines.append(f"## {_DOMAIN_LABELS.get(d, d)}  ({len(items)})")
        for name, _kind, first in sorted(items):
            lines.append(f"- **{name}** — {first or '—'}")
        lines.append("")
    if extras:
        lines.append("## Resources & prompts")
        for name, kind, first in sorted(extras):
            lines.append(f"- **{name}** ({kind}) — {first or '—'}")
        lines.append("")
    return "\n".join(lines)
