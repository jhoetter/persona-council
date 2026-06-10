"""`uvx sonaloop-mcp` shim (ticket one-sentence-mcp-install).

uvx resolves the requested command name as a PyPI DISTRIBUTION name, so the documented
one-liner `claude mcp add sonaloop -- uvx sonaloop-mcp` needs a package literally called
`sonaloop-mcp`. This is that package: a one-function shim that depends on `sonaloop` and
delegates to its MCP entrypoint. All real code lives in the main distribution.

Release: bump `version` here in lockstep with the main pyproject, then
`uv build && uv publish` from this directory.
"""
from __future__ import annotations


def main() -> None:
    from sonaloop.mcp_server import main as _main

    _main()
