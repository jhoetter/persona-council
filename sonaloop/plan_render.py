"""plan.md rendering (split out of plan.py to keep modules under the LOC bar; pure leaf)."""
from __future__ import annotations

from typing import Any


_STATUS_MARK = {"done": "x", "active": "~", "todo": " ", "blocked": "!"}


def _gate_summary(t: dict[str, Any]) -> str:
    r = t["requires"]
    parts = []
    if r["min_inputs"] is not None:
        parts.append(f"min_inputs={r['min_inputs']}")
    if r["gate_tag"]:
        parts.append(f"gate={r['gate_tag']}")
    if r["artifact_tags"]:
        parts.append(f"artifacts={','.join(r['artifact_tags'])}")
    if r["session_of_tags"]:
        parts.append(f"sessions={','.join(r['session_of_tags'])}")
    return ("; gates: " + " · ".join(parts)) if parts else ""


def render_plan_md(plan: dict[str, Any]) -> str:
    from .plan import ready_tasks
    """Render the plan as a human-readable, bucketed plan.md (bim-agent json→md style)."""
    tasks = plan["tasks"]
    ready = {t["id"] for t in ready_tasks(plan)}
    head = [
        f"# Research plan — {plan.get('goal', '') or plan['project_id']}",
        "",
        f"Methodology: {plan.get('methodology') or 'freeform'} · "
        f"Tasks: {len(tasks)} · Updated: {plan.get('updated_at', '')}",
        "",
    ]
    # Next (ready frontier)
    nxt = [t for t in tasks if t["id"] in ready]
    head.append("## Next (ready)")
    if nxt:
        for t in nxt:
            head.append(f"- **{t['id']}** [{t['bucket']}/{t['capability'] or '—'}] {t['title']} — {t['status']}")
    else:
        head.append("- _(none — plan complete or blocked)_" if tasks else "- _(no tasks yet)_")
    head.append("")
    # Buckets in analyze → act → verify order, then any others
    order = ["analyze", "act", "verify"]
    buckets = order + sorted({t["bucket"] for t in tasks} - set(order))
    for b in buckets:
        rows = [t for t in tasks if t["bucket"] == b]
        if not rows:
            continue
        head.append(f"## {b.capitalize()}")
        for t in rows:
            mark = _STATUS_MARK.get(t["status"], " ")
            ev = ", ".join(f"{r['kind']}:{r['id']}" for r in t["produces"] if r["id"]) or "—"
            cons = (" ⊂ " + ", ".join(t["consumes"])) if t["consumes"] else ""
            head.append(f"- [{mark}] **{t['id']}** ({t['capability'] or '—'}) {t['title']} — "
                        f"`{t['status']}`{cons}{_gate_summary(t)}")
            head.append(f"    evidence: {ev}")
            if t["plan_note"]:
                head.append(f"    note: {t['plan_note']}")
        head.append("")
    return "\n".join(head).rstrip() + "\n"
