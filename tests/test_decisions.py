"""Decision records — what we decided, on which evidence, rejecting what (the ADR-style node
that closes the research loop).

Citation validation (no based_on → rejected; unresolvable based_on/rejected refs → rejected;
why-not notes kept per rejected ref), status transitions (proposed|adopted flips; superseded only
via the supersede flow), the supersede flow (both directions recorded, the old record demoted and
immutable afterwards), the resolvable `decision` Ref kind + backlinks ("informed decision <title>"),
the plan-export Decisions section with citations, and the project-page section (adopted / proposed
/ superseded groups with evidence chips).
"""
from __future__ import annotations

import pytest

from conftest import create_persona
from sonaloop import artifacts, services
from sonaloop import plan as P


def _project(store, title="Pension awareness"):
    return services.create_research_project(title, goal="How do people plan retirement?",
                                            store=store)


def _council(store, project_id, prompt="Would a digital pension check help?"):
    pid = create_persona(store, "Evi Dence")
    statements = [{"persona_id": pid, "text": "it would help me", "stance": {"value": 1}}]
    return services.record_council(project_id, prompt, [pid], statements=statements,
                                   summary="useful", store=store)


def _record(store, project_id, **kw):
    council = kw.pop("council", None) or _council(store, project_id)
    args = {"title": "Ship the pension check as a standalone tool",
            "decision": "We build the check as its own flow, not a bank-portal plugin.",
            "based_on": [{"kind": "council", "id": council["id"]}]}
    args.update(kw)
    return services.record_decision(project_id, store=store, **args)["decision"]


# --------------------------------------------------------------- record: citation validation

def test_record_get_roundtrip_and_list(store):
    proj = _project(store)
    dec = _record(store, proj["id"])
    got = services.get_decision(dec["id"], store=store)
    assert got["status"] == "proposed" and got["superseded_by"] is None
    assert got["based_on"][0]["role"] == "based_on"          # default role
    assert services.list_decisions(proj["id"], store=store)[0]["id"] == dec["id"]
    assert services.list_decisions(proj["id"], status="proposed", store=store)
    assert not services.list_decisions(proj["id"], status="adopted", store=store)
    with pytest.raises(ValueError, match="status"):
        services.list_decisions(proj["id"], status="maybe", store=store)
    with pytest.raises(KeyError):
        services.get_decision("dec_missing", store=store)
    with pytest.raises(KeyError):
        services.record_decision("rproject_missing", "t", "d", [], store=store)


def test_a_decision_must_cite_evidence_that_resolves(store):
    proj = _project(store)

    def rec(based_on, **kw):
        return services.record_decision(proj["id"], "Pick A", "we pick A", based_on,
                                        store=store, **kw)

    with pytest.raises(ValueError, match="at least one resolvable ref"):
        rec([])                                              # no evidence → no decision record
    with pytest.raises(ValueError, match="at least one resolvable ref"):
        rec(None)
    with pytest.raises(ValueError, match="does not resolve"):
        rec([{"kind": "council", "id": "council_missing"}])  # the whole point: refs must resolve
    with pytest.raises(ValueError, match="needs an id"):
        rec([{"kind": "external", "text": "gut feeling"}])   # a free string is not citable evidence
    with pytest.raises(ValueError, match=r"based_on\[0\] must be a Ref dict"):
        rec(["council_abc"])
    council = _council(store, proj["id"])
    with pytest.raises(ValueError, match="title is required"):
        services.record_decision(proj["id"], "  ", "d",
                                 [{"kind": "council", "id": council["id"]}], store=store)
    with pytest.raises(ValueError, match="decision is required"):
        services.record_decision(proj["id"], "t", "",
                                 [{"kind": "council", "id": council["id"]}], store=store)
    with pytest.raises(ValueError, match="proposed|adopted"):
        rec([{"kind": "council", "id": council["id"]}], status="superseded")
    # a synthesis (whole artifact or a finding anchor) is the natural evidence kind
    syn = services.record_synthesis("Key problems", "hmw", [council["id"]],
                                    {"findings": [{"kind": "key_problem", "text": "trust gap"}]},
                                    store=store)
    dec = rec([{"kind": "synthesis", "id": syn["id"], "anchor": "f1"}])["decision"]
    assert dec["based_on"][0]["anchor"] == "f1"
    with pytest.raises(ValueError, match="does not resolve"):
        rec([{"kind": "synthesis", "id": syn["id"], "anchor": "f99"}])   # broken part anchor


def test_rejected_alternatives_resolve_and_keep_their_why_not_notes(store):
    proj = _project(store)
    keep = _council(store, proj["id"])
    alt = _council(store, proj["id"], prompt="Embed it in the bank portal instead?")
    with pytest.raises(ValueError, match=r"rejected\[0\] does not resolve"):
        _record(store, proj["id"], council=keep,
                rejected=[{"kind": "council", "id": "council_missing", "note": "too slow"}])
    dec = _record(store, proj["id"], council=keep,
                  rejected=[{"kind": "council", "id": alt["id"],
                             "note": "banks gatekeep the audience"}])
    assert dec["rejected"][0]["role"] == "rejected"          # default role
    assert dec["rejected"][0]["note"] == "banks gatekeep the audience"
    assert artifacts.resolve_ref(dec["rejected"][0], store)["exists"] is True


def test_stable_key_upserts_but_a_superseded_record_is_immutable(store):
    proj = _project(store)
    council = _council(store, proj["id"])
    d1 = _record(store, proj["id"], council=council, key="dec-1")
    d2 = _record(store, proj["id"], council=council, key="dec-1", title="Sharper title")
    assert d2["id"] == d1["id"] and d2["created_at"] == d1["created_at"]
    assert len(services.list_decisions(proj["id"], store=store)) == 1
    succ = _record(store, proj["id"], council=council, key="dec-2", title="The successor")
    services.update_decision(d1["id"], superseded_by=succ["id"], store=store)
    with pytest.raises(ValueError, match="superseded"):      # the record is the audit trail
        _record(store, proj["id"], council=council, key="dec-1")


# --------------------------------------------------------------- status transitions

def test_status_transitions(store):
    proj = _project(store)
    dec = _record(store, proj["id"])
    assert services.update_decision(dec["id"], status="adopted",
                                    store=store)["decision"]["status"] == "adopted"
    assert services.update_decision(dec["id"], status="proposed",
                                    store=store)["decision"]["status"] == "proposed"
    with pytest.raises(ValueError, match="status must be one of"):
        services.update_decision(dec["id"], status="abandoned", store=store)
    with pytest.raises(ValueError, match="superseded_by"):    # superseded needs the successor link
        services.update_decision(dec["id"], status="superseded", store=store)
    with pytest.raises(ValueError, match="nothing to update"):
        services.update_decision(dec["id"], store=store)
    with pytest.raises(KeyError):
        services.update_decision("dec_missing", status="adopted", store=store)
    # recording directly as adopted is fine — superseded is the only birth status rejected
    adopted = _record(store, proj["id"], key="adopted", status="adopted")
    assert adopted["status"] == "adopted"


def test_supersede_links_both_records_and_demotes_the_old_one(store):
    proj = _project(store)
    council = _council(store, proj["id"])
    old = _record(store, proj["id"], council=council, key="old", status="adopted")
    new = _record(store, proj["id"], council=council, key="new", title="Pivot to B2B2C",
                  status="adopted")
    out = services.update_decision(old["id"], superseded_by=new["id"], store=store)
    assert out["decision"]["status"] == "superseded"
    assert out["decision"]["superseded_by"] == new["id"]      # forward link
    assert out["successor"]["supersedes"] == old["id"]        # backward link — both directions
    assert services.get_decision(new["id"], store=store)["supersedes"] == old["id"]
    # a superseded record is frozen: no flips, no second supersede
    with pytest.raises(ValueError, match="already superseded"):
        services.update_decision(old["id"], status="adopted", store=store)
    with pytest.raises(ValueError, match="already superseded"):
        services.update_decision(old["id"], superseded_by=new["id"], store=store)
    # supersede guards: self-reference, unknown successor, cross-project
    with pytest.raises(ValueError, match="cannot supersede itself"):
        services.update_decision(new["id"], superseded_by=new["id"], store=store)
    with pytest.raises(KeyError):
        services.update_decision(new["id"], superseded_by="dec_missing", store=store)
    with pytest.raises(ValueError, match="cannot also flip"):
        services.update_decision(new["id"], status="adopted", superseded_by=old["id"], store=store)
    other = _project(store, "Other study")
    foreign = _record(store, other["id"], key="foreign")
    with pytest.raises(ValueError, match="same project"):
        services.update_decision(new["id"], superseded_by=foreign["id"], store=store)


# --------------------------------------------------------------- graph: ref kind + backlinks

def test_decision_is_a_resolvable_ref_kind(store):
    proj = _project(store)
    dec = _record(store, proj["id"])
    ref = {"kind": "decision", "id": dec["id"]}
    assert artifacts.ref_href(ref) == f'/decisions/{dec["id"]}'
    res = artifacts.resolve_ref(ref, store)
    assert res["exists"] is True and res["title"] == dec["title"]
    assert artifacts.resolve_ref({"kind": "decision", "id": "dec_missing"}, store)["exists"] is False


def test_backlinks_show_the_decision_a_synthesis_informed(store):
    proj = _project(store)
    council = _council(store, proj["id"])
    syn = services.record_synthesis("Key problems", "hmw", [council["id"]],
                                    {"gesamtbild": "the picture"}, store=store)
    alt = _council(store, proj["id"], prompt="The rejected alternative")
    dec = _record(store, proj["id"],
                  based_on=[{"kind": "synthesis", "id": syn["id"]}],
                  rejected=[{"kind": "council", "id": alt["id"], "note": "too narrow"}])
    idx = services.ref_backlinks(proj["id"], store=store)
    back = idx[artifacts.part_address("synthesis", syn["id"])]
    assert back == [{"href": f'/decisions/{dec["id"]}', "label": dec["title"], "role": "based_on"}]
    rej = idx[artifacts.part_address("council", alt["id"])]
    assert {"href": f'/decisions/{dec["id"]}', "label": dec["title"], "role": "rejected"} in rej


# --------------------------------------------------------------- exports: the Decisions section

def test_plan_export_gains_a_decisions_section_with_citations(store):
    proj = _project(store)
    P.save_plan(P.new_plan(proj["id"], goal="g", tasks=[
        {"id": "frame1", "title": "Frame", "bucket": "analyze", "capability": "frame"}]),
        store=store)
    md0 = services.export_plan_md(proj["id"], store=store)
    assert "## Decisions" not in md0                          # no decisions → no empty chrome
    council = _council(store, proj["id"])
    alt = _council(store, proj["id"], prompt="Bank-portal plugin?")
    old = _record(store, proj["id"], council=council, key="old", status="adopted",
                  rejected=[{"kind": "council", "id": alt["id"], "note": "banks gatekeep"}])
    new = _record(store, proj["id"], council=council, key="new", title="Pivot to B2B2C")
    services.update_decision(old["id"], superseded_by=new["id"], store=store)
    md = services.export_plan_md(proj["id"], store=store)
    assert "## Decisions" in md
    assert old["title"] in md and new["title"] in md and old["decision"] in md
    assert f'based on: {council["prompt"]} (council:{council["id"]})' in md   # live-resolved citation
    assert f'rejected: {alt["prompt"]} (council:{alt["id"]}) — banks gatekeep' in md
    assert f'superseded by: {new["title"]} (decision:{new["id"]})' in md
    assert "`superseded`" in md and "`proposed`" in md


# --------------------------------------------------------------- inspector: the project-page section

def test_project_page_groups_decisions_with_evidence_chips(store):
    from starlette.testclient import TestClient
    from sonaloop import web
    from sonaloop.web._i18n import STRINGS
    proj = _project(store)
    council = _council(store, proj["id"])
    alt = _council(store, proj["id"], prompt="The alternative considered")
    adopted = _record(store, proj["id"], council=council, key="a", status="adopted",
                      rejected=[{"kind": "council", "id": alt["id"], "note": "banks gatekeep"}])
    proposed = _record(store, proj["id"], council=council, key="p",
                       title="Offer a paper fallback")
    succ = _record(store, proj["id"], council=council, key="s", title="The successor",
                   status="adopted")
    services.update_decision(adopted["id"], superseded_by=succ["id"], store=store)
    client = TestClient(web.create_app())
    html = client.get(f'/projects/{proj["id"]}?lang=en').text
    assert STRINGS["en"]["decisions_h"] in html
    for key in ("dec_status_adopted", "dec_status_proposed", "dec_status_superseded"):
        assert STRINGS["en"][key] in html                     # the three groups
    assert adopted["title"] in html and proposed["title"] in html and succ["title"] in html
    assert adopted["decision"] in html
    assert f'/councils/{council["id"]}' in html               # evidence chip via render_ref
    assert f'/councils/{alt["id"]}' in html                   # rejected chip deep-links too
    assert "banks gatekeep" in html                           # the why-not note
    assert STRINGS["en"]["dec_superseded_by"] in html and STRINGS["en"]["dec_supersedes"] in html
    # the Ref route deep-links back into the project page section
    r = client.get(f'/decisions/{adopted["id"]}', follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == f'/projects/{proj["id"]}#dec-{adopted["id"]}'
    assert STRINGS["en"]["runtime_maybe_cleared"] in client.get("/decisions/nope?lang=en").text
    # a project without decisions shows no section (and no empty chrome)
    other = _project(store, "Quiet study")
    assert 'id="decisions"' not in client.get(f'/projects/{other["id"]}?lang=en').text


def test_global_decisions_list_renders_empty_and_populated(store):
    from starlette.testclient import TestClient
    from sonaloop import web
    from sonaloop.web._i18n import STRINGS
    client = TestClient(web.create_app())
    empty = client.get("/decisions?lang=en")                  # honest empty state, no chrome
    assert empty.status_code == 200 and STRINGS["en"]["no_decisions"] in empty.text
    pa, pb = _project(store, "Project A"), _project(store, "Project B")
    council = _council(store, pa["id"])
    alt = _council(store, pa["id"], prompt="The alternative considered")
    adopted = _record(store, pa["id"], council=council, key="a", status="adopted",
                      rejected=[{"kind": "council", "id": alt["id"], "note": "banks gatekeep"}])
    proposed = _record(store, pb["id"], key="p", title="Offer a paper fallback")
    page = client.get("/decisions?lang=en")
    assert page.status_code == 200
    html = page.text
    assert STRINGS["en"]["dec_status_adopted"] in html and STRINGS["en"]["dec_status_proposed"] in html
    assert adopted["title"] in html and proposed["title"] in html
    # each row deep-links into ITS project's decisions section, named after the project
    assert f'/projects/{pa["id"]}#dec-{adopted["id"]}' in html
    assert f'/projects/{pb["id"]}#dec-{proposed["id"]}' in html
    assert "Project A" in html and "Project B" in html
    # evidence + rejected chips render via render_ref, with the why-not note
    assert f'/councils/{council["id"]}' in html and f'/councils/{alt["id"]}' in html
    assert "banks gatekeep" in html
    # the list route does not shadow the canonical /decisions/{id} redirect
    r = client.get(f'/decisions/{adopted["id"]}', follow_redirects=False)
    assert r.status_code in (302, 307)
    assert r.headers["location"] == f'/projects/{pa["id"]}#dec-{adopted["id"]}'


def test_synthesis_page_shows_informed_decisions(store):
    from starlette.testclient import TestClient
    from sonaloop import web
    from sonaloop.web._i18n import STRINGS
    proj = _project(store)
    council = _council(store, proj["id"])
    syn = services.record_synthesis("Key problems", "hmw", [council["id"]],
                                    {"gesamtbild": "the picture"}, store=store)
    html_before = TestClient(web.create_app()).get(f'/syntheses/{syn["id"]}?lang=en').text
    assert STRINGS["en"]["dec_informed_h"] not in html_before
    dec = _record(store, proj["id"], based_on=[{"kind": "synthesis", "id": syn["id"]}])
    html = TestClient(web.create_app()).get(f'/syntheses/{syn["id"]}?lang=en').text
    assert STRINGS["en"]["dec_informed_h"] in html            # "informed decision <title>"
    assert dec["title"] in html and f'/decisions/{dec["id"]}' in html
