"""Persona-catalog services + MCP tools (core side of sonaloop-data/persona-pull-correctness
and sonaloop/catalog-sync-status-drift-safe-pull-refresh): browse the published catalog,
recommend, pull personas into the current store — drift-safe with status reporting —
with sonaloop-data installed (mocked module + optional real-checkout integration)
AND without it (the stdlib remote fallback + graceful in-band notes). Hermetic:
the remote fetcher is monkeypatched; no network."""
from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import types

import pytest

from sonaloop import services
from sonaloop.services import _catalog as cat
from sonaloop.mcp_server import build_server
from sonaloop.storage import Store

from conftest import make_profile


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #

FUTURE = "2999-01-01T00:00:00+00:00"


def _no_data_pkg(monkeypatch):
    """Force the not-installed path regardless of the local environment."""
    monkeypatch.setitem(sys.modules, "sonaloop_data", None)


def _serve(files: dict[str, bytes], monkeypatch):
    """Serve a fake published catalog: path-after-ref -> bytes (None == 404)."""
    def fake_fetch(url: str) -> bytes | None:
        assert url.startswith("https://raw.githubusercontent.com/jhoetter/sonaloop-data/")
        path = url.split("/", 6)[-1]                     # https://host/{owner}/{repo}/{ref}/{path}
        return files.get(path)
    monkeypatch.setattr(cat, "_fetch_bytes", fake_fetch)


def _manifest_only(n: int) -> dict[str, bytes]:
    personas = [{"slug": f"persona-{i:03d}", "display_name": f"Persona {i:03d}",
                 "role": "Bäckerin" if i % 2 else "Mechatroniker", "has_avatar": False}
                for i in range(n)]
    return {"manifest.json": json.dumps(
        {"generated_at": "2026-06-10T00:00:00+00:00", "schema_version": 4,
         "personas": personas}).encode()}


def _mini_catalog(store: Store, names: list[str]) -> tuple[dict[str, bytes], list[dict]]:
    """A published-catalog fixture with REAL persona records (created through the
    normal record path, then served as snapshot profile.json files). The manifest
    index carries per-persona updated_at, like core's export_snapshot emits it."""
    personas = [services.record_persona(f"{n} source", make_profile(n), store=store)
                for n in names]
    files = {"manifest.json": json.dumps(
        {"generated_at": "2026-06-10T00:00:00+00:00", "schema_version": 4,
         "personas": [{"slug": p["slug"], "display_name": p["display_name"],
                       "role": p["role"]["title"], "has_avatar": False,
                       "updated_at": p["updated_at"]} for p in personas]}).encode()}
    for p in personas:
        files[f"personas/{p['slug']}/profile.json"] = json.dumps(p).encode()
        files[f"personas/{p['slug']}/SOUL.md"] = b"# SOUL\n"
    files["packs/starter.json"] = json.dumps(
        {"id": "starter", "personas": [personas[0]["slug"]]}).encode()
    return files, personas


def _bump_local(store: Store, slug: str) -> None:
    """Simulate the persona living on locally after the pull (updated_at > pulled_at)."""
    p = store.get_persona(slug)
    p["updated_at"] = FUTURE
    store.upsert_persona(p, reason="local edit (test)")


# --------------------------------------------------------------------------- #
# without sonaloop-data: stdlib remote fallback + graceful notes               #
# --------------------------------------------------------------------------- #

def test_search_remote_fallback_paginates_per_convention(monkeypatch):
    _no_data_pkg(monkeypatch)
    _serve(_manifest_only(30), monkeypatch)
    out = cat.catalog_search()
    assert set(out) >= {"items", "total", "has_more", "next_cursor"}    # the shared envelope
    assert out["total"] == 30 and len(out["items"]) == 25 and out["has_more"] is True
    assert any(cat.INSTALL_NOTE == n for n in out["notes"])             # in-band, not an error
    page2 = cat.catalog_search(cursor=out["next_cursor"])
    assert [e["slug"] for e in page2["items"]] == [f"persona-{i:03d}" for i in range(25, 30)]
    assert page2["has_more"] is False and "next_cursor" not in page2


def test_search_query_filters_and_facets_are_noted_not_applied(monkeypatch):
    _no_data_pkg(monkeypatch)
    _serve(_manifest_only(10), monkeypatch)
    out = cat.catalog_search(query="bäckerin", facets={"role_family": ["handwerk"]})
    assert out["total"] == 5                                            # query composes
    assert out["facet_summary"] is None                                 # needs the package
    assert any("IGNORED" in n for n in out["notes"])                    # facet filter not silent


def test_search_cursor_rejects_changed_filters(monkeypatch):
    _no_data_pkg(monkeypatch)
    _serve(_manifest_only(30), monkeypatch)
    cursor = cat.catalog_search()["next_cursor"]
    with pytest.raises(ValueError, match="different filter set"):
        cat.catalog_search(query="bäckerin", cursor=cursor)


def test_recommend_without_package_is_an_inband_note(monkeypatch):
    _no_data_pkg(monkeypatch)
    out = cat.catalog_recommend({"keywords": ["schicht"], "n": 3})
    assert out["skipped"] is True and "sonaloop-data" in out["note"]


def test_pull_requires_a_selection(monkeypatch):
    _no_data_pkg(monkeypatch)
    with pytest.raises(ValueError, match="selective by design"):
        cat.catalog_pull()


def test_pull_remote_fallback_round_trip_idempotent_with_provenance(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    files, personas = _mini_catalog(Store(), ["Anna Architect", "Ben Baker"])
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")

    out = cat.catalog_pull(persona_slugs=[personas[0]["slug"]], store=dest)
    assert out["personas"] == [personas[0]["slug"]]
    assert len(out["landed"]) == 1
    landed = out["landed"][0]
    assert landed["id"] == personas[0]["id"]                            # stable id survived
    prov = landed["provenance"]
    assert prov["source"] == "sonaloop-data" and prov["repo"] == cat.CATALOG_REPO
    assert prov["ref"] == "main" and prov["slug"] == personas[0]["slug"]
    assert prov["schema_version"] == 4 and prov["pulled_at"]
    # the record is complete + readable through the normal service path
    got = services.get_persona(personas[0]["slug"], dest)["persona"]
    assert got["display_name"] == "Anna Architect" and got["pain_points"]

    again = cat.catalog_pull(persona_slugs=[personas[0]["slug"]], store=dest)  # re-pull
    assert len(again["landed"]) == 1
    assert "skipped_locally_modified" not in again                      # unmodified == no drift
    assert len(dest.list_personas()) == 1                               # upsert, no duplicate


def test_pull_remote_fallback_resolves_packs_and_rejects_unknowns(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    files, personas = _mini_catalog(Store(), ["Cara Chef", "Dev Driver"])
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")
    out = cat.catalog_pull(pack="starter", store=dest)
    assert [p["slug"] for p in out["landed"]] == [personas[0]["slug"]]
    assert out["landed"][0]["provenance"]["pack"] == "starter"
    with pytest.raises(KeyError, match="Unknown archetype pack"):
        cat.catalog_pull(pack="nope", store=dest)
    with pytest.raises(ValueError, match="Unknown persona slug"):
        cat.catalog_pull(persona_slugs=["ghost"], store=dest)


# --------------------------------------------------------------------------- #
# drift-safe pull: local modifications are never silently overwritten          #
# --------------------------------------------------------------------------- #

def test_pull_skips_locally_modified_unless_forced(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    files, personas = _mini_catalog(Store(), ["Anna Architect"])
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")
    slug = personas[0]["slug"]
    cat.catalog_pull(persona_slugs=[slug], store=dest)
    _bump_local(dest, slug)

    out = cat.catalog_pull(persona_slugs=[slug], store=dest)            # default: drift-safe
    assert out["landed"] == [] and out["personas"] == []
    assert [s["slug"] for s in out["skipped_locally_modified"]] == [slug]
    assert "force=True" in out["note"]
    assert dest.get_persona(slug)["updated_at"] == FUTURE               # untouched

    forced = cat.catalog_pull(persona_slugs=[slug], force=True, store=dest)
    assert [p["slug"] for p in forced["landed"]] == [slug]
    assert dest.get_persona(slug)["updated_at"] == personas[0]["updated_at"]  # catalog wins


def test_pull_pack_skips_modified_members(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    files, personas = _mini_catalog(Store(), ["Cara Chef"])
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")
    cat.catalog_pull(pack="starter", store=dest)
    _bump_local(dest, personas[0]["slug"])
    out = cat.catalog_pull(pack="starter", store=dest)
    assert out["landed"] == []
    assert [s["slug"] for s in out["skipped_locally_modified"]] == [personas[0]["slug"]]


def test_pull_protects_native_personas_occupying_a_catalog_slug(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    files, personas = _mini_catalog(Store(), ["Anna Architect"])
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")
    # A NATIVE persona (no catalog provenance) that happens to share the slug.
    services.record_persona("Anna Architect source", make_profile("Anna Architect"), store=dest)
    out = cat.catalog_pull(persona_slugs=[personas[0]["slug"]], store=dest)
    assert out["landed"] == []
    assert "without catalog provenance" in out["skipped_locally_modified"][0]["reason"]


# --------------------------------------------------------------------------- #
# catalog_status: the fetch/status half of the git analogy                     #
# --------------------------------------------------------------------------- #

def test_status_empty_store_is_an_inband_note(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    out = cat.catalog_status(store=Store(tmp_path / "dest.db"))
    assert out["items"] == [] and any("no catalog-pulled personas" in n for n in out["notes"])


def test_status_classifies_freshness_and_drift(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    files, personas = _mini_catalog(Store(), ["Anna Architect", "Ben Baker", "Cara Chef"])
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")
    slugs = [p["slug"] for p in personas]
    cat.catalog_pull(persona_slugs=slugs, store=dest)

    out = cat.catalog_status(store=dest)
    assert {i["status"] for i in out["items"]} == {"up_to_date"}
    assert out["counts"] == {"up_to_date": 3}

    # catalog moves on for Anna; Ben lives on locally; Cara does both -> diverged
    manifest = json.loads(files["manifest.json"])
    manifest["personas"][0]["updated_at"] = FUTURE
    manifest["personas"][2]["updated_at"] = FUTURE
    files["manifest.json"] = json.dumps(manifest).encode()
    _bump_local(dest, slugs[1])
    _bump_local(dest, slugs[2])

    by_slug = {i["slug"]: i for i in cat.catalog_status(store=dest)["items"]}
    assert by_slug[slugs[0]]["status"] == "behind"
    assert by_slug[slugs[1]]["status"] == "locally_modified"
    assert by_slug[slugs[2]]["status"] == "diverged"
    assert by_slug[slugs[0]]["catalog_updated_at"] == FUTURE


def test_status_removed_upstream_and_slug_filter(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    files, personas = _mini_catalog(Store(), ["Anna Architect", "Ben Baker"])
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")
    slugs = [p["slug"] for p in personas]
    cat.catalog_pull(persona_slugs=slugs, store=dest)

    manifest = json.loads(files["manifest.json"])
    manifest["personas"] = manifest["personas"][1:]                     # Anna gone upstream
    files["manifest.json"] = json.dumps(manifest).encode()

    out = cat.catalog_status(persona_slugs=[slugs[0]], store=dest)
    assert [i["status"] for i in out["items"]] == ["removed_upstream"]
    assert out["counts"] == {"removed_upstream": 1}                     # filter applied


def test_status_coarse_fallback_without_per_persona_timestamps(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    files, personas = _mini_catalog(Store(), ["Anna Architect"])
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")
    cat.catalog_pull(persona_slugs=[personas[0]["slug"]], store=dest)

    # An older-style manifest: regenerated since the pull, but no per-persona updated_at.
    manifest = json.loads(files["manifest.json"])
    manifest["generated_at"] = FUTURE
    for p in manifest["personas"]:
        del p["updated_at"]
    files["manifest.json"] = json.dumps(manifest).encode()

    out = cat.catalog_status(store=dest)
    assert [i["status"] for i in out["items"]] == ["possibly_behind"]
    assert any("no per-persona updated_at" in n for n in out["notes"])


# --------------------------------------------------------------------------- #
# refresh_persona_from_source: concrete for catalog personas, hint for native  #
# --------------------------------------------------------------------------- #

def test_refresh_repulls_catalog_personas(monkeypatch, tmp_path):
    _no_data_pkg(monkeypatch)
    files, personas = _mini_catalog(Store(), ["Anna Architect"])
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")
    slug = personas[0]["slug"]
    cat.catalog_pull(persona_slugs=[slug], store=dest)

    out = services.refresh_persona_from_source(slug, store=dest)
    assert [p["slug"] for p in out["landed"]] == [slug]
    assert out["refreshed_from"]["source"] == "sonaloop-data"
    assert out["persona_id"] == personas[0]["id"]

    _bump_local(dest, slug)                                             # drift-safe like pull
    skipped = services.refresh_persona_from_source(slug, store=dest)
    assert skipped["landed"] == [] and skipped["skipped_locally_modified"]
    forced = services.refresh_persona_from_source(slug, store=dest, force=True)
    assert [p["slug"] for p in forced["landed"]] == [slug]


def test_refresh_native_persona_answers_with_authoring_recipe(tmp_path):
    dest = Store(tmp_path / "dest.db")
    p = services.record_persona("Nora Native source", make_profile("Nora Native"), store=dest)
    with pytest.raises(NotImplementedError, match="re-authors"):
        services.refresh_persona_from_source(p["slug"], store=dest)
    with pytest.raises(KeyError, match="Unknown persona"):
        services.refresh_persona_from_source("ghost", store=dest)


# --------------------------------------------------------------------------- #
# with sonaloop-data (mocked module): delegation + the local/remote split      #
# --------------------------------------------------------------------------- #

def _fake_pkg(monkeypatch, tmp_path, *, local: bool, profiles: list[dict] | None = None):
    pkg = types.ModuleType("sonaloop_data")
    paths = types.ModuleType("sonaloop_data.paths")
    root = tmp_path / "catalog"
    root.mkdir(exist_ok=True)
    if local:
        (root / "manifest.json").write_text("{}")
    paths.catalog_root = lambda: root
    pkg.paths = paths
    calls: dict[str, dict] = {}
    pkg.read_persona_files = lambda: iter(profiles or [])
    pkg.derive_facets = lambda profile, pack_ids=None: {
        "role_family": ["handwerk" if "Bäcker" in (profile.get("role") or {}).get("title", "")
                        else "buero"]}
    pkg.recommend = lambda spec: {"spec": spec, "personas": [{"slug": "x", "rationale": ["r"]}],
                                  "warnings": []}

    def load_into(store, *, embed=False, persona_slugs=None, pack=None):
        calls["load_into"] = {"slugs": persona_slugs, "pack": pack, "embed": embed}
        return {"personas": persona_slugs or []}

    def pull_remote(store, *, persona_slugs=None, pack=None, ref="main", embed=False):
        calls["pull_remote"] = {"slugs": persona_slugs, "pack": pack, "ref": ref, "embed": embed}
        return {"personas": persona_slugs or [], "ref": ref, "repo": cat.CATALOG_REPO}

    pkg.load_into, pkg.pull_remote = load_into, pull_remote
    monkeypatch.setitem(sys.modules, "sonaloop_data", pkg)
    monkeypatch.setitem(sys.modules, "sonaloop_data.paths", paths)
    return pkg, calls


def test_pull_prefers_local_checkout_for_default_ref(monkeypatch, tmp_path):
    _, calls = _fake_pkg(monkeypatch, tmp_path, local=True)
    out = cat.catalog_pull(persona_slugs=["a-slug"], store=Store(tmp_path / "d.db"))
    assert calls["load_into"]["slugs"] == ["a-slug"] and "pull_remote" not in calls
    assert out["source"] == "local-catalog"


def test_pull_explicit_ref_goes_remote_even_with_checkout(monkeypatch, tmp_path):
    _, calls = _fake_pkg(monkeypatch, tmp_path, local=True)
    cat.catalog_pull(persona_slugs=["a-slug"], ref="v2", store=Store(tmp_path / "d.db"))
    assert calls["pull_remote"]["ref"] == "v2" and "load_into" not in calls


def test_pull_without_checkout_uses_pull_remote(monkeypatch, tmp_path):
    _, calls = _fake_pkg(monkeypatch, tmp_path, local=False)
    cat.catalog_pull(pack="starter", store=Store(tmp_path / "d.db"))
    assert calls["pull_remote"]["pack"] == "starter"


def test_search_local_catalog_facets_and_summary(monkeypatch, tmp_path):
    profiles = [
        {"slug": "anna", "display_name": "Anna", "role": {"title": "Bäckerin"},
         "goals": ["ruhe"], "pain_points": ["schichtplan"], "avatar": {"path": "x"}},
        {"slug": "ben", "display_name": "Ben", "role": {"title": "Controller"},
         "goals": [], "pain_points": []},
    ]
    _fake_pkg(monkeypatch, tmp_path, local=True, profiles=profiles)
    out = cat.catalog_search(facets={"role_family": ["handwerk"]})
    assert out["source"] == "local-catalog" and out["total"] == 1
    assert out["items"][0]["slug"] == "anna" and out["items"][0]["has_avatar"] is True
    assert out["facet_summary"] == {"role_family": {"handwerk": 1}}     # over the filtered set
    assert cat.catalog_search(query="schichtplan")["total"] == 1        # pain points searchable


def test_recommend_delegates_to_the_package(monkeypatch, tmp_path):
    _fake_pkg(monkeypatch, tmp_path, local=True, profiles=[{"slug": "anna"}])
    out = cat.catalog_recommend({"keywords": ["x"], "n": 1})
    assert out["personas"][0]["slug"] == "x"


def test_recommend_installed_but_no_catalog_is_noted(monkeypatch, tmp_path):
    _fake_pkg(monkeypatch, tmp_path, local=False)
    out = cat.catalog_recommend({})
    assert out["skipped"] is True and "no local catalog" in out["note"]


def test_status_uses_local_checkout_timestamps(monkeypatch, tmp_path):
    """With a checkout, status reads exact per-persona updated_at from the profiles."""
    files, personas = _mini_catalog(Store(), ["Anna Architect"])
    _no_data_pkg(monkeypatch)
    _serve(files, monkeypatch)
    dest = Store(tmp_path / "dest.db")
    slug = personas[0]["slug"]
    cat.catalog_pull(persona_slugs=[slug], store=dest)
    # now "install" the package with a checkout whose profile moved on
    moved = {**personas[0], "updated_at": FUTURE}
    _fake_pkg(monkeypatch, tmp_path, local=True, profiles=[moved])
    out = cat.catalog_status(store=dest)
    assert out["source"] == "local-catalog"
    assert [i["status"] for i in out["items"]] == ["behind"]


# --------------------------------------------------------------------------- #
# the MCP surface itself                                                       #
# --------------------------------------------------------------------------- #

def test_catalog_tools_registered_and_enveloped(monkeypatch):
    _no_data_pkg(monkeypatch)
    _serve(_manifest_only(3), monkeypatch)
    server = build_server()
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {"catalog_search", "catalog_recommend", "catalog_pull", "catalog_status"} <= names
    _, env = asyncio.run(server.call_tool("catalog_search", {"limit": 2}))
    assert env["ok"] is True and env["data"]["total"] == 3 and len(env["data"]["items"]) == 2
    assert env["next_recommended_tool"]["name"] == "catalog_pull"       # the browse->pull DAG


# --------------------------------------------------------------------------- #
# optional integration against the REAL sibling checkout (skipped elsewhere)   #
# --------------------------------------------------------------------------- #

_DATA_REPO = pathlib.Path.home() / "repos" / "sonaloop-data"


@pytest.mark.skipif(not (_DATA_REPO / "src" / "sonaloop_data").is_dir(),
                    reason="sonaloop-data checkout not present")
def test_real_package_local_recommend_and_pull(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(_DATA_REPO / "src"))
    monkeypatch.delenv("SONALOOP_DATA_CATALOG_ROOT", raising=False)
    for k in [k for k in sys.modules if k.startswith("sonaloop_data")]:
        monkeypatch.delitem(sys.modules, k)
    try:
        slug = json.loads((_DATA_REPO / "manifest.json").read_text())["personas"][0]["slug"]
        out = cat.catalog_recommend({"keywords": ["schicht"], "n": 3})
        assert len(out["personas"]) == 3 and all(p["rationale"] for p in out["personas"])
        dest = Store(tmp_path / "dest.db")
        pulled = cat.catalog_pull(persona_slugs=[slug], store=dest)
        assert pulled["source"] == "local-catalog"
        assert pulled["landed"][0]["slug"] == slug
        assert pulled["landed"][0]["provenance"]["source"] == "sonaloop-data"
        assert len(dest.list_personas()) == 1
        status = cat.catalog_status(store=dest)                          # checkout-exact status
        assert status["source"] == "local-catalog"
        assert status["items"][0]["status"] in ("up_to_date", "behind")
    finally:
        for k in [k for k in sys.modules if k.startswith("sonaloop_data")]:
            del sys.modules[k]
