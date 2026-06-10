"""Session replay inspector (ticket session-replay-inspector) — web smoke tests.

The list page (empty + populated + the ≥2-sessions funnel), the replay view (per-step anchors,
friction rail, screenshots only when the file exists), the read-only screenshot route (serves a real
file, rejects traversal), session-ref deep links on council pages, and the persona/prototype/project
cross-link sections.
"""
from __future__ import annotations

from starlette.testclient import TestClient

from conftest import create_persona
from sonaloop import artifacts, config, prototypes, services, web


_PROTO = {"kind": "prototype", "id": "proto-signup", "label": "Signup prototype"}


def _step(i, *, friction="none", would_continue=True, reason="", monologue=None, **state):
    return {
        "index": i,
        "action": {"type": "click", "target": f"button-{i}", "detail": f"clicked button {i}"},
        "monologue": monologue if monologue is not None else f"thinking aloud at step {i}",
        "state": {"screen": f"screen-{i}", **state},
        "friction": {"level": friction, "note": "label was ambiguous" if friction != "none" else ""},
        "verdict": {"would_continue": would_continue, "reason": reason},
    }


def _record(store, *, steps=None, outcome=None, persona_id="pX", subject=None, **kw):
    return services.record_usability_session(
        persona_id, subject or _PROTO, "prototype", "2026-06-10",
        steps if steps is not None else [_step(0), _step(1)],
        outcome if outcome is not None else
        {"completed": True, "dropoff_step": None, "summary": "walked it", "predicted_behaviors": []},
        store=store, **kw)["usability_session"]


def _client():
    return TestClient(web.create_app())


# ----------------------------------------------------------------------------- ref deep links

def test_session_ref_href_maps_step_anchor_to_dom_id():
    assert artifacts.ref_href({"kind": "session", "id": "u1", "anchor": "step:3"}) == "/sessions/u1#step-3"
    # a whole-session ref (no anchor) links to the session page
    assert artifacts.ref_href({"kind": "session", "id": "u1"}) == "/sessions/u1"


# ----------------------------------------------------------------------------- list page

def test_sessions_list_renders_empty_and_populated(store):
    client = _client()
    html = client.get("/sessions?lang=en").text
    assert "no sessions" in html
    sess = _record(store)
    html = client.get("/sessions?lang=en").text
    assert f'/sessions/{sess["id"]}' in html
    assert "Signup prototype" in html and "Prototype" in html and "Completed" in html
    # the project filter narrows honestly
    assert f'/sessions/{sess["id"]}' not in client.get("/sessions?project=nope&lang=en").text


def test_funnel_renders_only_with_two_or_more_sessions_of_one_subject(store):
    client = _client()
    _record(store, key="A", steps=[_step(0), _step(1), _step(2)])
    url = "/sessions?subject_kind=prototype&subject=proto-signup&lang=en"
    assert "Funnel" not in client.get(url).text                    # one walk is no funnel
    _record(store, key="B",
            steps=[_step(0), _step(1, friction="blocked", would_continue=False,
                                   reason="could not find the next button")],
            outcome={"completed": False, "dropoff_step": 1, "summary": "gave up",
                     "predicted_behaviors": []})
    html = client.get(url).text
    assert "Funnel" in html and "could not find the next button" in html
    assert "Step 1" in html and "entered" in html and "dropped" in html
    # without a subject filter the funnel stays off (it is a per-subject read)
    assert "Funnel" not in client.get("/sessions?lang=en").text


# ----------------------------------------------------------------------------- replay view

def test_replay_renders_step_anchors_friction_rail_and_verdicts(store):
    sess = _record(store, steps=[
        _step(0),
        _step(1, friction="confusion", url="https://example.test/x", title="Signup"),
        _step(2, friction="blocked", would_continue=False, reason="dead end"),
    ], outcome={"completed": False, "dropoff_step": 2, "summary": "bounced",
                "predicted_behaviors": []})
    html = _client().get(f'/sessions/{sess["id"]}?lang=en').text
    # every step is addressable; the friction rail jumps to the friction steps only
    assert 'id="step-0"' in html and 'id="step-1"' in html and 'id="step-2"' in html
    assert "Friction points" in html and 'href="#step-1"' in html and 'href="#step-2"' in html
    # no screenshot file -> the screen TEXT excerpt, no <img> in the timeline
    assert "sess-screen-txt" in html and "screen-1" in html and "/sessions-files/" not in html
    # think-aloud, action chip + target, per-step verdict, outcome banner
    assert "thinking aloud at step 1" in html and "button-2" in html
    assert "would continue" in html and "would drop" in html and "dead end" in html
    assert "Dropped at step 2" in html
    # friction accents come from the data-driven scale colors (friction_levels.json)
    assert "--sfc:var(--amber)" in html and "--sfc:var(--red)" in html
    # an unknown id renders the honest empty state
    assert "Session not found" in _client().get("/sessions/usession_missing?lang=en").text


def test_replay_shows_screenshot_img_only_when_the_file_exists(store, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    sess_id = services.stable_id("usession", "shots")
    d = config.sessions_dir() / sess_id
    d.mkdir(parents=True)
    (d / "step-0.png").write_bytes(b"\x89PNG fake")
    shot = _step(0)
    shot["state"]["screenshot"] = "step-0.png"
    sess = _record(store, steps=[shot, _step(1)], key="shots")
    html = _client().get(f'/sessions/{sess["id"]}?lang=en').text
    assert f'<img class="sess-shot" src="/sessions-files/{sess_id}/step-0.png"' in html
    # step 1 has no screenshot -> text excerpt
    assert "sess-screen-txt" in html and "screen-1" in html


def test_screenshot_route_serves_real_files_and_rejects_traversal(store, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    d = config.sessions_dir() / "u1"
    d.mkdir(parents=True)
    (d / "step-0.png").write_bytes(b"png-bytes")
    secret = tmp_path / "secret.txt"
    secret.write_text("not yours")
    client = _client()
    ok = client.get("/sessions-files/u1/step-0.png")
    assert ok.status_code == 200 and ok.content == b"png-bytes"
    # traversal out of the sessions dir -> 404, never a file read
    for path in ("/sessions-files/..%2Fsecret.txt", "/sessions-files/u1/..%2F..%2Fsecret.txt",
                 "/sessions-files/%2e%2e/%2e%2e/etc/passwd"):
        assert client.get(path).status_code == 404
    assert client.get("/sessions-files/u1/missing.png").status_code == 404


# ----------------------------------------------------------------------------- evidence deep links

def test_council_session_refs_render_as_replay_deep_links(store):
    proj = services.create_research_project("P", store=store)
    pid = create_persona(store, "Greta Tester")
    sess = _record(store, persona_id=pid, project_id=proj["id"])
    council = services.record_council(
        proj["id"], "Did the prototype hold up?", [pid],
        statements=[{"persona_id": pid, "text": "The second screen lost me.",
                     "refs": [{"kind": "session", "id": sess["id"], "anchor": "step:1"},
                              {"kind": "session", "id": sess["id"]}]}],
        key="c1", store=store)
    html = _client().get(f'/councils/{council["id"]}?lang=en').text
    assert f'/sessions/{sess["id"]}#step-1' in html               # anchored -> the exact step
    assert f'href="/sessions/{sess["id"]}"' in html               # whole-session ref -> the session page


# ----------------------------------------------------------------------------- cross-link sections

def test_persona_page_lists_its_sessions(store):
    pid = create_persona(store, "Heinz Walker")
    sess = _record(store, persona_id=pid)
    html = _client().get(f"/personas/{pid}?lang=en").text
    assert f'/sessions/{sess["id"]}' in html and "Signup prototype" in html


def test_project_page_lists_its_sessions(store):
    proj = services.create_research_project("Q", store=store)
    sess = _record(store, project_id=proj["id"])
    html = _client().get(f'/projects/{proj["id"]}?lang=en').text
    assert f'/sessions/{sess["id"]}' in html


# ----------------------------------------------------------------- sessions IN the project outline
# (tickets project-page-sessions-live-under-their-subject-in-the-outlin + outline-drops-study-nodes-
# on-plan-less-projects): sessions render as indented child rows under their SUBJECT row inside the
# outline; the appended flat section is gone from the project page (it stays on /sessions and the
# persona/prototype pages — covered by the cross-link tests above).


def _proto_project(store, title="Q"):
    proj = services.create_research_project(title, store=store)
    proto = prototypes.register_prototype("proto-signup", "Signup prototype", "prototypes/signup",
                                          project_id=proj["id"], store=store)
    return proj, proto


def test_project_outline_nests_sessions_under_their_subject(store):
    proj, proto = _proto_project(store)
    pid = create_persona(store, "Greta Tester")
    sess = _record(store, persona_id=pid, project_id=proj["id"],
                   subject={"kind": "prototype", "id": proto["id"], "label": "Signup prototype"})
    html = _client().get(f'/projects/{proj["id"]}?lang=en').text
    # the appended flat section is gone — sessions live IN the outline now
    assert 'id="sec-sessions"' not in html
    # the subject (prototype) row precedes its session child row, which carries the tree-connector
    # indent classes (the note→prototype nesting mechanics)
    assert html.index(f'data-oid="{proto["id"]}"') < html.index(f'data-oid="{sess["id"]}"')
    assert f'class="olrow ol-tw ol-last" data-oid="{sess["id"]}"' in html
    # child row content: persona name, fidelity kind label, outcome chip, replay href
    assert "Greta Tester" in html and "Prototype session" in html and "Completed" in html
    assert f'href="/sessions/{sess["id"]}"' in html
    # a single session earns no funnel chip (the class still appears in the inlined CSS)
    assert 'class="ol-funnel"' not in html


def test_project_outline_parent_row_carries_funnel_chip(store):
    proj, proto = _proto_project(store)
    subj = {"kind": "prototype", "id": proto["id"], "label": "Signup prototype"}
    _record(store, key="A", project_id=proj["id"], subject=subj,
            steps=[_step(0), _step(1), _step(2)])
    _record(store, key="B", project_id=proj["id"], subject=subj,
            steps=[_step(0), _step(1, friction="blocked", would_continue=False, reason="lost")],
            outcome={"completed": False, "dropoff_step": 1, "summary": "gave up",
                     "predicted_behaviors": []})
    html = _client().get(f'/projects/{proj["id"]}?lang=en').text
    # the aggregate chip on the parent row: count + the drop-off read (services.get_session_funnel)
    assert "2 sessions · 1× drop @ step 1" in html
    # it links to the filtered cross-session list; the row keeps its own stretched-link target
    assert f'href="/sessions?subject_kind=prototype&amp;subject={proto["id"]}"' in html
    assert 'class="ol-stretch"' in html
    # the dropped walk's child row shows the red outcome chip and the friction pill
    assert "Dropped at step 1" in html and "1× friction" in html


def test_project_outline_synthesizes_live_url_parent_row(store):
    proj = services.create_research_project("L", store=store)
    pid = create_persona(store, "Lena Live")
    subj = {"kind": "live_url", "url": "https://example.test/checkout", "label": "Checkout live"}
    sess = services.record_usability_session(
        pid, subj, "live", "2026-06-10",
        [_step(0, url="https://example.test/checkout", title="Checkout Example"), _step(1)],
        {"completed": True, "dropoff_step": None, "summary": "done", "predicted_behaviors": []},
        project_id=proj["id"], store=store)["usability_session"]
    html = _client().get(f'/projects/{proj["id"]}?lang=en').text
    # synthesized parent row: the recorded page title, the live-surface kind, an external target
    assert "Checkout Example" in html and "Live surface" in html
    assert 'href="https://example.test/checkout" target="_blank"' in html
    # its child row deep-links into the replay with the live fidelity kind label
    assert f'href="/sessions/{sess["id"]}"' in html and "Live session" in html


def test_planless_project_outline_shows_study_nodes_and_compacts(store):
    # hand-built plan-less project (no methodology plan): a synthesis attached via study_ids must
    # still render as an outline row — parity with the ?view=graph view.
    store.upsert_synthesis({
        "id": "syn0", "title": "Pains", "created_at": "2026-06-01T00:00:00+00:00",
        "council_ids": [], "gesamtbild": "big picture", "statements": [], "findings": [],
        "status": "done"})
    proj = services.create_research_project("Plan-less", store=store)
    p = store.get_research_project(proj["id"])
    p["study_ids"] = ["syn0"]
    store.upsert_research_project(p)
    html = _client().get(f'/projects/{proj["id"]}?lang=en').text
    assert "Pains" in html and 'href="/syntheses/syn0"' in html
    # a near-empty outline sizes to content instead of pinning a viewport-high dead zone
    assert "ol-compact" in html
