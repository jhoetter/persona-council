"""Ideation Job protocol (taxonomy `jobs[ideation_hmw].protocol` — structured HMW, end-to-end):
reframe (3–5 HMW questions as question records, promotable to real hypotheses) → diverge (ideas as
first-class attributed idea notes, queryable) → converge (forced ranking → an `ideation` council
block a decision record cites). Host-authored throughout — the server validates structure only."""
from __future__ import annotations

import pytest

from sonaloop import services
from sonaloop import job_taxonomy as T
from conftest import create_persona


HMWS = ["How might we shorten onboarding?",
        "How might we make value visible on day one?",
        "How might we get the team owner to invite others?"]


def _project(store, names=("Ana", "Ben")):
    pids = [create_persona(store, n, customer_type=ct) for n, ct in
            zip(names, ["Founder", "Enterprise", "Founder", "Enterprise"])]
    proj = services.create_research_project("Ideation study", goal="activation ideas",
                                            persona_ids=pids, store=store)
    return proj["id"], pids


def _reframed(store):
    pid, pids = _project(store)
    out = services.record_hmw_reframe(pid, "Users sign up and never come back", HMWS, store=store)
    return pid, pids, [h["id"] for h in out["hmw"]]


# --------------------------------------------------------------------------- taxonomy protocol

def test_ideation_job_carries_the_protocol():
    proto = T.get_job("ideation_hmw")["protocol"]
    assert [s["id"] for s in proto["steps"]] == ["reframe", "diverge", "converge"]
    for step in proto["steps"]:
        assert step["rule"] and step["tooling"], step["id"]


# --------------------------------------------------------------------------- reframe

def test_reframe_records_3_to_5_hmw_questions(store):
    pid, _ = _project(store)
    out = services.record_hmw_reframe(pid, "Users churn after signup", HMWS, store=store)
    assert out["schema"] == "hmw_reframe" and len(out["hmw"]) == 3
    # Each HMW is a stable question record on the project (the hmw_ref ideas attach to).
    oq_ids = {q["id"] for q in store.list_open_questions(pid)}
    assert {h["id"] for h in out["hmw"]} <= oq_ids
    with pytest.raises(ValueError, match="3–5"):
        services.record_hmw_reframe(pid, "p", HMWS[:2], store=store)
    with pytest.raises(ValueError, match="3–5"):
        services.record_hmw_reframe(pid, "p", [f"HMW {i}?" for i in range(6)], store=store)
    with pytest.raises(ValueError, match="distinct"):
        services.record_hmw_reframe(pid, "p", [HMWS[0]] * 3, store=store)


def test_reframe_promotes_betable_hmws_to_real_hypotheses(store):
    """An HMW with a host-authored falsifiable prediction is ALSO stamped as a hypothesis (full
    record_hypothesis validation, derived_from the question record) — a bare question is not."""
    pid, _ = _project(store)
    hmws = [HMWS[0],
            {"question": HMWS[1],
             "prediction": {"metric": "day1_return_rate", "expected_direction": "increase"}},
            HMWS[2]]
    out = services.record_hmw_reframe(pid, "Users churn after signup", hmws, store=store)
    assert "hypothesis_id" not in out["hmw"][0]
    hyp_id = out["hmw"][1]["hypothesis_id"]
    hyp = services.get_hypothesis(hyp_id, store=store)
    assert hyp["status"] == "open" and hyp["text"] == HMWS[1]
    assert any(r.get("kind") == "open_question" and r.get("id") == out["hmw"][1]["id"]
               for r in hyp["derived_from"])
    # An unfalsifiable prediction is rejected by the hypothesis validation, not silently stored.
    with pytest.raises(ValueError, match="metric"):
        services.record_hmw_reframe(
            pid, "p", [HMWS[0], HMWS[2], {"question": "How might we delight?",
                                          "prediction": {"expected_direction": "up"}}], store=store)


# --------------------------------------------------------------------------- diverge

def test_ideas_are_first_class_attributed_and_queryable(store):
    pid, (ana, ben), hmw = _reframed(store)
    ideas = services.record_ideas(pid, [
        {"text": "Concierge onboarding call", "persona_id": ana, "hmw_ref": hmw[0], "cluster": "high-touch"},
        {"text": "Interactive checklist", "persona_id": ben, "hmw_ref": hmw[0], "cluster": "self-serve"},
        {"text": "Day-one value report email", "persona_id": ben, "hmw_ref": hmw[1], "cluster": "self-serve"},
    ], store=store)
    assert len(ideas) == 3
    assert ideas[0]["kind"] == "idea"
    assert ideas[0]["hmw_question"] == HMWS[0]

    # Queryable for synthesis: by HMW, by source persona, by host-authored cluster.
    assert len(services.list_ideas(pid, store=store)) == 3
    assert {i["text"] for i in services.list_ideas(pid, hmw_ref=hmw[0], store=store)} == \
        {"Concierge onboarding call", "Interactive checklist"}
    assert [i["text"] for i in services.list_ideas(pid, persona_id=ana, store=store)] == \
        ["Concierge onboarding call"]
    assert len(services.list_ideas(pid, cluster="self-serve", store=store)) == 2
    # Idea notes ride the existing note primitive — they appear among the project's notes.
    assert {n["id"] for n in ideas} <= {n["id"] for n in services.list_notes(pid, store=store)}


def test_unattributed_or_unanchored_ideas_are_rejected(store):
    pid, (ana, _), hmw = _reframed(store)
    with pytest.raises(ValueError, match="persona_id"):
        services.record_ideas(pid, [{"text": "orphan idea", "persona_id": "nope", "hmw_ref": hmw[0]}],
                              store=store)
    with pytest.raises(ValueError, match="hmw_ref"):
        services.record_ideas(pid, [{"text": "unanchored", "persona_id": ana, "hmw_ref": "oq_nope"}],
                              store=store)
    with pytest.raises(ValueError, match="distinct"):
        services.record_ideas(pid, [{"text": "same", "persona_id": ana, "hmw_ref": hmw[0]},
                                    {"text": "same", "persona_id": ana, "hmw_ref": hmw[0]}],
                              store=store)


# --------------------------------------------------------------------------- converge

def _diverged(store):
    pid, (ana, ben), hmw = _reframed(store)
    ideas = services.record_ideas(pid, [
        {"text": "Concierge onboarding call", "persona_id": ana, "hmw_ref": hmw[0], "cluster": "high-touch"},
        {"text": "Interactive checklist", "persona_id": ben, "hmw_ref": hmw[0], "cluster": "self-serve"},
        {"text": "Day-one value report email", "persona_id": ben, "hmw_ref": hmw[1], "cluster": "self-serve"},
    ], store=store)
    return pid, (ana, ben), hmw, ideas


def test_forced_ranking_produces_a_citable_ideation_summary(store):
    pid, _, hmw, ideas = _diverged(store)
    session = services.record_ideation_summary(
        pid, "Users sign up and never come back",
        shortlist=[{"idea_id": ideas[1]["id"], "rationale": "Cheapest to ship, both segments nod."},
                   {"idea_id": ideas[2]["id"], "rationale": "Makes value visible without a human."}],
        exec_summary="Host convergence story.", key="ideation1", store=store)

    block = session["ideation"]
    assert [p["rank"] for p in block["shortlist"]] == [1, 2]          # rank = position (forced)
    assert block["shortlist"][0]["text"] == "Interactive checklist"
    assert block["shortlist"][0]["persona_id"] and block["shortlist"][0]["hmw_ref"] == hmw[0]
    assert block["shortlist"][0]["rationale"].startswith("Cheapest")
    assert len(block["ideas"]) == 3                                   # the full pool is aggregated
    assert {h["id"] for h in block["hmw"]} == {hmw[0], hmw[1]}        # the HMWs the pool answered
    assert services.is_ideation(session)

    # Round-trip + the decision-record seam: get_ideation returns the block and a cite_as ref
    # that record_decision accepts as based_on evidence (resolve_ref kind 'council').
    out = services.get_ideation(session["id"], store=store)
    assert out["shortlist"] == block["shortlist"]
    dec = services.record_decision(
        pid, "Ship the interactive checklist", "We build the checklist first.",
        based_on=[out["cite_as"]], store=store)["decision"]
    assert dec["based_on"][0]["id"] == session["id"]
    # Idempotent on key (resumable runs).
    again = services.record_ideation_summary(
        pid, "Users sign up and never come back",
        shortlist=[{"idea_id": ideas[1]["id"], "rationale": "r"}], key="ideation1", store=store)
    assert again["id"] == session["id"]


def test_converge_validates_the_forced_ranking(store):
    pid, _, _, ideas = _diverged(store)
    with pytest.raises(ValueError, match="rationale"):
        services.record_ideation_summary(pid, "p", [{"idea_id": ideas[0]["id"]}], store=store)
    with pytest.raises(ValueError, match="not a recorded idea"):
        services.record_ideation_summary(pid, "p", [{"idea_id": "note_nope", "rationale": "r"}],
                                         store=store)
    with pytest.raises(ValueError, match="ranked twice"):
        services.record_ideation_summary(
            pid, "p", [{"idea_id": ideas[0]["id"], "rationale": "a"},
                       {"idea_id": ideas[0]["id"], "rationale": "b"}], store=store)


def test_converge_requires_a_diverge(store):
    pid, _ = _project(store)
    with pytest.raises(ValueError, match="no ideas recorded"):
        services.record_ideation_summary(pid, "p", [{"idea_id": "x", "rationale": "r"}], store=store)
