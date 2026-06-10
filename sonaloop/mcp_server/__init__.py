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
from ._tools_methodology import register_methodologies
from ._tools_jobs import register_jobs
from ._tools_plan import register_plan
from ._tools_prototypes import register_prototypes
from ._tools_surveys import register_surveys
from ._tools_hypotheses import register_hypotheses
from ._tools_usability import register_usability
from ._tools_council import register_council
from ._tools_sections import register_sections
from ._tools_hooks import register_hooks
from ._tools_assets import register_assets


def build_server():
    from mcp.server.fastmcp import FastMCP
    from ._prompts import SERVER_INSTRUCTIONS, register_prompts

    # `instructions` rides the initialize response so EVERY host (Claude, Cursor, ChatGPT, …) gets the
    # operating contract — the provider-agnostic counterpart to the Claude-only claude-skills/.
    mcp = FastMCP("sonaloop", instructions=SERVER_INSTRUCTIONS)

    register_personas(mcp)
    register_simulation(mcp)
    register_eval(mcp)
    register_research(mcp)
    register_methodologies(mcp)
    register_jobs(mcp)
    register_plan(mcp)
    register_prototypes(mcp)
    register_surveys(mcp)
    register_hypotheses(mcp)
    register_usability(mcp)
    register_council(mcp)
    register_sections(mcp)
    register_hooks(mcp)
    register_assets(mcp)
    register_prompts(mcp)

    from ._catalogue import catalogue_md

    @mcp.resource("sonaloop://guide/catalogue")
    def catalogue_guide() -> str:
        """A browsable, by-domain index of EVERY tool (auto-generated from the live modules)."""
        return catalogue_md()

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
