"""The calibration backtest loop: scoring predictions against real outcomes,
the report/trend series, and the correction round (ticket calibration-backtest-loop)."""
from __future__ import annotations

import pytest

from sonaloop import services
from sonaloop.services import _hooks

from conftest import create_persona


@pytest.fixture(autouse=True)
def _clean_handlers(monkeypatch):
    monkeypatch.setattr(_hooks, "_HANDLERS", {})
    monkeypatch.setattr(_hooks, "_ENTRY_POINTS_LOADED", True)
    yield


@pytest.fixture
def world(store):
    pid = create_persona(store, "Calibrated Carla")
    project = services.start_project("Pricing study", "do they convert?", persona_ids=[pid], store=store)
    council = services.record_council(
        project["id"], "Walk the pricing page", [pid],
        predictions=[
            {"action": "abandons at the price reveal", "step": 2, "likelihood": "likely",
             "persona_id": pid},                                    # 0.7
            {"action": "books a demo", "likelihood": "unlikely", "persona_id": pid},  # 0.3
            {"action": "asks finance", "persona_id": pid},          # no likelihood → unscoreable
        ],
        store=store)
    return {"persona": pid, "project": project, "council": council}


def _ref(world, anchor):
    return {"kind": "council", "id": world["council"]["id"], "anchor": anchor}


# --- scoring: a prediction meets a real outcome -------------------------------------

def test_outcome_scoring_derives_brier_and_hit(store, world):
    out = services.record_prediction_outcome(
        world["project"]["id"], _ref(world, "pb1"), 0.8,
        source={"kind": "external", "text": "funnel analytics week 24: 80% bounce at price"},
        note="close to predicted", store=store)
    assert out["likelihood"] == 0.7 and out["observed"] == 0.8
    assert out["brier"] == round((0.7 - 0.8) ** 2, 4) and out["hit"] is True
    miss = services.record_prediction_outcome(
        world["project"]["id"], _ref(world, "pb2"), True,            # predicted unlikely, happened
        source={"kind": "external", "text": "the demo was booked"}, store=store)
    assert miss["observed"] == 1.0 and miss["hit"] is False and miss["brier"] == 0.49


def test_outcome_validation(store, world):
    prj = world["project"]["id"]
    with pytest.raises(ValueError):                                  # unscoreable: no likelihood
        services.record_prediction_outcome(prj, _ref(world, "pb3"), True,
                                           source={"kind": "external", "text": "x"}, store=store)
    with pytest.raises(KeyError):                                    # unknown anchor
        services.record_prediction_outcome(prj, _ref(world, "pb9"), True,
                                           source={"kind": "external", "text": "x"}, store=store)
    with pytest.raises(ValueError):                                  # rate out of range
        services.record_prediction_outcome(prj, _ref(world, "pb1"), 1.4,
                                           source={"kind": "external", "text": "x"}, store=store)
    with pytest.raises(ValueError):                                  # id-less record source
        services.record_prediction_outcome(prj, _ref(world, "pb1"), True,
                                           source={"kind": "survey"}, store=store)
    with pytest.raises(ValueError):                                  # unresolvable source
        services.record_prediction_outcome(prj, _ref(world, "pb1"), True,
                                           source={"kind": "survey", "id": "survey_missing"}, store=store)


def test_prediction_scored_event(store, world):
    seen = []
    services.add_hook_handler("prediction.scored", seen.append)
    services.record_prediction_outcome(world["project"]["id"], _ref(world, "pb1"), 0.7,
                                       source={"kind": "external", "text": "exact"}, store=store)
    assert seen and seen[0]["data"]["brier"] == 0.0 and seen[0]["data"]["hit"] is True


# --- the report + the trend ----------------------------------------------------------

def test_report_aggregates_and_persists_the_series(store, world):
    prj = world["project"]["id"]
    services.record_prediction_outcome(prj, _ref(world, "pb1"), 0.75,
                                       source={"kind": "external", "text": "near"}, store=store)
    services.record_prediction_outcome(prj, _ref(world, "pb2"), False,
                                       source={"kind": "external", "text": "no demo"}, store=store)
    r = services.calibration_report(prj, store=store)
    assert r["predictions"]["n"] == 2 and r["predictions"]["hit_rate"] == 1.0
    assert r["green"] is True                                        # both close to reality
    levels = {row["level"]: row for row in r["predictions"]["reliability"]}
    assert levels["likely"]["predicted_mean"] == 0.7 and levels["likely"]["observed_mean"] == 0.75
    assert levels["unlikely"]["observed_mean"] == 0.0
    # persisted: the trend reads the series back
    trend = services.calibration_trend(prj, store=store)
    assert len(trend["points"]) == 1 and trend["points"][0]["n"] == 2
    assert trend["brier_delta"] is None                              # one point, no delta yet


def test_trend_shows_improvement_after_corrections(store, world):
    """The whole loop: bad round → corrections → better round → improving trend."""
    prj, pid = world["project"]["id"], world["persona"]
    services.record_prediction_outcome(prj, _ref(world, "pb1"), False,   # 0.7 vs 0 → brier .49
                                       source={"kind": "external", "text": "nobody abandoned"}, store=store)
    first = services.calibration_report(prj, store=store)
    assert first["green"] is False
    brief = services.brief_calibration(prj, store=store)
    assert any(m["kind"] == "prediction" and m["brier"] == 0.49 for m in brief["misses"])
    assert "update_persona" in brief["instructions"]
    # the host authors a correction and stamps the round
    out = services.record_calibration_round(
        [{"persona_id": pid, "text": "price sensitivity was overweighted; grounded against funnel data",
          "refs": [{"kind": "external", "text": "funnel analytics week 24"}]}],
        note="round 1", project_id=prj, store=store)
    assert out["round"]["corrections"][0]["persona_id"] == pid
    # subsequent predictions land closer to reality
    c2 = services.record_council(prj, "Re-walk the pricing page", [pid],
                                 predictions=[{"action": "abandons at the price reveal",
                                               "likelihood": "rare", "persona_id": pid}], store=store)
    services.record_prediction_outcome(prj, {"kind": "council", "id": c2["id"], "anchor": "pb1"},
                                       False, source={"kind": "external", "text": "still nobody"},
                                       store=store)
    services.calibration_report(prj, store=store)
    trend = services.calibration_trend(prj, store=store)
    assert len(trend["points"]) >= 3                                 # report, round-report, report
    assert trend["improving"] is True and trend["brier_delta"] < 0


def test_brief_includes_refuted_hypotheses(store, world):
    prj = world["project"]["id"]
    hyp = services.record_hypothesis(prj, "conversion rises after redesign",
                                     {"metric": "conversion", "expected_direction": "increase"},
                                     store=store)
    services.record_hypothesis_result(hyp["hypothesis"]["id"] if "hypothesis" in hyp else hyp["id"],
                                      -5, {"kind": "external", "text": "conversion fell 5%"},
                                      store=store)
    misses = services.brief_calibration(prj, store=store)["misses"]
    assert any(m["kind"] == "hypothesis" for m in misses)


def test_calibration_round_validation(store, world):
    with pytest.raises(ValueError):
        services.record_calibration_round([], store=store)
    with pytest.raises(ValueError):
        services.record_calibration_round([{"persona_id": "", "text": "x"}], store=store)
    with pytest.raises(KeyError):
        services.record_calibration_round([{"persona_id": "persona_missing", "text": "x"}], store=store)
