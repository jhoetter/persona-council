"""/runs page + live topbar widget + extension seam (ticket agents-running-panel).

Fixtures mirror tests/test_autonomy.py: a planned project with no run is stalled,
a checkpointing run is active, a discharged freeform plan is finished."""
from __future__ import annotations

from starlette.testclient import TestClient

from sonaloop import services as S, web


def _client() -> TestClient:
    return TestClient(web.create_app())


def _planned(store, title: str) -> str:
    return S.start_project(title, "Wie können wir X erreichen?", methodology="double_diamond",
                           persona_ids=["p1"], store=store)["id"]


def test_runs_page_groups_active_stalled_finished(store):
    sid = _planned(store, "Stalled Proj")                      # open work, nobody driving
    aid = _planned(store, "Active Proj")
    S.start_run(aid, store=store)                              # an open, recently checkpointed run
    fid = S.start_project("Finished Proj", "frage?", store=store)["id"]
    S.record_frame(fid, "frame__root", ["q?"], memory_refs=["m"], store=store)
    html = _client().get("/runs?lang=en").text
    # all three projects show, each linking to its project page
    for pid, title in ((sid, "Stalled Proj"), (aid, "Active Proj"), (fid, "Finished Proj")):
        assert title in html and f'href="/projects/{pid}"' in html
    # the stalled lane is flagged and carries the copyable resume affordance
    assert web.STRINGS["en"]["runs_stalled_h"] in html
    assert "start_run(" in html and f"data-copy=" in html and sid in html
    # next-ready steps surface for the stalled project
    assert "frame__discover" in html
    # finished plans collapse
    assert "<details" in html and web.STRINGS["en"]["runs_finished_h"] in html


def test_runs_page_stalled_detection_honors_quiet_open_run(store):
    """An open run gone quiet past the threshold is stalled — and the page's resume
    snippet names the run id (the project_run_state contract, honored end to end)."""
    pid = _planned(store, "Quiet Run Proj")
    run = S.start_run(pid, store=store)
    run["updated_at"] = "2020-01-01T00:00:00+00:00"            # age the checkpoint
    store.upsert_run(run)
    html = _client().get("/runs?lang=en").text
    assert web.STRINGS["en"]["runs_stalled_h"] in html
    assert run["run_id"] in html                                # resume call names the run


def test_runs_page_empty_state(store):
    html = _client().get("/runs?lang=en").text
    assert web.STRINGS["en"]["no_runs"] in html


def test_topbar_widget_present_on_every_page(store):
    aid = _planned(store, "Active Proj")
    S.start_run(aid, store=store)
    _planned(store, "Stalled Proj")
    html = _client().get("/personas?lang=en").text             # any page — the widget is chrome
    assert 'id="runsw"' in html and "has-active" in html and "has-stalled" in html
    assert ">1</span>" in html.split('id="runsw-count"')[1][:40]   # server-rendered active count
    assert "Active Proj" in html.split('id="runsw-fly"')[0] or "Active Proj" in html
    assert 'href="/runs"' in html                               # flyout links the full page
    assert "sl:live-event" in html                              # live update wiring (SSE re-dispatch)


def test_project_header_run_chip_with_popover(store):
    """UX P3 (ux-contract §3.5 / decision §7.4): runs left the nav — a project with a
    plan carries the run-state chip in its header; the popover holds the state, last
    activity, the copyable resume hint (stalled) and the /runs journal link."""
    sid = _planned(store, "Stalled Proj")                      # open work, nobody driving
    html = _client().get(f"/projects/{sid}?lang=en").text
    assert 'class="runchip runchip--stalled"' in html          # the rendered chip, not the chrome CSS/JS
    assert f'{web.STRINGS["en"]["run_chip"]} · {web.STRINGS["en"]["runs_stalled_h"]}' in html
    pop = html.split('id="runchip-fly"')[1][:2500]
    assert web.STRINGS["en"]["run_last_activity"] in pop
    assert "start_run(" in pop                                        # copyable resume hint
    assert 'data-copy=' in html and 'href="/runs"' in html            # journal link
    # an active run flips the chip state
    aid = _planned(store, "Active Proj")
    S.start_run(aid, store=store)
    active_html = _client().get(f"/projects/{aid}?lang=en").text
    assert 'class="runchip runchip--active"' in active_html
    assert f'{web.STRINGS["en"]["run_chip"]} · {web.STRINGS["en"]["runs_active_h"]}' in active_html
    # a project without a plan shows no chip — there is no driver to show
    bare = S.create_research_project("No plan", goal="g", store=store)
    assert 'class="runchip-wrap"' not in _client().get(f'/projects/{bare["id"]}?lang=en').text


def test_api_runs_returns_grouped_states(store):
    aid = _planned(store, "Active Proj")
    S.start_run(aid, store=store)
    data = _client().get("/api/runs").json()
    assert [r["project_id"] for r in data["active"]] == [aid]
    assert data["active"][0]["url"] == f"/projects/{aid}"
    assert data["stalled"] == [] and data["finished"] == []


def test_runs_section_extension_seam(store):
    """register_runs_section: a downstream package (sonaloop-cloud) contributes an
    extra section to /runs without the core importing it. Idempotent by id."""
    from sonaloop.web.pages import runs as runs_mod

    web.register_runs_section("assignments", lambda store: '<div id="cloud-assignments">EXT</div>')
    web.register_runs_section("assignments", lambda store: '<div id="cloud-assignments">EXT2</div>')
    try:
        assert sum(1 for s in runs_mod._RUNS_SECTIONS if s["id"] == "assignments") == 1
        html = _client().get("/runs").text
        assert 'id="cloud-assignments"' in html and "EXT2" in html
    finally:
        runs_mod._RUNS_SECTIONS[:] = [s for s in runs_mod._RUNS_SECTIONS
                                      if s["id"] != "assignments"]
