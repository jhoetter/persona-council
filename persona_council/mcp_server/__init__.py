from __future__ import annotations

import time
from typing import Any

from ..config import MEMORY_SCHEMA_VERSION, load_env
from .. import services
from ..avatar import generate_persona_avatar
from ._env import _NEXT, SERVER_VERSION, _env
from ._tools_personas import register_personas
from ._tools_simulation import register_simulation
from ._tools_eval import register_eval
from ._tools_research import register_research
from ._tools_methodology import register_methodology
from ._tools_plan import register_plan
from ._tools_prototypes import register_prototypes
from ._tools_council import register_council


def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("persona-council")

    register_personas(mcp)
    register_simulation(mcp)
    register_eval(mcp)
    register_research(mcp)
    register_methodology(mcp)
    register_plan(mcp)
    register_prototypes(mcp)
    register_council(mcp)

    return mcp


def main() -> None:
    load_env()
    try:
        mcp = build_server()
    except ImportError as exc:
        raise SystemExit("Install MCP dependencies first: uv sync") from exc
    mcp.run()


if __name__ == "__main__":
    main()
