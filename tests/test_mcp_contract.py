"""Item 1 (part A): the MCP tool surface — every result is enveloped, and the
gather→author→write-back tools (incl. the new cohort + critic tools) are
registered. This pins the contract the host agent depends on."""
from __future__ import annotations

import asyncio

from persona_council.mcp_server import build_server, _env


def test_envelope_shape():
    env = _env("demo_tool", {"x": 1}, 0.0)
    assert env["ok"] is True
    assert env["data"] == {"x": 1}
    assert set(env) == {"ok", "data", "next_recommended_tool", "_meta"}
    assert env["_meta"]["tool"] == "demo_tool"
    assert "latency_ms" in env["_meta"] and "schema_version" in env["_meta"]


def test_next_recommended_dag():
    # The decision DAG points each gather step at its write-back step.
    env = _env("brief_synthesis", {}, 0.0)
    assert env["next_recommended_tool"]["name"] == "record_synthesis"
    env2 = _env("brief_cohort_critic", {}, 0.0)
    assert env2["next_recommended_tool"]["name"] == "record_cohort_critic"


def test_expected_tools_registered():
    server = build_server()
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    # Core gather→author→write-back pairs the host relies on.
    expected = {
        "brief_persona", "record_persona", "get_persona", "list_personas",
        "prepare_persona_agent_context",
        "brief_day", "put_day_plan", "record_day", "simulate_day",
        "brief_consolidation", "record_memory_deltas",
        "brief_synthesis", "record_synthesis", "export_synthesis",
        "record_council",
        "brief_eval_critic", "record_eval_critic", "evaluate_simulation_full",
        # the tracker's new tools:
        "evaluate_cohort_diversity", "brief_cohort_critic", "record_cohort_critic",
        # research graph + meta-report:
        "create_research_project", "list_research_projects", "get_project_graph",
        "add_study_to_project", "set_study_themes", "link_studies",
        "backfill_project_from_syntheses",
        "brief_meta_report", "record_meta_outline", "brief_meta_section",
        "record_meta_section", "export_meta_report",
        # deletes (CRUD complete via MCP):
        "delete_research_project", "remove_study_from_project", "unlink_studies",
        "delete_synthesis", "delete_council", "delete_persona",
        # methodologies = plan SEEDS (the single runtime engine is the plan; HX3):
        "list_methodologies", "get_methodology", "start_methodology_project",
        "set_project_methodology", "brief_next", "record_judgment",
        # research-plan engine (analyze/act/verify):
        "start_project", "get_plan", "add_task", "record_frame", "link_evidence",
        "complete_task", "next_action", "assess_project", "assess_progress",
        # prototypes + Playwright harness:
        "scaffold_prototype", "register_prototype", "list_prototypes", "get_prototype",
        "run_prototype", "stop_prototype", "delete_prototype",
        "proto_open", "proto_act", "proto_read", "proto_close", "list_proto_sessions",
        "brief_prototype_session", "record_prototype_session",
    }
    missing = expected - names
    assert not missing, f"MCP tools missing: {sorted(missing)}"
