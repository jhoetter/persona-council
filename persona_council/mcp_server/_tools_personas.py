from __future__ import annotations

import time
from typing import Any

from .. import services
from ..avatar import generate_persona_avatar
from ._env import _env


def register_personas(mcp):
    # ================= Persona / identity =================
    @mcp.tool()
    def brief_persona(description: str, segment_hint: str | None = None, evidence: str | None = None) -> dict[str, Any]:
        """Gather the prompt + frame to AUTHOR one persona profile from a source
        description. You write the profile JSON from `instructions`, then call
        record_persona. Detects/persists the content language from the description."""
        t = time.perf_counter()
        return _env("brief_persona", services.brief_persona(description, segment_hint, evidence), t)

    @mcp.tool()
    def record_persona(description: str, profile: dict[str, Any], segment_hint: str | None = None,
                       evidence: str | None = None, generate_avatar: bool = False) -> dict[str, Any]:
        """Validate + persist the persona profile you authored from brief_persona.
        This is the create path (no server-side text generation)."""
        t = time.perf_counter()
        return _env("record_persona", services.record_persona(description, profile, segment_hint, evidence, generate_avatar), t)

    @mcp.tool()
    def get_persona(persona_id: str) -> dict[str, Any]:
        """Full persona record + recent calendar/experience/pain points."""
        t = time.perf_counter()
        return _env("get_persona", services.get_persona(persona_id), t)

    @mcp.tool()
    def list_personas(filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """Compact list of all personas (overview before drilling in)."""
        t = time.perf_counter()
        return _env("list_personas", services.list_personas(filters), t)

    @mcp.tool()
    def get_persona_soul(persona_id: str) -> dict[str, Any]:
        """The persona's SOUL.md (authoritative identity + grown drift)."""
        t = time.perf_counter()
        return _env("get_persona_soul", services.get_persona_soul(persona_id), t)

    @mcp.tool()
    def prepare_persona_agent_context(persona_id: str, task: str | None = None, recent_events: int = 8) -> dict[str, Any]:
        """Build the launch context for a persona subagent (SOUL + state + recent events)."""
        t = time.perf_counter()
        return _env("prepare_persona_agent_context", services.prepare_persona_agent_context(persona_id, task, recent_events), t)

    @mcp.tool()
    def update_persona(persona_id: str, patch: dict[str, Any], reason: str) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("update_persona", services.update_persona(persona_id, patch, reason), t)

    @mcp.tool()
    def refresh_persona_from_source(persona_id: str) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("refresh_persona_from_source", services.refresh_persona_from_source(persona_id), t)

    @mcp.tool()
    def generate_avatar(persona_id: str, style: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("generate_avatar", generate_persona_avatar(persona_id, style), t)
