"""Item 2: regression fixtures for the seeded simulation scaffolding. The lived
content is LLM-authored, but the scaffolding (RNG-driven timestamps/gaps) must be
deterministic for a given seed so long-horizon runs are reproducible and
regressions are caught. Content generation is stubbed (no network)."""
from __future__ import annotations

from persona_council import services
from conftest import create_persona


def test_make_rng_is_deterministic_and_seed_sensitive():
    # Same seed -> identical stream (golden values pin the scaffolding RNG).
    r = services._make_rng("regression-seed")
    assert [round(r.random(), 6) for _ in range(3)] == [0.457066, 0.818739, 0.533061]
    # Re-seeding reproduces exactly.
    r2 = services._make_rng("regression-seed")
    assert [round(r2.random(), 6) for _ in range(3)] == [0.457066, 0.818739, 0.533061]
    # A different seed yields a different stream.
    other = services._make_rng("different-seed")
    assert round(other.random(), 6) != 0.457066


def _stub_generation(monkeypatch):
    def fake_plan(frame):
        tool = (frame.get("allowed_tools") or ["CAD"])[0]
        return {"mood_forecast": "steady", "blocks": [
            {"title": "Focus block", "duration_minutes": 60, "event_type": "focus",
             "tool": tool, "participants": [], "why_it_happens": "deep work"},
            {"title": "Sync", "duration_minutes": 30, "event_type": "meeting",
             "tool": tool, "participants": ["Client"], "why_it_happens": "coordinate"},
        ]}

    def fake_activity(frame):
        return {
            "what_happened": "did the work", "conversation": [], "key_quotes": ["quote"],
            "actions_done": ["acted"], "artifacts_touched": ["doc"], "persona_thought": "fine",
            "decision": None, "open_loops": [], "mood": "steady", "energy_delta": -1,
            "pain_points": [], "generation_mode": "host_authored", "llm_error": None,
        }

    monkeypatch.setattr(services, "generate_day_plan_with_llm", fake_plan)
    monkeypatch.setattr(services, "generate_activity", fake_activity)


def test_simulate_day_scaffolding_is_reproducible(store, monkeypatch):
    _stub_generation(monkeypatch)
    pid = create_persona(store, "Sim")

    run1 = services.simulate_day(pid, "2026-06-02", seed="regression-seed", store=store)
    run2 = services.simulate_day(pid, "2026-06-02", seed="regression-seed", store=store)

    sched1 = [(c["start"], c["end"], c["title"]) for c in run1["calendar_events"]]
    sched2 = [(c["start"], c["end"], c["title"]) for c in run2["calendar_events"]]
    assert sched1 == sched2, "same seed must reproduce identical scaffolding"

    # Golden anchor: the first event's start is driven entirely by the seeded RNG
    # (workday_start 08:00 + offset draw 40 + first gap draw 5 -> 08:45).
    assert sched1, "expected scaffolded calendar events"
    assert sched1[0][0].endswith("08:45"), sched1[0][0]
    # Blocks are laid sequentially with positive gaps (no overlaps / time moves forward).
    starts = [c["start"] for c in run1["calendar_events"]]
    assert starts == sorted(starts)


def test_simulate_day_seed_changes_schedule(store, monkeypatch):
    _stub_generation(monkeypatch)
    pid = create_persona(store, "Sim2")
    a = services.simulate_day(pid, "2026-06-02", seed="seed-A", store=store)
    b = services.simulate_day(pid, "2026-06-02", seed="seed-B", store=store)
    # Two unrelated seeds should not produce an identical schedule.
    assert [c["start"] for c in a["calendar_events"]] != [c["start"] for c in b["calendar_events"]]
