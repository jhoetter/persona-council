from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_simulation(mcp):
    # ================= Planning (Phase A, multi-resolution) =================
    @mcp.tool()
    def brief_day(persona_id: str, date: str | None = None) -> dict[str, Any]:
        """GATHER context for planning ONE day (active projects, open threads, recall,
        world). Returns instructions for you to author a day plan; then put_day_plan."""
        t = time.perf_counter()
        return _env("brief_day", services.brief_day(persona_id, date), t)

    @mcp.tool()
    def put_day_plan(persona_id: str, date: str, plan: dict[str, Any]) -> dict[str, Any]:
        """Persist the day plan you authored from brief_day."""
        t = time.perf_counter()
        return _env("put_day_plan", services.put_day_plan(persona_id, date, plan), t)

    @mcp.tool()
    def record_day(persona_id: str, date: str, day_plan: dict[str, Any], plan: dict[str, Any],
                   activities: dict[str, Any], deltas: dict[str, Any] | None = None,
                   workday_start_hour: int | None = None, seed: str | None = None) -> dict[str, Any]:
        """Persist a host-authored SINGLE day end-to-end (put_day_plan -> simulate the
        authored blocks/activities -> optional consolidation). See brief_day's
        `day_bundle_hint` for the schema. Use record_month_bundle for whole months."""
        t = time.perf_counter()
        return _env("record_day", services.record_day(persona_id, date, day_plan, plan, activities, deltas, workday_start_hour, seed), t)

    @mcp.tool()
    def get_day_plan(persona_id: str, date: str) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_day_plan", services.get_day_plan(persona_id, date), t)

    @mcp.tool()
    def brief_period(persona_id: str, scope: str, date: str | None = None) -> dict[str, Any]:
        """GATHER context for a week|month|quarter|year plan, incl. candidate sample days.
        Author a period plan (with sample_days) then put_period_plan. Trends over long
        spans come from period plans + sampled days, not from simulating every day."""
        t = time.perf_counter()
        return _env("brief_period", services.brief_period(persona_id, scope, date), t)

    @mcp.tool()
    def put_period_plan(persona_id: str, scope: str, date: str, plan: dict[str, Any]) -> dict[str, Any]:
        """Persist a period plan (its sample_days drive which days you simulate concretely)."""
        t = time.perf_counter()
        return _env("put_period_plan", services.put_period_plan(persona_id, scope, date, plan), t)

    @mcp.tool()
    def get_period_plan(persona_id: str, scope: str, date: str) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_period_plan", services.get_period_plan(persona_id, scope, date), t)

    @mcp.tool()
    def list_period_plans(persona_id: str, scope: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("list_period_plans", services.list_period_plans(persona_id, scope), t)

    # ================= Simulation (Phase B) =================
    @mcp.tool()
    def simulate_day(persona_id: str, date: str | None = None, timezone: str | None = None, seed: str | None = None, constraints: dict[str, Any] | None = None) -> dict[str, Any]:
        """Simulate one workday (plan/memory-aware). Day text is host-authored. Then consolidate."""
        t = time.perf_counter()
        return _env("simulate_day", services.simulate_day(persona_id, date, timezone, seed, constraints), t)

    @mcp.tool()
    def simulate_range(persona_id: str, start_date: str, end_date: str, cadence: str | None = None, seed: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("simulate_range", services.simulate_range(persona_id, start_date, end_date, cadence, seed), t)

    @mcp.tool()
    def continue_simulation(persona_id: str | None = None, days: int = 1) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("continue_simulation", services.continue_simulation(persona_id, days), t)

    @mcp.tool()
    def clear_simulations() -> dict[str, Any]:
        """Delete all generated simulation + memory state (personas kept)."""
        t = time.perf_counter()
        return _env("clear_simulations", services.clear_simulations(), t)

    @mcp.tool()
    def purge_runtime_data(remove_files: bool = True) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("purge_runtime_data", services.purge_runtime_data(remove_files), t)

    # ================= Consolidation (Phase C) =================
    @mcp.tool()
    def brief_consolidation(persona_id: str, date: str | None = None) -> dict[str, Any]:
        """GATHER a simulated day + known entities. Returns instructions for you to author
        memory_deltas (entities/facts/threads/event_links); then record_memory_deltas."""
        t = time.perf_counter()
        return _env("brief_consolidation", services.brief_consolidation(persona_id, date), t)

    @mcp.tool()
    def record_memory_deltas(persona_id: str, date: str, deltas: dict[str, Any]) -> dict[str, Any]:
        """Persist host-authored memory deltas: resolves/dedupes entities, writes bi-temporal
        facts (invalidating superseded status), opens/resolves threads, links events, embeds."""
        t = time.perf_counter()
        return _env("record_memory_deltas", services.record_memory_deltas(persona_id, date, deltas), t)

    # ================= Digests (Phase D) =================
    @mcp.tool()
    def brief_digest(persona_id: str, scope: str, date: str | None = None) -> dict[str, Any]:
        """GATHER a period for a consolidated digest (replaces hardcoded reflections)."""
        t = time.perf_counter()
        return _env("brief_digest", services.brief_digest(persona_id, scope, date), t)

    @mcp.tool()
    def put_digest(persona_id: str, scope: str, date: str, digest: dict[str, Any]) -> dict[str, Any]:
        """Persist + embed the digest you authored from brief_digest."""
        t = time.perf_counter()
        return _env("put_digest", services.put_digest(persona_id, scope, date, digest), t)

    @mcp.tool()
    def list_digests(persona_id: str, scope: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("list_digests", services.list_digests(persona_id, scope), t)

    # ================= Memory retrieval (the "check history" surface) =================
    @mcp.tool()
    def recall_memory(persona_id: str, query: str, as_of: str | None = None, k: int = 8) -> dict[str, Any]:
        """Hybrid (semantic + keyword/entity + recency + importance) recall over episodes,
        facts, digests, threads. USE when you want to check if the past has something relevant.
        `as_of` respects bi-temporal validity for time-travel."""
        t = time.perf_counter()
        return _env("recall_memory", services.recall_memory(persona_id, query, as_of, k), t)

    @mcp.tool()
    def list_active_projects(persona_id: str) -> dict[str, Any]:
        """Compact list of the persona's open projects with status + open-loop counts."""
        t = time.perf_counter()
        return _env("list_active_projects", services.list_active_projects(persona_id), t)

    @mcp.tool()
    def get_project(persona_id: str, entity_id: str, as_of: str | None = None) -> dict[str, Any]:
        """Full fact/status timeline of one project (use `as_of` for how it looked then)."""
        t = time.perf_counter()
        return _env("get_project", services.get_project(persona_id, entity_id, as_of), t)

    @mcp.tool()
    def get_state_at(persona_id: str, as_of: str) -> dict[str, Any]:
        """Time-travel: entities + facts + open threads + world valid at a given date."""
        t = time.perf_counter()
        return _env("get_state_at", services.get_state_at(persona_id, as_of), t)

    @mcp.tool()
    def get_timeline(persona_id: str, start: str | None = None, end: str | None = None, entity_id: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_timeline", services.get_timeline(persona_id, start, end, entity_id), t)

    @mcp.tool()
    def search_entities(persona_id: str, kind: str | None = None, name: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("search_entities", services.search_entities(persona_id, kind, name), t)

    @mcp.tool()
    def get_open_loops(persona_id: str, status: str | None = "open") -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_open_loops", services.get_open_loops(persona_id, status), t)

    @mcp.tool()
    def resolve_entity(persona_id: str, mention: str, kind: str | None = None) -> dict[str, Any]:
        """Resolve a free-text mention to an existing entity (dedup), or null if new."""
        t = time.perf_counter()
        return _env("resolve_entity", services.resolve_entity(persona_id, mention, kind), t)

    @mcp.tool()
    def get_persona_memory(persona_id: str) -> dict[str, Any]:
        """Render + return MEMORY.md: active projects (timelines), open threads, digests."""
        t = time.perf_counter()
        return _env("get_persona_memory", services.get_persona_memory(persona_id), t)
