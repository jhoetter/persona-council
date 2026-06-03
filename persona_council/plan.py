"""Research-plan engine (spec/research-plan-engine.md).

The orchestrator's SOURCE OF TRUTH for a project: a per-project DAG of tasks bucketed
analyze/act/verify, each bound to a capability and referencing the evidence it produced
(councils / syntheses / artifacts / sessions / frames). The methodology constellation seeds a
plan; a freeform project starts from a single `frame` task. Rendered to plan.md on demand.

Tag-driven, like the methodology engine: `bucket` and `capability` and evidence `kind` are OPEN
tags validated by reference — there is NO closed set in code. The host authors the plan + all text.
"""
from __future__ import annotations

from typing import Any

from .config import utc_now_iso
from .storage import Store


class PlanError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ------------------------------------------------------------------ normalization

def _ref(r: dict[str, Any]) -> dict[str, str]:
    """An EvidenceRef {kind, id} — kind is a free tag (council/synthesis/artifact/session/frame/…)."""
    return {"kind": str((r or {}).get("kind", "")), "id": str((r or {}).get("id", ""))}


def _norm_task(raw: dict[str, Any]) -> dict[str, Any]:
    requires = dict(raw.get("requires") or {})
    return {
        "id": raw.get("id"),
        "title": raw.get("title", raw.get("id") or ""),
        "intent": raw.get("intent", ""),
        "plan_note": raw.get("plan_note", ""),
        "bucket": raw.get("bucket", ""),            # analyze | act | verify (free tag)
        "capability": raw.get("capability", ""),    # frame | explore | cluster | decide | … (free tag)
        "step": raw.get("step", ""),                # optional grouping under a constellation step
        "consumes": [str(c) for c in (raw.get("consumes") or [])],
        "status": raw.get("status", "todo"),        # todo | active | done | blocked
        "produces": [_ref(r) for r in (raw.get("produces") or [])],
        "requires": {
            "min_inputs": int(requires["min_inputs"]) if requires.get("min_inputs") is not None else None,
            "gate_tag": requires.get("gate_tag", ""),
            "artifact_tags": list(requires.get("artifact_tags") or []),
            "session_of_tags": list(requires.get("session_of_tags") or []),
        },
        "loop_back": raw.get("loop_back", ""),
        "presentation": dict(raw.get("presentation") or {}),
    }


def _assert_acyclic(tasks: list[dict[str, Any]]) -> None:
    by_id = {t["id"]: t for t in tasks}
    state: dict[str, int] = {}

    def visit(tid: str) -> None:
        if state.get(tid) == 1:
            return
        if state.get(tid) == 0:
            raise PlanError("BAD_PLAN", f"`consumes` graph has a cycle at '{tid}'")
        state[tid] = 0
        for c in by_id[tid]["consumes"]:
            visit(c)
        state[tid] = 1

    for t in tasks:
        visit(t["id"])


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate + normalize a plan in place. Tag-agnostic: only graph mechanics + references."""
    if not isinstance(plan, dict):
        raise PlanError("BAD_PLAN", "plan must be an object")
    if not plan.get("project_id"):
        raise PlanError("BAD_PLAN", "plan needs a project_id")
    tasks = [_norm_task(t) for t in (plan.get("tasks") or [])]
    ids = [t["id"] for t in tasks]
    if not all(ids) or len(set(ids)) != len(ids):
        raise PlanError("BAD_PLAN", "task ids must be present and unique")
    idset = set(ids)
    for t in tasks:
        if not t["bucket"]:
            raise PlanError("BAD_PLAN", f"task '{t['id']}' needs a bucket tag")
        for c in t["consumes"]:
            if c not in idset:
                raise PlanError("BAD_PLAN", f"task '{t['id']}' consumes unknown task '{c}'")
            if c == t["id"]:
                raise PlanError("BAD_PLAN", f"task '{t['id']}' cannot consume itself")
        if t["loop_back"] and t["loop_back"] not in idset:
            raise PlanError("BAD_PLAN", f"task '{t['id']}' loop_back '{t['loop_back']}' is not a task")
    _assert_acyclic(tasks)
    plan["tasks"] = tasks
    return plan


# ------------------------------------------------------------------ lifecycle

def new_plan(project_id: str, goal: str = "", methodology: str = "",
             tasks: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    now = utc_now_iso()
    return validate_plan({"project_id": project_id, "goal": goal, "methodology": methodology,
                          "tasks": tasks or [], "created_at": now, "updated_at": now})


def seed_plan_from_methodology(project_id: str, goal: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Expand a methodology constellation into a seed plan: a `frame` (analyze) task per fan step
    and a `verify` task per decide step, wired along the step DAG and carrying the decide gates.
    The orchestrator fills the `act` lane (councils/artifacts/sessions consuming each frame) at run
    time. The first fan's frame is the root analyze task (dischargeable)."""
    from . import methodology as M
    steps = spec["steps"]
    fan_frame = {s["id"]: f"frame__{s['id']}" for s in steps if not M._is_decide(s)}
    decide_verify = {s["id"]: f"verify__{s['id']}" for s in steps if M._is_decide(s)}

    def map_target(step_id: str) -> str:
        return fan_frame.get(step_id) or decide_verify.get(step_id) or ""

    tasks: list[dict[str, Any]] = []
    for s in steps:
        sid = s["id"]
        cap = s["tags"][0] if s.get("tags") else ""
        if M._is_decide(s):
            cons = [fan_frame[c] for c in s["consumes"] if c in fan_frame]
            tasks.append({
                "id": decide_verify[sid], "title": f"Decide · {s['name']}", "bucket": "verify",
                "capability": cap or "decide", "step": sid, "intent": s["intent"], "consumes": cons,
                "requires": s["requires"], "loop_back": map_target(s.get("loop_back", "")),
                "produces": [], "presentation": s.get("presentation") or {}})
        else:
            cons = [decide_verify[c] for c in s["consumes"] if c in decide_verify]
            tasks.append({
                "id": fan_frame[sid], "title": f"Frame · {s['name']}", "bucket": "analyze",
                "capability": "frame", "step": sid, "consumes": cons,
                "intent": f"Frame the questions/angles for '{s['name']}' before acting — read persona "
                          f"memory + prior evidence; do not conclude early. {s['intent']}",
                "produces": [], "presentation": s.get("presentation") or {}})
    return new_plan(project_id, goal, spec["key"], tasks)


def get_plan(project_id: str, store: Store | None = None) -> dict[str, Any] | None:
    store = store or Store()
    p = store.get_research_plan(project_id)
    return validate_plan(p) if p else None


def save_plan(plan: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    validate_plan(plan)
    plan.setdefault("created_at", utc_now_iso())
    plan["updated_at"] = utc_now_iso()
    store.upsert_research_plan(plan)
    return plan


def task(plan: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    return next((t for t in plan["tasks"] if t["id"] == task_id), None)


def ready_tasks(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """The frontier: tasks whose `consumes` are all done and which are not themselves done."""
    done = {t["id"] for t in plan["tasks"] if t["status"] == "done"}
    return [t for t in plan["tasks"]
            if t["status"] != "done" and all(c in done for c in t["consumes"])]


def is_complete(plan: dict[str, Any]) -> bool:
    return all(t["status"] == "done" for t in plan["tasks"]) and bool(plan["tasks"])


# ------------------------------------------------------------------ plan.md render

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
