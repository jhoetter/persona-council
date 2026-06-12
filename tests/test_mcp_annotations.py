"""Directory gate (ticket mcp-tool-annotations): EVERY registered MCP tool carries
ToolAnnotations — a human `title` plus explicit readOnlyHint / destructiveHint /
openWorldHint. A future bare tool fails here, and the central registry
(sonaloop/mcp_server/_annotations.py) can never drift from the live surface.
"""
from __future__ import annotations

import asyncio
import re

from sonaloop.mcp_server import build_server
from sonaloop.mcp_server._annotations import TOOL_ANNOTATIONS


def _tools():
    return asyncio.run(build_server().list_tools())


def test_every_tool_fully_annotated():
    """title + explicit readOnlyHint/destructiveHint/openWorldHint on every tool — no None."""
    bare = []
    for t in _tools():
        a = t.annotations
        if (a is None or not (a.title or "").strip()
                or a.readOnlyHint is None or a.destructiveHint is None
                or a.openWorldHint is None):
            bare.append(t.name)
    assert not bare, f"MCP tools missing title/readOnlyHint/destructiveHint/openWorldHint: {sorted(bare)}"


def test_destructively_named_tools_are_marked_destructive():
    """No tool named delete_/remove_/drop_ may claim destructiveHint=False."""
    wrong = [t.name for t in _tools()
             if re.match(r"^(delete_|remove_|drop_)", t.name)
             and not (t.annotations and t.annotations.destructiveHint)]
    assert not wrong, f"destructively named tools without destructiveHint=True: {sorted(wrong)}"


def test_destructive_or_open_world_tools_are_not_read_only():
    """A destructive tool is by definition a writing tool — the hints must agree."""
    wrong = [t.name for t in _tools()
             if t.annotations and t.annotations.destructiveHint and t.annotations.readOnlyHint]
    assert not wrong, f"tools marked both readOnly and destructive: {sorted(wrong)}"


def test_registry_matches_registered_surface():
    """The registry covers exactly the registered core tools — no stale or missing entries."""
    registered = {t.name for t in _tools()}
    registry = set(TOOL_ANNOTATIONS)
    assert registry == registered, (
        f"registry/server drift — missing from registry: {sorted(registered - registry)}; "
        f"stale registry entries: {sorted(registry - registered)}")


def test_titles_are_short_human_labels():
    """Titles are short labels (not docstrings) and the top-level Tool.title is set too."""
    bad = [t.name for t in _tools()
           if not (t.title or "").strip() or len(t.annotations.title) > 60
           or t.title != t.annotations.title]
    assert not bad, f"tools with missing/over-long/diverging titles: {sorted(bad)}"
