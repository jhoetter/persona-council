"""Project assets: attach files/images as citable evidence, feed them to councils,
persist them in the snapshot (ticket attach-evidence-files-mcp)."""
from __future__ import annotations

import base64

import pytest

from sonaloop import services
from sonaloop.services import _hooks

from conftest import create_persona


@pytest.fixture(autouse=True)
def _quiet_hooks(monkeypatch):
    monkeypatch.setattr(_hooks, "_HANDLERS", {})
    monkeypatch.setattr(_hooks, "_ENTRY_POINTS_LOADED", True)
    yield


PNG_BYTES = base64.b64decode(  # a 1x1 transparent PNG
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


@pytest.fixture
def project(store):
    return services.start_project("Asset study", "ground reactions in real material", store=store)


def test_attach_from_path_is_idempotent_and_typed(store, project, tmp_path):
    shot = tmp_path / "onboarding.png"
    shot.write_bytes(PNG_BYTES)
    a1 = services.attach_asset(project["id"], path=str(shot), title="Onboarding step 2", store=store)
    a2 = services.attach_asset(project["id"], path=str(shot), notes="updated note", store=store)
    assert a1["id"] == a2["id"]                       # content-addressed, idempotent
    assert a2["kind"] == "image" and a2["media_type"] == "image/png"
    assert a2["title"] == "Onboarding step 2"         # kept across re-attach
    assert a2["notes"] == "updated note"
    assert len(services.list_assets(project["id"], store=store)) == 1


def test_attach_from_base64_with_document_excerpt(store, project):
    text = "## Interview notes\nThe approval flow confuses the Bauleiter persona."
    rec = services.attach_asset(project["id"],
                                content_base64=base64.b64encode(text.encode()).decode(),
                                filename="interview-01.md", store=store)
    assert rec["kind"] == "document"
    assert "approval flow" in rec["text_excerpt"]
    full = services.get_asset(project["id"], "interview-01.md", store=store)  # by filename too
    assert full["id"] == rec["id"]


def test_attach_validation(store, project, tmp_path):
    with pytest.raises(ValueError):
        services.attach_asset(project["id"], store=store)  # neither path nor content
    with pytest.raises(ValueError):
        services.attach_asset(project["id"], path="x", content_base64="eA==", store=store)  # both
    with pytest.raises(FileNotFoundError):
        services.attach_asset(project["id"], path=str(tmp_path / "missing.png"), store=store)
    with pytest.raises(ValueError):
        services.attach_asset(project["id"], content_base64="eA==", store=store)  # no filename


def test_get_asset_content_roundtrip_and_containment(store, project, tmp_path):
    shot = tmp_path / "screen.png"
    shot.write_bytes(PNG_BYTES)
    rec = services.attach_asset(project["id"], path=str(shot), kind="screenshot", store=store)
    data, meta = services.get_asset_content(project["id"], rec["id"], store=store)
    assert data == PNG_BYTES and meta["id"] == rec["id"]
    # A tampered record path must not read outside the asset store.
    p = store.get_research_project(project["id"])
    p["assets"][0]["asset_path"] = "../../etc/passwd"
    store.upsert_research_project(p)
    with pytest.raises(ValueError):
        services.get_asset_content(project["id"], rec["id"], store=store)


def test_remove_asset(store, project, tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("evidence")
    rec = services.attach_asset(project["id"], path=str(f), store=store)
    assert services.remove_asset(project["id"], rec["id"], store=store)["deleted"] == 1
    assert services.list_assets(project["id"], store=store) == []
    assert services.remove_asset(project["id"], rec["id"], store=store)["deleted"] == 0


def test_asset_attached_event_emitted(store, project, tmp_path):
    seen = []
    services.add_hook_handler("asset.attached", seen.append)
    f = tmp_path / "shot.png"
    f.write_bytes(PNG_BYTES)
    rec = services.attach_asset(project["id"], path=str(f), store=store)
    assert seen and seen[0]["data"] == {"project_id": project["id"], "asset_id": rec["id"],
                                        "kind": "image", "filename": "shot.png"}


def test_assets_ride_the_council_brief(store, project, tmp_path):
    pid = create_persona(store, "Evidence Reader")
    shot = tmp_path / "pricing-page.png"
    shot.write_bytes(PNG_BYTES)
    img = services.attach_asset(project["id"], path=str(shot), title="Pricing page", store=store)
    services.attach_asset(project["id"],
                          content_base64=base64.b64encode(b"churn risk: price reveal").decode(),
                          filename="notes.txt", store=store)
    brief = services.brief_council(project["id"], "React to our pricing page", [pid], store=store)
    assert [a["id"] for a in brief["assets"]] == [img["id"],
                                                  services.get_asset(project["id"], "notes.txt", store=store)["id"]]
    ctx = brief["participants"][0]["agent_context"]
    assert "EVIDENCE ASSETS IN THE ROOM" in ctx
    assert f"view_asset('{project['id']}', '{img['id']}')" in ctx   # image → host must LOOK first
    assert "churn risk: price reveal" in ctx                        # document excerpt inline
    assert "EVIDENCE ASSETS ARE IN THE ROOM" in brief["instructions"]


def test_assets_survive_the_snapshot_roundtrip(store, project, tmp_path, monkeypatch):
    shot = tmp_path / "evidence.png"
    shot.write_bytes(PNG_BYTES)
    rec = services.attach_asset(project["id"], path=str(shot), title="The evidence", store=store)
    out = services.export_snapshot(store=store)
    assert out["counts"]["projects"] >= 1 and out["counts"]["assets"] == 1
    # Wipe runtime state: fresh DB + empty asset store, then import the snapshot.
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'restored.db'}")
    from sonaloop.storage import Store
    binary = services.ROOT / rec["asset_path"]
    binary.unlink()
    store2 = Store()
    services.import_snapshot(store=store2, embed=False)
    restored = services.get_asset(project["id"], rec["id"], store=store2)
    assert restored["title"] == "The evidence"
    data, _ = services.get_asset_content(project["id"], rec["id"], store=store2)
    assert data == PNG_BYTES


def test_attach_prototype_shot_uses_capture(store, project, monkeypatch, tmp_path):
    # capture_prototype_shot is Playwright-backed; stub it to a stored file like the real one.
    from sonaloop import assets as assets_mod
    monkeypatch.setattr(assets_mod, "ASSETS_DIR", tmp_path / "captured")
    (tmp_path / "captured").mkdir()
    (tmp_path / "captured" / "abc.png").write_bytes(PNG_BYTES)
    monkeypatch.setattr(assets_mod, "capture_prototype_shot",
                        lambda prototype_id, store=None: "assets/abc.png")
    rec = services.attach_prototype_shot(project["id"], "proto-x", store=store)
    assert rec["kind"] == "screenshot" and rec["source"] == "prototype:proto-x"