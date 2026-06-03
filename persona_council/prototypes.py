"""Prototype artifacts (spec/methodology-engine-and-prototyping.md, Pillar B §6).

First-class generation of real, minimal, locally-runnable web apps from a host-authored
concept (the spa-min template renders a genuinely clickable SPA — real DOM, real refs — so a
persona-agent can drive it via Playwright), plus a registry and a local-only runner.
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

from .config import ROOT, prototype_templates_dir, prototypes_dir, utc_now_iso
from .models import Prototype
from .storage import Store


class PrototypeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# Running-prototype process table (in-memory; the durable record is the DB row).
_PROCS: dict[str, dict[str, Any]] = {}


# --------------------------------------------------------------------------- scaffolding

def _validate_concept(concept: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(concept, dict) or not str(concept.get("title", "")).strip():
        raise PrototypeError("BAD_CONCEPT", "concept needs a non-empty title")
    screens = concept.get("screens")
    if not isinstance(screens, list) or not screens:
        raise PrototypeError("BAD_CONCEPT", "concept needs >= 1 screen")
    ids = []
    for s in screens:
        if not isinstance(s, dict) or not str(s.get("id", "")).strip():
            raise PrototypeError("BAD_CONCEPT", "each screen needs an id")
        ids.append(s["id"])
        for el in s.get("elements", []) or []:
            if not isinstance(el, dict) or not str(el.get("id", "")).strip():
                raise PrototypeError("BAD_CONCEPT", "each element needs an id")
            if el.get("kind") not in {"button", "input", "select", "text", "link"}:
                raise PrototypeError("BAD_CONCEPT", f"bad element kind: {el.get('kind')}")
            if el.get("goto") and el["goto"] not in ids and el["goto"] not in [x.get("id") for x in screens]:
                raise PrototypeError("BAD_CONCEPT", f"element goto '{el['goto']}' is not a screen id")
    if concept.get("start") and concept["start"] not in [s["id"] for s in screens]:
        raise PrototypeError("BAD_CONCEPT", "start must be a screen id")
    return concept


TEMPLATES = {"spa-min": "midfi", "spa-sketch": "lofi"}


def _render_spa(name: str, concept: dict[str, Any], template: str = "spa-min") -> str:
    tpl = (prototype_templates_dir() / template / "index.html").read_text(encoding="utf-8")
    return (tpl
            .replace("__TITLE__", _esc(concept.get("title") or name))
            .replace("__SUMMARY__", _esc(concept.get("summary", "")))
            .replace("__CONCEPT_JSON__", json.dumps(concept, ensure_ascii=False)))


def _esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def scaffold_prototype(slug: str, name: str, concept: dict[str, Any], kind: str = "web",
                       template: str = "spa-min", project_id: str | None = None,
                       fidelity: str | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    if template not in TEMPLATES:
        raise PrototypeError("UNKNOWN_TEMPLATE", f"template must be one of {sorted(TEMPLATES)} (got {template})")
    fidelity = fidelity or TEMPLATES[template]
    concept = _validate_concept(concept)
    out_dir = prototypes_dir() / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(_render_spa(name, concept, template), encoding="utf-8")
    (out_dir / "concept.json").write_text(json.dumps(concept, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        stored_path = str(out_dir.relative_to(ROOT))
    except ValueError:
        stored_path = str(out_dir)
    return register_prototype(slug, name, stored_path, entry="index.html", run="static", version="v0.1",
                              project_id=project_id, fidelity=fidelity,
                              notes=f"generated from {template} ({len(concept['screens'])} screens)", store=store)


def register_prototype(slug: str, name: str, path: str, entry: str = "index.html", run: str = "static",
                       run_cmd: str | None = None, version: str = "v0.1", project_id: str | None = None,
                       notes: str = "", fidelity: str = "midfi", store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    from .services import stable_id
    now = utc_now_iso()
    existing = store.get_prototype(slug)
    pid = (existing or {}).get("id") or stable_id("prototype", slug, now)
    rec = Prototype(id=pid, slug=slug, project_id=project_id, name=name, version=version,
                    kind="web", path=path, entry=entry, run=run, run_cmd=run_cmd, notes=notes,
                    created_at=(existing or {}).get("created_at", now),
                    fidelity=(fidelity if fidelity in ("lofi", "midfi") else "midfi")).to_dict()
    store.upsert_prototype(rec)
    return rec


def list_prototypes(project_id: str | None = None, store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    out = store.list_prototypes(project_id)
    for p in out:
        p["running"] = p["id"] in _PROCS
        p["url"] = _PROCS.get(p["id"], {}).get("url")
    return out


def get_prototype(prototype_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    p = store.get_prototype(prototype_id)
    if not p:
        raise PrototypeError("UNKNOWN_PROTOTYPE", f"No prototype '{prototype_id}'")
    p["running"] = p["id"] in _PROCS
    p["url"] = _PROCS.get(p["id"], {}).get("url")
    return p


def delete_prototype(prototype_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    p = store.get_prototype(prototype_id)
    if p and p["id"] in _PROCS:
        stop_prototype(p["id"], store=store)
    return {"deleted": store.delete_prototype(prototype_id)}


# --------------------------------------------------------------------------- runner (local only)

def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def run_prototype(prototype_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    p = get_prototype(prototype_id, store=store)
    if p["id"] in _PROCS:
        return {"prototype_id": p["id"], "url": _PROCS[p["id"]]["url"], "pid": _PROCS[p["id"]]["proc"].pid,
                "already_running": True}
    app_dir = (ROOT / p["path"]).resolve()
    if not app_dir.exists():
        raise PrototypeError("MISSING_FILES", f"prototype dir not found: {p['path']}")
    port = _free_port()
    if p["run"] == "static":
        cmd = [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1",
               "--directory", str(app_dir)]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        if not p.get("run_cmd"):
            raise PrototypeError("NO_RUN_CMD", f"run='{p['run']}' needs a run_cmd")
        env_cmd = p["run_cmd"].replace("{port}", str(port))
        proc = subprocess.Popen(env_cmd, shell=True, cwd=str(app_dir),
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{port}/{p['entry'] if p['run'] == 'static' else ''}".rstrip("/")
    if p["run"] == "static":
        url = f"http://127.0.0.1:{port}/{p['entry']}"
    _PROCS[p["id"]] = {"proc": proc, "url": url, "port": port}
    return {"prototype_id": p["id"], "url": url, "pid": proc.pid}


def stop_prototype(prototype_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    p = store.get_prototype(prototype_id)
    key = (p or {}).get("id", prototype_id)
    entry = _PROCS.pop(key, None)
    if not entry:
        return {"stopped": False}
    try:
        entry["proc"].terminate()
        entry["proc"].wait(timeout=5)
    except Exception:
        try:
            entry["proc"].kill()
        except Exception:
            pass
    return {"stopped": True, "prototype_id": key}


def running_url(prototype_id: str) -> str | None:
    return _PROCS.get(prototype_id, {}).get("url")
