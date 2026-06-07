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
    # Breadth = distinct ACT tasks (angles) that produced evidence — NOT raw evidence refs. Counting
    # refs let one prototype's (artifact + N sessions) masquerade as "enough exploration", so a phase
    # could converge on a single angle. Distinct tasks force genuine breadth (≥ min_inputs angles).
    fan_tasks = [t for t in _fan_tasks(plan, vtask) if any(r.get("kind") != "frame" for r in t.get("produces", []))]
    eff = _eff_min(vtask)
    if len(fan_tasks) < eff:
        unmet.append(f"need >= {eff} act tasks (distinct angles) with evidence in the fan (have {len(fan_tasks)})")
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
        sess = M._sessions_of(store, pid, tg)
        if not sess:
            unmet.append(f"need >= 1 recorded session of an artifact tagged `{tg}`")
        elif _grounding_verifiable() and not any(s.get("grounded_verified") for s in sess):
            # GAP-5: when the harness CAN verify, an unverified session is not real-usage evidence —
            # a converge can't pass its proband-test gate on it. Degrades gracefully where Playwright
            # is unavailable (then any recorded session counts, as before).
            unmet.append(f"need >= 1 GROUNDED session of `{tg}` — {len(sess)} recorded but none verified "
                         f"against real observed usage; drive the prototype (proto_open/proto_act) and "
                         f"cite states you actually saw, then record")
    return unmet


def _grounding_verifiable() -> bool:
    """True when the Playwright harness is available, so an ungrounded proband session is a real gap
    (not just a degraded-environment artefact). Lazy import avoids a hard browser dependency."""
    try:
        from . import browser as _browser
        return bool(_browser.available())
    except Exception:
        return False


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


def coverage_hint(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """A NON-binding, descriptive evidence-coverage snapshot (counts only — never a score or a
    gate). Helps the host judge progress; it does not decide anything."""
    store = store or Store()
    plan = get_plan(project_id, store=store)
    refs = [r for t in (plan["tasks"] if plan else []) for r in t["produces"]]
    kinds: dict[str, int] = {}
    for r in refs:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    artifacts = store.list_prototypes(project_id)
    sessions = [s for s in store.list_prototype_sessions()
                if (store.get_prototype(s.get("prototype_id", "")) or {}).get("project_id") == project_id]
    personas_touched = set()
    for t in (plan["tasks"] if plan else []):
        for r in t["produces"]:
            if r["kind"] == "council":
                for pid in (store.get_council_session(r["id"]) or {}).get("persona_ids", []):
                    personas_touched.add(pid)
    return {"evidence_by_kind": kinds, "artifacts": len(artifacts), "sessions": len(sessions),
            "personas_touched": len(personas_touched),
            "tasks_done": sum(1 for t in (plan["tasks"] if plan else []) if t["status"] == "done"),
            "tasks_total": len(plan["tasks"]) if plan else 0}


def assess_progress(project_id: str, task_id: str, rationale: str, evidence_refs: list[str],
                    delta: str = "", store: Store | None = None) -> dict[str, Any]:
    """Record an evidence-backed, LLM-judged assessment of progress toward the HMW goal. `delta` is a
    FREE host judgment (e.g. 'näher', 'beantwortet', or prose) — never a hardcoded numeric metric.
    A non-binding coverage snapshot is attached for context."""
    store = store or Store()
    plan = get_plan(project_id, store=store)
    if plan is None:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    if task(plan, task_id) is None:
        raise PlanError("BAD_PROGRESS", f"unknown task '{task_id}'")
    refs = [str(r) for r in (evidence_refs or []) if str(r).strip()]
    if not rationale.strip():
        raise PlanError("BAD_PROGRESS", "a progress assessment needs a rationale")
    if not refs:
        raise PlanError("BAD_PROGRESS", "a progress assessment must cite >= 1 evidence_ref")
    rec = {"task_id": task_id, "goal": plan.get("goal", ""), "delta": str(delta),
           "rationale": rationale.strip(), "evidence_refs": refs,
           "coverage": coverage_hint(project_id, store=store), "created_at": utc_now_iso()}
    plan.setdefault("progress", []).append(rec)
    save_plan(plan, store=store)
    return rec


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


def assess_project(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """Project-level meta-assessment (read-only, COMPUTED — no LLM verdict): coverage, open evidence
    gates, open questions, a saturation hint, structural gaps, and a computed
    continue/converge/complete/blocked recommendation. The host reads this every iteration to stay
    purposeful in a long run and to decide when to stop (spec/harness-evaluation-and-autonomy.md HX1).
    """
    store = store or Store()
    plan = get_plan(project_id, store=store)
    if plan is None:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    tasks = plan["tasks"]
    by_bucket: dict[str, dict[str, int]] = {}
    for t in tasks:
        b = by_bucket.setdefault(t["bucket"], {"done": 0, "total": 0})
        b["total"] += 1
        b["done"] += 1 if t["status"] == "done" else 0
    # open evidence gates: every not-done verify and what it still needs
    open_gates = []
    for t in tasks:
        if t["bucket"] == "verify" and t["status"] != "done":
            unmet = verify_unmet(plan, t, store)
            open_gates.append({"task": t["id"], "title": t["title"], "unmet": unmet})
    cov = coverage_hint(project_id, store=store)
    try:
        oqs = [o["text"] for o in store.list_open_questions(project_id) if o.get("status") == "open"]
    except Exception:
        oqs = []
    # saturation hint: act evidence accumulated vs convergences produced (a coarse, honest proxy —
    # NOT a score; "are we still diverging faster than we converge?").
    n_act = sum(1 for t in tasks if t["bucket"] == "act" and t["status"] == "done")
    n_syn = cov["evidence_by_kind"].get("synthesis", 0)
    n_council = cov["evidence_by_kind"].get("council", 0)
    # structural gaps
    gaps = []
    for g in open_gates:
        for u in g["unmet"]:
            gaps.append(f"{g['title']}: {u}")
    # CONTENT-quality gaps (right level of assessment, not just structure): a verify that converged
    # without a linked synthesis (orphaned convergence), or whose synthesis is near-empty (the answer
    # artifact is hollow — substance may be stranded in notes). Soft signals; they don't block the gate.
    for tsk in tasks:
        if tsk["bucket"] != "verify":
            continue
        syn_refs = [r for r in tsk.get("produces", []) if r.get("kind") == "synthesis"]
        if tsk["status"] == "done" and not syn_refs:
            gaps.append(f"{tsk['title']}: completed without a linked synthesis — record_synthesis → "
                        f"link_evidence (the converging answer artifact is missing/orphaned)")
        for r in syn_refs:
            syn = store.get_synthesis(r["id"]) or {}
            body = (syn.get("gesamtbild", "") + syn.get("positionierung", "") + syn.get("arc_narrative", "")).strip()
            if len(body) < 200:
                gaps.append(f"{tsk['title']}: synthesis is thin/empty — fill gesamtbild/positionierung "
                            f"(the synthesis IS the answer; don't leave it only in notes)")
    # proband-session groundedness (GAP-5): unverified sessions mean the "personas really USED it"
    # evidence is soft — surface it so a long run doesn't converge on unverified usage.
    try:
        psess = [s for s in store.list_prototype_sessions()
                 if (store.get_prototype(s.get("prototype_id", "")) or {}).get("project_id") == project_id]
        ungrounded = [s for s in psess if not s.get("grounded_verified")]
        if psess and ungrounded:
            gaps.append(f"{len(ungrounded)}/{len(psess)} proband session(s) ungrounded (not verified "
                        f"against real observed usage) — re-test by driving the prototype so the evidence is real")
    except Exception:
        pass
    # novelty signal: distinct artifact KINDS + whether an interactive `model` exists, so a run sees
    # if its solution space is too narrow (forms only) and can push for bolder concept diversity. A
    # descriptive hint, never a hard gate — innovation is host-judged, not enforced (no hardcoded DT).
    try:
        protos = store.list_prototypes(project_id)
        kinds = sorted({(p.get("type") or "prototype") for p in protos})
        has_model = any((p.get("type") == "model") for p in protos)
        if protos:
            novelty = {"artifact_kinds": kinds, "distinct_kinds": len(kinds), "has_interactive_model": has_model,
                       "hint": ("diverse" if (len(kinds) >= 3 or has_model)
                                else "narrow — few concept KINDS and no interactive model; consider an "
                                     "experienceable model + a dark-horse (see next_action.act.ideation_lenses)")}
            if novelty["hint"].startswith("narrow"):
                gaps.append("solution space is narrow (few artifact kinds, no interactive model) — "
                            "apply the ideation lenses for a bolder, more experienceable concept")
        else:
            novelty = {"artifact_kinds": [], "distinct_kinds": 0, "has_interactive_model": False, "hint": "no artifacts yet"}
    except Exception:
        novelty = {}
    # FINISH readiness: gates-passed is NOT the same as a finished, exhaustive, well-told project. A
    # run must not stop at "a good starting point". `finish` checks the project is ORGANIZED (sections),
    # CONCLUDED (a substantial terminal synthesis), and HANDED OFF (a meta-report) — generic, data-
    # driven, methodology-agnostic. When the plan's gates are all met but these are missing, the
    # recommendation is `finish`, not `complete`.
    finish_gaps: list[str] = []
    # only a SUBSTANTIAL project (a methodology run, or one that produced prototypes) is held to the
    # finish bar — a minimal freeform inquiry (a lone frame) is legitimately complete as-is.
    substantial = bool(plan.get("methodology")) or bool(store.list_prototypes(project_id))
    try:
        project = store.get_research_project(project_id) or {}
        if substantial and not (project.get("sections") or []):
            finish_gaps.append("not organized — create phase/theme SECTIONS (Discover/Define/Solution/"
                               "Prototype-ladder/Deliver) so the hi-fi + conclusion are surfaced")
        # a substantial terminal conclusion: the last verify task's synthesis, non-thin
        verify_syn = [r["id"] for t in tasks if t["bucket"] == "verify"
                      for r in t.get("produces", []) if r.get("kind") == "synthesis"]
        concl = store.get_synthesis(verify_syn[-1]) if verify_syn else None
        body = (concl or {}).get("gesamtbild", "") + (concl or {}).get("positionierung", "") if concl else ""
        if substantial and (not concl or len(body.strip()) < 400):
            finish_gaps.append("no substantial CONCLUSION — author a rich terminal solution-presentation "
                               "synthesis (the answer, who-wins + non-targets, validated solvers, build spec)")
        try:
            if substantial and not store.list_meta_reports(project_id):
                finish_gaps.append("no META-REPORT — author the project narrative/handover (meta_report)")
        except Exception:
            pass
    except Exception:
        finish_gaps = []
    if finish_gaps:
        gaps.extend(finish_gaps)
    finish = {"organized": not any("organized" in g for g in finish_gaps),
              "concluded": not any("CONCLUSION" in g for g in finish_gaps),
              "handed_off": not any("META-REPORT" in g for g in finish_gaps),
              "finished": not finish_gaps, "gaps": finish_gaps}
    # memory_depth (ESV6): councils are only as deep as the simulated lives behind them — flag a thin
    # cohort so a run deepens memory (simulate-cohort) before concluding it has explored deeply.
    memory_depth = {}
    try:
        pids = (store.get_research_project(project_id) or {}).get("persona_ids", [])
        if pids:
            m = store.count_memory_for_personas(pids)
            avg = (m["facts"] + m["events"]) / max(1, len(pids))
            memory_depth = {"personas": len(pids), "facts": m["facts"], "events": m["events"],
                            "avg_per_persona": round(avg, 1),
                            "hint": "deep" if avg >= 6 else "thin — deepen the cohort (simulate-cohort) for richer councils"}
            if memory_depth["hint"].startswith("thin"):
                gaps.append("cohort memory is thin (few simulated events/facts per persona) — deepen it "
                            "(simulate-cohort) so councils are grounded in rich lived experience")
    except Exception:
        memory_depth = {}
    ready = ready_tasks(plan)
    complete = is_complete(plan)
    if complete and finish_gaps:
        rec = "finish"            # gates met but not a finished, organized, concluded project
    elif complete:
        rec = "complete"
    elif not ready:
        rec = "blocked"
    else:
        ready_verify = [t for t in ready if t["bucket"] == "verify" and not verify_unmet(plan, t, store)]
        ready_analyze = [t for t in ready if t["bucket"] == "analyze"]
        if ready_verify:
            rec = "converge"          # a gate is satisfied → consolidate
        elif ready_analyze:
            rec = "frame"             # understand before acting
        else:
            rec = "act"               # do more work to satisfy a gate
    return {
        "project_id": project_id, "goal": plan.get("goal", ""), "complete": complete,
        "recommendation": rec,
        "coverage": cov,
        "tasks_by_bucket": by_bucket,
        "open_gates": open_gates,
        "open_questions": oqs,
        "saturation": {"act_done": n_act, "councils": n_council, "syntheses": n_syn,
                       "hint": ("converging" if n_syn and n_act <= n_syn * 2 else "still diverging")},
        "novelty": novelty,
        "finish": finish,
        "memory_depth": memory_depth,
        "gaps": gaps,
        "ready": [t["id"] for t in ready],
        "next": brief_next(project_id, store=store).get("instructions", ""),
    }


# Methodology-agnostic divergence nudges surfaced on act steps so concept breadth (KIND + boldness) is
# reliable, not luck of a disciplined agent. These reference the DATA palette; no methodology vocabulary
# or design-thinking step is hardcoded (spec/exploration-depth-and-prototype-variety GAP-2 / SPEC-A).
_DIVERGENCE_NUDGES = [
    "Diversify the KIND of artifact (see artifact_palette): a guided flow, a comparison, an overview, a "
    "card interface, or an interactive MODEL (steerable numbers/curve a persona can actually drive) — "
    "not N near-identical forms.",
    "Include >= 1 deliberately EXTREME / unexpected concept (a 'dark-horse') to stretch the space; an "
    "honest 'this is not for you' verdict can be a legitimate, trust-winning concept.",
    "For an exploratory step, consider a DISCONFIRMATION council: deliberately load the segments most "
    "likely to REJECT the premise and test a Non-Fit motion — the most honest insight often comes from "
    "the refuters, not the supporters.",
]


def _artifact_palette() -> list[dict[str, Any]]:
    try:
        from . import presentation as _pres
        return _pres.artifact_palette()
    except Exception:
        return []


def _ideation_lenses() -> list[dict[str, Any]]:
    try:
        from . import presentation as _pres
        return _pres.ideation_lenses()
    except Exception:
        return []


def _diverse_participants(store: Store, persona_ids: list[str], k: int = 6) -> list[str]:
    """Pick up to k personas SPREAD across a segment axis (attitude/life-stage), so a council gets
    real diversity rather than keyword-matched look-alikes (anti-steering)."""
    buckets: dict[str, list[str]] = {}
    for pid in persona_ids:
        p = store.get_persona(pid)
        if not p:
            continue
        seg = p.get("segment") or {}
        key = str(seg.get("einstellung") or seg.get("lebensphase") or seg.get("kanal") or p.get("slug"))
        buckets.setdefault(key, []).append(p["slug"])
    pools = list(buckets.values())
    out: list[str] = []
    i = 0
    while len(out) < k and any(pools) and i < 500:
        pool = pools[i % len(pools)]
        if pool:
            out.append(pool.pop(0))
        i += 1
    return out[:k]


def next_action(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """Lean orchestration step (spec/harness-evaluation-and-autonomy.md HX2): the ready task FULLY
    loaded, so a long autonomous run is one `next_action` → author (subagent) → persist per
    iteration, keeping host context lean. For analyze → grounding (prior syntheses + open questions);
    for act → the framed questions of the consumed frame + segment-diverse suggested participants;
    for verify → the fan to consolidate + the gate to satisfy. Carries the project recommendation."""
    store = store or Store()
    plan = get_plan(project_id, store=store)
    if plan is None:
        raise PlanError("NO_PLAN", f"project {project_id} has no plan")
    b = brief_next(project_id, store=store)
    if b.get("complete"):
        return {"complete": True, "recommendation": "complete", "instructions": b.get("instructions", "")}
    t = task(plan, b["task"])
    project = store.get_research_project(project_id) or {}
    persona_ids = project.get("persona_ids", [])
    out: dict[str, Any] = {"complete": False, "task": b["task"], "bucket": b["bucket"],
                           "capability": b["capability"], "title": b["title"], "intent": b["intent"],
                           "unmet": b.get("unmet", []), "instructions": b["instructions"]}
    if b["bucket"] == "analyze":
        try:
            oqs = [o["text"] for o in store.list_open_questions(project_id) if o.get("status") == "open"]
        except Exception:
            oqs = []
        out["grounding"] = {
            "prior_syntheses": [{"id": s["id"], "title": s.get("title", "")} for s in store.list_syntheses()][:8],
            "open_questions": oqs[:8], "persona_pool": persona_ids,
            "guidance": "record_frame: >=1 research question grounded in CITED persona memory / prior evidence.",
        }
    elif b["bucket"] == "act":
        questions: list[str] = []
        for c in t["consumes"]:
            f = task(plan, c)
            if f and f.get("frame"):
                questions += f["frame"].get("questions", [])
        out["act"] = {
            "framed_questions": questions[:6],
            "suggested_participants": _diverse_participants(store, persona_ids, k=6),
            "artifact_palette": _artifact_palette(),
            "divergence": _DIVERGENCE_NUDGES,
            "ideation_lenses": _ideation_lenses(),
            "guidance": ("Add an act task per ANGLE; run a REAL multi-persona council, or "
                         "scaffold_artifact + a grounded proband session; link_evidence + complete. "
                         "Breadth = angles × persona diversity, not one council per persona."),
        }
    else:  # verify
        fan = _fan_evidence(plan, t)
        short = len(fan) < _eff_min(t)        # gate not yet satisfiable → ACT first, don't try to converge
        out["verify"] = {
            "fan_evidence": fan, "gate_tag": t["requires"].get("gate_tag"),
            "needs": b.get("unmet", []),
            "guidance": (
                f"Gate not yet satisfiable ({len(fan)}/{_eff_min(t)} inputs) — do the ACT work in `act` "
                f"first (consolidate only once the fan is complete)."
                if short else
                "Consolidate the fan into a synthesis (record_synthesis — councils are OPTIONAL/decoupled), "
                "record the gate judgment, assess_progress, complete_task."),
        }
        # If the fan is still short of min_inputs, the real next move is ACT work for this diamond:
        # surface the consuming frames' questions + diverse participants so the host adds act tasks.
        if short:
            questions: list[str] = []
            for c in t["consumes"]:
                f = task(plan, c)
                if f and f.get("frame"):
                    questions += f["frame"].get("questions", [])
            out["act"] = {
                "for_frame": t["consumes"], "framed_questions": questions[:6],
                "suggested_participants": _diverse_participants(store, persona_ids, k=6),
                "guidance": ("This verify's fan is incomplete — do ACT work first: add an act task "
                             "per ANGLE consuming the frame, run real councils / build+test prototypes, "
                             "link_evidence + complete, until the gate's min_inputs is met."),
            }
    try:
        out["recommendation"] = assess_project(project_id, store=store)["recommendation"]
    except Exception:
        out["recommendation"] = ""
    return out


# plan.md render lives in plan_render.py (kept under the LOC bar); re-exported for back-compat.
from .plan_render import render_plan_md  # noqa: E402,F401
