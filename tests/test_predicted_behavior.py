"""Predicted behavior, not just opinions: the canonical primitive (likelihood
scale + evidence refs), its ride through sessions/councils/syntheses, and the
segment aggregation (ticket behavioral-prediction-output)."""
from __future__ import annotations

import pytest

from sonaloop import artifacts as A
from sonaloop import services

from conftest import create_persona


# --- the primitive ------------------------------------------------------------------

def test_likelihood_resolves_terms_aliases_and_numbers():
    assert A.resolve_likelihood("likely") == {"value": 0.7, "label": "likely"}
    assert A.resolve_likelihood("WAHRSCHEINLICH") == {"value": 0.7, "label": "likely"}
    assert A.resolve_likelihood(0.82) == {"value": 0.82, "label": "likely"}   # raw kept exact
    assert A.resolve_likelihood(0.05) == {"value": 0.05, "label": "rare"}
    assert A.resolve_likelihood("plausible-ish") is None                      # rejected, not bucketed
    assert A.resolve_likelihood(1.4) is None
    assert A.resolve_likelihood(None) is None


def test_predicted_behavior_validates_and_carries_evidence():
    pb = A.predicted_behavior("abandons at the price reveal", step=3, likelihood="likely",
                              trigger="price shown without context", persona_id="p1",
                              refs=[{"kind": "evidence", "id": "chunk_abc", "quote": "too expensive"}])
    assert pb["likelihood"] == {"value": 0.7, "label": "likely"}
    assert pb["refs"][0]["kind"] == "evidence" and pb["refs"][0]["id"] == "chunk_abc"
    assert A.validate_predicted_behavior(pb) == pb                            # idempotent re-validation
    with pytest.raises(ValueError):
        A.predicted_behavior("")                                              # action required
    with pytest.raises(ValueError):
        A.predicted_behavior("clicks", likelihood="probably-ish")             # off-scale
    with pytest.raises(ValueError):
        A.predicted_behavior("clicks", step="two")                            # step must be int


def test_suggest_likelihood_levels_is_closed_and_ordered():
    out = services.suggest_likelihood_levels()
    terms = [i["term"] for i in out["items"]]
    assert terms == ["rare", "unlikely", "possible", "likely", "certain"]
    assert all("aliases" in i for i in out["items"])


# --- predictions ride councils and syntheses ----------------------------------------

@pytest.fixture
def project(store):
    pid = create_persona(store, "Predictor")
    pr = services.start_project("Pricing flow", "where do they bail?", persona_ids=[pid], store=store)
    return {"persona": pid, "project": pr}


def test_council_records_predictions_with_part_ids(store, project):
    c = services.record_council(
        project["project"]["id"], "Walk the pricing page", [project["persona"]],
        predictions=[{"action": "abandons at the price reveal", "step": 2, "likelihood": "likely",
                      "trigger": "no context for the number", "persona_id": project["persona"]}],
        store=store)
    stored = services.get_council(c["id"], store=store)
    pb = stored["predictions"][0]
    assert pb["id"] == "pb1" and pb["likelihood"]["value"] == 0.7
    assert pb["persona_id"] == project["persona"]


def test_synthesis_records_and_preserves_predictions(store, project):
    s1 = services.record_synthesis("Answer", "goal", key="arc", store=store,
                                   predictions=[{"action": "churns in month 2",
                                                 "likelihood": 0.65, "trigger": "no aha moment"}])
    assert s1["predictions"][0]["likelihood"] == {"value": 0.65, "label": "likely"}
    s2 = services.record_synthesis("Answer v2", "goal", key="arc", store=store)  # re-record, no preds
    assert s2["predictions"][0]["action"] == "churns in month 2"                 # preserved


def test_council_rejects_off_scale_predictions(store, project):
    with pytest.raises(ValueError):
        services.record_council(project["project"]["id"], "x", [project["persona"]],
                                predictions=[{"action": "clicks", "likelihood": "sorta"}], store=store)


# --- the segment aggregation ---------------------------------------------------------

def _session(store, project, persona_id, key, preds):
    steps = [{"index": 0, "action": {"type": "look", "target": "", "detail": ""},
              "monologue": "looking", "state": {"screen": "pricing page"},
              "friction": {"level": "confusion", "note": ""},
              "verdict": {"would_continue": False, "reason": "lost"}}]
    return services.record_usability_session(
        persona_id, {"kind": "flow", "id": "flow-pricing", "label": "Pricing"}, "artifact",
        "2026-06-10", steps,
        {"completed": False, "dropoff_step": 0, "summary": "", "predicted_behaviors": preds},
        project_id=project, key=key, store=store)


def test_aggregate_rolls_up_across_sessions_and_councils(store, project):
    p1 = project["persona"]
    p2 = create_persona(store, "Second Voice")
    prj = project["project"]["id"]
    _session(store, prj, p1, "s1", [{"action": "Abandons at the price reveal", "step": 0,
                                     "likelihood": "likely", "trigger": "sticker shock"}])
    _session(store, prj, p2, "s2", [{"action": "abandons at the PRICE reveal", "step": 0,
                                     "likelihood": 0.9, "trigger": "no comparison"}])
    services.record_council(prj, "pricing", [p1],
                            predictions=[{"action": "asks finance for approval", "likelihood": "possible",
                                          "persona_id": p1}], store=store)
    agg = services.aggregate_predictions(prj, store=store)
    assert agg["total"] == 3 and agg["personas"] == 2
    top = agg["groups"][0]
    assert top["count"] == 2 and sorted(top["personas"]) == sorted([p1, p2])
    assert top["likelihood_mean"] == 0.8                       # (0.7 + 0.9) / 2
    assert {s["kind"] for s in top["sources"]} == {"session"}
    assert agg["by_step"] == {"0": 2}
    # the aggregate rides the substrate study result and the hypothesis brief
    res = services.get_study_result(prj, store=store)
    assert res["predictions"]["total"] == 3
    brief = services.brief_hypothesis(prj, store=store)
    assert brief["predicted_behaviors_aggregate"][0]["count"] == 2


def test_session_outcome_predictions_are_canonical_and_citable(store, project):
    prj = project["project"]["id"]
    out = _session(store, prj, project["persona"], "s1",
                   [{"action": "asks a colleague", "step": 0, "likelihood": "likely",
                     "trigger": "unclear copy",
                     "refs": [{"kind": "evidence", "id": "chunk_x", "quote": "I always ask Tom"}]}])
    sess = services.get_usability_session(out["usability_session"]["id"], store=store)
    pb = sess["outcome"]["predicted_behaviors"][0]
    assert pb["id"] == "pb1"                                   # stable part id, addressable by refs
    assert pb["likelihood"] == {"value": 0.7, "label": "likely"}
    assert pb["refs"][0]["id"] == "chunk_x"                    # the evidence layer survives
    with pytest.raises(ValueError):
        _session(store, prj, project["persona"], "s-bad",
                 [{"action": "quits", "likelihood": "definitely-maybe"}])
