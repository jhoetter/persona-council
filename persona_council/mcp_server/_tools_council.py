from __future__ import annotations

import time
from typing import Any

from .. import services
from ..config import MEMORY_SCHEMA_VERSION
from ._env import _env


def register_council(mcp):
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
