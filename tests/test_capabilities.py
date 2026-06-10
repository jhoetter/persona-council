"""Persona capability profile — rungs, tech comfort, fidelity gating.

Defaults + the read-time DERIVED profile (never rewritten into the store), the deterministic
derivation heuristic, validated capability patches via update_persona, the data-driven tech-comfort
vocabulary, fidelity-gating warnings in the session briefs (warn, never block), the
capabilities_snapshot stamped onto recorded sessions, the SOUL.md Capabilities section, and the
inspector's capability card.
"""
from __future__ import annotations

import pytest

from conftest import create_persona, make_profile
from sonaloop import artifacts, services


_FLOW = {"kind": "flow", "id": "flow-signup", "label": "Signup flow"}


def _step(i):
    return {"index": i, "action": {"type": "click", "target": f"b{i}", "detail": ""},
            "monologue": "…", "state": {"screen": f"screen-{i}"},
            "friction": {"level": "none", "note": ""},
            "verdict": {"would_continue": True, "reason": ""}}


_OUTCOME = {"completed": True, "dropoff_step": None, "summary": "ok", "predicted_behaviors": []}


# --------------------------------------------------------------- defaults + derived-on-read

def test_new_persona_gets_derived_profile_on_read_without_rewrite(store):
    pid = create_persona(store, "Greta Default")
    caps = services.get_persona(pid, store)["persona"]["capabilities"]
    assert caps["rungs"] == {"see": True, "walk": True, "drive": True, "login": False}
    assert caps["tech_comfort"] == 3 and caps["provenance"] == "derived"
    # derived in the RETURNED dict only — the stored persona keeps capabilities unset
    assert store.get_persona(pid)["capabilities"] is None
    assert services.list_personas(store=store)[0]["capabilities"]["provenance"] == "derived"


def test_record_persona_validates_and_persists_declared_capabilities(store):
    profile = make_profile("Carla Authored")
    profile["capabilities"] = {"rungs": {"login": True}, "tech_comfort": "expert",
                               "devices": ["mobile"], "accessibility": "large fonts"}
    persona = services.record_persona("Carla — source", profile, store=store)
    caps = persona["capabilities"]
    assert caps["rungs"] == {"see": True, "walk": True, "drive": True, "login": True}
    assert caps["tech_comfort"] == 5 and caps["devices"] == ["mobile"]
    assert caps["accessibility"] == "large fonts" and caps["provenance"] == "authored"
    assert store.get_persona(persona["id"])["capabilities"] == caps      # persisted as declared
    with pytest.raises(ValueError, match="tech_comfort"):
        bad = make_profile("Bad")
        bad["capabilities"] = {"tech_comfort": "wizard"}
        services.record_persona("Bad — source", bad, store=store)


def test_brief_persona_asks_for_capabilities(store):
    brief = services.brief_persona("A cautious shop owner in Hamburg.", store=store)
    assert "capabilities" in brief["instructions"] and "tech_comfort" in brief["instructions"]
    assert [i["term"] for i in brief["tech_comfort"]["items"]] == \
        [r["term"] for r in artifacts.tech_comfort_terms()]


# --------------------------------------------------------------- the derivation heuristic

def test_derivation_technical_roles_score_fluent_or_expert(store):
    eng = create_persona(store, "Eva Engineer", title="Senior Engineer (machines)")
    dev = create_persona(store, "Dan Developer", title="Software Developer")
    assert services.get_persona(eng, store)["persona"]["capabilities"]["tech_comfort"] == 4
    assert services.get_persona(dev, store)["persona"]["capabilities"]["tech_comfort"] == 5


def test_derivation_senior_age_scores_cautious_or_novice(store):
    profile = make_profile("Rosa Rentnerin", title="Retired teacher")
    profile["demographics"] = {"age": 71}
    p1 = services.record_persona("Rosa — source", profile, store=store)
    assert services.get_persona(p1["id"], store)["persona"]["capabilities"]["tech_comfort"] == 2
    eldest = make_profile("Otto Oldest", title="Pensioner")
    eldest["demographics"] = {"age": 81}
    p2 = services.record_persona("Otto — source", eldest, store=store)
    assert services.get_persona(p2["id"], store)["persona"]["capabilities"]["tech_comfort"] == 1
    plain = create_persona(store, "Paula Plain")          # neither technical nor senior -> mid
    assert services.get_persona(plain, store)["persona"]["capabilities"]["tech_comfort"] == 3


# --------------------------------------------------------------- update_persona patches

def test_update_persona_capabilities_patch_merges_and_marks_authored(store):
    pid = create_persona(store, "Pia Patch")
    persona = services.update_persona(
        pid, {"capabilities": {"rungs": {"drive": False}, "tech_comfort": 2}}, "declared", store=store)
    caps = persona["capabilities"]
    assert caps["rungs"] == {"see": True, "walk": True, "drive": False, "login": False}
    assert caps["tech_comfort"] == 2 and caps["provenance"] == "authored"
    # a later partial patch keeps the earlier declarations
    caps2 = services.update_persona(
        pid, {"capabilities": {"accessibility": "screen reader"}}, "a11y", store=store)["capabilities"]
    assert caps2["rungs"]["drive"] is False and caps2["accessibility"] == "screen reader"


@pytest.mark.parametrize("bad,match", [
    ({"capabilities": {"telepathy": True}}, "unknown capabilities key"),
    ({"capabilities": {"rungs": {"fly": True}}}, "unknown rung"),
    ({"capabilities": {"rungs": {"drive": "no"}}}, "must be a bool"),
    ({"capabilities": {"tech_comfort": 9}}, "comfort scale"),
    ({"capabilities": {"devices": "desktop"}}, "devices"),
    ({"capabilities": {"provenance": "guessed"}}, "provenance"),
    ({"capabilities": "expert"}, "capabilities must be an object"),
])
def test_update_persona_rejects_invalid_capability_shapes(store, bad, match):
    pid = create_persona(store, "Vera Valid")
    with pytest.raises(ValueError, match=match):
        services.update_persona(pid, bad, "bad patch", store=store)


# --------------------------------------------------------------- fidelity gating (warn, not block)

def test_brief_warns_when_fidelity_exceeds_rungs_and_not_otherwise(store):
    pid = create_persona(store, "Walter Walker")
    services.update_persona(pid, {"capabilities": {"rungs": {"drive": False}}}, "declared", store=store)
    live = {"kind": "live_url", "url": "https://example.test/start", "label": "Live start"}
    brief = services.brief_usability_session(pid, live, "live", store=store)
    assert any(w.startswith("FIDELITY_EXCEEDS_RUNGS") for w in brief["warnings"])
    # within the declared rungs -> no gating warnings at all (warn only when exceeded)
    ok = services.brief_usability_session(pid, _FLOW, "artifact", store=store)
    assert "warnings" not in ok
    assert ok["capabilities"]["rungs"]["drive"] is False


def test_brief_warns_on_login_subjects_when_login_rung_is_off(store):
    pid = create_persona(store, "Lena Locked")
    subject = {"kind": "live_url", "url": "https://example.test/login", "label": "Account login"}
    brief = services.brief_usability_session(pid, subject, "live", store=store)
    assert any(w.startswith("LOGIN_RUNG") for w in brief["warnings"])


def test_brief_weaves_the_tech_comfort_hint_into_the_anti_steering_context(store):
    pid = create_persona(store, "Nora Novice")
    services.update_persona(pid, {"capabilities": {"tech_comfort": 1}}, "declared", store=store)
    brief = services.brief_usability_session(pid, _FLOW, "artifact", store=store)
    hint = artifacts.resolve_tech_comfort(1)["hint"]
    assert hint in brief["instructions"] and "Anti-steering" in brief["instructions"]


# --------------------------------------------------------------- snapshot on recorded sessions

def test_recorded_session_stamps_the_capability_snapshot_in_effect(store):
    pid = create_persona(store, "Sven Snapshot")
    services.update_persona(pid, {"capabilities": {"tech_comfort": 4}}, "declared", store=store)
    res = services.record_usability_session(pid, _FLOW, "artifact", "2026-06-10",
                                            [_step(0)], _OUTCOME, store=store)
    snap = res["usability_session"]["capabilities_snapshot"]
    assert snap["tech_comfort"] == 4 and snap["provenance"] == "authored"
    # the snapshot survives the persona evolving past it
    services.update_persona(pid, {"capabilities": {"tech_comfort": 1}}, "evolved", store=store)
    stored = services.get_usability_session(res["usability_session"]["id"], store=store)
    assert stored["capabilities_snapshot"]["tech_comfort"] == 4
    # ad-hoc persona ids (no stored persona) record without a snapshot — unchanged contract
    free = services.record_usability_session("pX", _FLOW, "artifact", "2026-06-10",
                                             [_step(0)], _OUTCOME, store=store)
    assert "capabilities_snapshot" not in free["usability_session"]


# --------------------------------------------------------------- vocabulary + SOUL + inspector

def test_suggest_tech_comfort_matches_scale_data():
    out = services.suggest_tech_comfort()
    assert [(i["term"], i["value"]) for i in out["items"]] == \
        [(r["term"], r["value"]) for r in artifacts.tech_comfort_terms()]
    by_term = {i["term"]: i for i in out["items"]}
    assert "power user" in by_term["expert"]["aliases"]
    assert by_term["novice"]["hint"].startswith("reads every label")
    assert artifacts.resolve_tech_comfort(" Versiert ") == artifacts.resolve_tech_comfort(4)
    assert artifacts.resolve_tech_comfort("wizard") is None    # unknown -> rejected, never bucketed


def test_soul_renders_the_capabilities_section(store):
    pid = create_persona(store, "Sami Soul")
    services.update_persona(pid, {"capabilities": {"tech_comfort": 5, "rungs": {"login": True}}},
                            "declared", store=store)
    soul = services.get_persona_soul(pid, store)["content"]
    assert "## Capabilities" in soul
    assert "see=yes · walk=yes · drive=yes · login=yes" in soul
    assert "5/5 (expert)" in soul and "Profile provenance: authored" in soul


def test_persona_page_shows_the_capability_card(store):
    from starlette.testclient import TestClient
    from sonaloop import web

    pid = create_persona(store, "Ines Inspector")
    services.update_persona(
        pid, {"capabilities": {"rungs": {"drive": False}, "tech_comfort": 2,
                               "accessibility": "screen reader"}}, "declared", store=store)
    client = TestClient(web.create_app())
    html = client.get(f"/personas/{pid}?lang=en").text
    assert "Capabilities" in html and "Tech comfort: Cautious" in html
    assert "authored" in html and "screen reader" in html
    # a never-declared persona renders the derived profile, marked as such
    other = create_persona(store, "Egon Derived")
    html2 = client.get(f"/personas/{other}?lang=en").text
    assert "Capabilities" in html2 and "derived" in html2
