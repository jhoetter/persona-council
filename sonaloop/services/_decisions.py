"""Decision records — what we decided, on which evidence, rejecting what.

Syntheses end in recommendations; a DecisionRecord captures the moment a human ACTS on one — the
ADR-style node that closes the research loop ("we decided X, based on syntheses A and B, rejecting
alternative C") so the graph can answer "why does the product look like this?" months later.
Host-authors-all-text: record_decision only VALIDATES + persists — at least one based_on Ref must
RESOLVE (decisions must cite evidence, that is the point), and every rejected Ref (an alternative
considered, optionally with a why-not `note`) must resolve too. update_decision flips the status
(proposed|adopted|superseded); superseding records BOTH directions — the old record is demoted to
superseded and points forward via `superseded_by`, the successor points back via `supersedes`.
Cross-module function references are bound at import time by services/__init__.py."""

from __future__ import annotations

from typing import Any

from .. import artifacts as _A
from ..config import utc_now_iso
from ..models import DecisionRecord
from ..storage import Store
from ._common import _require_research_project, stable_id


_DECISION_STATUSES = ("proposed", "adopted", "superseded")


def _require_decision(store: Store, decision_id: str) -> dict[str, Any]:
    dec = store.get_decision(decision_id)
    if not dec:
        raise KeyError(f"Unknown decision: {decision_id}")
    return dec


# --------------------------------------------------------------------------- validation

def _validate_evidence_refs(refs: Any, field: str, default_role: str, store: Store,
                            with_note: bool = False) -> list[dict[str, Any]]:
    """Every Ref must RESOLVE — a decision may only cite evidence (and name alternatives) that
    exists in the graph: syntheses / findings (via anchors) / hypotheses / councils / surveys /
    sessions, live through artifacts.resolve_ref. `with_note` keeps the per-ref why-not `note`
    (rejected alternatives carry the reason they lost)."""
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(refs or []):
        if not isinstance(raw, dict):
            raise ValueError(f"{field}[{i}] must be a Ref dict {{kind, id, anchor?, role?}}")
        r = _A.validate_ref(raw)
        r.setdefault("role", default_role)
        if not r.get("id"):
            raise ValueError(f"{field}[{i}] needs an id (the artifact it cites)")
        res = _A.resolve_ref(r, store)
        if not res.get("exists"):
            anchor = f"#{r['anchor']}" if r.get("anchor") else ""
            raise ValueError(f"{field}[{i}] does not resolve: {r.get('kind')}:{r['id']}{anchor}")
        if with_note and str(raw.get("note") or "").strip():
            r["note"] = str(raw["note"]).strip()
        out.append(r)
    return out


# --------------------------------------------------------------------------- record / update

def record_decision(project_id: str, title: str, decision: str, based_on: list,
                    rejected: list | None = None, status: str = "proposed",
                    key: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Persist a host-authored decision record. Validates: title + decision text present, status
    proposed|adopted (superseded only exists via the supersede flow — a decision is superseded BY
    another decision, never born that way), at least one based_on Ref that RESOLVES (decisions
    must cite evidence), and every rejected Ref resolves (each may carry a why-not `note`). A
    stable `key` gives a deterministic id (idempotent upsert → resumable runs); a SUPERSEDED
    record cannot be re-authored — the audit trail stays intact."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    # Collapsed to one line — the title is a heading everywhere it lands (web pill row, markdown
    # exports), and interior newlines would let it forge structure in the exported documents.
    title = " ".join(str(title or "").split())
    if not title:
        raise ValueError("title is required")
    decision = str(decision or "").strip()
    if not decision:
        raise ValueError("decision is required (what was decided)")
    if status not in ("proposed", "adopted"):
        raise ValueError(f"status must be proposed|adopted at record time (superseded only via "
                         f"update_decision's supersede flow), got {status!r}")
    refs = _validate_evidence_refs(based_on, "based_on", "based_on", store)
    if not refs:
        raise ValueError("based_on needs at least one resolvable ref — a decision must cite the "
                         "evidence it rests on (syntheses / findings / hypotheses)")
    rej = _validate_evidence_refs(rejected, "rejected", "rejected", store, with_note=True)
    now = utc_now_iso()
    # Project-scoped key hash — a key-only hash would let one project's record_decision silently
    # hijack and re-author another project's record on key collision (same fix as hypotheses).
    did = stable_id("dec", project["id"], key) if key else stable_id("dec", project["id"], title, now)
    existing = store.get_decision(did)
    if existing and existing.get("status") == "superseded":
        raise ValueError(f"decision {did} is superseded — a superseded record cannot be "
                         "re-authored; record a new decision")
    rec = DecisionRecord(id=did, project_id=project["id"], title=title, decision=decision,
                         status=status, based_on=refs, rejected=rej,
                         superseded_by=(existing or {}).get("superseded_by"),
                         supersedes=(existing or {}).get("supersedes"),
                         created_at=(existing or {}).get("created_at", now),
                         updated_at=now).to_dict()
    store.upsert_decision(rec)
    return {"decision": rec}


def update_decision(decision_id: str, status: str | None = None,
                    superseded_by: str | None = None,
                    store: Store | None = None) -> dict[str, Any]:
    """Flip a decision's status (proposed|adopted) — or supersede it: `superseded_by` names the
    SUCCESSOR decision and records the link in BOTH directions (this record is demoted to
    status=superseded and points forward via `superseded_by`; the successor points back via
    `supersedes`). A superseded record cannot be flipped back — record a new decision instead."""
    store = store or Store()
    dec = _require_decision(store, decision_id)
    if not status and not superseded_by:
        raise ValueError("nothing to update — pass status and/or superseded_by")
    if dec.get("status") == "superseded":
        raise ValueError(f"decision {decision_id} is already superseded by "
                         f"{dec.get('superseded_by')} — the link is the audit trail; "
                         "record a new decision instead")
    now = utc_now_iso()
    successor = None
    if superseded_by:
        if status and status != "superseded":
            raise ValueError(f"superseded_by demotes this record to superseded — it cannot also "
                             f"flip to {status!r}")
        successor = _require_decision(store, superseded_by)
        if successor["id"] == dec["id"]:
            raise ValueError("a decision cannot supersede itself")
        if successor.get("project_id") != dec.get("project_id"):
            raise ValueError("the superseding decision must belong to the same project")
        if successor.get("status") == "superseded":
            # Also closes the A→B→A cycle: once A is superseded it can never adopt a successor role.
            raise ValueError(f"decision {successor['id']} is itself superseded — a retired record "
                             "cannot supersede a live one; point at its successor instead")
        if successor.get("supersedes") and successor["supersedes"] != dec["id"]:
            raise ValueError(f"decision {successor['id']} already supersedes "
                             f"{successor['supersedes']} — one record supersedes one predecessor; "
                             "chain decisions instead of fanning in")
        dec["status"] = "superseded"
        dec["superseded_by"] = successor["id"]
        successor["supersedes"] = dec["id"]                 # both directions recorded
        successor["updated_at"] = now
        store.upsert_decision(successor)
    else:
        if status not in _DECISION_STATUSES:
            raise ValueError(f"status must be one of {'|'.join(_DECISION_STATUSES)}, got {status!r}")
        if status == "superseded":
            raise ValueError("superseding needs the successor — pass superseded_by=<decision id> "
                             "so the link is recorded in both directions")
        dec["status"] = status
    dec["updated_at"] = now
    store.upsert_decision(dec)
    out: dict[str, Any] = {"decision": dec}
    if successor:
        out["successor"] = successor
    return out


def get_decision(decision_id: str, store: Store | None = None) -> dict[str, Any]:
    """One decision record by id — what was decided, the evidence cited, the rejected
    alternatives, and the supersede links (both directions)."""
    store = store or Store()
    return _require_decision(store, decision_id)


def list_decisions(project_id: str | None = None, status: str | None = None,
                   store: Store | None = None) -> list[dict[str, Any]]:
    """List decision records (optionally per project and/or status: proposed|adopted|superseded)."""
    store = store or Store()
    if status and status not in _DECISION_STATUSES:
        raise ValueError(f"status must be one of {'|'.join(_DECISION_STATUSES)}, got {status!r}")
    return store.list_decisions(project_id, status)


# --------------------------------------------------------------------------- export (plan / report)

def _ref_cite(r: dict[str, Any], store: Store) -> str:
    """'Title (kind:id#anchor)' — the live-resolved citation line for an export."""
    res = _A.resolve_ref(r, store)
    addr = _A.part_address(r.get("kind", ""), r.get("id", ""), r.get("anchor"))
    title = res.get("title") or r.get("id", "")
    return f"{title} ({addr})"


def decisions_section_md(project_id: str, store: Store | None = None, de: bool = False) -> str:
    """The "Decisions" markdown block for the plan/report exports — every decision with its
    status, the cited evidence, the rejected alternatives (+ why-not notes) and the supersede
    links. Empty string when the project has no decisions (no empty chrome)."""
    store = store or Store()
    decs = store.list_decisions(project_id)
    if not decs:
        return ""
    by_id = {d["id"]: d for d in decs}
    lines = [f"## {'Entscheidungen' if de else 'Decisions'}", ""]
    # Host text is flattened to one line each — interior newlines in a title/body/note would
    # forge document structure (headings, status bullets) in this audit-trail section.
    flat = lambda s: " ".join(str(s or "").split())  # noqa: E731
    for d in decs:
        lines.append(f"- **{flat(d.get('title'))}** — `{d.get('status', '')}`")
        if d.get("decision"):
            lines.append(f"  {flat(d['decision'])}")
        if d.get("based_on"):
            cites = "; ".join(_ref_cite(r, store) for r in d["based_on"])
            lines.append(f"  - {'basiert auf' if de else 'based on'}: {cites}")
        for r in d.get("rejected") or []:
            note = f" — {flat(r['note'])}" if r.get("note") else ""
            lines.append(f"  - {'verworfen' if de else 'rejected'}: {_ref_cite(r, store)}{note}")
        if d.get("superseded_by"):
            succ = by_id.get(d["superseded_by"]) or store.get_decision(d["superseded_by"]) or {}
            lines.append(f"  - {'abgelöst durch' if de else 'superseded by'}: "
                         f"{succ.get('title', d['superseded_by'])} (decision:{d['superseded_by']})")
    return "\n".join(lines) + "\n"
