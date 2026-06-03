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


def test_invalid_outline_rejected(store):
    _seed_studies(store, 1)
    graph = services.backfill_project_from_syntheses("X", store=store)
    pid = graph["project"]["id"]
    with pytest.raises(ValueError):
        services.record_meta_outline(pid, {"sections": []}, store=store)
