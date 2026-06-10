"""Selective live actuation — rung 2 of the capability ladder
(ticket selective-live-actuation): personas driving LIVE surfaces WE OWN.

Rung 3 (walk_open) points the policy-guarded browser at any real URL. Rung 2
is the bounded middle: the SAME harness locked to OWNED surfaces only —
scaffolded prototypes and explicitly declared staging origins — with tighter
caps, so actuation depth grows on ground we control before it touches the
open web. The unreliability never leaks into core flows: the browser stays a
fail-soft optional (no Playwright → a structured fallback pointing at the
artifact walkthrough, never a crash).

The "fidelity vs theater" question gets an answer, not a vibe:
`record_actuation_gate` compares a rung-1 artifact walkthrough against a
rung-2 live drive of the SAME flow on derived evidence-quality dimensions
(verified states, trace density, friction granularity, …) and persists the
verdict — the recorded head-to-head the ticket requires before rung 2 can
become a default."""

from __future__ import annotations

import os
from typing import Any

from ..config import utc_now_iso
from ..storage import Store
from .. import walk_policy as _wp
from .. import browser as _browser

from ._common import *  # noqa: F401,F403  (stable_id, _require_research_project, …)


# Owned surfaces get TIGHTER caps than the open-web walkthrough defaults — a
# prototype/staging drive that needs more than this is a smell, not a need.
OWNED_MAX_ACTIONS = 40
OWNED_MAX_DURATION_S = 300

_LOCAL_ORIGINS = ("http://localhost", "http://127.0.0.1", "https://localhost", "https://127.0.0.1")


def owned_origins() -> list[str]:
    """The origins rung 2 may touch: loopback always; staging origins only when
    EXPLICITLY declared via SONALOOP_OWNED_ORIGINS (comma-separated) — the opt-in."""
    extra = [o.strip() for o in os.getenv("SONALOOP_OWNED_ORIGINS", "").split(",") if o.strip()]
    return list(_LOCAL_ORIGINS) + [_wp.origin_of(o) for o in extra]


def _is_owned(url: str) -> bool:
    origin = _wp.origin_of(url)
    return any(origin == o or origin.startswith(o + ":") for o in owned_origins())


def walk_own(persona_id: str, prototype_id: str | None = None, url: str | None = None,
             policy: dict[str, Any] | None = None, project_id: str | None = None,
             store: Store | None = None) -> dict[str, Any]:
    """Open a policy-guarded live session on an OWNED surface (rung 2). Pass EITHER
    `prototype_id` (the scaffolded app is started and driven on localhost) OR `url`
    (loopback, or a staging origin declared in SONALOOP_OWNED_ORIGINS — anything
    else is refused: that's rung 3, use walk_open deliberately). Caps are clamped
    to the owned-surface maxima. Fail-soft: without the browser harness this
    returns a structured fallback pointing at the artifact walkthrough."""
    store = store or Store()
    if bool(prototype_id) == bool(url):
        raise ValueError("Pass exactly one of `prototype_id` or `url`.")
    if not _browser.available():
        return {"ok": False, "unavailable": True, "rung": "owned",
                "fallback": "browser harness not installed (`sonaloop setup`) — use the artifact "
                            "rung instead: define_flow + brief_flow_walkthrough need no browser, "
                            "and every core flow works without one."}
    if prototype_id:
        run = run_prototype(prototype_id, store=store)  # noqa: F821 (bound)
        url = run["url"]
    if not _is_owned(url):
        raise ValueError(
            f"{_wp.origin_of(url)} is not an OWNED surface — rung 2 drives only loopback and the "
            "origins declared in SONALOOP_OWNED_ORIGINS. For a real third-party URL use walk_open "
            "(rung 3) deliberately, under its own policy.")
    merged = dict(policy or {})
    merged["allowed_origins"] = [_wp.origin_of(url)]    # owned surface = exactly this origin
    merged["max_actions"] = min(int(merged.get("max_actions", OWNED_MAX_ACTIONS)), OWNED_MAX_ACTIONS)
    merged["max_duration_s"] = min(int(merged.get("max_duration_s", OWNED_MAX_DURATION_S)),
                                   OWNED_MAX_DURATION_S)
    out = walk_open(url, persona_id, policy=merged, project_id=project_id, store=store)  # noqa: F821 (bound)
    out["rung"] = "owned"
    if prototype_id:
        out["prototype_id"] = prototype_id
    return out


# ----------------------------------------------------- the evidence-quality gate

def _session_evidence(sess: dict[str, Any]) -> dict[str, Any]:
    """Derived evidence-quality metrics for one usability session — counts only,
    no judgment; the gate's verdict follows mechanically."""
    steps = sess.get("steps") or []
    monologue = sum(len(s.get("monologue") or "") for s in steps)
    return {
        "session_id": sess.get("id"), "fidelity": sess.get("fidelity"),
        "steps": len(steps),
        "verified": bool(sess.get("grounded_verified")),
        "screenshots": sum(1 for s in steps if (s.get("state") or {}).get("screenshot")),
        "friction_levels": len({(s.get("friction") or {}).get("level") for s in steps} - {None}),
        "monologue_chars_per_step": round(monologue / len(steps), 1) if steps else 0.0,
        "statements": len(sess.get("statements") or []),
        "predicted_behaviors": len((sess.get("outcome") or {}).get("predicted_behaviors") or []),
    }


_GATE_DIMENSIONS = ("steps", "verified", "screenshots", "friction_levels",
                    "monologue_chars_per_step", "statements", "predicted_behaviors")


def record_actuation_gate(project_id: str, artifact_session_id: str, live_session_id: str,
                          note: str = "", store: Store | None = None) -> dict[str, Any]:
    """The recorded head-to-head: rung-1 artifact walkthrough vs rung-2 live drive of
    the same flow, compared on derived evidence-quality dimensions. The winner per
    dimension and overall follow from the numbers; the host's reading goes in `note`.
    Persists an eval_report (kind='actuation_gate') — the audit record the ticket
    requires before rung 2 may become a default."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # noqa: F821 (bound)
    sessions = {}
    for label, sid in (("artifact", artifact_session_id), ("live", live_session_id)):
        sess = store.get_usability_session(sid)
        if not sess:
            raise KeyError(f"Unknown usability session ({label}): {sid}")
        sessions[label] = sess
    art, live = _session_evidence(sessions["artifact"]), _session_evidence(sessions["live"])
    wins = {"artifact": [], "live": [], "tie": []}
    for dim in _GATE_DIMENSIONS:
        a, l = art[dim], live[dim]
        a, l = (int(a), int(l)) if isinstance(a, bool) else (a, l)
        wins["live" if l > a else "artifact" if a > l else "tie"].append(dim)
    winner = ("live" if len(wins["live"]) > len(wins["artifact"])
              else "artifact" if len(wins["artifact"]) > len(wins["live"]) else "inconclusive")
    subjects = {label: (s.get("subject") or {}).get("label", "") for label, s in sessions.items()}
    now = utc_now_iso()
    report = {
        "id": stable_id("evalrep", "actuation_gate", project["id"], now),  # noqa: F821 (bound)
        "kind": "actuation_gate", "scope": project["id"],
        "persona_id": None, "period_start": None, "period_end": None,
        "subjects": subjects,
        "same_subject": len(set(subjects.values())) == 1,
        "evidence": {"artifact": art, "live": live},
        "wins": wins, "winner": winner,
        "green": winner == "live",       # rung 2 earns default status only by WINNING
        "note": str(note or ""), "created_at": now,
    }
    store.insert_eval_report(report)
    store.commit()
    return report
