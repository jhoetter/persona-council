from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_decisions(mcp):
    # ===== Decision records — what we decided, on which evidence, rejecting what =====
    # ADR-style nodes that close the research loop: syntheses end in recommendations; a
    # DecisionRecord captures the moment a human ACTS on one. record_decision validates
    # (at least one based_on Ref that RESOLVES — decisions must cite evidence) + persists;
    # update_decision flips the status; superseding links BOTH directions (superseded_by on the
    # old record, supersedes on the successor). The server never writes text.
    @mcp.tool()
    def record_decision(project_id: str, title: str, decision: str,
                        based_on: list[dict[str, Any]],
                        rejected: list[dict[str, Any]] | None = None,
                        status: str = "proposed", key: str | None = None) -> dict[str, Any]:
        """Persist a host-authored decision record — "we decided X, based on syntheses A and B,
        rejecting alternative C". `based_on` = Refs to the evidence it rests on ({kind:
        synthesis|council|hypothesis|survey|session, id, anchor?, role?}); at least ONE must
        RESOLVE — a decision without evidence is REJECTED. `rejected` = the alternatives
        considered (same Ref shape, each may carry a why-not `note`); those refs must resolve
        too. status: proposed|adopted (superseded only exists via update_decision's supersede
        flow). A stable `key` gives a deterministic id (idempotent upsert)."""
        t = time.perf_counter()
        return _env("record_decision",
                    services.record_decision(project_id, title, decision, based_on, rejected,
                                             status, key), t)

    @mcp.tool()
    def update_decision(decision_id: str, status: str | None = None,
                        superseded_by: str | None = None) -> dict[str, Any]:
        """Flip a decision's status (proposed|adopted) — or supersede it: `superseded_by` names
        the SUCCESSOR decision and records the link in BOTH directions (this record is demoted
        to status=superseded and points forward via `superseded_by`; the successor points back
        via `supersedes`). A superseded record cannot be flipped back — record a new decision."""
        t = time.perf_counter()
        return _env("update_decision",
                    services.update_decision(decision_id, status, superseded_by), t)

    @mcp.tool()
    def get_decision(decision_id: str) -> dict[str, Any]:
        """One decision record by id — what was decided, the evidence cited (based_on), the
        rejected alternatives (+ why-not notes), and the supersede links (both directions)."""
        t = time.perf_counter()
        return _env("get_decision", services.get_decision(decision_id), t)

    @mcp.tool()
    def list_decisions(project_id: str | None = None, status: str | None = None) -> dict[str, Any]:
        """List decision records (optionally per project and/or status:
        proposed|adopted|superseded)."""
        t = time.perf_counter()
        return _env("list_decisions", {"decisions": services.list_decisions(project_id, status)}, t)
