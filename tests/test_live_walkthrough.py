"""Live SaaS walkthroughs (ticket live-saas-walkthrough) — the WalkPolicy safety contract.

The policy layer (defaults from the data-driven denylist, normalization rejections, redaction,
URL-scheme hardening) tests without a browser; the enforcement tests drive a REAL local page
(mirroring test_browser_harness's local-target + playwright-skip patterns): off-origin navigation
blocked + logged, denylisted clicks refused, caps auto-close, credential redaction end to end,
per-step screenshots, and the full pipeline walk_open → proto_act → close →
record_usability_session('live') → the replay page renders the screenshots."""
from __future__ import annotations

import functools
import http.server
import json
import socketserver
import threading
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from conftest import create_persona
from sonaloop import browser, config, services, walk_policy, web


_PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Acme Console</title></head>
<body>
<h1>Acme Console</h1>
<p>Welcome to the workspace overview.</p>
<a href="http://localhost:{port}/index.html">Partner portal</a>
<button onclick="document.getElementById('out').textContent='settings opened'">Open settings</button>
<button onclick="document.getElementById('out').textContent='ACCOUNT GONE'">Delete account</button>
<form onsubmit="event.preventDefault();document.getElementById('out').textContent=
  'signed in as '+document.getElementById('u').value+' / '+document.getElementById('p').value;">
  <input id="u" aria-label="Username" type="text">
  <input id="p" aria-label="Password" type="password">
  <button type="submit">Sign in</button>
</form>
<div id="out"></div>
</body></html>
"""


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # keep pytest output clean
        pass


@pytest.fixture
def site(tmp_path):
    """A tiny live 'SaaS' on 127.0.0.1: an off-origin link (same server via `localhost` — a
    DIFFERENT origin), a safe button, a denylisted button and a login form."""
    handler = functools.partial(_QuietHandler, directory=str(tmp_path))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    (tmp_path / "index.html").write_text(_PAGE.format(port=port), encoding="utf-8")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}/index.html"
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Screenshots land under DATA_DIR/sessions — keep them in the temp dir."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "data")
    return tmp_path / "data"


def _ref(snapshot, name_contains):
    return next(n["ref"] for n in snapshot["tree"]
                if n.get("ref") and name_contains in n["name"])


# ------------------------------------------------------------------- the policy layer (no browser)

def test_walk_policy_defaults_matches_the_denylist_json():
    raw = json.loads((Path(walk_policy.__file__).parent / "suggestions" / "walk_denylist.json")
                     .read_text(encoding="utf-8"))
    out = services.walk_policy_defaults()
    cats = [i["category"] for i in raw["items"]]
    assert out["policy"]["blocked_categories"] == cats
    assert [c["category"] for c in out["categories"]] == cats
    for item in raw["items"]:
        merged = [t.strip().lower() for lang in ("en", "de") for t in item["terms"][lang]]
        assert out["policy"]["denylist"][item["category"]] == merged
    assert out["policy"]["max_actions"] == 60 and out["policy"]["max_duration_s"] == 900
    assert out["policy"]["allowed_origins"] == []      # walk_open locks this to the opening URL


def test_normalize_policy_rejects_bad_patches_never_degrades_silently():
    url = "https://app.example.test/welcome"
    norm = walk_policy.normalize_policy(None, url)
    assert norm["allowed_origins"] == ["https://app.example.test"]
    assert norm["denylist"]["destructive"]             # resolved terms ride the enforced policy
    with pytest.raises(ValueError, match="unknown policy key"):
        walk_policy.normalize_policy({"allow_everything": True}, url)
    with pytest.raises(ValueError, match="unknown denylist categor"):
        walk_policy.normalize_policy({"blocked_categories": ["bribery"]}, url)
    with pytest.raises(ValueError, match="positive integer"):
        walk_policy.normalize_policy({"max_actions": 0}, url)
    with pytest.raises(ValueError, match="cannot\\s+start off its own allowlist"):
        walk_policy.normalize_policy({"allowed_origins": ["https://other.test"]}, url)
    with pytest.raises(ValueError, match="http"):
        walk_policy.normalize_policy(None, "javascript:alert(1)")
    # a disabled category drops out of the enforced denylist
    only_pay = walk_policy.normalize_policy({"blocked_categories": ["payment"]}, url)
    assert list(only_pay["denylist"]) == ["payment"]


def test_credentials_validation_and_redaction():
    assert walk_policy.validate_credentials(None) is None
    assert walk_policy.validate_credentials({"username": "u", "password": "p"}) == \
        {"username": "u", "password": "p"}
    with pytest.raises(ValueError, match="unknown credentials key"):
        walk_policy.validate_credentials({"token": "x"})
    with pytest.raises(ValueError, match="non-empty"):
        walk_policy.validate_credentials({"username": "  "})
    nested = {"text": "signed in as walter", "tree": [{"value": "hunter2"}], "n": 3}
    red = walk_policy.redact(nested, ["walter", "hunter2"])
    assert red == {"text": "signed in as ***", "tree": [{"value": "***"}], "n": 3}


def test_denylist_matching_is_case_insensitive_across_languages():
    deny = walk_policy.resolve_denylist()
    assert walk_policy.match_denylist("Delete account", deny) == \
        {"category": "destructive", "term": "delete"}
    assert walk_policy.match_denylist("Konto unwiderruflich LÖSCHEN", deny)["category"] == "destructive"
    assert walk_policy.match_denylist("Jetzt ABONNIEREN", deny)["category"] == "payment"
    assert walk_policy.match_denylist("Open settings", deny) is None


def test_subject_url_scheme_hardening(store):
    # the stored subject.url lands in an href on the replay page — non-http(s) is rejected
    bad = {"kind": "live_url", "url": "javascript:alert(1)", "label": "evil"}
    step = {"index": 0, "action": {"type": "look", "target": "", "detail": ""},
            "monologue": "", "state": {"screen": "s"},
            "friction": {"level": "none", "note": ""},
            "verdict": {"would_continue": True, "reason": ""}}
    outcome = {"completed": True, "dropoff_step": None, "summary": "", "predicted_behaviors": []}
    with pytest.raises(ValueError, match="http"):
        services.record_usability_session("pX", bad, "live", "2026-06-10", [step], outcome, store=store)


def test_walk_open_requires_a_known_persona(store):
    with pytest.raises(KeyError, match="Unknown persona"):
        services.walk_open("http://127.0.0.1:1/x", "nobody", store=store)


def test_walk_open_unavailable_is_graceful(store):
    if browser.available():
        pytest.skip("playwright present; covered by the live tests")
    pid = create_persona(store, "Walli Walker")
    with pytest.raises(browser.HarnessError) as e:
        services.walk_open("http://127.0.0.1:1/x", pid, store=store)
    assert e.value.code == "PLAYWRIGHT_UNAVAILABLE"


# ------------------------------------------------------------------- live enforcement (chromium)

@pytest.mark.skipif(not browser.available(), reason="chromium not installed")
def test_walk_open_defaults_capture_per_step_screenshots(store, site, data_dir):
    pid = create_persona(store, "Selma Screenshot")
    out = services.walk_open(site, pid, store=store)
    sid = out["session_id"]
    try:
        assert out["fidelity"] == "live"
        assert out["policy"]["allowed_origins"] == [walk_policy.origin_of(site)]
        # the open snapshot already carries its screenshot (path relative to the sessions dir)
        shot = out["snapshot"]["screenshot"]
        assert shot == f"{sid}/step-0.png" and (config.sessions_dir() / shot).is_file()
        # every snapshot ticks the monotonic counter — read() included (one harness, every step)
        again = services.proto_read(sid)["snapshot"]
        assert again["screenshot"] == f"{sid}/step-1.png"
        assert (config.sessions_dir() / again["screenshot"]).is_file()
        # ... and the session log references both
        shots = [e.get("screenshot") for e in browser.session_log(sid) if e["kind"] == "snapshot"]
        assert shots == [f"{sid}/step-0.png", f"{sid}/step-1.png"]
    finally:
        services.proto_close(sid)


@pytest.mark.skipif(not browser.available(), reason="chromium not installed")
def test_off_origin_navigation_is_blocked_and_logged(store, site, data_dir):
    pid = create_persona(store, "Olga Origin")
    out = services.walk_open(site, pid, store=store)
    sid = out["session_id"]
    try:
        # `localhost` is the SAME server but a DIFFERENT origin than 127.0.0.1 — the link is a trap
        res = services.proto_act(sid, {"type": "click", "ref": _ref(out["snapshot"], "Partner portal")})
        snap = res["snapshot"]
        assert snap["policy_block"]["rule"] == "origin"
        assert "localhost" in snap["policy_block"]["detail"]
        assert snap["url"].startswith("http://127.0.0.1:")        # navigated back on-policy
        blocks = [e for e in browser.session_log(sid) if e.get("kind") == "policy_block"]
        assert blocks and blocks[0]["rule"] == "origin"           # the block itself is evidence
    finally:
        services.proto_close(sid)


@pytest.mark.skipif(not browser.available(), reason="chromium not installed")
def test_denylisted_click_is_refused_and_logged(store, site, data_dir):
    pid = create_persona(store, "Dora Deny")
    out = services.walk_open(site, pid, store=store)
    sid = out["session_id"]
    try:
        res = services.proto_act(sid, {"type": "click", "ref": _ref(out["snapshot"], "Delete account")})
        snap = res["snapshot"]
        assert snap["policy_block"]["rule"] == "blocked_action"
        assert snap["policy_block"]["category"] == "destructive"
        assert "ACCOUNT GONE" not in snap["text"]                 # the click never ran
        blocks = [e for e in browser.session_log(sid) if e.get("kind") == "policy_block"]
        assert blocks and blocks[0]["category"] == "destructive" and blocks[0]["term"] == "delete"
        # a safe click on the same page still works
        ok = services.proto_act(sid, {"type": "click", "ref": _ref(snap, "Open settings")})
        assert "settings opened" in ok["snapshot"]["text"]
    finally:
        services.proto_close(sid)


@pytest.mark.skipif(not browser.available(), reason="chromium not installed")
def test_caps_auto_close_and_later_acts_error_clearly(store, site, data_dir):
    pid = create_persona(store, "Carla Cap")
    out = services.walk_open(site, pid, policy={"max_actions": 1}, store=store)
    sid = out["session_id"]
    try:
        ok = services.proto_act(sid, {"type": "click", "ref": _ref(out["snapshot"], "Open settings")})
        assert "settings opened" in ok["snapshot"]["text"]
        # the second act trips the cap: structured auto-close, not a crash
        capped = services.proto_act(sid, {"type": "click", "ref": "e1"})["snapshot"]
        assert capped["closed"] is True and capped["cap_reached"]["cap"] == "max_actions"
        assert any(e.get("kind") == "cap_reached" and e["cap"] == "max_actions"
                   for e in browser.session_log(sid))
        # ... and every act/read after that is a clear, stable error
        with pytest.raises(browser.HarnessError) as e:
            services.proto_act(sid, {"type": "click", "ref": "e1"})
        assert e.value.code == "CAP_REACHED"
        with pytest.raises(browser.HarnessError):
            services.proto_read(sid)
    finally:
        services.proto_close(sid)


@pytest.mark.skipif(not browser.available(), reason="chromium not installed")
def test_credential_redaction_secrets_appear_nowhere(store, site, data_dir):
    pid = create_persona(store, "Greta Geheim")
    creds = {"username": "walter.fields", "password": "s3cr3t-hunter2"}
    out = services.walk_open(site, pid, credentials=creds, store=store)
    sid = out["session_id"]
    # the persona's derived profile declares rungs.login=false — credentials trigger the warning
    assert any("LOGIN_RUNG" in w for w in out["warnings"])
    snaps = [out["snapshot"]]
    try:
        # secrets are filled in-worker via the dedicated act — they never transit the host loop
        snaps.append(services.proto_act(sid, {"type": "fill_credential", "field": "username",
                                              "ref": _ref(out["snapshot"], "Username")})["snapshot"])
        snaps.append(services.proto_act(sid, {"type": "fill_credential", "field": "password",
                                              "ref": _ref(snaps[-1], "Password")})["snapshot"])
        # submitting echoes both secrets into the PAGE — the snapshot must come back redacted
        snaps.append(services.proto_act(sid, {"type": "click",
                                              "ref": _ref(snaps[-1], "Sign in")})["snapshot"])
        assert "signed in as *** / ***" in snaps[-1]["text"]
        # an unknown credential field is refused (credentials are supplied at open only)
        with pytest.raises(browser.HarnessError) as e:
            services.proto_act(sid, {"type": "fill_credential", "field": "otp", "ref": "e1"})
        assert e.value.code == "BAD_ACTION"
    finally:
        services.proto_close(sid)
    # NOWHERE: not in any returned snapshot, not in the retained session log ...
    everything = json.dumps(snaps) + json.dumps(browser.session_log(sid))
    assert "walter.fields" not in everything and "s3cr3t-hunter2" not in everything
    # ... and not in the recorded session JSON of the full live trace
    step = {"index": 0, "action": {"type": "click", "target": "Sign in", "detail": "signed in"},
            "monologue": "logging in with the test account",
            "state": {"screen": "signed in as ***", "title": "Acme Console"},
            "friction": {"level": "none", "note": ""},
            "verdict": {"would_continue": True, "reason": ""}}
    rec = services.record_usability_session(
        pid, {"kind": "live_url", "url": site, "label": "Acme Console"}, "live", "2026-06-10",
        [step], {"completed": True, "dropoff_step": None, "summary": "logged in",
                 "predicted_behaviors": []}, session_id=sid, store=store)
    assert rec["grounded_verified"] is True
    recorded = json.dumps(rec["usability_session"])
    assert "walter.fields" not in recorded and "s3cr3t-hunter2" not in recorded


@pytest.mark.skipif(not browser.available(), reason="chromium not installed")
def test_full_pipeline_walkthrough_to_replay_page(store, site, data_dir):
    pid = create_persona(store, "Pia Pipeline")
    out = services.walk_open(site, pid, store=store)
    sid = out["session_id"]
    snap0 = out["snapshot"]
    try:
        snap1 = services.proto_act(sid, {"type": "click",
                                         "ref": _ref(snap0, "Open settings")})["snapshot"]
    finally:
        services.proto_close(sid)
    # the host authors the dual timeline FROM the observed snapshots, citing the harness-written
    # screenshot paths (<browser_session_id>/step-<n>.png, relative to the sessions dir)
    steps = [
        {"index": 0, "action": {"type": "look", "target": "", "detail": "landed on the console"},
         "monologue": "okay, a workspace overview",
         "state": {"screen": "Welcome to the workspace overview", "url": snap0["url"],
                   "title": "Acme Console", "screenshot": snap0["screenshot"]},
         "friction": {"level": "none", "note": ""},
         "verdict": {"would_continue": True, "reason": ""}},
        {"index": 1, "action": {"type": "click", "target": "Open settings", "detail": ""},
         "monologue": "let's look at the settings",
         "state": {"screen": "settings opened", "url": snap1["url"],
                   "title": "Acme Console", "screenshot": snap1["screenshot"]},
         "friction": {"level": "none", "note": ""},
         "verdict": {"would_continue": True, "reason": ""}},
    ]
    rec = services.record_usability_session(
        pid, {"kind": "live_url", "url": site, "label": "Acme Console"}, "live", "2026-06-10",
        steps, {"completed": True, "dropoff_step": None, "summary": "walked the console",
                "predicted_behaviors": []}, session_id=sid, store=store)
    assert rec["grounded_verified"] is True
    usess = rec["usability_session"]
    # the replay view resolves the harness paths and serves them via /sessions-files/
    client = TestClient(web.create_app())
    html = client.get(f'/sessions/{usess["id"]}?lang=en').text
    assert f"/sessions-files/{sid}/step-0.png" in html
    assert f"/sessions-files/{sid}/step-1.png" in html
    assert client.get(f"/sessions-files/{sid}/step-0.png").status_code == 200
