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
        "frame": dict(raw["frame"]) if raw.get("frame") else None,   # analyze output (questions/hypotheses)
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


# ------------------------------------------------------------------ mutations

def add_task(project_id: str, bucket: str, capability: str, title: str, intent: str = "",
             consumes: list[str] | None = None, requires: dict | None = None, step: str = "",
             plan_note: str = "", task_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Insert a task into the plan (the orchestrator shaping the breadth — e.g. another act council,
    an extra analyze, a mid-stream synthesis). Returns the created task."""
    store = store or Store()
    plan = get_plan(project_id, store=store)
    if plan is None:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    tid = task_id or _fresh_id(plan, f"{bucket}__{capability or 'task'}")
    raw = {"id": tid, "title": title, "bucket": bucket, "capability": capability, "intent": intent,
           "step": step, "consumes": consumes or [], "requires": requires or {}, "plan_note": plan_note}
    plan["tasks"].append(_norm_task(raw))
    save_plan(plan, store=store)
    return task(plan, tid)


def _fresh_id(plan: dict[str, Any], base: str) -> str:
    existing = {t["id"] for t in plan["tasks"]}
    if base not in existing:
        return base
    i = 2
    while f"{base}_{i}" in existing:
        i += 1
    return f"{base}_{i}"


def record_frame(project_id: str, task_id: str, questions: list[str], hypotheses: list[str] | None = None,
                 memory_refs: list[str] | None = None, store: Store | None = None) -> dict[str, Any]:
    """Discharge an `analyze` frame task: author research questions + hypotheses grounded in cited
    persona memory / prior evidence. Default-but-discharge­able: must cite >=1 memory ref and >=1
    question (can't be silently skipped), but a minimal honest frame discharges it."""
    store = store or Store()
    plan = get_plan(project_id, store=store)
    if plan is None:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    t = task(plan, task_id)
    if not t:
        raise PlanError("BAD_FRAME", f"unknown task '{task_id}'")
    if t["bucket"] != "analyze":
        raise PlanError("BAD_FRAME", f"record_frame targets an analyze task (got bucket '{t['bucket']}')")
    qs = [str(q).strip() for q in (questions or []) if str(q).strip()]
    refs = [str(r).strip() for r in (memory_refs or []) if str(r).strip()]
    if not qs:
        raise PlanError("BAD_FRAME", "a frame needs >= 1 research question")
    if not refs:
        raise PlanError("BAD_FRAME", "a frame must cite >= 1 memory ref (persona memory / prior evidence)")
    t["frame"] = {"questions": qs, "hypotheses": [str(h).strip() for h in (hypotheses or []) if str(h).strip()],
                  "memory_refs": refs}
    t["produces"] = [{"kind": "frame", "id": task_id}]
    t["status"] = "done"
    save_plan(plan, store=store)
    return t


# ------------------------------------------------------------------ evidence, judgments, gates

def link_evidence(project_id: str, task_id: str, ref: dict[str, Any],
                  store: Store | None = None) -> dict[str, Any]:
    """Attach an evidence ref {kind,id} (council/artifact/session/synthesis) to a task (usually an
    act task whose run-council/scaffold/session just produced it)."""
    store = store or Store()
    plan = get_plan(project_id, store=store)
    if plan is None:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    t = task(plan, task_id)
    if not t:
        raise PlanError("BAD_LINK", f"unknown task '{task_id}'")
    r = _ref(ref)
    if not r["id"] or not r["kind"]:
        raise PlanError("BAD_LINK", "evidence ref needs a kind and an id")
    if r not in t["produces"]:
        t["produces"].append(r)
    save_plan(plan, store=store)
    return t


def record_judgment(project_id: str, task_id: str, gate_tag: str, decided: bool, rationale: str,
                    evidence_refs: list[str] | None = None, store: Store | None = None) -> dict[str, Any]:
    """Record an evidence-backed gate judgment against a task (the fan or the verify). gate_tag is a
    FREE tag; a decided judgment needs a rationale + >=1 evidence_ref."""
    store = store or Store()
    plan = get_plan(project_id, store=store)
    if plan is None:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    if task(plan, task_id) is None:
        raise PlanError("BAD_JUDGMENT", f"unknown task '{task_id}'")
    if not (gate_tag or "").strip():
        raise PlanError("BAD_JUDGMENT", "a judgment needs a gate_tag")
    refs = [str(r) for r in (evidence_refs or []) if str(r).strip()]
    if decided and not rationale.strip():
        raise PlanError("BAD_JUDGMENT", "a decided judgment needs a rationale")
    if decided and not refs:
        raise PlanError("BAD_JUDGMENT", "a decided gate judgment needs >= 1 evidence_ref")
    j = {"task_id": task_id, "gate_tag": gate_tag, "decided": bool(decided),
         "rationale": rationale.strip(), "evidence_refs": refs, "created_at": utc_now_iso()}
    plan.setdefault("judgments", []).append(j)
    save_plan(plan, store=store)
    return j


def _fan_tasks(plan: dict[str, Any], vtask: dict[str, Any]) -> list[dict[str, Any]]:
    """The act 'fan' a verify task consolidates: sibling tasks sharing one of its consumed frames."""
    frames = set(vtask["consumes"])
    return [t for t in plan["tasks"]
            if t["id"] != vtask["id"] and (set(t["consumes"]) & frames) and t["bucket"] != "verify"]


def _fan_evidence(plan: dict[str, Any], vtask: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for t in _fan_tasks(plan, vtask):
        for r in t["produces"]:
            if r["kind"] != "frame":
                out.append(r)
    return out


def _eff_min(vtask: dict[str, Any]) -> int:
    mi = vtask["requires"]["min_inputs"]
    return mi if mi is not None else 2


def verify_unmet(plan: dict[str, Any], vtask: dict[str, Any], store: Store) -> list[str]:
    """Non-raising: what a verify task still needs before it can complete."""
    from . import methodology as M
    pid = plan["project_id"]
    req = vtask["requires"]
    unmet: list[str] = []
    fan = _fan_evidence(plan, vtask)
    eff = _eff_min(vtask)
    if len(fan) < eff:
        unmet.append(f"need >= {eff} act evidence items in the fan (have {len(fan)})")
    if req["gate_tag"]:
        scope = {vtask["id"], *vtask["consumes"], *[t["id"] for t in _fan_tasks(plan, vtask)]}
        ok = any(j.get("decided") and j["gate_tag"] == req["gate_tag"] and j["task_id"] in scope
                 for j in plan.get("judgments", []))
        if not ok:
            unmet.append(f"a decided `{req['gate_tag']}` judgment must exist")
    for tg in req["artifact_tags"]:
        if not M._project_artifacts_with(store, pid, tg):
            unmet.append(f"need >= 1 artifact tagged `{tg}`")
    for tg in req["session_of_tags"]:
        if not M._sessions_of(store, pid, tg):
            unmet.append(f"need >= 1 recorded session of an artifact tagged `{tg}`")
    return unmet


def complete_task(project_id: str, task_id: str, store: Store | None = None) -> dict[str, Any]:
    """Mark a ready task done. Verify tasks are gate-checked (breadth + gate judgment + artifacts/
    sessions) and rejected until satisfied. Handles loop_back on verify tasks."""
    store = store or Store()
    plan = get_plan(project_id, store=store)
    if plan is None:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    t = task(plan, task_id)
    if not t:
        raise PlanError("BAD_TASK", f"unknown task '{task_id}'")
    ready = {x["id"] for x in ready_tasks(plan)}
    if task_id not in ready:
        raise PlanError("TASK_NOT_READY", f"task '{task_id}' is not on the ready frontier")
    if t["bucket"] == "verify":
        unmet = verify_unmet(plan, t, store)
        if unmet:
            raise PlanError("GATE_UNMET", f"verify task '{task_id}' blocked: {unmet}")
    t["status"] = "done"
    save_plan(plan, store=store)
    return t


def brief_next(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """Plan router: the ready task frontier + per-task instructions (bucket/capability aware)."""
    store = store or Store()
    plan = get_plan(project_id, store=store)
    if plan is None:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    ready = ready_tasks(plan)
    if not ready:
        done = is_complete(plan)
        return {"project_id": project_id, "complete": done, "ready": [],
                "instructions": ("Plan complete — export plan.md and present the answer." if done
                                 else "No ready tasks — resolve a blocker / open question, or add tasks.")}
    # prefer analyze, then act, then verify when several are ready
    pref = {"analyze": 0, "act": 1, "verify": 2}
    primary = sorted(ready, key=lambda t: (pref.get(t["bucket"], 3), plan["tasks"].index(t)))[0]
    unmet: list[str] = []
    if primary["bucket"] == "analyze":
        instr = (f"ANALYZE/{primary['capability']}: {primary['intent']} → record_frame(questions, "
                 f"hypotheses, memory_refs citing persona memory). Understand before concluding.")
        if primary["capability"] == "frame":
            unmet.append("record_frame (>=1 question + >=1 memory ref)")
    elif primary["bucket"] == "verify":
        unmet = verify_unmet(plan, primary, store)
        instr = (f"VERIFY/{primary['capability']}: consolidate the fan into a {primary['capability']} "
                 f"(record_synthesis / record_decision), record the gate judgment, then complete_task.")
    else:
        instr = (f"ACT/{primary['capability']}: do the work (run-council on a framed question / "
                 f"scaffold_artifact / record_artifact_session), link_evidence, then complete_task. "
                 f"Breadth = angles × persona diversity, not one council per persona.")
    return {
        "project_id": project_id, "task": primary["id"], "ready": [t["id"] for t in ready],
        "bucket": primary["bucket"], "capability": primary["capability"], "title": primary["title"],
        "intent": primary["intent"], "step": primary["step"], "consumes": primary["consumes"],
        "requires": primary["requires"], "unmet": unmet, "complete": False, "instructions": instr,
        "goal": plan.get("goal", ""),
    }


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
