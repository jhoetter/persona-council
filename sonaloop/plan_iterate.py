"""Host-driven iteration rounds for `loop_back` tasks (split out of plan.py for the LOC bar).

The engine never FORCES a loop — no hardcoded dynamics; the host judges when to iterate (e.g. a
verify's gate outcome says "not there yet"). `iterate_task` is purely structural: clone the
loop-back subgraph + rewire `consumes`, no semantic interpretation of tags.
"""
from __future__ import annotations

import copy
import re
from typing import Any

from .config import utc_now_iso
from .storage import Store

_ROUND = re.compile(r"^(?P<base>.+)__r(?P<n>\d+)$")


def _round_of(task_id: str) -> tuple[str, int]:
    """(base id without a round suffix, round number) — an unsuffixed id is round 1."""
    m = _ROUND.match(task_id)
    return (m["base"], int(m["n"])) if m else (task_id, 1)


def _loop_subgraph(plan: dict[str, Any], target_id: str, loop_id: str) -> set[str]:
    """The task ids on a `consumes`-path target → looping task, BOTH ends included:
    forward-reachable from the target ∩ ancestors of the looping task."""
    by_id = {t["id"]: t for t in plan["tasks"]}
    succ: dict[str, list[str]] = {}
    for t in plan["tasks"]:
        for c in t["consumes"]:
            succ.setdefault(c, []).append(t["id"])

    def reach(start: str, edges) -> set[str]:
        seen, stack = {start}, [start]
        while stack:
            for nxt in edges(stack.pop()):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return seen

    fwd = reach(target_id, lambda tid: succ.get(tid, []))
    back = reach(loop_id, lambda tid: by_id[tid]["consumes"])
    return fwd & back


def iterate_task(project_id: str, task_id: str, note: str = "",
                 store: Store | None = None) -> dict[str, Any]:
    """Open the NEXT iteration round on a done-or-ready task with a `loop_back` target. Host-driven:
    the engine records the back-edge at seed time and only loops when the host asks — never on its
    own. Purely structural: the loop subgraph (the target through the looping task, along
    `consumes` edges) is cloned as fresh `__r<n>` tasks with statuses reset to todo, evidence refs
    and frames NOT carried over (the old round's record is history), and gate `requires` preserved.
    The cloned entry (the target's clone) additionally consumes the ORIGINAL looping task, so the
    new round only unlocks once the old one is done. In-set references are remapped — so the cloned
    looping task's `loop_back` points at the CLONED target and repeated iteration yields __r3,
    __r4, …; edges out of the set keep pointing at the originals. The graph stays a DAG: the only
    new cross-round edge points backward at the previous round. Raises a stable
    PlanError("NO_LOOP_BACK") on a task without a loop_back target."""
    from . import plan as P
    store = store or Store()
    plan = P.get_plan(project_id, store=store)
    if plan is None:
        raise P.PlanError("NO_PLAN", f"project {project_id} has no plan")
    t = P.task(plan, task_id)
    if not t:
        raise P.PlanError("BAD_TASK", f"unknown task '{task_id}'")
    if not t["loop_back"]:
        raise P.PlanError("NO_LOOP_BACK", f"task '{task_id}' has no loop_back target — nothing to iterate")
    if t["status"] != "done" and task_id not in {x["id"] for x in P.ready_tasks(plan)}:
        raise P.PlanError("TASK_NOT_READY", f"task '{task_id}' must be done or on the ready frontier to iterate")
    target_id = t["loop_back"]
    subgraph = _loop_subgraph(plan, target_id, task_id)
    if target_id not in subgraph or task_id not in subgraph:
        raise P.PlanError("BAD_LOOP", f"loop_back '{target_id}' is not a `consumes`-ancestor of '{task_id}'")
    existing = {x["id"] for x in plan["tasks"]}
    rnd = _round_of(task_id)[1] + 1
    while any(f"{_round_of(tid)[0]}__r{rnd}" in existing for tid in subgraph):
        rnd += 1
    mapping = {tid: f"{_round_of(tid)[0]}__r{rnd}" for tid in subgraph}
    clones: list[dict[str, Any]] = []
    for orig in plan["tasks"]:
        if orig["id"] not in subgraph:
            continue
        c = copy.deepcopy(orig)
        c["id"] = mapping[orig["id"]]
        c["consumes"] = [mapping.get(x, x) for x in orig["consumes"]]
        if orig["id"] == target_id:
            # The new round waits on the looping task; the back-edge REPLACES the previous round's
            # (same lineage base), so round N consumes round N-1's verify only, not every round.
            loop_base = _round_of(task_id)[0]
            c["consumes"] = [x for x in c["consumes"] if _round_of(x)[0] != loop_base] + [task_id]
            if note.strip():
                c["plan_note"] = note.strip()
        c["status"] = "todo"
        c["produces"] = []
        c["frame"] = None
        c["loop_back"] = mapping.get(orig["loop_back"], orig["loop_back"])
        clones.append(c)
    plan["tasks"].extend(clones)
    rec = {"task_id": task_id, "loop_back": target_id, "round": rnd, "note": note.strip(),
           "entry": mapping[target_id], "tasks": [c["id"] for c in clones], "created_at": utc_now_iso()}
    plan.setdefault("iterations", []).append(rec)
    P.save_plan(plan, store=store)                   # re-validates: ids unique, edges valid, acyclic
    return {**rec, "cloned": clones}
