"""Research graph (R1–R3) + meta-report (R4): project container, typed edges,
theme tags, backfill of existing syntheses, and the outline→section→export
round-trip. Deterministic, no network."""
from __future__ import annotations

import pytest

from persona_council import services


def _seed_studies(store, n=3):
    store.insert_council_session({"id": "c1", "created_at": "2026-06-01T00:00:00+00:00",
                                  "prompt": "P?", "persona_ids": ["p1"], "turns": [], "votes": [],
                                  "proposal": "", "summary": "", "exec_summary": "exec", "selection_reason": "x"})
    titles = ["Pains", "UX", "Pricing"][:n]
    for i, ttl in enumerate(titles):
        store.upsert_synthesis({
            "id": f"syn{i}", "title": ttl, "created_at": f"2026-06-0{i+1}T00:00:00+00:00",
            "council_ids": ["c1"], "voices": [{"persona_name": "A", "sentiment": "bedingt", "key_argument": "k"}],
            "offene_fragen": [f"open from {ttl}"], "gesamtbild": f"{ttl} big picture",
            "handlungsempfehlungen": [{"text": "do X", "aufwand": 3, "nutzen": 5}], "status": "done"})
    return [f"syn{i}" for i in range(n)]


def _project_with_studies(store, sids, title="MR"):
    """Create a project and attach study_ids directly (the constellation study-graph tools that used
    to do this are retired; the plan is the graph now). These tests cover the meta-report machinery,
    which still works over a project's study_ids."""
    proj = services.create_research_project(title, goal="g", store=store)
    p = store.get_research_project(proj["id"])
    p["study_ids"] = list(sids)
    store.upsert_research_project(p)
    return proj["id"]


def test_meta_report_round_trip(store):
    _seed_studies(store, 2)
    pid = _project_with_studies(store, ["syn0", "syn1"])

    brief = services.brief_meta_report(pid, store=store)
    assert brief["study_ids"] == ["syn0", "syn1"] and "instructions" in brief

    outline = {"build_order_narrative": "pains then pricing",
               "sections": [{"heading": "Pains", "theme_tags": ["pains"], "source_study_ids": ["syn0"], "intent": "establish"},
                            {"heading": "Pricing", "theme_tags": ["pricing"], "source_study_ids": ["syn1"], "intent": "price"}]}
    report = services.record_meta_outline(pid, outline, store=store)
    assert [s["id"] for s in report["outline"]] == ["sec1", "sec2"]

    sb = services.brief_meta_section(pid, "sec1", store=store)
    assert [s["title"] for s in sb["frame"]["studies"]] == ["Pains"]
    services.record_meta_section(pid, "sec1",
                                 {"markdown": "## Pains\nReconciliation is the core pain.",
                                  "citations": [{"study_id": "syn0", "council_id": "c1", "quote": "exec"}]}, store=store)

    md = services.export_meta_report(pid, format="md", store=store)
    assert "pains then pricing" in md and "Reconciliation is the core pain." in md
    # unauthored section shows a marker, not fabricated content
    assert ("not yet authored" in md) or ("noch nicht verfasst" in md)


def test_purge_clears_research_graph(store):
    _seed_studies(store, 2)
    pid = _project_with_studies(store, ["syn0", "syn1"], title="Wipe me")
    services.record_open_questions(pid, ["q?"], store=store)
    assert services.list_research_projects(store=store)
    services.purge_runtime_data(remove_files=False, store=store)
    assert services.list_research_projects(store=store) == []
    assert store.list_meta_reports(pid) == []
    assert store.list_open_questions(pid) == []


def test_deletes_cascade_and_detach(store):
    _seed_studies(store, 2)
    pid = _project_with_studies(store, ["syn0", "syn1"], title="Del")
    # delete a synthesis -> also detaches from the project graph
    services.delete_synthesis("syn0", store=store)
    assert store.get_synthesis("syn0") is None
    assert "syn0" not in services.get_research_project(pid, store=store)["study_ids"]
    # delete the project container
    services.delete_research_project(pid, store=store)
    assert services.list_research_projects(store=store) == []
    # delete a council
    services.delete_council("c1", store=store)
    assert store.get_council_session("c1") is None


def test_delete_persona(store):
    from conftest import create_persona
    pid = create_persona(store, "Doomed")
    assert any(p["id"] == pid for p in services.list_personas(store=store))
    out = services.delete_persona(pid, store=store)
    assert out["deleted"]["personas"] == 1
    assert all(p["id"] != pid for p in services.list_personas(store=store))


def test_invalid_outline_rejected(store):
    _seed_studies(store, 1)
    pid = _project_with_studies(store, ["syn0"], title="X")
    with pytest.raises(ValueError):
        services.record_meta_outline(pid, {"sections": []}, store=store)


def test_synthesis_preserves_structured_blocks_and_warns_when_thin(store):
    """GAP-3 (spec/exploration-depth-and-prototype-variety): a methodology's converge output —
    clusters / key_problems / ranking / shortlist — must survive record_synthesis and render in the
    web view + export; a near-empty synthesis returns a SYNTHESIS_THIN soft-warning."""
    from persona_council import web
    payload = {
        "gesamtbild": "Der Kern: nicht alle fuer LV begeistern.",
        "clusters": [{"label": "Sprachbarriere", "member_node_ids": ["c1"], "insight": "Das Wort ist die Huerde."}],
        "key_problems": ["LV ist fuer 4/6 ein struktureller Non-Fit"],
        "ranking": [{"prototype_id": "proto_a", "score_rationale": "ehrlichster Pfad"}],
        "shortlist": ["proto_a"],
    }
    rec = services.record_synthesis("Define POV", "hmw", ["c1"], payload, store=store)
    got = services.get_synthesis(rec["id"], store=store)
    assert got["clusters"][0]["label"] == "Sprachbarriere"
    assert got["key_problems"] == ["LV ist fuer 4/6 ein struktureller Non-Fit"]
    assert got["ranking"][0]["prototype_id"] == "proto_a" and got["shortlist"] == ["proto_a"]
    # re-recording the SAME id without re-supplying a block keeps it (additive-safe update)
    rec2 = services.record_synthesis("Define POV", "hmw", ["c1"], {"gesamtbild": "更新", "synthesis_id": got["id"]},
                                     synthesis_id=got["id"], store=store)
    assert services.get_synthesis(rec2["id"], store=store)["key_problems"] == ["LV ist fuer 4/6 ein struktureller Non-Fit"]
    # web + export surface the structured content
    html = web._synthesis_html(store, got)
    assert "Sprachbarriere" in html and "Shortlist" in html and "proto_a" in html
    md = services.export_synthesis(got["id"], "md", store=store)
    assert "Sprachbarriere" in md and "proto_a" in md
    # a truly empty synthesis warns (soft, non-blocking)
    thin = services.record_synthesis("Empty", "hmw", [], {}, store=store)
    assert any("SYNTHESIS_THIN" in w for w in thin.get("warnings", []))


def test_derive_sections_and_scaffold_meta_report_finish_by_construction(store):
    """ESV1: derive_sections organizes a completed methodology project (phase + prototype + deliver +
    run-journal sections, idempotent) and scaffold_meta_report seeds a meta-report — together flipping
    assess_project.finish to organized + handed-off, so a finished run is organized BY CONSTRUCTION."""
    proj = services.start_project("ESV1", "hmw?", "double_diamond", persona_ids=["p1"], store=store)
    pid = proj["id"]
    services.record_frame(pid, "frame__discover", ["q?"], memory_refs=["m1"], store=store)
    for cid in ("c1", "c2"):
        store.insert_council_session({"id": cid, "created_at": "2026-06-05T00:00:00+00:00", "prompt": "p",
            "persona_ids": ["p1"], "turns": [], "votes": [], "proposal": "", "summary": "",
            "exec_summary": "e", "selection_reason": "x"})
        a = services.add_task(pid, "act", "explore", f"angle {cid}", consumes=["frame__discover"], store=store)
        services.link_evidence(pid, a["id"], {"kind": "council", "id": cid}, store=store)
    services.record_judgment(pid, "verify__define", "divergence_complete", True, "ok", evidence_refs=["c1", "c2"], store=store)
    syn = services.record_synthesis("Define POV", "hmw", ["c1", "c2"],
                                    {"gesamtbild": "G" * 250, "positionierung": "P" * 250}, key="t:define", store=store)
    services.link_evidence(pid, "verify__define", {"kind": "synthesis", "id": syn["id"]}, store=store)
    services.complete_task(pid, "verify__define", store=store)
    assert services.assess_project(pid, store=store)["finish"]["organized"] is False
    out = services.derive_sections(pid, store=store)
    assert "Discover" in out["created"] and "Deliver — Conclusion" in out["created"]
    services.scaffold_meta_report(pid, store=store)
    f = services.assess_project(pid, store=store)["finish"]
    assert f["organized"] is True and f["handed_off"] is True
    # idempotent: re-deriving doesn't duplicate
    n1 = len(services.list_sections(pid, store=store))
    services.derive_sections(pid, store=store)
    assert len(services.list_sections(pid, store=store)) == n1
    assert services.scaffold_meta_report(pid, store=store)["id"]  # returns existing, no error


def test_concept_notes_connect_into_the_graph(store):
    """Connectivity: a concept note carries note_kind+prototype_id (so the layout can route
    concept→prototype→tested-synthesis), and an UN-prototyped concept note gets a plan_graph edge to
    the ideation down-select synthesis — so no concept floats disconnected (the 'no lines' fix)."""
    proj = services.start_project("CN", "hmw?", "double_diamond_deep", persona_ids=["p1"], store=store)
    pid = proj["id"]
    services.record_frame(pid, "frame__ideate", ["q?"], memory_refs=["m"], store=store)
    services.create_note(pid, "an un-prototyped bold idea", "Dark-horse", kind="concept",
                         data={"lens": "reversal", "artifact_kind": "flow", "prototype_id": None}, store=store)
    # a down-select synthesis exists (the verify with a session gate)
    syn = services.record_synthesis("Down-Select", "x", [], {"gesamtbild": "G" * 250, "positionierung": "P" * 250},
                                    key="cn:sel", store=store)
    services.link_evidence(pid, "verify__lofi_select", {"kind": "synthesis", "id": syn["id"]}, store=store)
    g = services.get_project_graph(pid, store=store)
    cn = next(n for n in g["nodes"] if n.get("note_kind") == "concept")
    assert cn["prototype_id"] is None and cn["kind_label"] == "Konzept"
    # the un-prototyped concept is wired to the down-select synthesis (no float)
    assert any(e["from_study"] == cn["study_id"] and e["to_study"] == f"synthesis:{syn['id']}"
               for e in g["edges"]), "un-prototyped concept must connect to the down-select synthesis"


def test_council_modes_discovery_evaluation_decision(store):
    """Q1/Q2: a council's shape is DERIVED — discovery (open `questions`, no proposal/votes),
    evaluation (a proposal reacted to), decision (proposal + votes). `questions` is stored first-class."""
    pid = services.start_project("M", "hmw?", None, persona_ids=[], store=store)["id"]
    disc = services.record_council(pid, "Geldgewohnheiten", [], [{"content": "Ich spare per ETF"}],
                                   questions=["Wie sparst du gerade?", "Welche Versicherungen hast du?"],
                                   store=store, key="d")
    assert disc["questions"] == ["Wie sparst du gerade?", "Welche Versicherungen hast du?"]
    assert services.council_mode(disc) == "discovery"
    dec = services.record_council(pid, "Bauen?", [], [{"content": "ja"}], proposal="Wir bauen X",
                                  votes=[{"vote": "SUPPORT"}], store=store, key="x")
    assert services.council_mode(dec) == "decision"
    ev = services.record_council(pid, "Reaktion", [], [{"content": "gut"}], proposal="Das Konzept",
                                 store=store, key="e")
    assert services.council_mode(ev) == "evaluation"
