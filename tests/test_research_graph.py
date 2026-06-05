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


def test_backfill_builds_chronological_graph(store):
    _seed_studies(store, 3)
    graph = services.backfill_project_from_syntheses("Demo Research", store=store)
    assert [n["title"] for n in graph["nodes"]] == ["Pains", "UX", "Pricing"]  # build order
    edges = [(e["from_study"], e["to_study"], e["type"]) for e in graph["edges"]]
    assert edges == [("syn0", "syn1", "spawned_from"), ("syn1", "syn2", "spawned_from")]
    assert graph["counts"]["open_questions"] == 3  # promoted from offene_fragen


def test_tags_edges_and_validation(store):
    _seed_studies(store, 2)
    proj = services.create_research_project("P", goal="g", store=store)
    pid = proj["id"]
    services.add_study_to_project(pid, "syn0", store=store)
    services.add_study_to_project(pid, "syn1", store=store)
    services.set_study_themes(pid, "syn0", ["Pains"], store=store)
    services.link_studies(pid, "syn0", "syn1", "spawned_from", "because", store=store)
    g = services.get_project_graph(pid, store=store)
    assert "pains" in g["project"]["themes"]
    assert g["counts"]["edges"] == 1
    with pytest.raises(ValueError):
        services.link_studies(pid, "syn0", "syn1", "not_a_type", store=store)
    with pytest.raises(KeyError):
        services.add_study_to_project(pid, "does-not-exist", store=store)


def test_meta_report_round_trip(store):
    _seed_studies(store, 2)
    graph = services.backfill_project_from_syntheses("MR", store=store)
    pid = graph["project"]["id"]

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
    graph = services.backfill_project_from_syntheses("Wipe me", store=store)
    pid = graph["project"]["id"]
    assert services.list_research_projects(store=store)
    assert store.list_study_edges(pid)
    services.purge_runtime_data(remove_files=False, store=store)
    assert services.list_research_projects(store=store) == []
    assert store.list_study_edges(pid) == []
    assert store.list_meta_reports(pid) == []
    assert store.list_open_questions(pid) == []


def test_deletes_cascade_and_detach(store):
    _seed_studies(store, 2)
    g = services.backfill_project_from_syntheses("Del", store=store)
    pid = g["project"]["id"]
    # unlink an edge
    assert services.unlink_studies(pid, "syn0", "syn1", "spawned_from", store=store)["removed"] == 1
    # remove a study from the project (keeps the synthesis)
    services.remove_study_from_project(pid, "syn1", store=store)
    assert "syn1" not in services.get_research_project(pid, store=store)["study_ids"]
    assert store.get_synthesis("syn1") is not None
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
    graph = services.backfill_project_from_syntheses("X", store=store)
    pid = graph["project"]["id"]
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
