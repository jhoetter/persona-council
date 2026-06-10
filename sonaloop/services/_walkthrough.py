"""Live SaaS walkthroughs — rung 3 of the Deep Persona ladder (ticket live-saas-walkthrough).

"Here's a URL and a test login — go use it." The SAME Playwright harness as prototype sessions,
but opened under a WalkPolicy (walk_policy.py; docs/live-walkthrough-safety.md): origin allowlist,
deny-by-default action denylist, hard caps, credential redaction. walk_open returns a normal
browser session — proto_act / proto_read / proto_close drive and end it transparently, and
record_usability_session(fidelity='live', session_id=…) persists the verified trace.
Cross-module function references are bound at import time by services/__init__.py."""

from __future__ import annotations

from typing import Any

from .. import browser as _browser
from .. import walk_policy as _wp
from ..storage import Store
from ._common import _require_persona


def walk_policy_defaults():
    """The safe default WalkPolicy walk_open applies when none is passed, WITH the resolved
    denylist (suggestions/walk_denylist.json) — hosts see exactly what would be enforced before
    opening anything."""
    return _wp.policy_defaults()


def walk_open(url, persona_id, policy=None, credentials=None, project_id=None,
              store: Store | None = None):
    """Open a policy-guarded LIVE walkthrough session on a real URL. The host-supplied `policy`
    patch normalizes over the safe defaults (allowed_origins defaults to the opening URL's origin;
    non-http(s) URLs are rejected outright); optional `credentials` {username?, password?} stay
    inside the harness worker — filled via {type:'fill_credential'}, redacted from every retained
    snapshot/log entry, never logged at open. The envelope carries the persona's capability
    warnings (fidelity 'live'; the login rung when credentials ride along) — warn, never block."""
    store = store or Store()
    norm = _wp.normalize_policy(policy, url)          # also rejects non-http(s) opening URLs
    creds = _wp.validate_credentials(credentials)
    persona = _require_persona(store, persona_id)
    profile = capability_profile(persona)             # noqa: F821 (bound) — declared, else derived
    subject_text = url + (" login credentials" if creds else "")
    warnings = capability_fidelity_warnings(profile, "live", subject_text)   # noqa: F821 (bound)
    opened = _browser.open_session(url, prototype_id=None, persona_id=persona_id,
                                   policy=norm, credentials=creds)
    out: dict[str, Any] = {"session_id": opened["session_id"], "snapshot": opened["snapshot"],
                           "fidelity": "live", "policy": norm}
    if project_id:
        out["project_id"] = project_id
    if warnings:
        out["warnings"] = warnings
    return out
