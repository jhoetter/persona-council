"""Phase 1 — record→primitive adapters (spec/unified-artifact-schema-rollout.md §1A)."""
from __future__ import annotations

from persona_council import artifacts as A


def test_council_adapter_maps_turns_votes_questions():
    c = {"prompt": "P?", "questions": ["q0?", "q1?"], "proposal": "",
         "turns": [{"persona_id": "p1", "content": "ans0", "question_index": 0, "memory_refs": ["m"]},
                   {"persona_id": "p2", "content": "ans1", "stance": "dafür", "question_index": 1},
                   {"content": "moderator line"}],            # moderator (no persona_id) → skipped
         "votes": [{"persona_id": "p1", "vote": "OPPOSE"}]}
    sts = A.council_statements(c)
    assert len(sts) == 2                                       # moderator turn dropped
    assert sts[0]["persona_id"] == "p1" and sts[0]["about"]["id"] == "q0"
    assert sts[0]["stance"]["value"] == -2                    # vote OPPOSE → stance -2 (no turn.stance)
    assert sts[0]["refs"][0] == {"kind": "memory", "text": "m"}
    assert sts[1]["stance"]["value"] == 2                     # turn.stance "dafür" → +2 (wins over vote)
    prompts = A.council_prompts(c)
    assert [p["id"] for p in prompts] == ["prompt", "q0", "q1"]


def test_synthesis_adapter_maps_lists_and_voices():
    s = {"key_problems": ["kp1"], "pain_solvers": ["ps1"], "offene_fragen": ["of1"], "shortlist": [],
         "handlungsempfehlungen": [{"text": "do x", "aufwand": 2, "nutzen": 5}, "plain rec"],
         "voices": [{"persona_id": "p1", "key_argument": "arg", "sentiment": "bedingt",
                     "evidence": [{"council_id": "c1", "quote": "q"}], "relevance": "strong"}]}
    fs = A.synthesis_findings(s)
    kinds = [f["kind"] for f in fs]
    assert kinds == ["key_problem", "pain_solver", "open_question", "recommendation", "recommendation"]
    rec = next(f for f in fs if f["kind"] == "recommendation" and f.get("score"))
    assert rec["score"] == {"effort": 2, "value": 5}
    voices = A.synthesis_statements(s)
    assert voices[0]["stance"]["value"] == 1 and voices[0]["relevance"] == "strong"
    assert voices[0]["refs"][0]["kind"] == "council" and voices[0]["refs"][0]["id"] == "c1"


def test_session_adapter_one_statement_with_refs():
    se = {"persona_id": "p1", "observed_state_refs": ["saw X"], "grounded_verified": True,
          "reaction": {"persona": "Aylin", "verdict": "**good**", "focus": "does it work?",
                       "fidelity": "hi-fi", "version": "v0.2"}}
    sts = A.session_statements(se)
    assert len(sts) == 1
    assert sts[0]["text"] == "**good**"                       # markdown kept (rendered later via _prose)
    assert sts[0]["refs"][0] == {"kind": "prototype_state", "text": "saw X"}
    assert sts[0]["about"] == {"kind": "prompt", "id": "focus"}   # focus → the prompt banner
    assert sts[0]["meta"]["grounded"] is True and "hi-fi" in sts[0]["meta"]["context"]
    assert "focus" not in sts[0]["meta"]                      # focus is the banner now, not a card line
    assert A.session_focus(se) == "does it work?"


def test_adapters_prefer_native_primitive_fields():
    # forward-compat: if a record already carries primitives, the adapter returns them verbatim
    native = [A.statement("p9", "native")]
    assert A.council_statements({"statements": native, "turns": [{"persona_id": "x", "content": "y"}]}) == native
    assert A.synthesis_findings({"findings": [A.finding("f", kind="risk")], "key_problems": ["ignored"]})[0]["kind"] == "risk"
