"""M2 — prototype generation + local runner."""
from __future__ import annotations

import time
import urllib.request

from sonaloop import prototypes


_CONCEPT = {
    "title": "Übergabe-Check",
    "summary": "Was hat sich geändert?",
    "start": "home",
    "screens": [
        {"id": "home", "title": "Start", "elements": [
            {"kind": "text", "id": "t1", "label": "Lade zwei Stände und vergleiche."},
            {"kind": "button", "id": "go", "label": "Vergleichen", "goto": "result"}]},
        {"id": "result", "title": "Ergebnis", "elements": [
            {"kind": "text", "id": "t2", "label": "W-12 (tragende Wand) entfernt."},
            {"kind": "input", "id": "note", "label": "Notiz"},
            {"kind": "button", "id": "proto", "label": "Protokoll erzeugen"}]},
    ],
}


def test_scaffold_creates_runnable_app(store, tmp_path, monkeypatch):
    # write generated app under a temp prototypes dir to keep the repo clean
    monkeypatch.setattr(prototypes, "prototypes_dir", lambda: tmp_path)
    rec = prototypes.scaffold_prototype("ueberg-test", "Übergabe-Check", _CONCEPT, store=store)
    assert rec["run"] == "static" and rec["entry"] == "index.html"
    html = (tmp_path / "ueberg-test" / "index.html").read_text(encoding="utf-8")
    assert "Vergleichen" in html and "concept" in html
    assert store.get_prototype("ueberg-test")["id"] == rec["id"]


def test_run_prototype_serves_locally(store, tmp_path, monkeypatch):
    monkeypatch.setattr(prototypes, "prototypes_dir", lambda: tmp_path)
    prototypes.scaffold_prototype("ueberg-run", "Übergabe-Check", _CONCEPT, store=store)
    info = prototypes.run_prototype("ueberg-run", store=store)
    try:
        assert info["url"].startswith("http://127.0.0.1:")
        body = None
        for _ in range(20):
            try:
                body = urllib.request.urlopen(info["url"], timeout=2).read().decode("utf-8")
                break
            except Exception:
                time.sleep(0.1)
        assert body is not None and "Vergleichen" in body
    finally:
        prototypes.stop_prototype("ueberg-run", store=store)
