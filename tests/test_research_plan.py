"""R1 — research-plan model + storage + plan.md render (spec/research-plan-engine.md §9 R1).

A hand-authored plan persists, round-trips, and renders a bucketed plan.md; buckets/capabilities
are validated by REFERENCE (no closed enum in code).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from persona_council import plan as P
from persona_council import services, web


def _plan(pid="proj1"):
    return P.new_plan(pid, goal="How might we test the plan?", methodology="double_diamond_deep", tasks=[
        {"id": "frame1", "title": "Frame the inquiry", "bucket": "analyze", "capability": "frame",
         "intent": "understand before concluding", "plan_note": "read persona memory first"},
        {"id": "c1", "title": "Pain council", "bucket": "act", "capability": "explore",
         "consumes": ["frame1"], "produces": [{"kind": "council", "id": "council_abc"}]},
        {"id": "c2", "title": "Provider council", "bucket": "act", "capability": "explore",
         "consumes": ["frame1"], "produces": [{"kind": "council", "id": "council_def"}]},
        {"id": "v1", "title": "Key problems", "bucket": "verify", "capability": "synthesize",
         "consumes": ["c1", "c2"], "requires": {"min_inputs": 2, "gate_tag": "divergence_complete"}},
    ])


def test_plan_roundtrips_through_store(store):
    p = _plan()
    P.save_plan(p, store=store)
    got = P.get_plan("proj1", store=store)
    assert got is not None
    assert got["goal"] == "How might we test the plan?"
    assert [t["id"] for t in got["tasks"]] == ["frame1", "c1", "c2", "v1"]
    assert got["tasks"][1]["produces"][0] == {"kind": "council", "id": "council_abc"}
    # the verify task carries its gate
    v1 = next(t for t in got["tasks"] if t["id"] == "v1")
    assert v1["requires"]["min_inputs"] == 2 and v1["requires"]["gate_tag"] == "divergence_complete"


def test_ready_frontier_and_completion(store):
    p = _plan()
    ready = {t["id"] for t in P.ready_tasks(p)}
    assert ready == {"frame1"}                      # only the root frame is ready
    P.task(p, "frame1")["status"] = "done"
    assert {t["id"] for t in P.ready_tasks(p)} == {"c1", "c2"}   # both act councils unlock (branch)
    for t in p["tasks"]:
        t["status"] = "done"
    assert P.is_complete(p)


def test_render_plan_md_is_bucketed(store):
    md = P.render_plan_md(_plan())
    assert "# Research plan — How might we test the plan?" in md
    assert "## Next (ready)" in md
    for section in ("## Analyze", "## Act", "## Verify"):
        assert section in md, section
    assert "council:council_abc" in md          # evidence ref rendered
    assert "gate=divergence_complete" in md       # gate rendered
    # export via services
    services.save_plan(_plan(), store=store)
    assert "## Analyze" in services.export_plan_md("proj1", store=store)


def test_bad_plan_rejected(store):
    with pytest.raises(P.PlanError):                # missing bucket tag
        P.validate_plan({"project_id": "x", "tasks": [{"id": "a", "title": "A"}]})
    with pytest.raises(P.PlanError):                # consumes unknown
        P.validate_plan({"project_id": "x", "tasks": [
            {"id": "a", "bucket": "act"}, {"id": "b", "bucket": "act", "consumes": ["ghost"]}]})
    with pytest.raises(P.PlanError):                # cycle
        P.validate_plan({"project_id": "x", "tasks": [
            {"id": "a", "bucket": "act", "consumes": ["b"]}, {"id": "b", "bucket": "act", "consumes": ["a"]}]})


def test_no_hardcoded_bucket_or_capability_set():
    """R1 acceptance: the plan engine must not encode a closed bucket/capability/kind vocabulary."""
    src = Path(P.__file__).read_text()
    for banned in ("BUCKETS =", "CAPABILITIES =", "KINDS =", "ALLOWED_BUCKETS", "VALID_CAPABILITIES"):
        assert banned not in src, banned
    # an invented bucket + capability + evidence kind validate fine
    P.validate_plan({"project_id": "x", "tasks": [
        {"id": "a", "bucket": "ponder", "capability": "divine", "produces": [{"kind": "omen", "id": "o1"}]}]})


# --------------------------------------------------------------------------- R2: seeding

def test_methodology_seeds_plan_with_gated_verify_tasks(store):
    proj = services.start_project("Deep", "How might we test seeding?", "double_diamond_deep",
                                  persona_ids=["p1"], store=store)
    plan = services.get_plan(proj["id"], store=store)
    by = {t["id"]: t for t in plan["tasks"]}
    # a frame (analyze) per fan step, a verify per decide step
    assert by["frame__discover"]["bucket"] == "analyze" and by["frame__discover"]["consumes"] == []
    assert by["verify__define"]["bucket"] == "verify"
    assert by["verify__define"]["requires"]["min_inputs"] == 2
    assert by["verify__define"]["requires"]["gate_tag"] == "divergence_complete"
    # session gates carried from the constellation (lofi at lofi_select, midfi at deliver)
    assert by["verify__lofi_select"]["requires"]["session_of_tags"] == ["lofi"]
    assert by["verify__deliver"]["requires"]["session_of_tags"] == ["midfi"]
    # the DAG threads frame -> verify -> frame -> ...
    assert by["verify__define"]["consumes"] == ["frame__discover"]
    assert by["frame__ideate"]["consumes"] == ["verify__define"]
    # only the root frame is ready at the start
    assert {t["id"] for t in services.ready_tasks(plan)} == {"frame__discover"}


def test_freeform_seeds_single_root_frame(store):
    proj = services.start_project("Freeform", "What do users want?", None,
                                  persona_ids=["p1"], store=store)
    plan = services.get_plan(proj["id"], store=store)
    assert len(plan["tasks"]) == 1
    t = plan["tasks"][0]
    assert t["bucket"] == "analyze" and t["capability"] == "frame" and t["consumes"] == []
    assert "## Analyze" in services.export_plan_md(proj["id"], store=store)


# --------------------------------------------------------------------------- R3: frame

def test_act_blocked_until_frame_discharged(store):
    proj = services.start_project("Deep", "hmw?", "double_diamond_deep", persona_ids=["p1"], store=store)
    pid = proj["id"]
    # orchestrator adds an act council under the discover frame
    services.add_task(pid, "act", "explore", "Pain council", consumes=["frame__discover"], store=store)
    plan = services.get_plan(pid, store=store)
    ready = {t["id"] for t in services.ready_tasks(plan)}
    assert "frame__discover" in ready and not any(t.startswith("act__") for t in ready)  # act blocked

    # frame requires >=1 question AND >=1 memory ref (can't silently skip)
    import pytest
    with pytest.raises(services.PlanError):
        services.record_frame(pid, "frame__discover", ["q?"], memory_refs=[], store=store)
    with pytest.raises(services.PlanError):
        services.record_frame(pid, "frame__discover", [], memory_refs=["fact:1"], store=store)

    # a minimal honest frame discharges it; act now unlocks
    services.record_frame(pid, "frame__discover",
                          questions=["Welche Versicherungen haben sie schon?", "Vorsorge-Bewusstsein?"],
                          hypotheses=["KFZ-Moment ist Pflichtakt"], memory_refs=["persona:aylin/day:2026-05-20"],
                          store=store)
    plan = services.get_plan(pid, store=store)
    fr = next(t for t in plan["tasks"] if t["id"] == "frame__discover")
    assert fr["status"] == "done" and fr["frame"]["memory_refs"] == ["persona:aylin/day:2026-05-20"]
    assert fr["produces"] == [{"kind": "frame", "id": "frame__discover"}]
    ready = {t["id"] for t in services.ready_tasks(plan)}
    assert any(t.startswith("act__") for t in ready)   # the act council is now ready


# --------------------------------------------------------------------------- R4: router + gates

def test_verify_gated_until_breadth_and_judgment(store):
    proj = services.start_project("Deep", "hmw?", "double_diamond_deep", persona_ids=["p1"], store=store)
    pid = proj["id"]
    services.record_frame(pid, "frame__discover", ["q1?", "q2?"], memory_refs=["persona:p1/day:1"], store=store)
    # one act council so far
    a1 = services.add_task(pid, "act", "explore", "Council A", consumes=["frame__discover"], store=store)
    services.link_evidence(pid, a1["id"], {"kind": "council", "id": "c1"}, store=store)

    # verify is on the frontier (frame done) but GATED: needs >=2 fan evidence + a gate judgment
    b = services.brief_next(pid, store=store)
    assert "verify__define" in b["ready"]
    import pytest
    with pytest.raises(services.PlanError) as e:
        services.complete_task(pid, "verify__define", store=store)
    assert e.value.code == "GATE_UNMET"

    # add the second council → breadth ok, but still no judgment
    a2 = services.add_task(pid, "act", "explore", "Council B", consumes=["frame__discover"], store=store)
    services.link_evidence(pid, a2["id"], {"kind": "council", "id": "c2"}, store=store)
    with pytest.raises(services.PlanError):
        services.complete_task(pid, "verify__define", store=store)   # missing divergence_complete

    # record the evidence-backed gate judgment → verify can complete
    services.record_judgment(pid, "verify__define", "divergence_complete", True,
                             "two distinct pain clusters; saturating", evidence_refs=["c1", "c2"], store=store)
    services.complete_task(pid, "verify__define", store=store)
    plan = services.get_plan(pid, store=store)
    assert next(t for t in plan["tasks"] if t["id"] == "verify__define")["status"] == "done"
    # next frame unlocks
    assert "frame__ideate" in {t["id"] for t in services.ready_tasks(plan)}


def test_brief_next_dispatches_to_plan(store):
    proj = services.start_project("F", "what?", None, persona_ids=["p1"], store=store)
    b = services.brief_next(proj["id"], store=store)
    assert b["task"] == "frame__root" and b["bucket"] == "analyze" and not b["complete"]


# --------------------------------------------------------------------------- R5: evidence graph

def _council(store, cid):
    store.insert_council_session({"id": cid, "created_at": f"2026-06-0{cid[-1]}T00:00:00+00:00",
        "prompt": f"Council {cid}", "persona_ids": ["p1"], "turns": [], "votes": [], "proposal": "",
        "summary": "", "exec_summary": "e", "selection_reason": "x"})
    return cid


def test_heterogeneous_graph_councils_and_synthesis(store):
    proj = services.start_project("Deep", "hmw?", "double_diamond_deep", persona_ids=["p1"], store=store)
    pid = proj["id"]
    services.record_frame(pid, "frame__discover", ["q?"], memory_refs=["m1"], store=store)
    # three real act councils as first-class evidence (NOT wrapped in syntheses)
    for i in (1, 2, 3):
        _council(store, f"cc{i}")
        a = services.add_task(pid, "act", "explore", f"Council {i}", consumes=["frame__discover"], store=store)
        services.link_evidence(pid, a["id"], {"kind": "council", "id": f"cc{i}"}, store=store)
    # one optional verify synthesis consolidating them
    syn = services.record_synthesis("Key problems", "hmw", ["cc1", "cc2", "cc3"],
                                    {"gesamtbild": "clustered"}, store=store)
    services.link_evidence(pid, "verify__define", {"kind": "synthesis", "id": syn["id"]}, store=store)

    g = services.get_project_graph(pid, store=store)
    kinds = sorted(n["kind"] for n in g["nodes"])
    assert kinds == ["council", "council", "council", "synthesis"]   # 3 councils + 1 synthesis, not 3 wrappers
    # the synthesis consolidates all three councils (refines edges)
    refines = [(e["from_study"], e["to_study"]) for e in g["edges"] if e["type"] == "refines"]
    assert (f"council:cc1", f"synthesis:{syn['id']}") in refines
    assert len([e for e in refines if e[1] == f"synthesis:{syn['id']}"]) == 3
    # colors come from data (present(kind)), not code
    council_node = next(n for n in g["nodes"] if n["kind"] == "council")
    assert council_node["color"] == "#6b7cff"          # from suggestions/evidence_kinds.json
    assert "rgdata" in web._graph_interactive(g)        # renders


def test_no_hardcoded_evidence_kind_literal_in_web():
    from pathlib import Path
    src = "\n".join(f.read_text() for f in sorted(Path(web.__file__).parent.glob("*.py")))
    for lit in ('== "council"', '== "synthesis"', '== "frame"', '{"council"', '{"synthesis"',
                '"kind": "council"', '"kind": "synthesis"'):
        assert lit not in src, f"web.py must not hardcode evidence-kind literal {lit}"


# --------------------------------------------------------------------------- R6: progress

def test_assess_progress_is_evidence_cited_no_metric(store):
    proj = services.start_project("Deep", "Win young KFZ buyers for LV?", "double_diamond_deep",
                                  persona_ids=["p1"], store=store)
    pid = proj["id"]
    services.record_frame(pid, "frame__discover", ["q?"], memory_refs=["m1"], store=store)
    _council(store, "cx1")
    a = services.add_task(pid, "act", "explore", "Council", consumes=["frame__discover"], store=store)
    services.link_evidence(pid, a["id"], {"kind": "council", "id": "cx1"}, store=store)
    import pytest
    with pytest.raises(services.PlanError):              # must cite evidence
        services.assess_progress(pid, "verify__deliver", "we are closer", [], store=store)
    rec = services.assess_progress(pid, "verify__deliver",
                                   "Problem space framed; one pain council in. The surprising core "
                                   "segment is emerging.", evidence_refs=["cx1"], delta="näher",
                                   store=store)
    assert rec["delta"] == "näher" and rec["evidence_refs"] == ["cx1"]
    assert rec["coverage"]["evidence_by_kind"]["council"] == 1   # descriptive count, not a score
    plan = services.get_plan(pid, store=store)
    assert plan["progress"][0]["goal"] == "Win young KFZ buyers for LV?"


def test_no_hardcoded_progress_metric_threshold():
    from pathlib import Path
    import re
    src = Path(P.__file__).read_text()
    # the coverage/progress code must not compare a count to a hardcoded score threshold
    fn = src[src.index("def assess_progress"):src.index("def brief_next")]
    assert not re.search(r">=\s*0\.\d|score\s*=", fn), "no hardcoded progress score/threshold allowed"


# --------------------------------------------------------------------------- R8: migration + gate

def test_grep_gate_no_hardcoded_bucket_kind_vocabulary():
    """R8: no closed bucket/capability/kind VOCABULARY in the engine, and no kind PRESENTATION
    literal in the UI (kind presentation comes from suggestions/evidence_kinds.json via present()).
    (Storage dispatch — which table a council vs synthesis lives in — is legitimate, not vocabulary.)"""
    from pathlib import Path
    psrc = Path(P.__file__).read_text()
    for banned in ("BUCKETS =", "CAPABILITIES =", "KINDS ="):
        assert banned not in psrc, banned
    wsrc = "\n".join(f.read_text() for f in sorted(Path(web.__file__).parent.glob("*.py")))
    for lit in ('== "council"', '== "synthesis"', '{"council"', '{"synthesis"',
                '"kind": "council"', '"kind": "synthesis"'):
        assert lit not in wsrc, f"web.py must not hardcode evidence-kind literal {lit}"


# --------------------------------------------------------------------------- GAP-5: groundedness

def test_browser_log_retained_past_close_for_grounding():
    """GAP-5: a session's observed-state log survives close() so a proband reaction recorded AFTER
    closing the browser still verifies (the clean drive→close→record order no longer loses evidence)."""
    from persona_council import browser
    browser._RETAINED_LOGS.clear()
    sid = "psession_test_retain"
    browser._retain_log(sid, [{"kind": "snapshot", "refs": ["r1"], "text": "Du hast die Hand drauf"}])
    log = browser.session_log(sid)            # not in _SESSIONS, but retained
    assert log and log[0]["refs"] == ["r1"]


def test_ungrounded_proband_session_warns_and_blocks_gate(store, tmp_path, monkeypatch):
    """GAP-5: an unverified proband session (no observed-state log) is flagged on write AND does not
    satisfy a session_of_tags gate when the harness can verify; a grounded session clears it."""
    import persona_council.prototypes as P
    monkeypatch.setattr(P, "prototypes_dir", lambda: tmp_path / "protos")
    from persona_council import plan as PL, services, browser
    monkeypatch.setattr(browser, "available", lambda: True)
    proj = services.start_project("G", "hmw?", None, persona_ids=["p1"], store=store)
    pid = proj["id"]
    concept = {"title": "P", "summary": "", "start": "a", "screens": [
        {"id": "a", "title": "A", "elements": [{"kind": "text", "id": "t", "label": "x"}]}]}
    art = services.scaffold_artifact("g5-proto", "G5", concept, type="prototype", tags=["lofi"],
                                     project_id=pid, store=store)
    # record a session with a session_id that has NO browser log -> grounded False + warning
    out = services.record_prototype_session("p1", art["id"], "no-such-session", "2026-06-05",
        {"summary": "ok", "observed_state_refs": ["x"], "verdict": "ok"}, store=store)
    assert out["grounded_verified"] is False
    assert any("UNVERIFIED_SESSION" in w for w in out.get("warnings", []))
    # a verify task requiring a session of `lofi` is blocked while only the ungrounded session exists
    vtask = {"id": "v", "bucket": "verify", "capability": "decide", "consumes": [],
             "requires": {"session_of_tags": ["lofi"]}}
    plan = {"project_id": pid, "tasks": [vtask]}
    PL.validate_plan(plan)
    unmet = PL.verify_unmet(plan, PL.task(plan, "v"), store)
    assert any("GROUNDED" in u for u in unmet), unmet
    # a verified session of the same artifact clears the groundedness gap
    store.insert_prototype_session({"id": "ps_grounded", "persona_id": "p1", "prototype_id": art["id"],
        "session_id": "s", "date": "2026-06-05", "reaction": {}, "observed_state_refs": ["x"],
        "created_at": "2026-06-05T00:00:00+00:00", "grounded_verified": True})
    unmet2 = PL.verify_unmet(plan, PL.task(plan, "v"), store)
    assert not any("GROUNDED" in u for u in unmet2), unmet2


def test_next_action_act_surfaces_artifact_palette_and_divergence_nudges(store):
    """GAP-2/SPEC-A: an act step surfaces the artifact archetype PALETTE (from data, incl. the
    interactive `model`) + methodology-agnostic divergence nudges (diversify KIND, a dark-horse,
    a disconfirmation council) — so concept breadth is reliable, not luck of a disciplined agent."""
    proj = services.start_project("G", "hmw?", None, persona_ids=["p1"], store=store)
    pid = proj["id"]
    services.record_frame(pid, "frame__root", ["q?"], memory_refs=["m1"], store=store)
    services.add_task(pid, "act", "explore", "angle", consumes=["frame__root"], store=store)
    act = services.next_action(pid, store=store)["act"]
    tags = {p["tag"] for p in act["artifact_palette"]}
    assert {"flow", "comparison", "model"} <= tags          # varied non-form archetypes, incl. model
    nudges = " ".join(act["divergence"]).lower()
    assert "dark-horse" in nudges and "disconfirmation" in nudges and "model" in nudges


def test_next_action_act_surfaces_ideation_lenses_for_innovation(store):
    """Innovation: an act step surfaces data-driven creativity lenses (analogy, make-the-invisible-
    EXPERIENCEABLE→simulation, reversal, …) so ideation pushes for non-obvious concepts, not tweaks."""
    proj = services.start_project("G", "hmw?", None, persona_ids=["p1"], store=store)
    pid = proj["id"]
    services.record_frame(pid, "frame__root", ["q?"], memory_refs=["m1"], store=store)
    services.add_task(pid, "act", "ideate", "ideas", consumes=["frame__root"], store=store)
    act = services.next_action(pid, store=store)["act"]
    lenses = {l["tag"] for l in act["ideation_lenses"]}
    assert {"analogy", "experienceable", "reversal"} <= lenses
    exp = next(l for l in act["ideation_lenses"] if l["tag"] == "experienceable")
    assert "model" in exp["prompt"].lower() or "simulation" in exp["prompt"].lower()


def test_assess_project_surfaces_novelty_signal(store, tmp_path, monkeypatch):
    """Innovation reliability: assess_project reports concept-KIND diversity + whether an interactive
    model exists, and flags a narrow (forms-only) space so a run can push for a bolder concept."""
    import persona_council.prototypes as PP
    monkeypatch.setattr(PP, "prototypes_dir", lambda: tmp_path / "p")
    proj = services.start_project("G", "hmw?", None, persona_ids=["p1"], store=store)
    pid = proj["id"]
    concept = {"title": "T", "start": "a", "screens": [{"id": "a", "title": "A", "elements": [
        {"kind": "text", "id": "t", "label": "x"}]}]}
    services.scaffold_artifact("only-form", "F", concept, type="survey", tags=["lofi"], project_id=pid, store=store)
    n = services.assess_project(pid, store=store)["novelty"]
    assert n["has_interactive_model"] is False and n["hint"].startswith("narrow")
    services.scaffold_artifact("a-model", "M", concept, type="model", tags=["lofi"], project_id=pid, store=store)
    n2 = services.assess_project(pid, store=store)["novelty"]
    assert n2["has_interactive_model"] is True and n2["hint"] == "diverse"


def test_assess_project_finish_readiness_gate(store, tmp_path, monkeypatch):
    """A run must not stop at 'gates passed'. assess_project reports FINISH readiness (organized +
    concluded + handed-off); when the plan is complete but unfinished, the recommendation is 'finish'."""
    import persona_council.prototypes as PP
    monkeypatch.setattr(PP, "prototypes_dir", lambda: tmp_path / "p")
    proj = services.start_project("G", "hmw?", None, persona_ids=["p1"], store=store)
    pid = proj["id"]
    services.record_frame(pid, "frame__root", ["q?"], memory_refs=["m1"], store=store)  # completes it -> plan complete
    concept = {"title": "T", "start": "a", "screens": [{"id": "a", "title": "A", "elements": [
        {"kind": "text", "id": "t", "label": "x"}]}]}
    services.scaffold_artifact("p", "P", concept, type="prototype", tags=["lofi"], project_id=pid, store=store)  # substantial
    a = services.assess_project(pid, store=store)
    assert a["complete"] is True and a["recommendation"] == "finish"
    assert a["finish"]["organized"] is False and a["finish"]["finished"] is False
    assert any("organized" in g for g in a["gaps"])
