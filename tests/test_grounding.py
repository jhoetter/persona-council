"""Grounding personas & sessions in real material: corpus ingestion (chunking,
dedup, messy input), the brief→record provenance flow, session feed-through,
and evidence traceability (ticket ground-personas-from-real-material)."""
from __future__ import annotations

import pytest

from sonaloop import services
from sonaloop.services import _hooks

from conftest import create_persona, make_profile


@pytest.fixture(autouse=True)
def _clean_handlers(monkeypatch):
    monkeypatch.setattr(_hooks, "_HANDLERS", {})
    monkeypatch.setattr(_hooks, "_ENTRY_POINTS_LOADED", True)
    yield


TRANSCRIPT = """Interviewer: How do you plan your week?

Maria: Honestly, everything lives in a paper notebook. The scheduling tool we bought
is too slow on site, so I stopped opening it.

Interviewer: What happens when a supplier is late?

Maria: I call them. Twice. Then I rebook the crew by hand and lose half a morning.
The phone is my real tool.

Maria: I call them. Twice. Then I rebook the crew by hand and lose half a morning.
The phone is my real tool.

Interviewer: What would make a new tool acceptable?

Maria: It has to work offline in the basement and survive dirty fingers. Anything
that needs a login every morning is dead to me.
"""


@pytest.fixture
def corpus(store):
    return services.ingest_corpus(TRANSCRIPT, "interview", title="Maria interview 01", store=store)


# --- ingestion: chunking, dedup, messy input ---------------------------------------

def test_ingest_chunks_and_dedupes(store, corpus):
    assert corpus["id"].startswith("corpus_") and corpus["source_type"] == "interview"
    assert corpus["deduped"] >= 1                       # the repeated supplier paragraph
    full = services.get_corpus(corpus["id"], include_chunks=True, store=store)
    texts = [c["text"] for c in full["chunk_list"]]
    assert len(texts) == corpus["chunks"] and len(set(texts)) == len(texts)
    assert any("paper notebook" in t for t in texts)
    again = services.ingest_corpus(TRANSCRIPT, "interview", store=store)
    assert again["id"] == corpus["id"]                  # idempotent on content


def test_ingest_from_file_and_validation(store, tmp_path):
    f = tmp_path / "reviews.txt"
    f.write_text("Great app.\n\nTerrible sync, lost a day of work twice this month.")
    c = services.ingest_corpus(str(f), "review", store=store)
    assert c["title"] == "reviews.txt" and c["source"] == str(f) and c["chunks"] >= 1
    with pytest.raises(ValueError):
        services.ingest_corpus("   ", "review", store=store)


def test_search_corpus_scores_real_signal(store, corpus):
    hits = services.search_corpus("offline login basement", [corpus["id"]], store=store)
    assert hits and "offline" in hits[0]["text"]
    assert services.search_corpus("blockchain", [corpus["id"]], store=store) == []


# --- brief → author → record: provenance -------------------------------------------

def test_brief_grounding_create_and_update_modes(store, corpus):
    brief = services.brief_grounding([corpus["id"]], store=store)
    assert brief["mode"] == "create" and brief["chunks"]
    assert "provenance" in brief["instructions"] and "record_persona" in brief["instructions"]
    pid = create_persona(store, "Maria")
    brief2 = services.brief_grounding([corpus["id"]], persona_id=pid, store=store)
    assert brief2["mode"] == "update" and brief2["persona"]["persona_id"] == pid
    assert "patch" in brief2["instructions"]


def test_record_grounding_persists_provenance_and_links_evidence(store, corpus):
    pid = create_persona(store, "Maria")
    chunks = services.get_corpus(corpus["id"], include_chunks=True, store=store)["chunk_list"]
    offline = next(c for c in chunks if "offline" in c["text"])
    seen = []
    services.add_hook_handler("persona.grounded", seen.append)
    out = services.record_grounding(
        pid, [corpus["id"]],
        provenance=[{"claim": "Rejects tools that require a daily login; needs offline",
                     "chunk_ids": [offline["id"]]}],
        patch={"constraints": ["must work offline on site"]},
        store=store)
    assert out["claims"] == 1 and out["patched"]
    persona = store.get_persona(pid)
    assert persona["constraints"] == ["must work offline on site"]          # patch applied
    assert persona["grounding"]["corpus_ids"] == [corpus["id"]]
    assert persona["grounding"]["claims"][0]["chunk_ids"] == [offline["id"]]
    evidence = store.list_evidence(pid)
    assert any(e["content_or_path"] == f"corpus:{corpus['id']}" for e in evidence)
    assert seen and seen[0]["data"]["persona_id"] == pid                    # event emitted


def test_record_grounding_validates_provenance(store, corpus):
    pid = create_persona(store, "Strict")
    with pytest.raises(ValueError):
        services.record_grounding(pid, [corpus["id"]], provenance=[], store=store)
    with pytest.raises(ValueError):
        services.record_grounding(pid, [corpus["id"]],
                                  provenance=[{"claim": "x", "chunk_ids": ["chunk_nope"]}],
                                  store=store)
    with pytest.raises(KeyError):
        services.record_grounding(pid, ["corpus_missing"],
                                  provenance=[{"claim": "x", "chunk_ids": ["y"]}], store=store)


def test_grounding_works_alongside_source_prompts(store, corpus):
    """The done-when: grounding complements the authored source, never replaces it."""
    persona = services.record_persona("Maria — site manager, source-prompt authored",
                                      make_profile("Maria"), store=store)
    chunks = services.get_corpus(corpus["id"], include_chunks=True, store=store)["chunk_list"]
    services.record_grounding(persona["id"], [corpus["id"]],
                              provenance=[{"claim": "phone-first", "chunk_ids": [chunks[0]["id"]]}],
                              store=store)
    fresh = store.get_persona(persona["id"])
    assert fresh["source_description"] == "Maria — site manager, source-prompt authored"
    assert fresh["grounding"]["claims"]                  # both live side by side


# --- sessions draw on grounded material ---------------------------------------------

def test_agent_context_carries_grounded_chunks_with_citation_contract(store, corpus):
    pid = create_persona(store, "Maria")
    chunks = services.get_corpus(corpus["id"], include_chunks=True, store=store)["chunk_list"]
    services.record_grounding(pid, [corpus["id"]],
                              provenance=[{"claim": "offline-first", "chunk_ids": [chunks[0]["id"]]}],
                              store=store)
    ctx = services.prepare_persona_agent_context(pid, "Would you adopt a new scheduling app?",
                                                 store=store)["agent_context"]
    assert "Grounded Source Material" in ctx
    assert "scheduling tool we bought" in ctx            # the task-relevant REAL chunk
    assert "{kind: 'evidence', id:" in ctx               # the citation contract
    ungrounded = create_persona(store, "Fresh")
    ctx2 = services.prepare_persona_agent_context(ungrounded, "anything", store=store)["agent_context"]
    assert "Grounded Source Material" not in ctx2


def test_trace_evidence_resolves_citation_to_source_and_claims(store, corpus):
    pid = create_persona(store, "Maria")
    chunks = services.get_corpus(corpus["id"], include_chunks=True, store=store)["chunk_list"]
    cited = chunks[1]
    services.record_grounding(pid, [corpus["id"]],
                              provenance=[{"claim": "loses mornings to supplier churn",
                                           "chunk_ids": [cited["id"]]}], store=store)
    trace = services.trace_evidence(cited["id"], store=store)
    assert trace["chunk"]["text"] == cited["text"]
    assert trace["corpus"]["title"] == "Maria interview 01"
    assert trace["grounded_claims"][0]["claim"] == "loses mornings to supplier churn"
    with pytest.raises(KeyError):
        services.trace_evidence("chunk_missing", store=store)
