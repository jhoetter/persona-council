"""Autonomy harness — assess_project (HX1) + next_action (HX2).
Spec: spec/harness-evaluation-and-autonomy.md. Pure structural (no LLM/subagents): these are the
lean-loop steering tools a long autonomous run calls each iteration.
"""
from __future__ import annotations

from persona_council import services as S


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
    # the seeded verify is gated-open (needs act evidence)
    assert any("act evidence" in u for g in a["open_gates"] for u in g["unmet"])
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
