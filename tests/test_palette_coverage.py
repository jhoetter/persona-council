"""THE CANARY — the Cmd+K palette must never fall behind the app
(ticket cmdk-registry-driven-coverage).

Walks the live route table, the nav registry and the presence-contract entity kinds,
and fails — naming exactly what to add — whenever something exists that the palette's
coverage registry (sonaloop/web/_palette_registry.py) cannot reach. Plus behavioral
tests for the newly searchable entity types (sessions, hypotheses, decisions, surveys).
"""
from __future__ import annotations

import re

from starlette.testclient import TestClient

from conftest import create_persona
from sonaloop import services, web
from sonaloop.web._ext import nav_model
from sonaloop.web._palette_registry import (
    KIND_SEARCH, NON_SEARCHABLE_ROUTES, SEARCH_SOURCES, NotSearchable,
    nav_commands, search_rows,
)

# a top-level detail route: one literal prefix segment + one path parameter
_DETAIL_ROUTE = re.compile(r"^(/[a-z-]+)/\{[^/}]+\}$")


def test_canary_every_nav_item_is_a_palette_command(store):
    """Every registered nav item (core seeds + anything an extension registers) must
    surface as a palette jump command — derived, not hand-copied."""
    web.create_app()                                   # seeds the nav registry + extensions
    urls = {c["url"] for c in nav_commands()}
    missing = [it["href"] for _sec, items in nav_model() for it in items
               if it["href"] not in urls]
    assert not missing, (
        "palette fell behind the nav registry — these nav items have no jump command: "
        f"{missing}. nav_commands() derives from nav_model(), so this means someone "
        "bypassed register_nav_item or filtered commands; fix the derivation in "
        "sonaloop/web/_palette_registry.py, do not hand-add commands.")
    # the chrome surfaces the ticket names explicitly
    for required in ("/activity", "/runs", "/documentation", "#settings", "#shortcuts"):
        assert required in urls, f"palette misses the required jump command {required!r}"


def test_canary_every_detail_route_is_searchable_or_excused(store):
    """Every GET /{prefix}/{id} page route must be reachable through entity search —
    or carry an explicit reason in NON_SEARCHABLE_ROUTES."""
    app = web.create_app()
    prefixes = {src.url_prefix for src in SEARCH_SOURCES.values()}
    offenders = []
    for r in app.routes:
        path = getattr(r, "path", "")
        methods = getattr(r, "methods", None) or set()
        m = _DETAIL_ROUTE.match(path)
        if not m or "GET" not in methods or path.startswith("/api/"):
            continue
        prefix = m.group(1)
        if prefix in prefixes or prefix in NON_SEARCHABLE_ROUTES:
            continue
        offenders.append(
            f"{path}: add a SEARCH_SOURCES entry with url_prefix '{prefix}' in "
            "sonaloop/web/_palette_registry.py (label, icon, color, rows reader) — or, "
            "if its records are genuinely not palette targets, excuse the prefix in "
            "NON_SEARCHABLE_ROUTES with the reason")
    assert not offenders, "palette fell behind the app's routes:\n  " + "\n  ".join(offenders)


def test_canary_every_entity_kind_is_searchable_or_excused():
    """Every presence-contract kind (the app's entity inventory — web/_presence.REGISTRY)
    must map to a search source or an explicit NotSearchable reason; no stale mappings."""
    from sonaloop.web._presence import REGISTRY
    problems = []
    for kind in REGISTRY:
        target = KIND_SEARCH.get(kind)
        if target is None:
            problems.append(f"kind {kind!r} is missing from KIND_SEARCH — map it to its "
                            "SEARCH_SOURCES type or declare NotSearchable(reason) in "
                            "sonaloop/web/_palette_registry.py")
        elif isinstance(target, NotSearchable):
            if not target.reason:
                problems.append(f"NotSearchable for kind {kind!r} must carry a reason")
        elif target not in SEARCH_SOURCES:
            problems.append(f"kind {kind!r} maps to unknown search source {target!r}")
    for kind in set(KIND_SEARCH) - set(REGISTRY):
        problems.append(f"KIND_SEARCH maps {kind!r} which is no longer a presence kind — "
                        "drop the stale entry")
    assert not problems, "palette fell behind the entity kinds:\n  " + "\n  ".join(problems)


def test_palette_markup_seeds_registry_commands_and_groups(store):
    """The rendered chrome carries the registry-derived commands (every nav item, incl.
    /runs and /activity) and the per-type group labels/icons/order as JSON."""
    html = TestClient(web.create_app()).get("/?lang=en").text
    cfg = html.split('id="cmdk-cfg" type="application/json">')[1].split("</script>")[0]
    for url in ("/projects", "/personas", "/activity", "/runs", "/documentation",
                "/surveys", "/hypotheses", "/decisions", "#settings", "#shortcuts"):
        assert f'"url": "{url}"' in cfg or f'"{url}"' in cfg, f"palette command {url} missing"
    import json
    parsed = json.loads(cfg)
    assert parsed["order"] == ["go", *SEARCH_SOURCES]
    assert set(parsed["labels"]) == {"go", *SEARCH_SOURCES}
    assert set(parsed["icons"]) == {"go", *SEARCH_SOURCES}


# ------------------------------------------------------------- new searchable types

_STEP = {"index": 0, "action": {"type": "click", "target": "b0", "detail": "clicked"},
         "monologue": "thinking aloud", "state": {"screen": "start screen"},
         "friction": {"level": "none", "note": ""},
         "verdict": {"would_continue": True, "reason": ""}}
_OUTCOME = {"completed": True, "dropoff_step": None, "summary": "walked it",
            "predicted_behaviors": []}


def _seed_new_entities(store):
    proj = services.create_research_project("Pension awareness",
                                            goal="How do people plan retirement?", store=store)
    pid = proj["id"]
    services.record_hypothesis(
        pid, text="Savers complete the digital pension check",
        prediction={"metric": "signup_rate", "expected_value": 40, "tolerance": 5,
                    "confidence": 0.7}, store=store)
    per = create_persona(store, "Evi Dence")
    council = services.record_council(
        pid, "Would a digital pension check help?", [per],
        statements=[{"persona_id": per, "text": "it would help", "stance": {"value": 1}}],
        summary="useful", store=store)
    services.record_decision(
        pid, title="Ship the pension check standalone",
        decision="Own flow, not a portal plugin.",
        based_on=[{"kind": "council", "id": council["id"]}], store=store)
    services.record_survey(
        pid, title="Retirement readiness pulse",
        questions=[{"id": "q1", "text": "How do you save today?", "kind": "text"}], store=store)
    services.record_usability_session(
        per, {"kind": "flow", "id": "flow-check", "label": "Pension check walkthrough"},
        "artifact", "2026-06-10", [_STEP], _OUTCOME, project_id=pid, store=store)
    return pid


def test_search_covers_sessions_hypotheses_decisions_surveys(store):
    _seed_new_entities(store)
    client = TestClient(web.create_app())

    def hit(q, typ, url_prefix):
        rows = client.get(f"/api/search?q={q}").json()
        matches = [r for r in rows if r["type"] == typ]
        assert matches, f"no {typ} hit for q={q!r}: {rows}"
        assert matches[0]["url"].startswith(url_prefix + "/")
        return matches[0]

    hit("Savers complete", "hypothesis", "/hypotheses")
    hit("Ship the pension", "decision", "/decisions")
    hit("Retirement readiness", "survey", "/surveys")
    hit("Pension check walkthrough", "session", "/sessions")


def test_search_rows_matches_api_contract(store):
    """search_rows is the same read the API serves: typed, grouped-ready rows."""
    _seed_new_entities(store)
    rows = search_rows("pension", store=store)
    types = {r["type"] for r in rows}
    assert {"project", "hypothesis", "decision", "session"} <= types
    for r in rows:
        assert set(r) == {"type", "title", "subtitle", "url"}
