"""Persona-catalog MCP tools — the core half of sonaloop-data's pull story
(ticket sonaloop-data/persona-pull-correctness): an MCP host can BROWSE the
curated catalog and PULL personas into the current store conversationally.

Layering (sonaloop-data depends on core, never the reverse, so nothing here
imports `sonaloop_data` at module level):

1. **sonaloop-data installed** (lazy import): the full surface — local-checkout
   or remote pulls via `load_into`/`pull_remote` (identical provenance stamping,
   idempotent re-pulls), facet derivation + the deterministic `recommend` scorer.
2. **Not installed**: `catalog_search` and `catalog_pull` keep working against
   the PUBLISHED catalog through a thin built-in fallback (stdlib urllib, zero
   extra dependencies) that mirrors sonaloop-data's raw.githubusercontent URL
   contract (`manifest.json`, `packs/<id>.json`, `personas/<slug>/<file>`) and
   its `provenance.catalog` stamp. The duplication is deliberate and small
   (~60 lines): the ticket wants browse+pull usable from ANY sonaloop install,
   and the price is keeping `_PERSONA_FILES`/`RAW_URL`/the stamp shape in sync
   with `sonaloop_data.remote` — guarded by tests on both sides. Everything
   richer (packs metadata, facets, recommend) answers in-band with an
   "install sonaloop-data" note instead of erroring.

The three pull paths, documented for hosts: (a) in-process `load_into(store)`
from a checkout (sonaloop-data), (b) `sonaloop-data pull` CLI / `pull_remote`
without a checkout, (c) these MCP tools — search → recommend → pull.

`catalog_search` paginates per the shared convention (docs/pagination.md:
limit default 25 + opaque cursor, {items,total,has_more,next_cursor} envelope).
"""
from __future__ import annotations

import json
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .. import services
from ..storage import Store
from ._env import _env

CATALOG_REPO = "jhoetter/sonaloop-data"
RAW_URL = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"

# Mirror of sonaloop_data.remote.PERSONA_FILES (the per-persona snapshot files;
# profile.json is required, the rest optional). Keep in lockstep.
_PERSONA_FILES = ("profile.json", "SOUL.md", "MEMORY.md", "calendar.json",
                  "experiences.json", "daily_summaries.json", "memory.json", "eval.json")

INSTALL_NOTE = ("The sonaloop-data package is not installed — catalog_search and "
                "catalog_pull keep working against the published catalog "
                f"(github.com/{CATALOG_REPO}), but facet filtering, recommendation and "
                "local-checkout pulls need it: `uv add sonaloop-data` (or pip install).")


class CatalogFetchError(RuntimeError):
    """A remote catalog fetch failed for a reason other than a plain 404."""


def _data_pkg():
    """The optional sonaloop-data package, or None — NEVER imported at module level
    (sonaloop-data depends on core; core only ever looks for it lazily)."""
    try:
        import sonaloop_data
        return sonaloop_data
    except ImportError:
        return None


def _local_root(pkg) -> Path | None:
    """The installed package's local catalog root (repo checkout or
    SONALOOP_DATA_CATALOG_ROOT) — None when there is no manifest to read."""
    try:
        from sonaloop_data.paths import catalog_root
        root = catalog_root()
        return root if (root / "manifest.json").exists() else None
    except Exception:
        return None


def _fetch_bytes(url: str) -> bytes | None:
    """stdlib fetcher mirroring sonaloop_data.remote._urllib_fetcher (None == 404)."""
    req = urllib.request.Request(url, headers={"User-Agent": "sonaloop"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — https only
            return resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise CatalogFetchError(f"GET {url} -> HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise CatalogFetchError(f"GET {url} failed: {exc.reason}") from exc


def _get(ref: str, path: str, *, required: bool = False) -> bytes | None:
    url = RAW_URL.format(repo=CATALOG_REPO, ref=ref, path=path)
    data = _fetch_bytes(url)
    if data is None and required:
        raise CatalogFetchError(f"{path} not found at {url}")
    return data


# --------------------------------------------------------------------------- #
# search                                                                        #
# --------------------------------------------------------------------------- #

def _facet_summary(entries: list[dict[str, Any]], cap: int = 10) -> dict[str, dict[str, int]]:
    """Facet value counts over the FULL filtered set (never just the visible page)."""
    counts: dict[str, dict[str, int]] = {}
    for e in entries:
        for facet, values in (e.get("facets") or {}).items():
            bucket = counts.setdefault(facet, {})
            for v in values:
                bucket[v] = bucket.get(v, 0) + 1
    return {f: dict(sorted(vals.items(), key=lambda kv: (-kv[1], kv[0]))[:cap])
            for f, vals in sorted(counts.items())}


def _local_entries(pkg) -> list[dict[str, Any]]:
    """Browse rows from the local catalog: identity + derived facets + search text."""
    entries = []
    for profile in pkg.read_persona_files():
        role = (profile.get("role") or {}).get("title") or ""
        entry = {"slug": profile.get("slug"), "display_name": profile.get("display_name", ""),
                 "role": role, "has_avatar": bool(profile.get("avatar")),
                 "facets": pkg.derive_facets(profile)}
        entry["_text"] = " ".join([entry["slug"] or "", entry["display_name"], role,
                                   " ".join(profile.get("goals") or []),
                                   " ".join(profile.get("pain_points") or [])]).casefold()
        entries.append(entry)
    return entries


def _remote_entries(ref: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Browse rows from the published manifest (no checkout, no extra package)."""
    manifest = json.loads(_get(ref, "manifest.json", required=True))
    entries = []
    for p in manifest.get("personas", []):
        entry = {"slug": p.get("slug"), "display_name": p.get("display_name", ""),
                 "role": p.get("role", ""), "has_avatar": bool(p.get("has_avatar"))}
        entry["_text"] = " ".join(str(v) for v in (entry["slug"], entry["display_name"],
                                                   entry["role"]) if v).casefold()
        entries.append(entry)
    return entries, manifest


def _search_impl(query: str | None = None, facets: dict[str, list[str]] | None = None,
                 limit: int = 25, cursor: str | None = None, ref: str = "main") -> dict[str, Any]:
    pkg = _data_pkg()
    notes: list[str] = []
    manifest_meta: dict[str, Any] = {}
    if pkg is not None and _local_root(pkg) is not None:
        source = "local-catalog"
        entries = _local_entries(pkg)
    else:
        source = f"{CATALOG_REPO}@{ref}"
        entries, manifest = _remote_entries(ref)
        manifest_meta = {"generated_at": manifest.get("generated_at"),
                         "schema_version": manifest.get("schema_version")}
        if pkg is None:
            notes.append(INSTALL_NOTE)
        if facets:
            notes.append("facet filtering needs the sonaloop-data package with a local "
                         "catalog — the facet filter was IGNORED for this remote search")
            facets = None

    if query:
        needle = query.strip().casefold()
        entries = [e for e in entries if needle in e["_text"]]
    for facet, wanted in sorted((facets or {}).items()):
        wanted_set = {str(v) for v in wanted}
        entries = [e for e in entries if wanted_set & set((e.get("facets") or {}).get(facet, []))]

    for e in entries:
        e.pop("_text", None)
    entries.sort(key=lambda e: e["slug"] or "")
    fp = {"query": query or "", "facets": facets or {}, "source": source}
    page = services.paginate(entries, lambda e: e["slug"] or "",
                             limit=limit, cursor=cursor, filters=fp)
    summary = _facet_summary(entries) if source == "local-catalog" else None
    return {**page, "source": source, "facet_summary": summary,
            **({"manifest": manifest_meta} if manifest_meta else {}),
            **({"notes": notes} if notes else {})}


# --------------------------------------------------------------------------- #
# recommend                                                                    #
# --------------------------------------------------------------------------- #

def _recommend_impl(spec: dict[str, Any]) -> dict[str, Any]:
    pkg = _data_pkg()
    if pkg is None:
        return {"skipped": True, "note": INSTALL_NOTE}
    if _local_root(pkg) is None:
        return {"skipped": True,
                "note": "sonaloop-data is installed but no local catalog was found — "
                        "recommendation scores full profiles, which only the checkout has. "
                        "Clone the catalog (or set SONALOOP_DATA_CATALOG_ROOT), or use "
                        "catalog_search + catalog_pull against the published catalog."}
    return pkg.recommend(spec)


# --------------------------------------------------------------------------- #
# pull                                                                         #
# --------------------------------------------------------------------------- #

def _builtin_pull(store: Store, persona_slugs: list[str] | None, pack: str | None,
                  ref: str, embed: bool) -> dict[str, Any]:
    """The dependency-free remote pull: fetch the selection from the published
    catalog (mirroring sonaloop_data.remote's URL contract), stamp
    `provenance.catalog` on each profile exactly like sonaloop_data.loader does,
    and import through core's own snapshot importer (idempotent upserts)."""
    manifest_raw = _get(ref, "manifest.json", required=True)
    manifest = json.loads(manifest_raw)
    roster = {p["slug"]: p for p in manifest.get("personas", [])}

    slugs: list[str] = []
    if pack:
        pack_raw = _get(ref, f"packs/{pack}.json")
        if pack_raw is None:
            raise KeyError(f"Unknown archetype pack: {pack!r} "
                           f"(no packs/{pack}.json in {CATALOG_REPO}@{ref})")
        slugs.extend(json.loads(pack_raw).get("personas") or [])
    for s in persona_slugs or []:
        if s not in slugs:
            slugs.append(s)
    unknown = [s for s in slugs if s not in roster]
    if unknown:
        raise ValueError(f"Unknown persona slug(s) in {CATALOG_REPO}@{ref}: {unknown}")

    stamp: dict[str, Any] = {"source": "sonaloop-data",
                             "manifest_generated_at": manifest.get("generated_at"),
                             "schema_version": manifest.get("schema_version"),
                             "pulled_at": services.utc_now_iso(),
                             "repo": CATALOG_REPO, "ref": ref}
    if pack:
        stamp["pack"] = pack

    with tempfile.TemporaryDirectory(prefix="sonaloop-catalog-") as tmp:
        base = Path(tmp)
        (base / "manifest.json").write_bytes(manifest_raw)
        for slug in slugs:
            pdir = base / "personas" / slug
            pdir.mkdir(parents=True, exist_ok=True)
            for name in _PERSONA_FILES:
                data = _get(ref, f"personas/{slug}/{name}", required=(name == "profile.json"))
                if data is None:
                    continue
                if name == "profile.json":
                    profile = json.loads(data)
                    profile.setdefault("provenance", {})["catalog"] = {**stamp, "slug": slug}
                    data = (json.dumps(profile, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
                (pdir / name).write_bytes(data)
            if roster[slug].get("has_avatar"):
                avatar = _get(ref, f"personas/{slug}/avatar.png")
                if avatar is not None:
                    (pdir / "avatar.png").write_bytes(avatar)
        try:
            out = services.import_snapshot(in_dir=str(base), store=store, embed=embed)
        except ValueError:
            # import_snapshot computes a ROOT-relative summary path AFTER every DB write
            # (and the embed backfill); a temp snapshot outside the repo trips exactly that
            # last step. State is fully imported by then — same absorb as sonaloop_data.loader.
            store.commit()
            out = {"embeddings": "re-derived" if embed else "skipped"}
    return {**out, "personas": slugs, "repo": CATALOG_REPO, "ref": ref,
            "source": "built-in remote fallback", "note": INSTALL_NOTE}


def _pull_impl(persona_slugs: list[str] | None = None, pack: str | None = None,
               ref: str = "main", embed: bool = False, store: Store | None = None) -> dict[str, Any]:
    if not persona_slugs and not pack:
        raise ValueError("catalog_pull is selective by design — pass persona_slugs and/or pack "
                         "(a full 300+-persona import belongs to sonaloop-data's load_into/CLI)")
    store = store or Store()
    pkg = _data_pkg()
    if pkg is not None:
        if ref == "main" and _local_root(pkg) is not None:
            # Same data, no network: the checkout (or SONALOOP_DATA_CATALOG_ROOT) wins for
            # the default ref; pass an explicit ref to force a published-version pull.
            out = pkg.load_into(store, embed=embed, persona_slugs=persona_slugs or None, pack=pack)
            out.setdefault("source", "local-catalog")
        else:
            out = pkg.pull_remote(store, persona_slugs=persona_slugs or None, pack=pack,
                                  ref=ref, embed=embed)
            out.setdefault("source", f"{CATALOG_REPO}@{ref}")
    else:
        out = _builtin_pull(store, persona_slugs, pack, ref, embed)

    landed = []
    for slug in out.get("personas") or persona_slugs or []:
        p = store.get_persona(slug)
        if p:
            landed.append({"slug": p["slug"], "id": p["id"],
                           "display_name": p.get("display_name", ""),
                           "provenance": (p.get("provenance") or {}).get("catalog")})
    return {**out, "landed": landed}


def register_catalog(mcp):
    # ================= Persona catalog (sonaloop-data) =================
    @mcp.tool()
    def catalog_search(query: str | None = None, facets: dict[str, list[str]] | None = None,
                       limit: int = 25, cursor: str | None = None, ref: str = "main") -> dict[str, Any]:
        """Browse the curated persona catalog (github:jhoetter/sonaloop-data): slugs, names,
        roles + a facet summary over the filtered set. `query` is a free-text filter; `facets`
        ({facet -> [values]}, e.g. {"lebensphase": ["schichtarbeit"]}) needs the sonaloop-data
        package with a local catalog. Paginated per the shared convention (docs/pagination.md):
        `limit` (default 25) + opaque `cursor`; answers {items, total, has_more, next_cursor}.
        Works WITHOUT the sonaloop-data package via the published manifest at git `ref`."""
        t = time.perf_counter()
        return _env("catalog_search", _search_impl(query, facets, limit, cursor, ref), t)

    @mcp.tool()
    def catalog_recommend(spec: dict[str, Any]) -> dict[str, Any]:
        """Deterministic, explainable persona-SET recommendation over the catalog (no LLM):
        spec = {keywords?: [...], facets?: {facet -> [values]}, n?: int, seed_pack?: id,
        min_coverage?: int}. Returns ranked picks with human-readable rationales, the set's
        facet coverage, gap warnings and a ready pull list. Needs the sonaloop-data package
        + a local catalog (answers in-band with an install note otherwise)."""
        t = time.perf_counter()
        return _env("catalog_recommend", _recommend_impl(spec), t)

    @mcp.tool()
    def catalog_pull(persona_slugs: list[str] | None = None, pack: str | None = None,
                     ref: str = "main", embed: bool = False) -> dict[str, Any]:
        """Pull catalog personas (by slug and/or archetype `pack`) into the CURRENT store —
        profiles, SOUL/MEMORY, lived memories, avatars — with `provenance.catalog` stamped on
        each persona; re-pulls are idempotent (stable ids, upserts). Uses sonaloop-data when
        installed (local checkout for the default ref, else the published catalog at `ref`);
        without it a built-in stdlib fallback pulls from the published catalog directly.
        `embed=True` re-derives embedding vectors (needs a configured provider; skipped
        gracefully otherwise). Returns what landed (slug, id, provenance)."""
        t = time.perf_counter()
        return _env("catalog_pull", _pull_impl(persona_slugs, pack, ref, embed), t)
