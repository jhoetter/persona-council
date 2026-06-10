"""Pricing Job protocol (taxonomy `jobs[pricing].protocol` — willingness-to-pay ladder): the
van-Westendorp-style price ladder. Covers: the taxonomy protocol block, the brief (ladder folded
into each persona's context), response validation (closed band vocabulary, on-ladder prices only),
the deterministic aggregation (acceptance per rung, acceptable range + cliff, overall and per
segment), persistence as a queryable CouncilSession block, and the tier-comparison reuse of
head_to_head with price as variant metadata. Host-authored throughout — no server-side text-LLM."""
from __future__ import annotations

import pytest

from sonaloop import services
from sonaloop import job_taxonomy as T
from conftest import create_persona


def _project(store, personas, **kw):
    pids = [create_persona(store, n, **(kw | ({"customer_type": ct} if ct else {})))
            for n, ct in personas]
    proj = services.create_research_project("Pricing study", goal="what should I charge",
                                            persona_ids=pids, store=store)
    return proj["id"], pids


LADDER = ["$9/mo", "$29/mo", "$49/mo", "$99/mo"]


# --------------------------------------------------------------------------- taxonomy protocol

def test_pricing_job_carries_the_ladder_protocol():
    proto = T.get_job("pricing")["protocol"]
    assert proto["name"] == "Willingness-to-pay ladder"
    assert [s["id"] for s in proto["steps"]] == [
        "ladder_up_front", "anchor_band_reactions", "grounded_in_profile",
        "range_and_cliffs", "tier_head_to_head"]
    for step in proto["steps"]:
        assert step["rule"] and step["tooling"], step["id"]
    # The four anchor bands are named in the protocol (the closed vocabulary the code enforces).
    summary = proto["summary"]
    for band in ("too_cheap", "bargain", "getting_expensive", "too_expensive"):
        assert band in summary


# --------------------------------------------------------------------------- brief

def test_brief_folds_the_ladder_into_each_persona_context(store):
    pid, [p1] = _project(store, [("Solo", "Founder")])
    brief = services.brief_price_ladder(pid, "SaaS tiers", LADDER, persona_ids=[p1], store=store)
    assert brief["schema"] == "price_ladder"
    assert [pt["label"] for pt in brief["price_points"]] == LADDER          # ascending, verbatim labels
    assert [pt["amount"] for pt in brief["price_points"]] == [9, 29, 49, 99]
    assert brief["bands"] == ["too_cheap", "bargain", "getting_expensive", "too_expensive"]
    ctx = brief["participants"][0]["agent_context"]
    assert "PRICE LADDER" in ctx and "$29/mo" in ctx and "$99/mo" in ctx
    assert "too_cheap" in ctx                                                # bands are in the room
    assert "price:" in brief["instructions"]


def test_ladder_is_normalized_and_validated(store):
    pid, [p1] = _project(store, [("Solo", None)])
    # Out-of-order, mixed-shape rungs sort ascending by parsed amount.
    brief = services.brief_price_ladder(
        pid, "?", [{"label": "Pro", "amount": 49}, 9, "29 €"], persona_ids=[p1], store=store)
    assert [pt["amount"] for pt in brief["price_points"]] == [9, 29, 49]
    with pytest.raises(ValueError, match="at least two"):
        services.brief_price_ladder(pid, "?", ["$9"], persona_ids=[p1], store=store)
    with pytest.raises(ValueError, match="no readable amount"):
        services.brief_price_ladder(pid, "?", ["cheap", "expensive"], persona_ids=[p1], store=store)
    with pytest.raises(ValueError, match="distinct"):
        services.brief_price_ladder(pid, "?", ["$9", 9], persona_ids=[p1], store=store)


# --------------------------------------------------------------------------- record + validation

def test_record_validates_bands_and_rungs(store):
    pid, [p1] = _project(store, [("Solo", None)])
    with pytest.raises(ValueError, match="anchor scale"):
        services.record_price_ladder(pid, "?", LADDER,
                                     responses=[{"persona_id": p1, "price": "$9/mo", "band": "meh"}],
                                     store=store)
    with pytest.raises(ValueError, match="not a rung"):
        services.record_price_ladder(pid, "?", LADDER,
                                     responses=[{"persona_id": p1, "price": "$19/mo", "band": "bargain"}],
                                     store=store)


def test_price_response_rows_round_trip(store):
    """The structured willingness-to-pay payload (persona, price point, band, quote) persists on
    the council record and comes back queryable — the pricing analytics seam."""
    pid, [p1] = _project(store, [("Solo", "Founder")])
    session = services.record_price_ladder(
        pid, "What should I charge?", LADDER,
        responses=[{"persona_id": p1, "price": "$9/mo", "band": "too_cheap",
                    "quote": "At $9 I'd assume it's abandoned."},
                   {"persona_id": p1, "price": 29, "band": "bargain", "quote": "Fits my tool budget."},
                   {"persona_id": p1, "price": "$49/mo", "band": "getting_expensive", "quote": "Hmm."},
                   {"persona_id": p1, "price": "$99/mo", "band": "too_expensive", "quote": "No."}],
        exec_summary="Host pricing story.", store=store)

    assert services.is_price_ladder(session)
    pl = services.get_price_ladder(session["id"], store=store)
    assert len(pl["responses"]) == 4
    # An amount resolves onto its rung label; quotes survive verbatim.
    by_price = {r["price"]: r for r in pl["responses"]}
    assert by_price["$29/mo"]["band"] == "bargain"
    assert by_price["$29/mo"]["amount"] == 29
    assert by_price["$9/mo"]["quote"] == "At $9 I'd assume it's abandoned."
    # It is a real CouncilSession on the project graph, with the queryable finding seam.
    proj = services.get_research_project(pid, store=store)
    assert session["id"] in proj["council_ids"]
    fetched = services.get_council(session["id"], store=store)
    assert "price_ladder" in [f.get("kind") for f in fetched.get("findings", [])]
    # Idempotent on key (resumable runs), like every recorder.
    again = services.record_price_ladder(
        pid, "What should I charge?", LADDER,
        responses=[{"persona_id": p1, "price": 29, "band": "bargain"}], key="run1", store=store)
    assert services.record_price_ladder(
        pid, "What should I charge?", LADDER,
        responses=[{"persona_id": p1, "price": 29, "band": "bargain"}], key="run1",
        store=store)["id"] == again["id"]


# --------------------------------------------------------------------------- aggregation

def test_acceptable_range_and_cliff_per_segment(store):
    """Two segments with different wallets: Founders accept $9–$29 and fall off a cliff at $49;
    Enterprise accepts $29–$99. The derived result carries range + cliff overall AND per segment."""
    pid, pids = _project(store, [("F1", "Founder"), ("F2", "Founder"),
                                 ("E1", "Enterprise"), ("E2", "Enterprise")])
    f1, f2, e1, e2 = pids

    def react(persona, bands):
        return [{"persona_id": persona, "price": lab, "band": band}
                for lab, band in zip(LADDER, bands)]

    responses = (
        react(f1, ["bargain", "bargain", "too_expensive", "too_expensive"]) +
        react(f2, ["bargain", "getting_expensive", "too_expensive", "too_expensive"]) +
        react(e1, ["too_cheap", "bargain", "bargain", "getting_expensive"]) +
        react(e2, ["too_cheap", "bargain", "bargain", "getting_expensive"]))
    session = services.record_price_ladder(pid, "tiers?", LADDER, responses=responses, store=store)

    res = session["price_ladder"]["result"]
    seg = {s["segment"]: s for s in res["segments"]}
    # Founders: acceptance 1.0, 1.0, 0.0, 0.0 → range $9–$29, cliff between $29 and $49 (drop 1.0).
    assert seg["Founder"]["acceptable_range"]["low"] == "$9/mo"
    assert seg["Founder"]["acceptable_range"]["high"] == "$29/mo"
    assert seg["Founder"]["cliff"] == {"from": "$29/mo", "to": "$49/mo",
                                       "from_amount": 29, "to_amount": 49, "drop": 1.0}
    # Enterprise: acceptance 0, 1, 1, 1 → range $29–$99, no positive drop → no cliff.
    assert seg["Enterprise"]["acceptable_range"] == {"low": "$29/mo", "low_amount": 29,
                                                     "high": "$99/mo", "high_amount": 99}
    assert seg["Enterprise"]["cliff"] is None
    # Overall: acceptance 0.5, 1.0, 0.5, 0.5 → range spans the ladder; cliff after $29 (drop 0.5).
    overall = res["overall"]
    assert overall["respondents"] == 4
    assert [pt["acceptance"] for pt in overall["points"]] == [0.5, 1.0, 0.5, 0.5]
    assert overall["cliff"]["from"] == "$29/mo" and overall["cliff"]["drop"] == 0.5

    # The analytics helper exposes the same numbers by session id.
    analysis = services.price_ladder_analysis(session["id"], store=store)
    assert analysis["schema"] == "price_ladder_analysis"
    assert analysis["overall"]["cliff"]["from"] == "$29/mo"
    assert {s["segment"] for s in analysis["segments"]} == {"Founder", "Enterprise"}


def test_unanswered_rungs_stay_out_of_the_math(store):
    pid, [p1] = _project(store, [("Solo", "Founder")])
    session = services.record_price_ladder(
        pid, "?", LADDER,
        responses=[{"persona_id": p1, "price": "$29/mo", "band": "bargain"}], store=store)
    points = session["price_ladder"]["result"]["overall"]["points"]
    assert [pt["acceptance"] for pt in points] == [None, 1.0, None, None]
    rng = session["price_ladder"]["result"]["overall"]["acceptable_range"]
    assert rng == {"low": "$29/mo", "low_amount": 29, "high": "$29/mo", "high_amount": 29}
    assert session["price_ladder"]["result"]["overall"]["cliff"] is None


# --------------------------------------------------------------------------- tier comparison reuse

def test_tier_comparison_reuses_head_to_head_with_price_metadata(store):
    """Protocol step `tier_head_to_head`: comparing tiers is a head_to_head with price riding as
    variant metadata — no parallel comparison path."""
    pid, [p1] = _project(store, [("Solo", "Founder")])
    session = services.record_head_to_head(
        pid, "Starter vs Pro", ["Starter — $29/mo", "Pro — $49/mo"],
        preferences=[{"persona_id": p1, "choice": "A", "intensity": 1, "reason": "budget"}],
        variant_meta={"variants": {"A": {"id": "tier-starter", "price": 29},
                                   "B": {"id": "tier-pro", "price": 49}}},
        store=store)
    ht = services.get_head_to_head(session["id"], store=store)
    assert ht["variant_meta"]["variants"]["B"] == {"id": "tier-pro", "price": 49}
    assert ht["result"]["preference"] == "A"
