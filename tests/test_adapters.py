"""Phase 1 — record→primitive adapters (spec/unified-artifact-schema-rollout.md §1A)."""
from __future__ import annotations

from persona_council import artifacts as A


def test_council_prompts_built_from_canonical_fields():
    # prompts are derived from the council's canonical question/proposal fields (not legacy)
    c = {"prompt": "P?", "questions": ["q0?", "q1?"], "proposal": ""}
    assert [p["id"] for p in A.council_prompts(c)] == ["prompt", "q0", "q1"]


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
