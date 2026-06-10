"""First-run diagnostics behind `sonaloop info` (ticket one-sentence-mcp-install).

Checks the MCP wiring end-to-end as far as it can locally: the server binary on PATH,
the data dir actually writable, the optional providers' status (headless browser,
embeddings), and whether any known MCP host config on this machine registers a
"sonaloop" server. When none does, the payload carries the EXACT per-host one-liners
so the agent (or human) can paste them verbatim.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

# The canonical one-sentence installs (documented verbatim in the README; keep in sync).
REGISTER_CLAUDE_CODE = "claude mcp add sonaloop -- uvx sonaloop-mcp"
REGISTER_JSON_SNIPPET: dict[str, Any] = {
    "mcpServers": {"sonaloop": {"command": "uvx", "args": ["sonaloop-mcp"]}}
}
DOCS_URL = "https://jhoetter.github.io/sonaloop-docs/"
DOCS_GETTING_STARTED_URL = "https://jhoetter.github.io/sonaloop-docs/getting-started/"


def _data_dir_writable(data_dir: Path) -> bool:
    """Probe with a real write (mkdir alone can lie on read-only mounts)."""
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _browser_ready() -> bool:
    """True when the playwright package AND the fetched chromium binary are present
    (`available()` alone only proves the pip package). Fail-soft: any error = not ready."""
    from . import browser as _browser

    if not _browser.available():
        return False
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


def _host_config_paths() -> dict[str, list[Path]]:
    """Where the known MCP hosts keep their server registrations on this platform."""
    home = Path.home()
    if sys.platform == "darwin":
        desktop = [home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"]
    elif sys.platform.startswith("win"):
        desktop = [Path(os.getenv("APPDATA", str(home / "AppData" / "Roaming"))) / "Claude"
                   / "claude_desktop_config.json"]
    else:
        desktop = [home / ".config" / "Claude" / "claude_desktop_config.json"]
    return {
        "claude_code": [home / ".claude.json", Path.cwd() / ".mcp.json"],
        "claude_desktop": desktop,
        "cursor": [home / ".cursor" / "mcp.json", Path.cwd() / ".cursor" / "mcp.json"],
    }


def _registered_in(path: Path) -> bool | None:
    """True/False when the host config is readable; None when the host isn't set up here."""
    try:
        if not path.exists():
            return None
        return '"sonaloop"' in path.read_text(encoding="utf-8")
    except OSError:
        return None


def mcp_wiring() -> dict[str, Any]:
    """The `mcp` section of `sonaloop info`: binary → data dir → host registration."""
    from . import config as _cfg

    registered: dict[str, bool | None] = {}
    for host, paths in _host_config_paths().items():
        states = [_registered_in(p) for p in paths]
        registered[host] = (True if any(s is True for s in states)
                            else False if any(s is False for s in states) else None)
    wiring: dict[str, Any] = {
        "server_binary": shutil.which("sonaloop-mcp"),
        "uvx_on_path": shutil.which("uvx") is not None,
        "data_dir_writable": _data_dir_writable(_cfg.DATA_DIR),
        "registered": registered,   # None = that host has no config on this machine
    }
    if not any(registered.values()):
        wiring["register"] = {
            "claude_code": REGISTER_CLAUDE_CODE,
            "claude_desktop_or_cursor_json": REGISTER_JSON_SNIPPET,
            "getting_started": DOCS_GETTING_STARTED_URL,
        }
    return wiring


def info_payload(version: str) -> dict[str, Any]:
    """Everything `sonaloop info` prints (stdout stays pure JSON for agents)."""
    from . import browser as _browser
    from . import config as _cfg
    from . import embeddings as _emb

    return {
        "version": version,
        "data_dir": str(_cfg.DATA_DIR),
        "db_path": str(_cfg.database_path()),
        "prototypes_dir": str(_cfg.prototypes_dir()),
        "source_checkout": _cfg._is_source_checkout(),
        "browser_available": _browser.available(),
        "browser_ready": _browser_ready(),
        "embeddings_enabled": _cfg.embeddings_enabled(),
        "embeddings_provider": _emb.active_provider(),
        "embeddings_model": _emb.provider_model(),
        "content_language": _cfg.content_language(),
        "docs": DOCS_URL,
        "mcp": mcp_wiring(),
    }


def register_hint_text(wiring: dict[str, Any]) -> str | None:
    """Human-readable per-host one-liners, printed to stderr after the JSON so stdout
    stays machine-parseable. None when sonaloop is already registered somewhere."""
    if not wiring.get("register"):
        return None
    return (
        "\nSonaloop is not registered as an MCP server in any host config found on this machine.\n"
        f"  Claude Code:             {REGISTER_CLAUDE_CODE}\n"
        "  Claude Desktop / Cursor:  add this to the host's MCP config (mcpServers):\n"
        f"    {json.dumps(REGISTER_JSON_SNIPPET)}\n"
        f"  Getting started: {DOCS_GETTING_STARTED_URL}"
    )
