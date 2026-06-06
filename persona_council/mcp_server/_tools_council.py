from __future__ import annotations

import time
from typing import Any

from .. import services
from ..config import MEMORY_SCHEMA_VERSION
from ._env import _env


def register_council(mcp):
    # M3 — persona timeline/activity reads (get_current_state/get_calendar/get_calendar_period/
    # get_activity/summarize_persona_period/extract_pain_points) moved to _tools_simulation (memory).

    # ================= Council =================
    @mcp.tool()
    def brief_council(project_id: str, prompt: str, persona_ids: list[str] | None = None, filters: dict[str, Any] | None = None,
                      count: int = 3, context: str | None = None) -> dict[str, Any]:
        """Gather a council. A council is scoped to a research project, so `project_id` is
        REQUIRED (create one first with create_research_project; personas are global and need
        no project). Without persona_ids: returns candidate personas to select from. With
        persona_ids: returns each participant's loaded agent context (SOUL + memory) to author
        turns against. Then author proposal/votes/exec_summary and call record_council. See the
        run-council skill."""
        t = time.perf_counter()
        return _env("brief_council", services.brief_council(project_id, prompt, persona_ids, filters, count, context), t)

    @mcp.tool()
    def brief_ask(persona_id: str, question: str, context: str | None = None) -> dict[str, Any]:
        """Gather one persona's loaded context (SOUL + recent events + task-keyed memory)
        so you can author an honest, in-character answer. No server-side generation."""
        t = time.perf_counter()
        return _env("brief_ask", services.brief_ask(persona_id, question, context), t)

    @mcp.tool()
    def record_council(project_id: str, prompt: str, persona_ids: list[str], turns: list[dict[str, Any]], votes: list[dict[str, Any]] | None = None, proposal: str = "", summary: str = "", exec_summary: str = "", selection_reason: str = "", questions: list[str] | None = None, key: str | None = None, statements: list[dict[str, Any]] | None = None, findings: list[dict[str, Any]] | None = None, prompts: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Persist a host-authored council. Shape it by what you pass (the UI derives the mode):
        DISCOVERY = `questions` (open user-research questions) + answer turns, NO proposal/votes;
        EVALUATION = `proposal` (a concept reacted to) + stances; DECISION = `proposal` + `votes`.
        DISCOVERY turns: author ONE turn per (persona, question) and set `question_index` (0-based
        index into `questions`) on each, so the council page renders a moderated Q→A transcript —
        the moderator's question, then each persona's answer to it. A turn that addresses no single
        question may omit it. Turn fields: persona_id, content, question_index, stance, memory_refs,
        input. A council MUST belong to a research project. Pass a stable `key` for a deterministic
        id (idempotent upsert → resumable runs).

        UNIFIED PRIMITIVES (spec/unified-artifact-schema.md, preferred going forward): instead of
        turns/votes you MAY pass `statements` (one per persona utterance: {persona_id, text, stance:
        {value -2..2,label}, about:{kind:'prompt',id}, refs:[{kind,id|text}], meta}) and `findings`
        (the analysis: {text, kind: summary|key_problem|recommendation|…, score, refs}) and `prompts`
        ({text, kind, id}). These render through the one renderer; legacy turns/votes still work."""
        t = time.perf_counter()
        return _env("record_council", services.record_council(project_id, prompt, persona_ids, turns, votes, proposal, summary, exec_summary, selection_reason, questions, key, statements, findings, prompts), t)

    @mcp.tool()
    def get_council(session_id: str) -> dict[str, Any]:
        t = time.perf_counter()
        return _env("get_council", services.get_council(session_id), t)

    @mcp.tool()
    def list_councils() -> dict[str, Any]:
        t = time.perf_counter()
        return _env("list_councils", services.list_councils(), t)

    # M3 — attach_evidence / export_persona (persona-scoped) moved to _tools_personas.

    # M2 — export_logs / export_snapshot / import_snapshot are operator backup/debug actions, CLI-only.

    @mcp.tool()
    def export_council_session(session_id: str, format: str = "json") -> dict[str, Any]:
        t = time.perf_counter()
        return _env("export_council_session", services.export_council_session(session_id, format), t)

    # ----- Synthesis (study arc over a chain of councils) -----
    @mcp.tool()
    def brief_synthesis(council_ids: list[str], title: str | None = None, start_input: str | None = None, goal: str | None = None) -> dict[str, Any]:
        """GATHER an ordered chain of councils (their exec_summaries/votes) so you can author
        a cross-council synthesis (arc, gesamtbild, recommendations, positioning, pain-solvers)."""
        t = time.perf_counter()
        return _env("brief_synthesis", services.brief_synthesis(council_ids, title, start_input, goal), t)

    @mcp.tool()
    def record_synthesis(title: str, start_input: str, council_ids: list[str] | None = None, payload: dict[str, Any] | None = None, goal: str = "", synthesis_id: str | None = None, key: str | None = None) -> dict[str, Any]:
        """Persist/UPDATE a host-authored synthesis. A synthesis is DECOUPLED from councils:
        `council_ids` is OPTIONAL (may be empty — affinity over notes, a synthesis over syntheses, or
        a standalone analysis); councils are cited evidence, not sub-parts. Pass the same synthesis_id
        (or a stable `key`) to update in place / make a long run resumable. Link it to its verify task
        with link_evidence."""
        t = time.perf_counter()
        return _env("record_synthesis", services.record_synthesis(title, start_input, council_ids, payload, goal, synthesis_id, key), t)

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
        """THE FRONT DOOR — read this first: the canonical path to drive a research project via MCP."""
        return (
            "Persona Council — the canonical research path (ESV). The PLAN is the single engine; a\n"
            "deterministic run loop drives it, an independent critic decides when it's DONE.\n"
            "\n"
            "0. PERSONAS FIRST. Ensure a richly-segmented cohort with simulated memory exists\n"
            "   (list_personas; if thin, build via the simulate-cohort skill / simulate_range +\n"
            "   record_month_bundle). Councils are only as deep as the lives behind them.\n"
            "\n"
            "1. START. start_project(title, goal=<How-Might-We>, methodology='double_diamond_deep',\n"
            "   persona_ids=[...]) seeds the analyze->act->verify plan. Then start_run(project_id,\n"
            "   budget=<steps>) creates the resumable run object.\n"
            "\n"
            "2. LOOP (you are the thin host over the engine). Repeat:\n"
            "     s = run_step(run_id)\n"
            "     - s.kind == 'done'   -> stop (status finished|capped|stopped).\n"
            "     - s.kind == 'critic' -> spawn an INDEPENDENT critic on s.brief; it authors the verdict,\n"
            "       calls record_completeness_critic + record_critic_round. (Loops until exhaustive.)\n"
            "     - else (analyze|act|verify) -> author ONE step grounded in s.next_action, keyed by\n"
            "       s.key; then checkpoint_step(run_id, {...}). Resumable: re-run start_run(run_id=...).\n"
            "\n"
            "3. AUTHOR a step:\n"
            "   - analyze (frame): read cited memory -> record_frame (research questions).\n"
            "   - act: run a COUNCIL or build+test a PROTOTYPE.\n"
            "       COUNCIL has three shapes (derived; the UI branches): pass `questions=[...]` for\n"
            "       open DISCOVERY ('Welche Versicherungen hast du? Wie sparst du gerade?') with NO\n"
            "       proposal/votes (you are LISTENING — hypotheses come LATER, in Define); a `proposal`\n"
            "       to REACT to a concept (evaluation); proposal+votes only for an explicit DECISION.\n"
            "       Flow: brief_council -> author turns (set each turn's persona_id, content, stance,\n"
            "       memory_refs, input; for DISCOVERY also question_index = which question it answers,\n"
            "       one turn per persona+question) -> record_council.\n"
            "       PROTOTYPE: scaffold_prototype(concept) -> run_prototype -> a grounded proband session\n"
            "       (proto_open -> proto_act -> proto_read -> proto_close) -> record_prototype_session.\n"
            "       Then add_task + link_evidence + complete_task.\n"
            "   - verify: consolidate the fan -> record_synthesis (structured: clusters/key_problems/\n"
            "       ranking/shortlist) -> record_judgment(gate) -> complete_task.\n"
            "\n"
            "4. FINISH (the engine drives this on recommendation=='finish'): derive_sections (organize)\n"
            "   + scaffold_meta_report -> brief_meta_section/record_meta_section + a rich terminal Deliver\n"
            "   synthesis. score_run(project_id) snapshots quality. DONE only when assess_project.finish\n"
            "   is finished AND the completeness critic passes.\n"
            "\n"
            "PRINCIPLES: personas are STATELESS per council (each prompt stands alone); stay\n"
            "anti-steering (rejection is valid — don't nudge toward a product); honest unknowns become\n"
            "open questions, never fake progress. INSPECT anytime: list_research_projects ->\n"
            "get_project_graph -> assess_project (the pulse: recommendation, gaps, novelty, finish).\n"
            "Browse EVERY tool by domain: the `persona-council://guide/catalogue` resource.\n"
            "Richer playbooks live in the skills: compose-research-plan / autonomous-research-run."
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
