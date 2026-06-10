"""Autonomy harness — assess_project (HX1) + next_action (HX2).
Spec: spec/harness-evaluation-and-autonomy.md. Pure structural (no LLM/subagents): these are the
lean-loop steering tools a long autonomous run calls each iteration.
"""
from __future__ import annotations

from sonaloop import services as S


def _proj(store):
    personas = [p["slug"] for p in store.list_personas()] or ["p1"]
    return S.start_project("Auto Harness", "Wie können wir X erreichen?", methodology="double_diamond",
                           persona_ids=personas, store=store)["id"], personas


def test_assess_project_pulse_on_fresh_plan(store):
    pid, _ = _proj(store)
    a = S.assess_project(pid, store=store)
    assert a["complete"] is False
    assert a["recommendation"] == "frame"                 # an analyze frame is ready first
    assert "verify" in a["tasks_by_bucket"] and a["tasks_by_bucket"]["verify"]["total"] >= 1
    # the seeded verify is gated-open (needs ≥ min_inputs distinct act tasks/angles)
    assert any("act task" in u or "angles" in u for g in a["open_gates"] for u in g["unmet"])
    assert "saturation" in a and "coverage" in a


def test_next_action_loads_each_step(store):
    pid, personas = _proj(store)
    # 1) analyze step is fully loaded with grounding
    n = S.next_action(pid, store=store)
    assert n["bucket"] == "analyze" and n["complete"] is False
    assert n["grounding"]["persona_pool"]                  # personas available to ground the frame
    # 2) after framing, the gated verify surfaces ACT guidance (framed questions + diverse personas)
    S.record_frame(pid, "frame__discover", ["Was treibt sie?", "Warum nicht?"],
                   memory_refs=["persona: lived memory"], store=store)
    n2 = S.next_action(pid, store=store)
    assert n2["bucket"] == "verify"
    assert n2["act"]["framed_questions"]                   # the consumed frame's questions
    parts = n2["act"]["suggested_participants"]
    assert isinstance(parts, list) and len(parts) == len(set(parts))  # de-duped (empty if no cohort in test DB)
    assert S.assess_project(pid, store=store)["recommendation"] == "act"


def test_assess_project_complete_when_plan_done(store):
    # a freeform project with a single discharged frame is "complete"
    pid = S.start_project("Freeform", "frage?", store=store)["id"]
    S.record_frame(pid, "frame__root", ["q?"], memory_refs=["m"], store=store)
    a = S.assess_project(pid, store=store)
    assert a["complete"] is True and a["recommendation"] == "complete"


def test_saturation_never_converging_while_a_diamond_is_unopened(store):
    """The stalled-run snapshot (2026-06-10): Discover+Define done, second diamond untouched.
    The old ratio-only hint read "converging" here — with open_questions empty, both published
    stop conditions were green at the exact stall point. Plan-aware: still diverging."""
    pid = S.start_project("Stall", "hmw?", "double_diamond", persona_ids=["p1"], store=store)["id"]
    a = S.assess_project(pid, store=store)
    assert a["saturation"]["hint"].startswith("early")            # no act evidence at all yet
    S.record_frame(pid, "frame__discover", ["q1?", "q2?"], memory_refs=["m1"], store=store)
    for i in (1, 2):
        t = S.add_task(pid, "act", "explore", f"Council {i}", consumes=["frame__discover"], store=store)
        S.link_evidence(pid, t["id"], {"kind": "council", "id": f"c{i}"}, store=store)
        S.complete_task(pid, t["id"], store=store)
    syn = S.record_synthesis("Define POV", "hmw?", ["c1", "c2"], {"gesamtbild": "pov"}, store=store)
    S.link_evidence(pid, "verify__define", {"kind": "synthesis", "id": syn["id"]}, store=store)
    S.record_judgment(pid, "verify__define", "divergence_complete", True, "saturating",
                      evidence_refs=["c1", "c2"], store=store)
    S.complete_task(pid, "verify__define", store=store)
    a = S.assess_project(pid, store=store)
    # 2 act done vs 1 synthesis satisfied the old ratio — but frame__ideate (analyze) is still open
    assert a["saturation"]["act_done"] == 2 and a["saturation"]["syntheses"] >= 1
    assert a["saturation"]["hint"] == "still diverging"
    assert a["complete"] is False


def test_saturation_converging_once_divergent_work_is_done(store):
    """When every analyze/act task is done and consolidation kept pace, the hint is honest again."""
    pid = S.start_project("Conv", "frage?", store=store)["id"]          # freeform: one root frame
    S.record_frame(pid, "frame__root", ["q?"], memory_refs=["m"], store=store)
    t = S.add_task(pid, "act", "explore", "Council", consumes=["frame__root"], store=store)
    S.link_evidence(pid, t["id"], {"kind": "council", "id": "c1"}, store=store)
    S.complete_task(pid, t["id"], store=store)
    syn = S.record_synthesis("Answer", "frage?", ["c1"], {"gesamtbild": "answer"}, store=store)
    v = S.add_task(pid, "verify", "consolidate", "Decide", consumes=[t["id"]], store=store)
    S.link_evidence(pid, v["id"], {"kind": "synthesis", "id": syn["id"]}, store=store)
    a = S.assess_project(pid, store=store)
    assert a["saturation"]["hint"] == "converging"                      # 1 act ≤ 2·1 syn, nothing divergent open
