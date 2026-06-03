"""M1 — methodology engine: structure enforced, dynamics LLM-judged (no hardcoded gates).

The acceptance tests from spec/methodology-engine-and-prototyping.md §12: a converge phase
cannot be recorded until its diverge phase has >=2 explorations AND a divergence_complete
judgment; the graph comes out wide->narrow->wide->narrow; no numeric dynamic threshold exists.
"""
from __future__ import annotations

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


def test_builtins_load_and_validate(store):
    keys = {m["key"] for m in M.list_methodologies(store=store)}
    assert {"double_diamond", "dschool_micro", "lean_jtbd"} <= keys
    dd = M.get_methodology("double_diamond", store=store)
    assert [p["mode"] for p in dd["phases"]] == ["diverge", "converge", "diverge", "converge"]


def test_bad_spec_rejected(store):
    with pytest.raises(M.MethodologyError):
        M.validate_methodology_spec({"key": "x", "name": "x", "description": "d",
                                     "when_to_use": "w", "phases": [{"key": "a", "mode": "converge",
                                                                     "produces_role": "spec",
                                                                     "council_strategy": "goal"}]})


def test_converge_blocked_until_breadth_and_judgment(store):
    proj = M.start_methodology_project("DD", "How might we test the engine?", "double_diamond", store=store)
    pid = proj["id"]
    b = M.brief_phase(pid, store=store)
    assert b["phase"] == "discover" and b["mode"] == "diverge"

    _council(store, "c1")
    e1 = M.record_exploration(pid, "Pain A", ["c1"], _payload("pain a"), store=store)

    # converging during a diverge phase is out of order
    with pytest.raises(M.MethodologyError) as e:
        M.record_convergence(pid, "Define", [e1["id"]], _payload("core"), store=store)
    assert e.value.code == "PHASE_OUT_OF_ORDER"

    # advance with only ONE exploration -> convergence must fail on breadth
    M.advance_phase(pid, store=store)
    assert M.brief_phase(pid, store=store)["phase"] == "define"
    with pytest.raises(M.MethodologyError) as e:
        M.record_convergence(pid, "Define", [e1["id"]], _payload("core"), store=store)
    assert e.value.code == "BREADTH_TOO_LOW"


def test_full_diverge_converge_happy_path(store):
    proj = M.start_methodology_project("DD", "How might we test the engine?", "double_diamond", store=store)
    pid = proj["id"]
    _council(store, "c1"); _council(store, "c2")
    e1 = M.record_exploration(pid, "Pain A", ["c1"], _payload("pain a"), store=store)
    e2 = M.record_exploration(pid, "Pain B", ["c2"], _payload("pain b"), store=store)
    M.advance_phase(pid, store=store)  # -> define

    # breadth ok now, but no divergence_complete judgment yet
    with pytest.raises(M.MethodologyError) as e:
        M.record_convergence(pid, "Define", [e1["id"], e2["id"]], _payload("core"), store=store)
    assert e.value.code == "MISSING_DIVERGENCE_JUDGMENT"

    M.record_judgment(pid, "discover", "divergence_complete", True,
                      "Two distinct pains; no new cluster emerging.", evidence_refs=["c1", "c2"], store=store)
    conv = M.record_convergence(pid, "Define · POV", [e1["id"], e2["id"]], _payload("the core problem"), store=store)
    assert conv["mode"] == "converge" and conv["role"] == "point-of-view"

    # edges: both explorations refine the convergence node
    graph = services.get_project_graph(pid, store=store)
    refines = [(x["from_study"], x["to_study"]) for x in graph["edges"] if x["type"] == "refines"]
    assert (e1["id"], conv["id"]) in refines and (e2["id"], conv["id"]) in refines

    M.advance_phase(pid, store=store)  # -> develop (diverge)
    assert M.brief_phase(pid, store=store)["phase"] == "develop"

    st = M.get_methodology_state(pid, store=store)
    by = {p["key"]: p for p in st["phases"]}
    assert by["discover"]["exploration_count"] == 2          # wide
    assert by["define"]["convergence_node"] == conv["id"]    # narrow (the waist)


def test_no_hardcoded_dynamic_threshold():
    """A4: the engine must not encode a numeric saturation/min-count that decides dynamics."""
    import re
    from pathlib import Path
    src = Path(M.__file__).read_text()
    # the only count compared is the structural invariant '>= 2 explorations'
    nums = re.findall(r"len\([^)]*\)\s*<\s*(\d+)", src)
    assert nums == ["2"] or all(n == "2" for n in nums)
