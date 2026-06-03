from __future__ import annotations

import time
from typing import Any

from .config import MEMORY_SCHEMA_VERSION, load_env
from . import services
from .avatar import generate_persona_avatar

SERVER_VERSION = "0.2.0"

# Implicit decision DAG: each tool hints the natural next
# step so the host agent can route the simulate -> consolidate -> digest loop.
_NEXT: dict[str, dict[str, Any]] = {
    "brief_persona": {"name": "record_persona", "reason": "persist the profile JSON you authored"},
    "record_persona": {"name": "brief_day", "reason": "plan the persona's first day before simulating"},
    "brief_day": {"name": "record_day", "reason": "author day_plan + activities, then persist the whole day"},
    "record_day": {"name": "brief_consolidation", "reason": "consolidate the day into memory"},
    "put_day_plan": {"name": "simulate_day", "reason": "simulate the planned day"},
    "simulate_day": {"name": "brief_consolidation", "reason": "consolidate the day into memory"},
    "brief_consolidation": {"name": "record_memory_deltas", "reason": "persist the entities/facts/threads you extracted"},
    "record_memory_deltas": {"name": "evaluate_simulation", "reason": "check quality, or brief_digest to roll up"},
    "brief_period": {"name": "put_period_plan", "reason": "persist the period plan + its sample_days"},
    "put_period_plan": {"name": "simulate_day", "reason": "simulate the chosen sample_days, then consolidate each"},
    "brief_digest": {"name": "put_digest", "reason": "persist the digest you authored"},
    "brief_persona_revision": {"name": "record_persona_revision", "reason": "persist the (usually small) identity drift"},
    "recall_memory": {"name": "get_project", "reason": "open the timeline of a project a hit pointed to"},
    "list_active_projects": {"name": "get_project", "reason": "open one project's full timeline"},
    "get_persona": {"name": "get_persona_memory", "reason": "see the rendered memory (active projects, threads)"},
    "brief_eval_critic": {"name": "record_eval_critic", "reason": "persist the semantic verdict you authored"},
    "record_eval_critic": {"name": "evaluate_simulation_full", "reason": "combined structural+semantic top verdict"},
    "brief_cohort_critic": {"name": "record_cohort_critic", "reason": "persist the cohort outlier verdict you authored"},
    "backfill_project_from_syntheses": {"name": "get_project_graph", "reason": "inspect the freshly-built project graph"},
    "create_research_project": {"name": "add_study_to_project", "reason": "attach studies as graph nodes"},
    "brief_meta_report": {"name": "record_meta_outline", "reason": "persist the outline you derived from the graph"},
    "record_meta_outline": {"name": "brief_meta_section", "reason": "author each section grounded in its source studies"},
    "brief_meta_section": {"name": "record_meta_section", "reason": "persist the authored section + citations"},
    "record_meta_section": {"name": "export_meta_report", "reason": "render the assembled meta-report"},
    "brief_month": {"name": "record_month_bundle", "reason": "persist the authored month bundle through the loop"},
    "record_month_bundle": {"name": "brief_month", "reason": "continue with the next month"},
    "brief_evidence_check": {"name": "record_evidence_check", "reason": "persist provenance verdict (confirmed/contradicted)"},
    "brief_synthesis": {"name": "record_synthesis", "reason": "persist the cross-council synthesis you authored"},
    "record_synthesis": {"name": "export_synthesis", "reason": "render the stakeholder report"},
    "brief_council": {"name": "record_council", "reason": "author the turns + synthesis, then persist the council"},
    "record_council": {"name": "brief_synthesis", "reason": "fold this council into a synthesis when you have several"},
    # --- methodology engine: tag-driven constellations (spec/methodology-constellations.md) ---
    "list_methodologies": {"name": "get_methodology", "reason": "inspect a constellation's steps before starting"},
    "get_methodology": {"name": "start_methodology_project", "reason": "bind a project to this methodology"},
    "start_methodology_project": {"name": "brief_next", "reason": "gather what the ready frontier needs"},
    "set_project_methodology": {"name": "brief_next", "reason": "gather what the ready frontier needs"},
    "brief_next": {"name": "record_node", "reason": "fan step: record_node each; decide step: record_decision"},
    "record_node": {"name": "record_judgment", "reason": "more nodes, or judge the fan's gate_tag"},
    "record_judgment": {"name": "advance", "reason": "advance the fan once its gate judgment is recorded"},
    "record_decision": {"name": "advance", "reason": "advance to recompute the frontier"},
    "advance": {"name": "brief_next", "reason": "gather what the next ready step needs"},
    "suggest_capabilities": {"name": "suggest_methodologies", "reason": "browse suggested step/whole-methodology templates"},
    # --- prototypes + harness ---
    "scaffold_prototype": {"name": "run_prototype", "reason": "start the generated app locally"},
    "run_prototype": {"name": "proto_open", "reason": "open the running app in a headless browser session"},
    "proto_open": {"name": "proto_act", "reason": "act on the snapshot (click/type), or proto_read"},
    "brief_prototype_session": {"name": "proto_open", "reason": "drive the app as the persona, then record the session"},
    "record_prototype_session": {"name": "brief_council", "reason": "fold the grounded reaction into a test council"},
}


def _env(tool: str, data: Any, started: float) -> dict[str, Any]:
    return {
        "ok": True,
        "data": data,
        "next_recommended_tool": _NEXT.get(tool),
        "_meta": {
            "tool": tool,
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
            "server_version": SERVER_VERSION,
            "schema_version": MEMORY_SCHEMA_VERSION,
        },
    }


def build_server():
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("persona-council")

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

    # ================= World, evolution, anomalies, eval =================
    @mcp.tool()
    def set_world_context(items: list[dict[str, Any]]) -> dict[str, Any]:
        """Set exogenous backdrop facts (season, regulation, market...). Not shared persona knowledge."""
        t = time.perf_counter()
        return _env("set_world_context", services.set_world_context(items), t)

    @mcp.tool()
    def get_world_context(as_of: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_world_context", services.get_world_context(as_of), t)

    @mcp.tool()
    def get_language() -> dict[str, Any]:
        """Read the active content language (host-authored text) and UI language."""
        from .config import content_language, ui_language
        t = time.perf_counter()
        return _env("get_language", {"content_language": content_language(), "ui_language": ui_language()}, t)

    @mcp.tool()
    def set_language(content_language: str | None = None, ui_language: str | None = None) -> dict[str, Any]:
        """Set the content language (de|en) for generated text and/or the web UI
        language. By default content is authored in the language the user writes in;
        use this to override. Returns the resulting settings."""
        from . import config as _cfg
        t = time.perf_counter()
        if content_language:
            _cfg.set_content_language(content_language, also_ui=ui_language is None)
        if ui_language:
            _cfg.set_ui_language(ui_language)
        return _env("set_language", {"content_language": _cfg.content_language(), "ui_language": _cfg.ui_language()}, t)

    @mcp.tool()
    def brief_persona_revision(persona_id: str, date: str | None = None) -> dict[str, Any]:
        """GATHER evidence (digests/facts) to propose SLOW identity drift. Change is the exception."""
        t = time.perf_counter()
        return _env("brief_persona_revision", services.brief_persona_revision(persona_id, date), t)

    @mcp.tool()
    def record_persona_revision(persona_id: str, revision: dict[str, Any]) -> dict[str, Any]:
        """Persist evidence-backed identity drift (re-renders SOUL); source identity preserved."""
        t = time.perf_counter()
        return _env("record_persona_revision", services.record_persona_revision(persona_id, revision), t)

    @mcp.tool()
    def list_persona_revisions(persona_id: str) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("list_persona_revisions", services.list_persona_revisions(persona_id), t)

    @mcp.tool()
    def list_memory_anomalies(persona_id: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("list_memory_anomalies", services.list_memory_anomalies(persona_id), t)

    @mcp.tool()
    def evaluate_simulation(persona_id: str | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        """Run the quality harness (uniformity, repetition, continuity, project movement,
        consistency, anti-steering). Returns green/warn/red — the measurable 'top' bar."""
        t = time.perf_counter()
        return _env("evaluate_simulation", services.evaluate_simulation(persona_id, start, end), t)

    # ----- F2 LLM critic (semantic eval) -----
    @mcp.tool()
    def brief_eval_critic(persona_id: str, start: str | None = None, end: str | None = None, sample_k: int | None = None) -> dict[str, Any]:
        """GATHER source+SOUL+sampled activities+arcs for a semantic critique. Author a
        verdict (anti_steering/in_character/dialogue/arc/mundane 0-5 + flags) then record.
        sample_k/threshold default from config (PERSONA_COUNCIL_CRITIC_SAMPLE_K / _THRESHOLD)."""
        t = time.perf_counter()
        return _env("brief_eval_critic", services.brief_eval_critic(persona_id, start, end, sample_k), t)

    @mcp.tool()
    def record_eval_critic(persona_id: str, verdict: dict[str, Any], start: str | None = None, end: str | None = None) -> dict[str, Any]:
        """Persist the host-authored critic verdict; flags low dimensions + items as anomalies."""
        t = time.perf_counter()
        return _env("record_eval_critic", services.record_eval_critic(persona_id, verdict, start, end), t)

    @mcp.tool()
    def evaluate_simulation_full(persona_id: str, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        """Combined 'top' verdict: structural harness + latest LLM critic (definition v2)."""
        t = time.perf_counter()
        return _env("evaluate_simulation_full", services.evaluate_simulation_full(persona_id, start, end), t)

    # ----- Cohort quality: diversity gate + cross-persona critic -----
    @mcp.tool()
    def evaluate_cohort_diversity(persona_ids: list[str] | None = None) -> dict[str, Any]:
        """Structural bulk-generation gate: flag near-duplicate personas and implausibly
        uniform cohorts (Jaccard over segment/role/pains/goals/tools). No authoring needed."""
        t = time.perf_counter()
        return _env("evaluate_cohort_diversity", services.evaluate_cohort_diversity(persona_ids), t)

    @mcp.tool()
    def brief_cohort_critic(persona_ids: list[str] | None = None, start: str | None = None, end: str | None = None) -> dict[str, Any]:
        """GATHER compact per-persona records across the cohort so you can judge which
        personas fall OUT of the cohort's range (relative outliers / clones). Then record."""
        t = time.perf_counter()
        return _env("brief_cohort_critic", services.brief_cohort_critic(persona_ids, start, end), t)

    @mcp.tool()
    def record_cohort_critic(verdict: dict[str, Any]) -> dict[str, Any]:
        """Persist the host-authored cohort critique (outliers + cohort_note) as an eval
        report + an anomaly per flagged outlier persona."""
        t = time.perf_counter()
        return _env("record_cohort_critic", services.record_cohort_critic(verdict), t)

    # ----- Research graph: Project container + typed study edges + theme tags -----
    @mcp.tool()
    def create_research_project(title: str, goal: str = "", persona_ids: list[str] | None = None,
                                description: str = "") -> dict[str, Any]:
        """Create a research Project: a themed GRAPH of studies (syntheses). Distinct from
        the memory get_project (a persona's own work project)."""
        t = time.perf_counter()
        return _env("create_research_project", services.create_research_project(title, goal, persona_ids, description), t)

    @mcp.tool()
    def list_research_projects() -> dict[str, Any]:
        """List research projects (graph containers) with study/edge/theme counts."""
        t = time.perf_counter()
        return _env("list_research_projects", services.list_research_projects(), t)

    @mcp.tool()
    def get_project_graph(project_id: str) -> dict[str, Any]:
        """The core navigation call: nodes (studies + theme tags + sentiment), typed edges,
        themes, build order, and open questions for one research project."""
        t = time.perf_counter()
        return _env("get_project_graph", services.get_project_graph(project_id), t)

    @mcp.tool()
    def add_study_to_project(project_id: str, study_id: str, theme_tags: list[str] | None = None) -> dict[str, Any]:
        """Attach an EXISTING synthesis (study) as a node in an EXISTING project graph
        (optionally with theme_tags). Use link_studies to connect it to other studies."""
        t = time.perf_counter()
        return _env("add_study_to_project", services.add_study_to_project(project_id, study_id, theme_tags), t)

    @mcp.tool()
    def set_study_themes(project_id: str, study_id: str, tags: list[str]) -> dict[str, Any]:
        """Assign LLM-derived theme tags to a study (grows the project's theme vocabulary)."""
        t = time.perf_counter()
        return _env("set_study_themes", services.set_study_themes(project_id, study_id, tags), t)

    @mcp.tool()
    def link_studies(project_id: str, from_study_id: str, to_study_id: str, type: str, rationale: str = "") -> dict[str, Any]:
        """Add a typed edge between two studies (spawned_from|refines|contrasts|depends_on|duplicates|answers)."""
        t = time.perf_counter()
        return _env("link_studies", services.link_studies(project_id, from_study_id, to_study_id, type, rationale), t)

    @mcp.tool()
    def record_open_questions(project_id: str, questions: list[str], study_id: str | None = None) -> dict[str, Any]:
        """Promote open questions raised by a study into first-class graph nodes."""
        t = time.perf_counter()
        return _env("record_open_questions", {"open_questions": services.record_open_questions(project_id, questions, study_id)}, t)

    @mcp.tool()
    def get_research_frontier(project_id: str) -> dict[str, Any]:
        """The anti-explosion surface: the project's still-open questions + structural notes."""
        t = time.perf_counter()
        return _env("get_research_frontier", services.get_research_frontier(project_id), t)

    @mcp.tool()
    def backfill_project_from_syntheses(title: str = "Research", synthesis_ids: list[str] | None = None) -> dict[str, Any]:
        """Group existing syntheses into one project graph (chronological spawned_from edges)."""
        t = time.perf_counter()
        return _env("backfill_project_from_syntheses", services.backfill_project_from_syntheses(title, synthesis_ids), t)

    # ----- Meta-Report: second-order synthesis over a whole project graph -----
    @mcp.tool()
    def brief_meta_report(project_id: str) -> dict[str, Any]:
        """GATHER the whole project graph + study content so you can author the meta-report OUTLINE."""
        t = time.perf_counter()
        return _env("brief_meta_report", services.brief_meta_report(project_id), t)

    @mcp.tool()
    def record_meta_outline(project_id: str, outline: dict[str, Any]) -> dict[str, Any]:
        """Persist the host-authored meta-report outline (sections derived from the graph)."""
        t = time.perf_counter()
        return _env("record_meta_outline", services.record_meta_outline(project_id, outline), t)

    @mcp.tool()
    def brief_meta_section(project_id: str, section_id: str, report_id: str | None = None) -> dict[str, Any]:
        """GATHER one section's source studies (+ councils) so you can author it with citations."""
        t = time.perf_counter()
        return _env("brief_meta_section", services.brief_meta_section(project_id, section_id, report_id), t)

    @mcp.tool()
    def record_meta_section(project_id: str, section_id: str, content: dict[str, Any], report_id: str | None = None) -> dict[str, Any]:
        """Persist one authored meta-report section (markdown + citations: study_id/council_id)."""
        t = time.perf_counter()
        return _env("record_meta_section", services.record_meta_section(project_id, section_id, content, report_id), t)

    @mcp.tool()
    def export_meta_report(project_id: str, report_id: str | None = None, format: str = "md") -> dict[str, Any]:
        """Render the assembled meta-report (md or json)."""
        t = time.perf_counter()
        return _env("export_meta_report", services.export_meta_report(project_id, report_id, format), t)

    # ============ Methodology engine: tag-driven constellations (structure+LLM-judged) ============
    # A methodology = a DAG of steps carrying OPEN TAGS. The engine is tag-agnostic; common
    # building blocks are SUGGESTED as data (suggest_*), never enforced. See
    # spec/methodology-constellations.md. Old tool names (brief_phase/record_exploration/
    # record_convergence/advance_phase) remain as aliases.
    @mcp.tool()
    def suggest_capabilities() -> dict[str, Any]:
        """SUGGESTED capability tags (explore/cluster/decide/build/test/synthesize, …) for a step's
        `tags`. Recommendations only — adopt, tweak, or invent your own; the engine never enforces."""
        t = time.perf_counter()
        return _env("suggest_capabilities", services.suggest_capabilities(), t)

    @mcp.tool()
    def suggest_roles() -> dict[str, Any]:
        """SUGGESTED role tags for a step's produces.role. Recommendations only."""
        t = time.perf_counter()
        return _env("suggest_roles", services.suggest_roles(), t)

    @mcp.tool()
    def suggest_artifact_types() -> dict[str, Any]:
        """SUGGESTED artifact-type tags for produces.artifact_type / requires.*_tags (matched by
        tag-equality, no string is special-cased). Recommendations only."""
        t = time.perf_counter()
        return _env("suggest_artifact_types", services.suggest_artifact_types(), t)

    @mcp.tool()
    def suggest_methodologies() -> dict[str, Any]:
        """SUGGESTED whole-constellation templates to copy and adapt (the registered methodologies
        + any extra templates). Tags are free; nothing here constrains what you may author."""
        t = time.perf_counter()
        return _env("suggest_methodologies", services.suggest_methodologies(), t)

    @mcp.tool()
    def list_methodologies() -> dict[str, Any]:
        """List available methodologies (built-in + user-defined) and their step keys."""
        t = time.perf_counter()
        return _env("list_methodologies", services.list_methodologies(), t)

    @mcp.tool()
    def get_methodology(key: str) -> dict[str, Any]:
        """The full constellation spec for one methodology (steps, tags, consumes, produces, requires)."""
        t = time.perf_counter()
        return _env("get_methodology", services.get_methodology(key), t)

    @mcp.tool()
    def start_methodology_project(title: str, goal: str, methodology_key: str,
                                  persona_ids: list[str] | None = None, description: str = "") -> dict[str, Any]:
        """Create a research project bound to a methodology (the goal is the How-Might-We)."""
        t = time.perf_counter()
        return _env("start_methodology_project",
                    services.start_methodology_project(title, goal, methodology_key, persona_ids, description), t)

    @mcp.tool()
    def set_project_methodology(project_id: str, methodology_key: str) -> dict[str, Any]:
        """Bind an existing research project to a methodology (resets the frontier to the roots)."""
        t = time.perf_counter()
        return _env("set_project_methodology", services.set_project_methodology(project_id, methodology_key), t)

    @mcp.tool()
    def brief_next(project_id: str) -> dict[str, Any]:
        """GATHER what the ready frontier needs now: the primary ready step (+ the full ready set),
        its tags, strategy, unmet `requires`, consumed nodes. The engine's heartbeat — a fan step:
        record_node each + judge its gate_tag; a decide step: record_decision."""
        t = time.perf_counter()
        return _env("brief_next", services.brief_next(project_id), t)

    @mcp.tool()
    def brief_phase(project_id: str) -> dict[str, Any]:
        """Alias of brief_next, shaped like the legacy single-step brief."""
        t = time.perf_counter()
        return _env("brief_phase", services.brief_phase(project_id), t)

    @mcp.tool()
    def record_node(project_id: str, title: str, council_ids: list[str], payload: dict[str, Any],
                    start_input: str = "", step_id: str | None = None) -> dict[str, Any]:
        """Record ONE exploration node (a synthesis over council(s)) against a ready fan step."""
        t = time.perf_counter()
        return _env("record_node",
                    services.record_node(project_id, title, council_ids, payload, start_input, step_id=step_id), t)

    @mcp.tool()
    def record_exploration(project_id: str, title: str, council_ids: list[str], payload: dict[str, Any],
                           start_input: str = "") -> dict[str, Any]:
        """Alias of record_node."""
        t = time.perf_counter()
        return _env("record_exploration",
                    services.record_exploration(project_id, title, council_ids, payload, start_input), t)

    @mcp.tool()
    def record_judgment(project_id: str, step_id: str, gate_tag: str, decided: bool, rationale: str,
                        evidence_refs: list[str] | None = None) -> dict[str, Any]:
        """Record an evidence-backed LLM gate judgment on a step. `gate_tag` is a FREE tag (e.g.
        divergence_complete, or whatever the consuming decide step requires). The engine requires
        its presence to decide but never dictates its content or a number."""
        t = time.perf_counter()
        return _env("record_judgment",
                    services.record_judgment(project_id, step_id, gate_tag, decided, rationale, evidence_refs), t)

    @mcp.tool()
    def record_decision(project_id: str, title: str, from_node_ids: list[str], payload: dict[str, Any],
                        start_input: str = "", step_id: str | None = None) -> dict[str, Any]:
        """Consolidate a fan into one decision node on a ready decide step (validates the invariants)."""
        t = time.perf_counter()
        return _env("record_decision",
                    services.record_decision(project_id, title, from_node_ids, payload, start_input, step_id=step_id), t)

    @mcp.tool()
    def record_convergence(project_id: str, title: str, from_node_ids: list[str], payload: dict[str, Any],
                           start_input: str = "") -> dict[str, Any]:
        """Alias of record_decision."""
        t = time.perf_counter()
        return _env("record_convergence",
                    services.record_convergence(project_id, title, from_node_ids, payload, start_input), t)

    @mcp.tool()
    def advance(project_id: str, step_id: str | None = None) -> dict[str, Any]:
        """Mark a ready step complete and recompute the frontier (or loop back); errors if a
        decide step has no decision node yet."""
        t = time.perf_counter()
        return _env("advance", services.advance(project_id, step_id), t)

    @mcp.tool()
    def advance_phase(project_id: str) -> dict[str, Any]:
        """Alias of advance (primary ready step)."""
        t = time.perf_counter()
        return _env("advance_phase", services.advance_phase(project_id), t)

    @mcp.tool()
    def get_methodology_state(project_id: str) -> dict[str, Any]:
        """Step-by-step progress: status, node counts, judgments, decision nodes, tags, the DAG."""
        t = time.perf_counter()
        return _env("get_methodology_state", services.get_methodology_state(project_id), t)

    # ================= Prototypes (real, minimal, locally-runnable apps) =================
    @mcp.tool()
    def scaffold_prototype(slug: str, name: str, concept: dict[str, Any], kind: str = "web",
                           template: str = "spa-min", project_id: str | None = None,
                           fidelity: str | None = None) -> dict[str, Any]:
        """Generate a real, minimal, runnable web app from a host-authored concept (screens +
        elements) and register it. The app is genuinely clickable (real DOM) for Playwright.
        template: 'spa-min' (mid-fi, clean) or 'spa-sketch' (lo-fi). fidelity overrides default."""
        t = time.perf_counter()
        return _env("scaffold_prototype",
                    services.scaffold_prototype(slug, name, concept, kind, template, project_id, fidelity), t)

    @mcp.tool()
    def register_prototype(slug: str, name: str, path: str, entry: str = "index.html", run: str = "static",
                           run_cmd: str | None = None, version: str = "v0.1", project_id: str | None = None,
                           notes: str = "", fidelity: str = "midfi") -> dict[str, Any]:
        """Register a hand-authored app under prototypes/ as a runnable artifact (fidelity: lofi|midfi)."""
        t = time.perf_counter()
        return _env("register_prototype",
                    services.register_prototype(slug, name, path, entry, run, run_cmd, version, project_id, notes, fidelity), t)

    @mcp.tool()
    def list_prototypes(project_id: str | None = None) -> dict[str, Any]:
        """List registered prototype artifacts (optionally for one project)."""
        t = time.perf_counter()
        return _env("list_prototypes", services.list_prototypes_artifacts(project_id), t)

    @mcp.tool()
    def get_prototype(prototype_id: str) -> dict[str, Any]:
        """One prototype artifact by id or slug."""
        t = time.perf_counter()
        return _env("get_prototype", services.get_prototype_artifact(prototype_id), t)

    @mcp.tool()
    def run_prototype(prototype_id: str) -> dict[str, Any]:
        """Start the app on an ephemeral localhost port; returns {url, pid}. Local-only."""
        t = time.perf_counter()
        return _env("run_prototype", services.run_prototype(prototype_id), t)

    @mcp.tool()
    def stop_prototype(prototype_id: str) -> dict[str, Any]:
        """Stop a running prototype."""
        t = time.perf_counter()
        return _env("stop_prototype", services.stop_prototype(prototype_id), t)

    @mcp.tool()
    def delete_prototype(prototype_id: str) -> dict[str, Any]:
        """Delete a prototype artifact record (files on disk are kept)."""
        t = time.perf_counter()
        return _env("delete_prototype", services.delete_prototype_artifact(prototype_id), t)

    # ================= Playwright harness — agents drive the real app =================
    @mcp.tool()
    def proto_open(prototype_id: str | None = None, url: str | None = None,
                   persona_id: str | None = None) -> dict[str, Any]:
        """Open a real running app in a headless browser session; returns {session_id, snapshot}."""
        t = time.perf_counter()
        return _env("proto_open", services.proto_open(prototype_id, url, persona_id), t)

    @mcp.tool()
    def proto_act(session_id: str, action: dict[str, Any]) -> dict[str, Any]:
        """Act on the latest snapshot: {type: click|type|select|scroll|key|wait, ref?, text?, value?}."""
        t = time.perf_counter()
        return _env("proto_act", services.proto_act(session_id, action), t)

    @mcp.tool()
    def proto_read(session_id: str) -> dict[str, Any]:
        """Re-read the current snapshot of a session."""
        t = time.perf_counter()
        return _env("proto_read", services.proto_read(session_id), t)

    @mcp.tool()
    def proto_close(session_id: str) -> dict[str, Any]:
        """Close a browser session."""
        t = time.perf_counter()
        return _env("proto_close", services.proto_close(session_id), t)

    @mcp.tool()
    def list_proto_sessions() -> dict[str, Any]:
        """List live browser sessions."""
        t = time.perf_counter()
        return _env("list_proto_sessions", services.list_proto_sessions(), t)

    @mcp.tool()
    def brief_prototype_session(persona_id: str, prototype_id: str) -> dict[str, Any]:
        """GATHER persona context + how-to-drive + anti-steering before a persona uses the app."""
        t = time.perf_counter()
        return _env("brief_prototype_session", services.brief_prototype_session(persona_id, prototype_id), t)

    @mcp.tool()
    def record_prototype_session(persona_id: str, prototype_id: str, session_id: str, date: str,
                                 reaction: dict[str, Any]) -> dict[str, Any]:
        """Persist a persona's grounded prototype use as an experience + memory + artifact;
        rejects claims with no matching observed state in the session log."""
        t = time.perf_counter()
        return _env("record_prototype_session",
                    services.record_prototype_session(persona_id, prototype_id, session_id, date, reaction), t)

    # ----- Deletes (CRUD complete; delete is MCP/CLI-only, never the read-only UI) -----
    @mcp.tool()
    def delete_research_project(project_id: str) -> dict[str, Any]:
        """Delete a project container + its edges/open-questions/meta-reports. Syntheses are kept."""
        t = time.perf_counter()
        return _env("delete_research_project", services.delete_research_project(project_id), t)

    @mcp.tool()
    def remove_study_from_project(project_id: str, study_id: str) -> dict[str, Any]:
        """Detach a study (synthesis) from a project (drops its edges there); keeps the synthesis."""
        t = time.perf_counter()
        return _env("remove_study_from_project", services.remove_study_from_project(project_id, study_id), t)

    @mcp.tool()
    def unlink_studies(project_id: str, from_study_id: str, to_study_id: str, type: str | None = None) -> dict[str, Any]:
        """Remove an edge (or all edges) between two studies in a project."""
        t = time.perf_counter()
        return _env("unlink_studies", services.unlink_studies(project_id, from_study_id, to_study_id, type), t)

    @mcp.tool()
    def delete_synthesis(synthesis_id: str) -> dict[str, Any]:
        """Delete a synthesis (study) and detach it from any project graphs."""
        t = time.perf_counter()
        return _env("delete_synthesis", services.delete_synthesis(synthesis_id), t)

    @mcp.tool()
    def delete_council(session_id: str) -> dict[str, Any]:
        """Delete a council session."""
        t = time.perf_counter()
        return _env("delete_council", services.delete_council(session_id), t)

    @mcp.tool()
    def delete_persona(persona_id: str) -> dict[str, Any]:
        """Delete a persona + all its persona-scoped rows and rendered SOUL/avatar files."""
        t = time.perf_counter()
        return _env("delete_persona", services.delete_persona(persona_id), t)

    # ----- F3 autonomous loop driver -----
    @mcp.tool()
    def brief_month(persona_id: str, month: str) -> dict[str, Any]:
        """GATHER context to author a whole month bundle (period plan + sample days + digest),
        chained on the prior month. Then record_month_bundle."""
        t = time.perf_counter()
        return _env("brief_month", services.brief_month(persona_id, month), t)

    @mcp.tool()
    def record_month_bundle(persona_id: str, month: str, bundle: dict[str, Any]) -> dict[str, Any]:
        """Persist a host-authored month bundle through the full loop (plan→sample days→
        simulate→consolidate→digest→embed)."""
        t = time.perf_counter()
        return _env("record_month_bundle", services.record_month_bundle(persona_id, month, bundle), t)

    # ----- F5 evidence integration -----
    @mcp.tool()
    def brief_evidence_check(persona_id: str) -> dict[str, Any]:
        """GATHER profile claims + attached evidence to validate synthesis against reality."""
        t = time.perf_counter()
        return _env("brief_evidence_check", services.brief_evidence_check(persona_id), t)

    @mcp.tool()
    def record_evidence_check(persona_id: str, result: dict[str, Any]) -> dict[str, Any]:
        """Persist provenance verdict: confirmed/contradicted/unsupported; flags contradictions."""
        t = time.perf_counter()
        return _env("record_evidence_check", services.record_evidence_check(persona_id, result), t)

    @mcp.tool()
    def backfill_embeddings(persona_id: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("backfill_embeddings", services.backfill_embeddings(persona_id), t)

    @mcp.tool()
    def prune_memory(persona_id: str, keep_days: int = 120, as_of: str | None = None) -> dict[str, Any]:
        """Salience forgetting: drop embeddings of old, unlinked, loop-free episodes."""
        t = time.perf_counter()
        return _env("prune_memory", services.prune_memory(persona_id, keep_days, as_of), t)

    # ================= Inspection (existing) =================
    @mcp.tool()
    def get_current_state(persona_id: str, at_time: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_current_state", services.get_current_state(persona_id, at_time), t)

    @mcp.tool()
    def get_calendar(persona_id: str, date: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_calendar", services.get_calendar(persona_id, date), t)

    @mcp.tool()
    def get_calendar_period(persona_id: str, date: str | None = None, view: str = "day") -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_calendar_period", services.get_calendar_period(persona_id, date, view), t)

    @mcp.tool()
    def get_activity(activity_id: str) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_activity", services.get_activity(activity_id), t)

    @mcp.tool()
    def summarize_persona_period(persona_id: str, start_date: str | None = None, end_date: str | None = None, lens: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("summarize_persona_period", services.summarize_persona_period(persona_id, start_date, end_date, lens), t)

    @mcp.tool()
    def extract_pain_points(persona_id: str, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("extract_pain_points", services.extract_pain_points(persona_id, start_date, end_date), t)

    # ================= Council =================
    @mcp.tool()
    def brief_council(prompt: str, persona_ids: list[str] | None = None, filters: dict[str, Any] | None = None,
                      count: int = 3, context: str | None = None) -> dict[str, Any]:
        """Gather a council. Without persona_ids: returns candidate personas to select
        from. With persona_ids: returns each participant's loaded agent context (SOUL +
        memory) to author turns against. Then author proposal/votes/exec_summary and
        call record_council. See the run-council skill."""
        t = time.perf_counter()
        return _env("brief_council", services.brief_council(prompt, persona_ids, filters, count, context), t)

    @mcp.tool()
    def brief_ask(persona_id: str, question: str, context: str | None = None) -> dict[str, Any]:
        """Gather one persona's loaded context (SOUL + recent events + task-keyed memory)
        so you can author an honest, in-character answer. No server-side generation."""
        t = time.perf_counter()
        return _env("brief_ask", services.brief_ask(persona_id, question, context), t)

    @mcp.tool()
    def record_council(prompt: str, persona_ids: list[str], turns: list[dict[str, Any]], votes: list[dict[str, Any]] | None = None, proposal: str = "", summary: str = "", exec_summary: str = "", selection_reason: str = "") -> dict[str, Any]:
        """Persist a host-authored council (openings/moderator/directed turns + votes +
        exec_summary). Use from the run-council / synthesize skills instead of writing the DB."""
        t = time.perf_counter()
        return _env("record_council", services.record_council(prompt, persona_ids, turns, votes, proposal, summary, exec_summary, selection_reason), t)

    @mcp.tool()
    def get_council(session_id: str) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_council", services.get_council(session_id), t)

    @mcp.tool()
    def list_councils() -> dict[str, Any]:
        t = time.perf_counter()
        return _env("list_councils", services.list_councils(), t)

    # ================= Evidence / export =================
    @mcp.tool()
    def attach_evidence(persona_id: str, source_type: str, content_or_path: str, notes: str | None = None) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("attach_evidence", services.attach_evidence(persona_id, source_type, content_or_path, notes), t)

    @mcp.tool()
    def export_persona(persona_id: str, format: str = "json") -> dict[str, Any]:
        t = time.perf_counter()
        return _env("export_persona", services.export_persona(persona_id, format), t)

    @mcp.tool()
    def export_logs(persona_id: str, start_date: str | None = None, end_date: str | None = None, format: str = "json") -> dict[str, Any]:
        t = time.perf_counter()
        return _env("export_logs", services.export_logs(persona_id, start_date, end_date, format), t)

    @mcp.tool()
    def export_council_session(session_id: str, format: str = "json") -> dict[str, Any]:
        t = time.perf_counter()
        return _env("export_council_session", services.export_council_session(session_id, format), t)

    @mcp.tool()
    def export_snapshot(out_dir: str | None = None) -> dict[str, Any]:
        """Write a portable snapshot of ALL generated state (profiles, SOUL/MEMORY,
        events, memory graph, eval, avatars) to data/export/ — gitignored/local-only."""
        t = time.perf_counter()
        return _env("export_snapshot", services.export_snapshot(out_dir), t)

    @mcp.tool()
    def import_snapshot(in_dir: str | None = None, embed: bool = True) -> dict[str, Any]:
        """Rebuild the runtime DB (+ avatars, SOUL/MEMORY) from data/export/. The portable
        round-trip: clone + import_snapshot reproduces the exact state, no re-generation."""
        t = time.perf_counter()
        return _env("import_snapshot", services.import_snapshot(in_dir, embed=embed), t)

    # ----- Synthesis (study arc over a chain of councils) -----
    @mcp.tool()
    def brief_synthesis(council_ids: list[str], title: str | None = None, start_input: str | None = None, goal: str | None = None) -> dict[str, Any]:
        """GATHER an ordered chain of councils (their exec_summaries/votes) so you can author
        a cross-council synthesis (arc, gesamtbild, recommendations, positioning, pain-solvers)."""
        t = time.perf_counter()
        return _env("brief_synthesis", services.brief_synthesis(council_ids, title, start_input, goal), t)

    @mcp.tool()
    def record_synthesis(title: str, start_input: str, council_ids: list[str], payload: dict[str, Any], goal: str = "", synthesis_id: str | None = None) -> dict[str, Any]:
        """Persist/UPDATE the host-authored synthesis over a council chain. Pass the same
        synthesis_id (and an EXTENDED council_ids list) to ADD more councils to an existing
        synthesis — re-authoring the report over the longer chain. Then add_study_to_project
        to place it in a project graph."""
        t = time.perf_counter()
        return _env("record_synthesis", services.record_synthesis(title, start_input, council_ids, payload, goal, synthesis_id), t)

    @mcp.tool()
    def get_synthesis(synthesis_id: str) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_synthesis", services.get_synthesis(synthesis_id), t)

    @mcp.tool()
    def list_syntheses() -> dict[str, Any]:
        t = time.perf_counter()
        return _env("list_syntheses", services.list_syntheses(), t)

    @mcp.tool()
    def export_synthesis(synthesis_id: str, format: str = "md") -> dict[str, Any]:
        """Render the synthesis as a stakeholder report (md|json), referencing each council."""
        t = time.perf_counter()
        return _env("export_synthesis", services.export_synthesis(synthesis_id, format), t)

    # ================= Resources & prompts =================
    @mcp.resource("persona-council://schema/memory")
    def memory_schema() -> str:
        """Read-only: the memory object model + the simulate->consolidate->digest loop."""
        return (
            "Persona Council memory model (schema v%d):\n"
            "- entities(kind: project|person|org|building|authority|topic, status)\n"
            "- entity_facts(fact, status, t_valid, t_invalid, importance)  # bi-temporal, time-travel\n"
            "- threads(open loops with identity), event_entities(links), embeddings(semantic recall)\n"
            "- plans(day|week|month|quarter|year), memory_digests, persona_revisions, world_context\n"
            "Loop per day: brief_day -> put_day_plan -> simulate_day -> brief_consolidation -> "
            "record_memory_deltas -> (brief_digest/put_digest periodically) -> evaluate_simulation.\n"
            "Long horizons: brief_period -> put_period_plan (with sample_days) -> simulate only those days.\n"
            "All text is authored by you (the MCP host). The server gathers context and persists."
            % MEMORY_SCHEMA_VERSION
        )

    @mcp.resource("persona-council://guide/research")
    def research_guide() -> str:
        """Read-only: how the research graph fits together and how to drive it via MCP."""
        return (
            "Persona Council — research workflow (Project > Synthesis > Council).\n"
            "\n"
            "HIERARCHY (each level contains the next):\n"
            "- Council  = one debate among personas (record_council). Lives INSIDE a synthesis.\n"
            "- Synthesis (a.k.a. study) = a chain of councils consolidated into one report\n"
            "  (brief_synthesis -> record_synthesis). Lives INSIDE a project.\n"
            "- Project  = a themed GRAPH of syntheses with typed edges (create_research_project).\n"
            "\n"
            "RUN A STUDY (one node of the graph):\n"
            "1. run_council/record_council  — author the turns+votes for a question.\n"
            "2. brief_synthesis([council_ids]) -> author -> record_synthesis  — fold councils into a report.\n"
            "3. add_study_to_project(project_id, synthesis_id, theme_tags=[...])  — place it in the graph.\n"
            "4. link_studies(project_id, from, to, type)  — connect it (spawned_from|refines|contrasts|\n"
            "   depends_on|duplicates|answers).\n"
            "\n"
            "ADD TO EXISTING THINGS:\n"
            "- Add a synthesis to an existing project: add_study_to_project(project_id, synthesis_id).\n"
            "- Add MORE councils to an existing synthesis: record the new council, then call\n"
            "  record_synthesis again with the SAME synthesis_id and the EXTENDED council_ids list\n"
            "  (re-authoring the report over the longer chain). This is the synthesize loop.\n"
            "- Tag/retag a study: set_study_themes(project_id, study_id, tags).\n"
            "- Promote/raise open questions: record_open_questions; close them with resolve_open_question.\n"
            "\n"
            "META-REPORT over the whole graph:\n"
            "  brief_meta_report -> record_meta_outline -> (per section) brief_meta_section ->\n"
            "  record_meta_section -> export_meta_report. Every section cites study_id/council_id.\n"
            "\n"
            "FRAMING TIPS:\n"
            "- Personas are STATELESS across councils: every council question must STAND ALONE\n"
            "  (include the essential briefing + the precise angle). They remember nothing of prior councils.\n"
            "- Seed with pain-discovery (no solution pitched); let the answers spawn UX/pricing/etc. studies.\n"
            "- Stay non-directional: do not nudge personas toward liking a product; rejection is valid.\n"
            "- Keep provenance: syntheses carry citations; meta-report sections cite study+council.\n"
            "- Inspect anytime: list_research_projects -> get_project_graph -> get_research_frontier."
        )

    @mcp.prompt()
    def simulate_persona_day(persona_id: str, date: str) -> str:
        """Playbook: drive one persona-day through the full memory loop."""
        return (
            f"Simulate persona {persona_id} on {date} with memory:\n"
            f"1. brief_day({persona_id}, {date}) -> author a day plan grounded in the briefing -> put_day_plan.\n"
            f"2. simulate_day({persona_id}, {date}).\n"
            f"3. brief_consolidation({persona_id}, {date}) -> author memory_deltas -> record_memory_deltas.\n"
            f"4. Periodically brief_digest/put_digest; run evaluate_simulation to check quality.\n"
            "Author all text yourself; ground it in SOUL + recalled memory; never steer toward a product thesis."
        )

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
