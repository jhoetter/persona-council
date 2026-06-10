"""Screenshot flows: define from assets, walk as a persona (artifact-first, no
browser), aggregate the segment drop-off funnel (ticket prototype-walkthrough-dropoff)."""
from __future__ import annotations

import base64

import pytest

from sonaloop import services

from conftest import create_persona


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


@pytest.fixture
def world(store, tmp_path):
    p1 = create_persona(store, "Walker One")
    p2 = create_persona(store, "Walker Two")
    project = services.start_project("Onboarding study", "where do they drop?",
                                     persona_ids=[p1, p2], store=store)
    assets = []
    for i, name in enumerate(["welcome", "signup-form", "price-reveal"]):
        f = tmp_path / f"{name}.png"
        f.write_bytes(PNG_BYTES + bytes([i]))           # distinct content → distinct assets
        assets.append(services.attach_asset(project["id"], path=str(f),
                                            title=name.replace("-", " "), store=store))
    return {"personas": [p1, p2], "project": project, "assets": assets}


@pytest.fixture
def flow(store, world):
    return services.define_flow(
        world["project"]["id"], "Onboarding v2",
        steps=[{"asset_id": a["id"]} for a in world["assets"]],
        key="onboarding-v2", store=store)


# --- defining a flow -----------------------------------------------------------------

def test_define_flow_orders_and_validates(store, world, flow):
    assert [s["index"] for s in flow["steps"]] == [0, 1, 2]
    assert flow["steps"][2]["caption"] == "price reveal"          # caption falls back to asset title
    again = services.define_flow(world["project"]["id"], "Onboarding v2 (renamed)",
                                 steps=[{"asset_id": world["assets"][0]["id"]}],
                                 key="onboarding-v2", store=store)
    assert again["id"] == flow["id"] and len(again["steps"]) == 1  # keyed upsert
    assert services.list_flows(world["project"]["id"], store=store)[0]["id"] == flow["id"]
    with pytest.raises(KeyError):
        services.define_flow(world["project"]["id"], "bad",
                             steps=[{"asset_id": "asset_missing"}], store=store)
    with pytest.raises(ValueError):
        services.define_flow(world["project"]["id"], "empty", steps=[], store=store)


def test_flow_steps_must_be_image_assets(store, world):
    doc = services.attach_asset(world["project"]["id"],
                                content_base64=base64.b64encode(b"notes").decode(),
                                filename="notes.txt", store=store)
    with pytest.raises(ValueError):
        services.define_flow(world["project"]["id"], "doc flow",
                             steps=[{"asset_id": doc["id"]}], store=store)


# --- the walkthrough brief: artifacts only, real pixels -------------------------------

def test_brief_carries_screens_and_the_no_browser_contract(store, world, flow):
    pid = world["personas"][0]
    brief = services.brief_flow_walkthrough(pid, world["project"]["id"], flow["id"], store=store)
    assert brief["subject"] == {"kind": "flow", "id": flow["id"], "label": "Onboarding v2"}
    assert brief["fidelity"] == "artifact"
    steps = brief["flow"]["steps"]
    assert [s["index"] for s in steps] == [0, 1, 2]
    assert steps[0]["view"] == f"view_asset('{world['project']['id']}', '{world['assets'][0]['id']}')"
    assert "no live browser" in brief["how_to_drive"].lower()
    assert "agent_context" in brief                               # the persona context rides along
    # the generic usability brief ALSO sees defined-flow screens for the same subject
    generic = services.brief_usability_session(pid, brief["subject"], "artifact",
                                               project_id=world["project"]["id"], store=store)
    assert [s["asset_id"] for s in generic["flow_screens"]] == [a["id"] for a in world["assets"]]


# --- the segment funnel ---------------------------------------------------------------

def _walk(store, world, flow, persona_id, dropoff, key):
    """Record one persona's walkthrough; dropoff=None completes the flow."""
    steps = []
    for s in flow["steps"]:
        bail = dropoff is not None and s["index"] == dropoff
        steps.append({"index": s["index"], "action": {"type": "look", "target": s["caption"], "detail": ""},
                      "monologue": f"looking at {s['caption']}",
                      "state": {"screen": f"{s['asset_id']}: {s['caption']}"},
                      "friction": {"level": "blocked" if bail else "none", "note": ""},
                      "verdict": {"would_continue": not bail,
                                  "reason": "price shown with no context — I'm out" if bail else "fine"}})
        if bail:
            break
    outcome = {"completed": dropoff is None, "dropoff_step": dropoff,
               "summary": "" if dropoff is None else "bailed at the price reveal",
               "predicted_behaviors": [] if dropoff is None else
               [{"action": "abandons at the price reveal", "step": dropoff, "likelihood": "likely"}]}
    return services.record_usability_session(
        persona_id, {"kind": "flow", "id": flow["id"], "label": flow["title"]}, "artifact",
        "2026-06-10", steps, outcome, project_id=world["project"]["id"], key=key, store=store)


def test_funnel_aggregates_dropoff_across_the_segment(store, world, flow):
    p1, p2 = world["personas"]
    _walk(store, world, flow, p1, dropoff=2, key="w1")            # bails at the price reveal
    _walk(store, world, flow, p2, dropoff=None, key="w2")         # completes
    funnel = services.flow_funnel(world["project"]["id"], flow["id"], store=store)
    assert funnel["sessions"] == 2 and funnel["completed"] == 1
    assert funnel["flow"]["title"] == "Onboarding v2"
    row = funnel["rows"][2]
    assert row["caption"] == "price reveal" and row["dropped"] == 1
    assert row["personas"] == [p1]
    assert "no context" in row["drop_reasons"][0]
    head = funnel["biggest_dropoff"]
    assert head["step"] == 2 and head["caption"] == "price reveal" and head["dropped"] == 1
    with pytest.raises(KeyError):
        services.flow_funnel(world["project"]["id"], "flow_missing", store=store)


def test_walkthrough_predictions_feed_the_calibration_loop(store, world, flow):
    """The arc the tickets promise: walkthrough → predicted drop → scored against reality."""
    p1 = world["personas"][0]
    res = _walk(store, world, flow, p1, dropoff=2, key="w1")
    sid = res["usability_session"]["id"]
    out = services.record_prediction_outcome(
        world["project"]["id"], {"kind": "session", "id": sid, "anchor": "pb1"},
        0.65, source={"kind": "external", "text": "real funnel: 65% bounce at price"}, store=store)
    assert out["brier"] == round((0.7 - 0.65) ** 2, 4) and out["hit"] is True
