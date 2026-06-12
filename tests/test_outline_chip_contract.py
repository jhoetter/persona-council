"""Outline chip CONTRACT — house gate (tracker: outline-chip-contract-every-row-kind-declares-
its-chips-enfo).

Every row KIND the project outline emits must declare its chips in the _outline_chips REGISTRY:
either a builder (whose row renders a non-empty .ol-chips slot) or an explicit NoChips sentinel
carrying the reason. The gate renders a project carrying one of EVERY row kind and asserts the
contract row by row; an undeclared kind fails the gate (production renders it chip-less and
records it in UNDECLARED_KINDS — a page never crashes over a chip).
"""
from __future__ import annotations

import re

import pytest
from starlette.testclient import TestClient

from sonaloop import plan as P
from sonaloop import presentation, prototypes, services, web
from sonaloop.web import _outline_chips as OC
from sonaloop.web._graph_outline import _outline_html

_RKIND = re.compile(r'data-rkind="([^"]*)"')


def _client():
    return TestClient(web.create_app())


# --------------------------------------------------------------------- the contract machinery

def _rows(html: str) -> list[tuple[str, bool]]:
    """(rkind, has_chips) for every rendered outline row. Each chunk runs from one olrow start
    to the next, so an ol-chips hit is scoped to its own row (the CSS rule `.ol-chips{` never
    matches the attribute form `class="ol-chips"`)."""
    out = []
    for chunk in html.split('class="olrow')[1:]:
        m = _RKIND.search(chunk.split(">", 1)[0])
        out.append((m.group(1) if m else "", 'class="ol-chips"' in chunk))
    return out


def _assert_chip_contract(html: str) -> None:
    """The contract: every rendered row's kind is registered, and a builder-backed kind rendered
    real chips. NoChips kinds must name their reason. No kind may have hit the renderer
    undeclared."""
    rows = _rows(html)
    assert rows, "no outline rows rendered"
    for kind, has_chips in rows:
        entry = OC.REGISTRY.get(kind)
        assert entry is not None, f"outline row kind {kind!r} is not declared in the chip registry"
        if isinstance(entry, OC.NoChips):
            assert entry.reason, f"NoChips for {kind!r} must carry a reason"
            continue
        assert has_chips, f"row kind {kind!r} declared a chip builder but rendered an empty chips slot"
    assert not OC.UNDECLARED_KINDS, (
        f"row kinds hit the renderer without a registry entry: {sorted(OC.UNDECLARED_KINDS)}")


# --------------------------------------------------------------------- seeding (every row kind)

def _steps(n=2, blocked_last=False):
    out = []
    for i in range(n):
        fr = "blocked" if (blocked_last and i == n - 1) else "none"
        out.append({"index": i,
                    "action": {"type": "click", "target": f"b{i}", "detail": f"clicked {i}"},
                    "monologue": "thinking", "state": {"screen": f"s{i}"},
                    "friction": {"level": fr, "note": "stuck" if fr != "none" else ""},
                    "verdict": {"would_continue": fr == "none", "reason": ""}})
    return out


def _record(store, pid, persona_id, subject, fidelity, key, completed=True):
    outcome = {"completed": completed, "dropoff_step": None if completed else 1,
               "summary": "walked", "predicted_behaviors": []}
    return services.record_usability_session(
        persona_id, subject, fidelity, "2026-06-10",
        _steps(blocked_last=not completed), outcome,
        project_id=pid, key=key, store=store)["usability_session"]


def _every_kind_project(store) -> str:
    """One project whose outline emits EVERY row kind: plan-based council + synthesis, a plain
    note + a built concept note (paired prototype), a standalone prototype with two walks (the
    funnel chip), a live_url subject, a flow subject, a report — and the UX-P2 absorbed kinds
    (decision, survey, hypothesis, open question, evidence + deliverable assets)."""
    proj = services.create_research_project("Chip contract", goal="g", store=store)
    pid = proj["id"]
    P.save_plan(P.new_plan(pid, goal="hmw?", methodology="double_diamond_deep", tasks=[
        {"id": "frame1", "title": "Frame · Discover", "bucket": "analyze", "capability": "frame"},
        {"id": "act1", "title": "Council", "bucket": "act", "capability": "explore",
         "consumes": ["frame1"], "produces": [{"kind": "council", "id": "cA"}]},
        {"id": "v1", "title": "Define", "bucket": "verify", "capability": "synthesize",
         "consumes": ["act1"], "produces": [{"kind": "synthesis", "id": "sA"}]},
    ]), store=store)
    # decision-mode council (proposal + votes) with two statements
    store.insert_council_session({
        "id": "cA", "created_at": "2026-06-01T09:00:00+00:00", "prompt": "Adopt the new flow?",
        "persona_ids": ["p1", "p2"], "proposal": "We adopt the new flow.",
        "statements": [{"persona_id": "p1", "text": "yes", "stance": {"value": 1}},
                       {"persona_id": "p2", "text": "no", "stance": {"value": -1}}],
        "votes": [{"persona_id": "p1", "vote": "dafür", "reason": "works"}],
        "summary": "s", "exec_summary": "e", "selection_reason": "x"})
    # in-progress synthesis with three findings
    store.upsert_synthesis({
        "id": "sA", "title": "Key problems", "created_at": "2026-06-02T09:00:00+00:00",
        "council_ids": ["cA"], "gesamtbild": "big picture", "statements": [],
        "findings": [{"text": "f1", "kind": "cluster"}, {"text": "f2", "kind": "key_problem"},
                     {"text": "f3", "kind": "recommendation"}],
        "status": "in_progress"})
    # notes: a plain observation + a concept note built into a prototype
    services.create_note(pid, "a plain observation",
                         created_at="2026-06-03T09:00:00+00:00", store=store)
    built = prototypes.register_prototype("built-proto", "Paired proto", "prototypes/built",
                                          project_id=pid, fidelity="lofi", store=store)
    services.create_note(pid, "a concept that got real", title="Concept",
                         data={"artifact_kind": "comparison", "prototype_ids": [built["id"]]},
                         created_at="2026-06-03T10:00:00+00:00", store=store)
    # a standalone prototype with two walks -> the funnel chip on the parent row
    solo = prototypes.register_prototype("solo-proto", "Solo proto", "prototypes/solo",
                                         project_id=pid, store=store)
    subj = {"kind": "prototype", "id": solo["id"], "label": "Solo proto"}
    _record(store, pid, "p1", subj, "prototype", key="walkA")
    _record(store, pid, "p2", subj, "prototype", key="walkB", completed=False)
    # synthesized live_url + flow parent rows, one session child each
    _record(store, pid, "p1", {"kind": "live_url", "url": "https://example.test/x",
                               "label": "Live x"}, "live", key="walkL")
    _record(store, pid, "p2", {"kind": "flow", "id": "flow-1", "label": "Signup flow"},
            "artifact", key="walkF")
    # the report (a project-scope synthesis) with two sections
    services.record_synthesis_outline(pid, {"build_order_narrative": "n",
                                            "sections": [{"heading": "A"}, {"heading": "B"}]},
                                      store=store)
    # a URL artifact (council-pool A/B capture) — an outline row on the DEFAULT view with the
    # A/B label + capture-status chips (tracker: sonaloop/project-presence-contract)
    services.add_artifact(pid, "https://example.test/landing", kind="url", title="Landing A",
                          capture=False, store=store)
    # the UX-P2 absorbed kinds — every one an outline row with declared chips (§3.4):
    services.record_decision(pid, "Adopt the new flow", "We adopt it.",
                             based_on=[{"kind": "council", "id": "cA"}],
                             key="d1", status="adopted", store=store)
    services.record_survey(pid, "Pricing survey",
                           [{"id": "q1", "kind": "text", "text": "Why this price?"}], store=store)
    services.record_hypothesis(pid, "Half would pay",
                               {"metric": "conversion", "expected_direction": "increase"},
                               key="h1", store=store)
    services.record_open_questions(pid, ["What about pricing?"], store=store)
    import base64
    services.attach_asset(pid, content_base64=base64.b64encode(b"field note").decode(),
                          filename="note.txt", title="Field note", store=store)
    services.attach_asset(pid, content_base64=base64.b64encode(b"deck bytes").decode(),
                          filename="final.pptx", title="Final deck", direction="out", store=store)
    return pid


# ----------------------------------------------------------------------------- the house gate

def test_every_outline_row_kind_declares_its_chips(store):
    OC.UNDECLARED_KINDS.clear()
    pid = _every_kind_project(store)
    html = _client().get(f"/projects/{pid}?lang=en").text
    _assert_chip_contract(html)
    # registry completeness, both directions: the fixture exercises every registered kind, and
    # nothing rendered outside the registry — the registry IS the row-kind inventory.
    emitted = {kind for kind, _ in _rows(html)}
    assert emitted == set(OC.REGISTRY), (
        f"registry/inventory drift — emitted {sorted(emitted)} vs registered {sorted(OC.REGISTRY)}")


def test_contract_catches_an_undeclared_kind(store):
    """The 'fails on undeclared kind' proof: a new row kind that nobody registered renders
    chip-less (production never crashes) but lands in UNDECLARED_KINDS and fails the gate."""
    pid = _every_kind_project(store)
    graph = services.get_project_graph(pid, store=store)
    for n in graph["nodes"]:
        if n.get("kind") == "council":
            n["kind"] = "martian"
    OC.UNDECLARED_KINDS.clear()
    html = _outline_html(graph)                      # renders fine — the fallback is no chips
    assert 'data-rkind="martian"' in html
    with pytest.raises(AssertionError):
        _assert_chip_contract(html)
    assert "martian" in OC.UNDECLARED_KINDS
    OC.UNDECLARED_KINDS.clear()                      # leave no state behind for other tests


def test_planless_fallback_rows_carry_chips(store):
    """The plan-less study_ids path (hand-built data) must satisfy the same contract — its
    synthesis rows carry the findings chip."""
    store.upsert_synthesis({
        "id": "syn0", "title": "Pains", "created_at": "2026-06-01T00:00:00+00:00",
        "council_ids": [], "gesamtbild": "big picture", "statements": [],
        "findings": [{"text": "f1", "kind": "cluster"}, {"text": "f2", "kind": "key_problem"}],
        "status": "done"})
    proj = services.create_research_project("Plan-less", store=store)
    p = store.get_research_project(proj["id"])
    p["study_ids"] = ["syn0"]
    store.upsert_research_project(p)
    OC.UNDECLARED_KINDS.clear()
    html = _client().get(f'/projects/{proj["id"]}?lang=en').text
    _assert_chip_contract(html)
    assert 'data-rkind="synthesis"' in html and "2 findings" in html


# ----------------------------------------------------------------- peek universality (§7.3)

def test_every_row_kind_opens_a_resolving_peek(store):
    """'Click a row → peek' must be universally true (spec/ux-contract.md §3.3, decision §7.3):
    every peek-armed outline row's data-drawer URL resolves, and every peekable kind is armed.
    External/synthesized rows (url_artifact, live_url/flow subjects) legitimately carry none."""
    import re as _re
    pid = _every_kind_project(store)
    client = _client()
    html = client.get(f"/projects/{pid}?lang=en").text
    urls = sorted(set(_re.findall(r'data-drawer="(/peek/[^"]+)"', html)))
    kinds = {u.split("/")[2] for u in urls}
    assert {"council", "synthesis", "report", "note", "prototype", "session",
            "decision", "survey", "hypothesis", "open_question", "asset"} <= kinds, kinds
    for u in urls:
        assert client.get(u).status_code == 200, f"peek fragment {u} did not resolve"


# ------------------------------------------------------------------- the chips themselves

def test_seeded_chip_counts_render(store):
    pid = _every_kind_project(store)
    html = _client().get(f"/projects/{pid}?lang=en").text
    # council: mode (decision — proposal + votes) + statement count
    assert "Decision</span>" in html and "2 statements" in html
    # synthesis: finding count + the amber in-progress chip
    assert "3 findings" in html and "running</span>" in html
    # report: section count (the shared n_sections key)
    assert "2 sections" in html
    # notes: the quiet observation chip; the built concept shows its artifact kind + built marker
    assert "Observation</span>" in html and "built</span>" in html
    assert presentation.present("comparison")["label"] in html
    # session children + the parent funnel chip keep their existing chips (now via the registry)
    assert "Completed</span>" in html and "Dropped at step 1" in html and "1× friction" in html
    assert "2 sessions" in html


def test_child_rows_leave_the_phase_column_to_the_parent(store):
    """Polish bundled with the contract: an indented child row renders an EMPTY phase label —
    the parent carries it (no 'LIVE SURFACE' repeated down a session group)."""
    pid = _every_kind_project(store)
    html = _client().get(f"/projects/{pid}?lang=en").text
    parent_seen = child_seen = False
    for chunk in html.split('class="olrow')[1:]:
        ptag = re.search(r'<span class="ol-ptag">([^<]*)</span>', chunk)
        assert ptag is not None
        if 'data-rkind="live_url"' in chunk.split(">", 1)[0]:
            assert ptag.group(1) != ""               # the parent carries the label
            parent_seen = True
        if 'data-rkind="session"' in chunk.split(">", 1)[0]:
            assert ptag.group(1) == ""               # children never repeat it
            child_seen = True
    assert parent_seen and child_seen
