"""R1 — research-plan model + storage + plan.md render (spec/research-plan-engine.md §9 R1).

A hand-authored plan persists, round-trips, and renders a bucketed plan.md; buckets/capabilities
are validated by REFERENCE (no closed enum in code).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from persona_council import plan as P
from persona_council import services


def _plan(pid="proj1"):
    return P.new_plan(pid, goal="How might we test the plan?", methodology="double_diamond_deep", tasks=[
        {"id": "frame1", "title": "Frame the inquiry", "bucket": "analyze", "capability": "frame",
         "intent": "understand before concluding", "plan_note": "read persona memory first"},
        {"id": "c1", "title": "Pain council", "bucket": "act", "capability": "explore",
         "consumes": ["frame1"], "produces": [{"kind": "council", "id": "council_abc"}]},
        {"id": "c2", "title": "Provider council", "bucket": "act", "capability": "explore",
         "consumes": ["frame1"], "produces": [{"kind": "council", "id": "council_def"}]},
        {"id": "v1", "title": "Key problems", "bucket": "verify", "capability": "synthesize",
         "consumes": ["c1", "c2"], "requires": {"min_inputs": 2, "gate_tag": "divergence_complete"}},
    ])


def test_plan_roundtrips_through_store(store):
    p = _plan()
    P.save_plan(p, store=store)
    got = P.get_plan("proj1", store=store)
    assert got is not None
    assert got["goal"] == "How might we test the plan?"
    assert [t["id"] for t in got["tasks"]] == ["frame1", "c1", "c2", "v1"]
    assert got["tasks"][1]["produces"][0] == {"kind": "council", "id": "council_abc"}
    # the verify task carries its gate
    v1 = next(t for t in got["tasks"] if t["id"] == "v1")
    assert v1["requires"]["min_inputs"] == 2 and v1["requires"]["gate_tag"] == "divergence_complete"


def test_ready_frontier_and_completion(store):
    p = _plan()
    ready = {t["id"] for t in P.ready_tasks(p)}
    assert ready == {"frame1"}                      # only the root frame is ready
    P.task(p, "frame1")["status"] = "done"
    assert {t["id"] for t in P.ready_tasks(p)} == {"c1", "c2"}   # both act councils unlock (branch)
    for t in p["tasks"]:
        t["status"] = "done"
    assert P.is_complete(p)


def test_render_plan_md_is_bucketed(store):
    md = P.render_plan_md(_plan())
    assert "# Research plan — How might we test the plan?" in md
    assert "## Next (ready)" in md
    for section in ("## Analyze", "## Act", "## Verify"):
        assert section in md, section
    assert "council:council_abc" in md          # evidence ref rendered
    assert "gate=divergence_complete" in md       # gate rendered
    # export via services
    services.save_plan(_plan(), store=store)
    assert "## Analyze" in services.export_plan_md("proj1", store=store)


def test_bad_plan_rejected(store):
    with pytest.raises(P.PlanError):                # missing bucket tag
        P.validate_plan({"project_id": "x", "tasks": [{"id": "a", "title": "A"}]})
    with pytest.raises(P.PlanError):                # consumes unknown
        P.validate_plan({"project_id": "x", "tasks": [
            {"id": "a", "bucket": "act"}, {"id": "b", "bucket": "act", "consumes": ["ghost"]}]})
    with pytest.raises(P.PlanError):                # cycle
        P.validate_plan({"project_id": "x", "tasks": [
            {"id": "a", "bucket": "act", "consumes": ["b"]}, {"id": "b", "bucket": "act", "consumes": ["a"]}]})


def test_no_hardcoded_bucket_or_capability_set():
    """R1 acceptance: the plan engine must not encode a closed bucket/capability/kind vocabulary."""
    src = Path(P.__file__).read_text()
    for banned in ("BUCKETS =", "CAPABILITIES =", "KINDS =", "ALLOWED_BUCKETS", "VALID_CAPABILITIES"):
        assert banned not in src, banned
    # an invented bucket + capability + evidence kind validate fine
    P.validate_plan({"project_id": "x", "tasks": [
        {"id": "a", "bucket": "ponder", "capability": "divine", "produces": [{"kind": "omen", "id": "o1"}]}]})


# --------------------------------------------------------------------------- R2: seeding

def test_methodology_seeds_plan_with_gated_verify_tasks(store):
    proj = services.start_project("Deep", "How might we test seeding?", "double_diamond_deep",
                                  persona_ids=["p1"], store=store)
    plan = services.get_plan(proj["id"], store=store)
    by = {t["id"]: t for t in plan["tasks"]}
    # a frame (analyze) per fan step, a verify per decide step
    assert by["frame__discover"]["bucket"] == "analyze" and by["frame__discover"]["consumes"] == []
    assert by["verify__define"]["bucket"] == "verify"
    assert by["verify__define"]["requires"]["min_inputs"] == 2
    assert by["verify__define"]["requires"]["gate_tag"] == "divergence_complete"
    # session gates carried from the constellation (lofi at lofi_select, midfi at deliver)
    assert by["verify__lofi_select"]["requires"]["session_of_tags"] == ["lofi"]
    assert by["verify__deliver"]["requires"]["session_of_tags"] == ["midfi"]
    # the DAG threads frame -> verify -> frame -> ...
    assert by["verify__define"]["consumes"] == ["frame__discover"]
    assert by["frame__ideate"]["consumes"] == ["verify__define"]
    # only the root frame is ready at the start
    assert {t["id"] for t in services.ready_tasks(plan)} == {"frame__discover"}


def test_freeform_seeds_single_root_frame(store):
    proj = services.start_project("Freeform", "What do users want?", None,
                                  persona_ids=["p1"], store=store)
    plan = services.get_plan(proj["id"], store=store)
    assert len(plan["tasks"]) == 1
    t = plan["tasks"][0]
    assert t["bucket"] == "analyze" and t["capability"] == "frame" and t["consumes"] == []
    assert "## Analyze" in services.export_plan_md(proj["id"], store=store)


# --------------------------------------------------------------------------- R3: frame

def test_act_blocked_until_frame_discharged(store):
    proj = services.start_project("Deep", "hmw?", "double_diamond_deep", persona_ids=["p1"], store=store)
    pid = proj["id"]
    # orchestrator adds an act council under the discover frame
    services.add_task(pid, "act", "explore", "Pain council", consumes=["frame__discover"], store=store)
    plan = services.get_plan(pid, store=store)
    ready = {t["id"] for t in services.ready_tasks(plan)}
    assert "frame__discover" in ready and not any(t.startswith("act__") for t in ready)  # act blocked

    # frame requires >=1 question AND >=1 memory ref (can't silently skip)
    import pytest
    with pytest.raises(services.PlanError):
        services.record_frame(pid, "frame__discover", ["q?"], memory_refs=[], store=store)
    with pytest.raises(services.PlanError):
        services.record_frame(pid, "frame__discover", [], memory_refs=["fact:1"], store=store)

    # a minimal honest frame discharges it; act now unlocks
    services.record_frame(pid, "frame__discover",
                          questions=["Welche Versicherungen haben sie schon?", "Vorsorge-Bewusstsein?"],
                          hypotheses=["KFZ-Moment ist Pflichtakt"], memory_refs=["persona:aylin/day:2026-05-20"],
                          store=store)
    plan = services.get_plan(pid, store=store)
    fr = next(t for t in plan["tasks"] if t["id"] == "frame__discover")
    assert fr["status"] == "done" and fr["frame"]["memory_refs"] == ["persona:aylin/day:2026-05-20"]
    assert fr["produces"] == [{"kind": "frame", "id": "frame__discover"}]
    ready = {t["id"] for t in services.ready_tasks(plan)}
    assert any(t.startswith("act__") for t in ready)   # the act council is now ready
