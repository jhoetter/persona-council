"""Methodology engine — tag-driven constellations (spec/methodology-constellations.md).

Structure enforced, dynamics LLM-judged, ZERO hardcoded vocabularies. A decide step cannot
record until its consumed fan has >= min_inputs nodes AND a decided gate judgment; the graph
comes out wide->narrow->wide->narrow; no numeric dynamic threshold exists; capability/role/
artifact-type are OPEN TAGS (an invented tag loads and runs); non-alternating DAG shapes work.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from persona_council import methodology as M
from persona_council import services


def _council(store, cid: str) -> str:
    store.insert_council_session({
        "id": cid, "created_at": "2026-06-01T00:00:00+00:00", "prompt": "P?",
        "persona_ids": ["p1"], "turns": [], "votes": [], "proposal": "", "summary": "",
        "exec_summary": "exec", "selection_reason": "x"})
    return cid


def _payload(text: str) -> dict:
    return {"gesamtbild": text, "arc_narrative": text}


# --------------------------------------------------------------------------- C1: tags

def test_builtins_load_and_validate(store):
    keys = {m["key"] for m in M.list_methodologies(store=store)}
    assert {"double_diamond", "double_diamond_deep", "dschool_micro", "lean_jtbd"} <= keys
    dd = M.get_methodology("double_diamond", store=store)
    # shape is derived from structure: explore (fan) then decide (waist), alternating here
    assert [M._mode(s) for s in dd["steps"]] == ["diverge", "converge", "diverge", "converge"]


def test_no_hardcoded_vocabularies_in_engine_source():
    """C1 acceptance: no closed capability/role/breadth/judgment/artifact SET remains in code."""
    import inspect
    src = Path(M.__file__).read_text()
    for banned in ("DIVERGE_ROLES", "CONVERGE_ROLES", "ROLES =", "JUDGMENT_KINDS", "FIDELITIES", "MODES ="):
        assert banned not in src, banned
    # the INVARIANTS must be artifact-type-generic: no literal artifact string special-cased.
    # (The legacy phases->steps translator may still name old strings — that is back-compat glue,
    # not an invariant.)
    for fn in (M.record_decision, M.brief_next):
        s = inspect.getsource(fn)
        for lit in ('"prototype"', "'prototype'", '"prototype_session"', '"survey"', '"lofi"', '"midfi"'):
            assert lit not in s, f"{fn.__name__} hardcodes artifact tag {lit}"


def test_invented_capability_and_artifact_tags_load(store):
    """An invented capability tag + an invented gate tag validate & run (tag-agnostic)."""
    spec = {
        "key": "invented", "name": "Invented", "description": "d", "when_to_use": "w",
        "steps": [
            {"id": "scout", "name": "Scout", "tags": ["divine-the-vibe"], "intent": "explore",
             "produces": {"role": "vibe-map"}},
            {"id": "land", "name": "Land", "tags": ["crystallize"], "intent": "decide",
             "consumes": ["scout"], "requires": {"min_inputs": 2, "gate_tag": "vibes_are_clear"},
             "produces": {"role": "the-vibe"}},
        ],
    }
    M.register_methodology(spec, store=store)
    got = M.get_methodology("invented", store=store)
    assert [s["tags"] for s in got["steps"]] == [["divine-the-vibe"], ["crystallize"]]
    proj = M.start_methodology_project("Inv", "g", "invented", store=store)
    pid = proj["id"]
    _council(store, "c1"); _council(store, "c2")
    e1 = M.record_node(pid, "A", ["c1"], _payload("a"), store=store)
    e2 = M.record_node(pid, "B", ["c2"], _payload("b"), store=store)
    M.advance(pid, "scout", store=store)
    with pytest.raises(M.MethodologyError) as e:
        M.record_decision(pid, "Land", [e1["id"], e2["id"]], _payload("v"), store=store)
    assert e.value.code == "MISSING_GATE_JUDGMENT"      # enforced by the FREE gate tag name
    M.record_judgment(pid, "scout", "vibes_are_clear", True, "clear", evidence_refs=["c1"], store=store)
    dec = M.record_decision(pid, "Land", [e1["id"], e2["id"]], _payload("v"), store=store)
    assert dec["role"] == "the-vibe"


# --------------------------------------------------------------------------- C2: engine

def test_bad_spec_rejected(store):
    with pytest.raises(M.MethodologyError):  # missing steps
        M.validate_methodology_spec({"key": "x", "name": "x", "description": "d", "when_to_use": "w"})
    with pytest.raises(M.MethodologyError):  # consumes an unknown step
        M.validate_methodology_spec({"key": "x", "name": "x", "description": "d", "when_to_use": "w",
                                     "steps": [{"id": "a", "name": "A"},
                                               {"id": "b", "name": "B", "consumes": ["ghost"]}]})


def test_cycle_rejected(store):
    with pytest.raises(M.MethodologyError):
        M.validate_methodology_spec({"key": "x", "name": "x", "description": "d", "when_to_use": "w",
                                     "steps": [{"id": "a", "name": "A", "consumes": ["b"]},
                                               {"id": "b", "name": "B", "consumes": ["a"]}]})


def test_decide_blocked_until_breadth_and_judgment(store):
    proj = M.start_methodology_project("DD", "How might we test the engine?", "double_diamond", store=store)
    pid = proj["id"]
    b = M.brief_next(pid, store=store)
    assert b["step"] == "discover" and b["mode"] == "diverge"

    _council(store, "c1")
    e1 = M.record_node(pid, "Pain A", ["c1"], _payload("pain a"), store=store)

    # define isn't ready until discover completes -> out of order
    with pytest.raises(M.MethodologyError) as e:
        M.record_decision(pid, "Define", [e1["id"]], _payload("core"), store=store)
    assert e.value.code == "PHASE_OUT_OF_ORDER"

    M.advance(pid, "discover", store=store)
    assert M.brief_next(pid, store=store)["step"] == "define"
    with pytest.raises(M.MethodologyError) as e:
        M.record_decision(pid, "Define", [e1["id"]], _payload("core"), store=store)
    assert e.value.code == "BREADTH_TOO_LOW"


def test_full_diverge_converge_happy_path(store):
    proj = M.start_methodology_project("DD", "How might we test the engine?", "double_diamond", store=store)
    pid = proj["id"]
    _council(store, "c1"); _council(store, "c2")
    e1 = M.record_node(pid, "Pain A", ["c1"], _payload("pain a"), store=store)
    e2 = M.record_node(pid, "Pain B", ["c2"], _payload("pain b"), store=store)
    M.advance(pid, "discover", store=store)  # -> define

    with pytest.raises(M.MethodologyError) as e:
        M.record_decision(pid, "Define", [e1["id"], e2["id"]], _payload("core"), store=store)
    assert e.value.code == "MISSING_GATE_JUDGMENT"

    M.record_judgment(pid, "discover", "divergence_complete", True,
                      "Two distinct pains; no new cluster emerging.", evidence_refs=["c1", "c2"], store=store)
    conv = M.record_decision(pid, "Define · POV", [e1["id"], e2["id"]], _payload("the core problem"), store=store)
    assert conv["mode"] == "converge" and conv["role"] == "point-of-view"

    graph = services.get_project_graph(pid, store=store)
    refines = [(x["from_study"], x["to_study"]) for x in graph["edges"] if x["type"] == "refines"]
    assert (e1["id"], conv["id"]) in refines and (e2["id"], conv["id"]) in refines

    M.advance(pid, "define", store=store)  # -> develop (fan)
    assert M.brief_next(pid, store=store)["step"] == "develop"

    st = M.get_methodology_state(pid, store=store)
    by = {p["key"]: p for p in st["steps"]}
    assert by["discover"]["exploration_count"] == 2          # wide
    assert by["define"]["convergence_node"] == conv["id"]    # narrow (the waist)


def test_legacy_aliases_still_work(store):
    """brief_phase/record_exploration/record_convergence/advance_phase remain as aliases."""
    proj = M.start_methodology_project("DD", "g", "double_diamond", store=store)
    pid = proj["id"]
    assert M.brief_phase(pid, store=store)["phase"] == "discover"
    _council(store, "c1"); _council(store, "c2")
    e1 = M.record_exploration(pid, "A", ["c1"], _payload("a"), store=store)
    e2 = M.record_exploration(pid, "B", ["c2"], _payload("b"), store=store)
    M.advance_phase(pid, store=store)
    M.record_judgment(pid, "discover", "divergence_complete", True, "ok", evidence_refs=["c1"], store=store)
    conv = M.record_convergence(pid, "Def", [e1["id"], e2["id"]], _payload("c"), store=store)
    assert conv["role"] == "point-of-view"


def test_non_alternating_dag_with_nonprototype_artifact(store):
    """C2 acceptance: a NON-alternating shape (one fan feeding two parallel decides) and a
    NON-prototype artifact type (a `survey`) run end-to-end — zero code changes."""
    spec = {
        "key": "branchy", "name": "Branchy", "description": "d", "when_to_use": "w",
        "steps": [
            {"id": "scan", "name": "Scan", "tags": ["explore", "build"], "intent": "explore + build",
             "produces": {"role": "landscape", "artifact_type": "survey", "more_tags": ["survey"]}},
            {"id": "pick_a", "name": "Pick A", "tags": ["decide"], "intent": "branch A",
             "consumes": ["scan"], "requires": {"min_inputs": 2, "gate_tag": "scanned_enough"},
             "produces": {"role": "pov-a"}},
            {"id": "pick_b", "name": "Pick B", "tags": ["decide"], "intent": "branch B (needs a survey response)",
             "consumes": ["scan"],
             "requires": {"min_inputs": 2, "gate_tag": "scanned_enough", "session_of_tags": ["survey"]},
             "produces": {"role": "pov-b"}},
        ],
    }
    M.register_methodology(spec, store=store)
    proj = M.start_methodology_project("Br", "g", "branchy", persona_ids=["p1"], store=store)
    pid = proj["id"]
    _council(store, "c1"); _council(store, "c2")
    e1 = M.record_node(pid, "x", ["c1"], _payload("x"), store=store)
    e2 = M.record_node(pid, "y", ["c2"], _payload("y"), store=store)
    # a NON-prototype artifact tagged "survey" + a recorded session of it
    proto = services.scaffold_prototype("br-survey", "Survey", {"title": "S", "summary": "",
        "start": "home", "screens": [{"id": "home", "title": "H", "elements": [
            {"kind": "text", "id": "t", "label": "done"}]}]},
        project_id=pid, fidelity="survey", store=store)
    services.record_prototype_session("p1", proto["id"], "offline", "2026-06-01",
        {"summary": "ok", "observed_state_refs": ["done"], "verdict": "ok"}, store=store)
    M.record_judgment(pid, "scan", "scanned_enough", True, "enough", evidence_refs=["c1"], store=store)
    M.advance(pid, "scan", store=store)
    ready = set(M.brief_next(pid, store=store)["ready"])
    assert ready == {"pick_a", "pick_b"}            # NON-alternating: two parallel decides at once
    da = M.record_decision(pid, "A", [e1["id"], e2["id"]], _payload("a"), step_id="pick_a", store=store)
    db = M.record_decision(pid, "B", [e1["id"], e2["id"]], _payload("b"), step_id="pick_b", store=store)
    assert da["role"] == "pov-a" and db["role"] == "pov-b"   # survey + session satisfied pick_b


def test_no_hardcoded_dynamic_threshold():
    """A4: the engine must not encode a numeric saturation/min-count that decides dynamics.
    Breadth comparisons use the spec-provided `min_inputs` variable, not a literal."""
    import re
    src = Path(M.__file__).read_text()
    nums = re.findall(r"len\([^)]*\)\s*<\s*(\d+)", src)
    # the only literal is the structural ">= 2 steps" spec check; breadth uses `min_inputs`.
    assert all(n == "2" for n in nums), f"unexpected dynamic threshold literal(s): {nums}"
