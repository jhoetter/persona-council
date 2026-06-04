"""Sections (overlay frames) + note nodes — methodology-independent composable graph primitives.
Spec: spec/sections-and-composable-graph.md.

Sections reference nodes by id (explicit, overlap allowed), are reference-not-containment (deleting a
section never deletes nodes), and resolve their `kind` presentation from DATA (no hardcoded vocab).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from persona_council import presentation as P
from persona_council import services as S
from persona_council import web


def test_note_nodes_are_first_class_in_the_graph(store):
    proj = S.create_research_project("Sec Test", "goal", store=store)
    pid = proj["id"]
    n1 = S.create_note(pid, "Observation A", store=store)
    n2 = S.create_note(pid, "Observation B", title="Obs B", store=store)
    g = S.get_project_graph(pid, store=store)
    ids = {n["study_id"] for n in g["nodes"]}
    assert {f"note:{n1['id']}", f"note:{n2['id']}"} <= ids
    assert any(n["kind"] == "note" for n in g["nodes"])


def test_section_membership_overlap_validation_and_decoupling(store):
    proj = S.create_research_project("Sec Test 2", "goal", store=store)
    pid = proj["id"]
    a, b = S.create_note(pid, "A", store=store), S.create_note(pid, "B", store=store)
    ida, idb = f"note:{a['id']}", f"note:{b['id']}"
    s1 = S.create_section(pid, "Theme X", kind="theme", member_ids=[ida, idb], store=store)
    s2 = S.create_section(pid, "Theme Y", kind="problem", member_ids=[ida], store=store)  # OVERLAP on ida
    assert ida in S.get_section(s1["id"], store=store)["member_ids"]
    assert ida in S.get_section(s2["id"], store=store)["member_ids"]  # a node can be in 2 sections
    # unknown member id is rejected
    with pytest.raises(ValueError):
        S.create_section(pid, "bad", member_ids=["note:does-not-exist"], store=store)
    # add / remove / set
    S.remove_from_section(s1["id"], [idb], store=store)
    assert idb not in S.get_section(s1["id"], store=store)["member_ids"]
    S.set_section_members(s1["id"], [ida, idb], store=store)  # promote-cluster
    assert set(S.get_section(s1["id"], store=store)["member_ids"]) == {ida, idb}
    # reference-not-containment: deleting a section keeps its member nodes
    S.delete_section(s1["id"], store=store)
    g = S.get_project_graph(pid, store=store)
    assert ida in {n["study_id"] for n in g["nodes"]}


def test_export_section_is_self_contained(store):
    proj = S.create_research_project("Sec Test 3", "goal", store=store)
    pid = proj["id"]
    n = S.create_note(pid, "Junge Leute sehen den KFZ-Abschluss als Reflex.", title="Reflex", store=store)
    sec = S.create_section(pid, "Affinity Reflex", kind="theme", member_ids=[f"note:{n['id']}"], store=store)
    md = S.export_section(sec["id"], "md", store=store)
    assert "Affinity Reflex" in md and "Reflex" in md
    js = S.export_section(sec["id"], "json", store=store)
    assert js["section"]["title"] == "Affinity Reflex" and len(js["members"]) == 1


def test_section_kind_presentation_is_data_driven():
    # kinds resolve label/color from suggestions/section_kinds.json, not code
    for kind in ("theme", "phase", "research", "problem", "solution"):
        r = P.present(kind)
        assert r["label"] and r["color"]
    # an invented kind still resolves (generic fallback) — no code change needed
    assert P.present("totally-new-section-kind")["color"]


def test_no_hardcoded_section_kind_labels_in_web():
    """Section-kind LABELS/colors live in suggestions/section_kinds.json — never in the web UI."""
    src = "\n".join(f.read_text() for f in sorted(Path(web.__file__).parent.glob("*.py")))
    for lit in ('"Thema"', '"Problemraum"', '"Lösungsraum"', '"Notiz"', '"Research"'):
        assert lit not in src, f"web must not hardcode section-kind label {lit}"
