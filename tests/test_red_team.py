"""Red-Team / Falsification Format (taxonomy id `red_team`): run a council that deliberately argues the
NEGATIVE case — "why would this segment NOT adopt / NOT pay / churn?" — so the output stress-tests the idea
instead of flattering it. Covers: the disconfirmation briefing (reframes the task + stamps an adversarial
role into each persona's context), the deterministic case-against aggregation (objections grouped by theme,
personas-per-blocker count, worst severity), running the SAME question in both directions (stance='both'),
persistence (a queryable CouncilSession carrying a `red_team` block), and an artifact-grounded red-team.

Capture is stubbed (no network) by monkeypatching sonaloop.capture.capture_url, mirroring the rest of the
suite (host/IO output supplied inline; no server-side text-LLM calls)."""
from __future__ import annotations

from sonaloop import services
from sonaloop import capture as _capture
from conftest import create_persona


def _fake_capture(mapping):
    def _cap(url, *, timeout=12.0):
        snap = mapping.get(url)
        if snap is None:
            return {"ok": False, "mode": "unavailable", "url": url, "captured_at": "2026-06-09T00:00:00Z",
                    "title": "", "description": "", "headings": [], "text": "", "status": None,
                    "final_url": url, "bytes": 0, "content_hash": "deadbeef", "error": "boom"}
        return {"ok": True, "mode": "text", "url": url, "final_url": url, "status": 200,
                "captured_at": "2026-06-09T00:00:00Z", "bytes": len(snap["text"]),
                "content_hash": snap["hash"], "title": snap["title"], "description": snap.get("desc", ""),
                "headings": snap.get("headings", []), "text": snap["text"]}
    return _cap


def _project(store, personas=("Alpha",), **kw):
    pids = [create_persona(store, n, **kw) for n in personas]
    proj = services.create_research_project("Adoption study", goal="will they adopt?",
                                            persona_ids=pids, store=store)
    return proj["id"], pids


# --------------------------------------------------------------------------- disconfirmation briefing

def test_red_team_briefing_reframes_task_and_assigns_adversarial_roles(store):
    pid, [persona] = _project(store)
    brief = services.brief_red_team(
        pid, "Would freelancers pay $29/mo for this?", persona_ids=[persona], store=store)
    assert brief["schema"] == "red_team"
    assert brief["stance"] == "against"
    ctx = brief["participants"][0]["agent_context"]
    # The task is reframed toward DISCONFIRMATION, not a flattering reaction.
    assert "RED-TEAM" in ctx and "CASE AGAINST" in ctx
    assert "NOT adopt" in ctx and "boilerplate" in ctx.lower()
    # An explicit, deterministic adversarial lens is stamped into the persona's context AND surfaced.
    assert brief["participants"][0]["role"]["id"] == "skeptic"   # first persona → first role, round-robin
    assert "ADVERSARIAL LENS" in ctx
    # The roles are VISIBLE in the brief (a reviewer can see who attacks from which angle).
    assert "ADVERSARIAL ROLES" in brief["roles_block"]
    assert "red_team" in brief["instructions"]


def test_red_team_assigns_distinct_lenses_round_robin(store):
    pids = [create_persona(store, f"P{i}") for i in range(6)]
    proj = services.create_research_project("p", goal="g", persona_ids=pids, store=store)
    brief = services.brief_red_team(proj["id"], "?", persona_ids=pids, store=store)
    role_ids = [p["role"]["id"] for p in brief["participants"]]
    # Five distinct adversarial lenses are covered, then they wrap (round-robin, deterministic).
    assert role_ids[:5] == ["skeptic", "blocker", "switching_cost", "status_quo", "risk"]
    assert role_ids[5] == "skeptic"


def test_red_team_selection_returns_candidate_panel(store):
    pid, [persona] = _project(store)
    brief = services.brief_red_team(pid, "Why might they churn?", store=store)
    assert brief["schema"] == "red_team_selection"
    assert brief["candidate_personas"] and brief["roles"]


# --------------------------------------------------------------------------- case-against aggregation math

def test_case_against_groups_objections_by_theme_with_counts_and_severity(store):
    a = create_persona(store, "A")
    b = create_persona(store, "B")
    c = create_persona(store, "C")
    proj = services.create_research_project("agg", goal="g", persona_ids=[a, b, c], store=store)

    objections = [
        {"persona_id": a, "theme": "switching cost", "text": "I'd have to migrate 200 docs.", "severity": "high"},
        {"persona_id": b, "theme": "switching cost", "text": "My team is trained on the old tool.", "severity": "critical"},
        {"persona_id": c, "theme": "switching cost", "text": "Re-doing my templates is a week of work.", "severity": "medium"},
        {"persona_id": a, "theme": "no proof", "text": "No case study for my segment.", "severity": "low"},
    ]
    session = services.record_red_team(
        proj["id"], "Will they switch?", objections=objections,
        exec_summary="Host-authored case-against.", summary="TL;DR.", store=store)

    case = session["red_team"]["case_against"]
    by_theme = {th["theme"]: th for th in case["themes"]}
    # 'switching cost' is raised by 3 distinct personas, worst severity critical → it leads (most reach).
    assert case["themes"][0]["theme"] == "switching cost"
    assert by_theme["switching cost"]["count"] == 3
    assert by_theme["switching cost"]["severity"] == "critical"
    assert by_theme["no proof"]["count"] == 1
    assert case["theme_count"] == 2
    assert case["voices"] == 3
    assert case["worst_severity"] == "critical"
    assert case["top_blocker"] == "switching cost"


def test_case_against_dedupes_personas_per_theme(store):
    a = create_persona(store, "A")
    proj = services.create_research_project("dedup", goal="g", persona_ids=[a], store=store)
    session = services.record_red_team(
        proj["id"], "?", objections=[
            {"persona_id": a, "theme": "price", "text": "too pricey", "severity": "high"},
            {"persona_id": a, "theme": "price", "text": "and no annual plan", "severity": "medium"}],
        store=store)
    th = session["red_team"]["case_against"]["themes"][0]
    # Same persona raising one theme twice still counts as ONE persona, but BOTH items are kept.
    assert th["count"] == 1 and len(th["items"]) == 2
    assert th["severity"] == "high"   # worst across the persona's items


def test_unknown_severity_coerces_to_medium_but_keeps_the_raw_token(store):
    a = create_persona(store, "A")
    proj = services.create_research_project("sev", goal="g", persona_ids=[a], store=store)
    session = services.record_red_team(
        proj["id"], "?", objections=[
            {"persona_id": a, "theme": "trust", "text": "hm", "severity": "Showstopper!"},
            {"persona_id": a, "theme": "trust", "text": "ok", "severity": " HIGH "}],
        store=store)
    items = session["red_team"]["case_against"]["themes"][0]["items"]
    # coercion default stays 'medium', but the host's token survives inspectably on the item
    assert items[0]["severity"] == "medium" and items[0]["severity_raw"] == "Showstopper!"
    assert items[1]["severity"] == "high" and "severity_raw" not in items[1]   # known token, case/space-tolerant


def test_no_objections_yields_empty_case_against(store):
    a = create_persona(store, "A")
    proj = services.create_research_project("empty", goal="g", persona_ids=[a], store=store)
    session = services.record_red_team(proj["id"], "?", objections=[], persona_ids=[a], store=store)
    case = session["red_team"]["case_against"]
    assert case["theme_count"] == 0 and case["top_blocker"] is None and case["voices"] == 0


# --------------------------------------------------------------------------- both directions on one question

def test_stance_both_runs_same_question_in_both_directions(store):
    a = create_persona(store, "A")
    b = create_persona(store, "B")
    proj = services.create_research_project("both", goal="g", persona_ids=[a, b], store=store)
    brief = services.brief_red_team(proj["id"], "Adopt or not?", persona_ids=[a, b], stance="both", store=store)
    assert brief["stance"] == "both"
    assert "CASE AGAINST" in brief["participants"][0]["agent_context"]
    assert "CASE FOR" in brief["participants"][0]["agent_context"]

    session = services.record_red_team(
        proj["id"], "Adopt or not?", stance="both",
        objections=[{"persona_id": a, "theme": "trust", "text": "Never heard of them.", "severity": "high"}],
        endorsements=[{"persona_id": b, "theme": "time saved", "text": "Cuts my admin in half."}],
        store=store)
    rt = session["red_team"]
    # Case-for and case-against sit side by side and are comparable.
    assert rt["case_against"]["top_blocker"] == "trust"
    assert rt["case_for"]["themes"][0]["theme"] == "time saved"
    assert rt["case_for"]["voices"] == 1


# --------------------------------------------------------------------------- artifact-grounded red-team

def test_red_team_can_attack_a_real_artifact(store, monkeypatch):
    monkeypatch.setattr(_capture, "capture_url", _fake_capture({
        "https://pricing.test": {"title": "Pricing", "text": "Only $99/mo, no free tier.", "hash": "hp"}}))
    pid, [persona] = _project(store)
    art = services.add_artifact(pid, "https://pricing.test", kind="url", store=store)
    brief = services.brief_red_team(
        pid, "Why would they NOT pay this price?", persona_ids=[persona],
        artifact_ids=[art["id"]], store=store)
    ctx = brief["participants"][0]["agent_context"]
    # The captured artifact is in the room AND the disconfirmation reframing wraps it.
    assert "Only $99/mo, no free tier." in ctx
    assert "RED-TEAM" in ctx and brief["artifacts"]


# --------------------------------------------------------------------------- persistence + queryable seam

def test_red_team_persists_as_queryable_council(store):
    pid, [persona] = _project(store)
    session = services.record_red_team(
        pid, "Will they churn?",
        objections=[{"persona_id": persona, "theme": "missing feature", "text": "No SSO.", "severity": "high"}],
        exec_summary="The host's case-against.", store=store)
    sid = session["id"]

    # It is a real CouncilSession (reuses council persistence + the project graph).
    assert services.is_red_team(session)
    fetched = services.get_council(sid, store=store)
    assert fetched["red_team"]["case_against"]["top_blocker"] == "missing feature"
    proj = services.get_research_project(pid, store=store)
    assert sid in proj["council_ids"]

    # get_red_team returns the structured result directly.
    rt = services.get_red_team(sid, store=store)
    assert rt["stance"] == "against"
    assert rt["case_against"]["voices"] == 1

    # The result is ALSO a queryable finding (the analytics/calibration seam).
    from sonaloop import artifacts as _A
    kinds = [f.get("kind") for f in fetched.get("findings", [])]
    assert "red_team" in kinds


def test_get_red_team_rejects_a_plain_council(store):
    import pytest
    pid, [persona] = _project(store)
    council = services.record_council(pid, "plain", [persona], store=store)
    with pytest.raises(KeyError):
        services.get_red_team(council["id"], store=store)


def test_red_team_renders_in_the_inspector(store):
    """The inspector council page surfaces the red-team case-against (blocker themes + severity) — German UI
    strings (match the surrounding language)."""
    from starlette.testclient import TestClient
    from sonaloop import web

    a = create_persona(store, "A")
    b = create_persona(store, "B")
    proj = services.create_research_project("render", goal="g", persona_ids=[a, b], store=store)
    session = services.record_red_team(
        proj["id"], "Why might they not adopt?",
        objections=[{"persona_id": a, "theme": "switching cost", "text": "Costly migration.", "severity": "high"},
                    {"persona_id": b, "theme": "switching cost", "text": "Team retraining.", "severity": "critical"}],
        exec_summary="Host case-against.", store=store)

    client = TestClient(web.create_app())
    html = client.get(f"/councils/{session['id']}?lang=de").text
    assert "Red-Team" in html                       # the red-team section title (German UI)
    assert "Argumente dagegen" in html              # case-against headline
    assert "switching cost" in html                 # the blocker theme row
    assert "kritisch" in html                        # worst severity (German)


def test_red_team_idempotent_on_key(store):
    pid, [persona] = _project(store)
    common = dict(prompt="Will they churn?",
                  objections=[{"persona_id": persona, "theme": "price", "text": "too pricey", "severity": "high"}],
                  key="run1", store=store)
    s1 = services.record_red_team(pid, **common)
    s2 = services.record_red_team(pid, **common)
    assert s1["id"] == s2["id"]
    assert len([c for c in services.list_councils(store=store) if c["id"] == s1["id"]]) == 1
