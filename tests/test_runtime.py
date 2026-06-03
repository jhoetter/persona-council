"""M5 — autonomous runtime: run_methodology drives a full diamond unattended (offline stub),
honoring the engine's structural invariants (real divergence, prototype, prototype_session)."""
from __future__ import annotations

from persona_council import methodology as M
from persona_council import runtime
from persona_council import prototypes


def test_run_methodology_completes_full_diamond(store, tmp_path, monkeypatch):
    monkeypatch.setattr(prototypes, "prototypes_dir", lambda: tmp_path)
    proj = M.start_methodology_project("Auto DD", "How might we ship the engine?",
                                       "double_diamond", persona_ids=["p1"], store=store)
    pid = proj["id"]

    state = runtime.run_methodology(pid, backend=runtime.StubAuthoringBackend(), max_steps=40, store=store)

    assert state["complete"] is True
    by = {p["key"]: p for p in state["phases"]}
    # both diverge phases fanned out (wide), both converge phases produced a node (narrow)
    assert by["discover"]["exploration_count"] >= 2
    assert by["develop"]["exploration_count"] >= 2
    assert by["define"]["convergence_node"] and by["deliver"]["convergence_node"]
    # the invariants were satisfied for real: a prototype + a recorded prototype_session exist
    assert store.list_prototypes(pid), "develop must have produced a prototype artifact"
    sessions = store.list_prototype_sessions()
    assert any(store.get_prototype(s["prototype_id"]) and
               store.get_prototype(s["prototype_id"]).get("project_id") == pid for s in sessions)


def test_deep_methodology_completes_six_phases(store, tmp_path, monkeypatch):
    monkeypatch.setattr(prototypes, "prototypes_dir", lambda: tmp_path)
    proj = M.start_methodology_project("Deep", "How might we test the deep flow?",
                                       "double_diamond_deep", persona_ids=["p1"], store=store)
    pid = proj["id"]
    state = runtime.run_methodology(pid, backend=runtime.StubAuthoringBackend(), max_steps=60, store=store)
    assert state["complete"] is True
    by = {p["key"]: p for p in state["phases"]}
    # three diverge fans, each with breadth; three converge waists
    for d in ("discover", "ideate", "refine"):
        assert by[d]["exploration_count"] >= 2, d
    for c in ("define", "lofi_select", "deliver"):
        assert by[c]["convergence_node"], c
    # lo-fi prototype tested (session) before the mid-fi refine + a mid-fi session at deliver
    assert store.list_prototypes(pid) and store.list_prototype_sessions()
