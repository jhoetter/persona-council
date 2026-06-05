from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_research(mcp):
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

    # M1 — the pre-HX3 constellation study-graph tools (add_study_to_project / set_study_themes /
    # link_studies) are RETIRED from the agent surface: the plan engine (add_task / link_evidence /
    # record_frame) is the single graph-building path. The service fns remain for internal callers +
    # the CLI (spec/mcp-surface-cleanup.md M1).

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
