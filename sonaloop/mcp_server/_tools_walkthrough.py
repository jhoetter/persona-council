from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_walkthrough(mcp):
    # ================= Live walkthroughs — rung 3: policy-guarded real-SaaS sessions =================
    # The SAME harness as proto_* (one session registry): walk_open starts the session under a
    # WalkPolicy, then proto_act / proto_read / proto_close drive and end it transparently, and
    # record_usability_session(fidelity='live', session_id=…) persists the verified, replayable
    # trace. The safety contract lives in docs/live-walkthrough-safety.md.
    @mcp.tool()
    def walk_policy_defaults() -> dict[str, Any]:
        """The safe default WalkPolicy walk_open applies when none is passed — origin-locked to the
        opening URL, ALL denylist categories enabled (payment/destructive/outbound/account, EN+DE;
        data-driven from suggestions/walk_denylist.json), max_actions=60 / max_duration_s=900 —
        including the RESOLVED denylist terms, so you see exactly what would be enforced before
        opening anything. Tweak per category/cap via walk_open(policy={…})."""
        t = time.perf_counter()
        return _env("walk_policy_defaults", services.walk_policy_defaults(), t)

    @mcp.tool()
    def walk_open(url: str, persona_id: str, policy: dict[str, Any] | None = None,
                  credentials: dict[str, str] | None = None,
                  project_id: str | None = None) -> dict[str, Any]:
        """Open a LIVE walkthrough session on a real SaaS URL under the WalkPolicy safety contract
        (docs/live-walkthrough-safety.md): origin allowlist (off-origin navigations are blocked +
        logged), deny-by-default action denylist (no payments/deletes/outbound — refusals come back
        structured in the act result, never as crashes), hard caps (auto-close), per-step
        screenshots, credential redaction. `policy` is a patch over walk_policy_defaults
        ({allowed_origins?, blocked_categories?, max_actions?, max_duration_s?}; defaults to the
        URL's own origin, all categories, 60 actions / 900 s); `credentials` {username?, password?}
        are filled via proto_act {type:'fill_credential', field, ref} and NEVER appear in retained
        output. Returns {session_id, snapshot (with screenshot path), policy, warnings?} — drive
        with proto_act/proto_read, close with proto_close, then
        record_usability_session(fidelity='live', session_id=…)."""
        t = time.perf_counter()
        return _env("walk_open",
                    services.walk_open(url, persona_id, policy, credentials, project_id), t)

    @mcp.tool()
    def walk_own(persona_id: str, prototype_id: str | None = None, url: str | None = None,
                 policy: dict[str, Any] | None = None, project_id: str | None = None) -> dict[str, Any]:
        """Rung 2 — drive a live surface WE OWN: pass `prototype_id` (the scaffolded app is
        started on localhost) or a loopback/declared-staging `url` (SONALOOP_OWNED_ORIGINS).
        Tighter caps than walk_open; anything not owned is refused (that's rung 3). Fail-soft:
        without the browser harness you get a structured fallback to the artifact walkthrough."""
        t = time.perf_counter()
        return _env("walk_own", services.walk_own(persona_id, prototype_id, url, policy, project_id), t)

    @mcp.tool()
    def record_actuation_gate(project_id: str, artifact_session_id: str, live_session_id: str,
                              note: str = "") -> dict[str, Any]:
        """The fidelity-vs-theater head-to-head: compare a rung-1 artifact walkthrough against a
        rung-2 live drive of the SAME flow on derived evidence-quality dimensions; the verdict is
        mechanical and persists as an eval_report. Rung 2 earns default status only by winning."""
        t = time.perf_counter()
        return _env("record_actuation_gate",
                    services.record_actuation_gate(project_id, artifact_session_id, live_session_id, note), t)

