"""Items 3 + 6: cohort diversity discrimination and the tunable critic threshold /
sample size. Deterministic, no network."""
from __future__ import annotations

from sonaloop import services
from conftest import create_persona

_CLONE_KW = dict(customer_type="Solo architect", title="Owner",
                 pains=["recurring reconciliation", "stale plan versions"],
                 goals=["save time"], tools=["CAD"])


def test_diversity_flags_near_duplicates(store):
    create_persona(store, "Clone1", **_CLONE_KW)
    create_persona(store, "Clone2", **_CLONE_KW)
    create_persona(store, "Energy", customer_type="Energy advisor", title="Consultant",
                   pains=["thermal envelope data missing", "funding paperwork"],
                   goals=["faster GEG calculation"], tools=["GEG software"])
    report = services.evaluate_cohort_diversity(store=store)
    assert report["status"] == "red"  # two interchangeable personas
    assert report["duplicate_pairs"], "near-duplicate pair must be flagged"
    pair = report["duplicate_pairs"][0]
    assert pair["similarity"] >= 0.85
    # a duplicate anomaly is persisted
    assert any(x["kind"] == "cohort_duplicate" for x in store.list_anomalies())


def test_diversity_distinct_cohort_has_no_duplicate_pairs(store):
    create_persona(store, "Arch", customer_type="Solo architect", title="Owner",
                   pains=["rework on plan aufmass"], goals=["more design time"], tools=["Vectorworks"])
    create_persona(store, "Dev", customer_type="Property developer", title="Acquisitions",
                   pains=["deal velocity", "owners stall"], goals=["close faster"], tools=["Excel"])
    create_persona(store, "GU", customer_type="General contractor", title="Calculation lead",
                   pains=["quantity transfer errors"], goals=["protect margin"], tools=["calculation suite"])
    report = services.evaluate_cohort_diversity(store=store)
    assert report["duplicate_pairs"] == []
    assert report["status"] != "red"


def test_critic_threshold_is_tunable(store, monkeypatch):
    pid = create_persona(store, "Critic")
    dims = {"anti_steering": 4, "in_character": 4, "dialogue_believability": 4,
            "arc_plausibility": 4, "mundane_balance": 4}

    # Default threshold (4): all-4 dimensions pass -> green.
    rep_default = services.record_eval_critic(pid, {"dimensions": dims}, store=store)
    assert rep_default["threshold"] == 4
    assert rep_default["green"] is True

    # Raise the bar to 5 via env: the same all-4 verdict now fails.
    monkeypatch.setenv("PERSONA_COUNCIL_CRITIC_THRESHOLD", "5")
    rep_strict = services.record_eval_critic(pid, {"dimensions": dims}, store=store)
    assert rep_strict["threshold"] == 5
    assert rep_strict["green"] is False
    assert set(rep_strict["low_dimensions"]) == set(dims)


def test_critic_sample_k_and_threshold_surface_in_brief(store, monkeypatch):
    pid = create_persona(store, "Briefed")
    brief = services.brief_eval_critic(pid, store=store)
    assert brief["frame"]["sample_k"] == 12  # default
    assert brief["frame"]["threshold"] == 4

    monkeypatch.setenv("PERSONA_COUNCIL_CRITIC_SAMPLE_K", "3")
    monkeypatch.setenv("PERSONA_COUNCIL_CRITIC_THRESHOLD", "5")
    brief2 = services.brief_eval_critic(pid, store=store)
    assert brief2["frame"]["sample_k"] == 3
    assert brief2["frame"]["threshold"] == 5
    # explicit arg still wins over config
    brief3 = services.brief_eval_critic(pid, sample_k=7, store=store)
    assert brief3["frame"]["sample_k"] == 7
