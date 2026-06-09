"""The plan drawer's FRAMEWORK + current-STAGE indicator (surface the methodology engine).

A running study seeds its plan from a Framework (a methodology under sonaloop/methodologies/*.json);
this renders which Framework it runs through and which diverge→converge stage it is currently in, so
the otherwise-invisible methodology layer is visible in the inspector. Pure presentation — the
structured data comes from job_taxonomy.framework_descriptions (the single source the website + job
presets also consume)."""
from __future__ import annotations

from ._components import _icon
from ._html import h, raw, fragment


def _framework_strip(plan: dict, tasks: list) -> str:
    """For a running study: which FRAMEWORK it runs through + which STAGE it is in. The framework is
    the plan's methodology key resolved to its plain-language description (job_taxonomy); the current
    stage is the step of the ready frontier's primary task (analyze→act→verify preference), placed in
    the framework's ordered diverge→converge stages. Freeform plans (no methodology) show nothing."""
    from .. import job_taxonomy as _jt
    key = plan.get("methodology")
    if not key:
        return ""
    try:
        fw = _jt.get_framework_description(key)
    except KeyError:
        return ""
    stages = fw.get("stages") or []
    # The current stage = the step the ready frontier points at (preferring analyze, then act, verify).
    # A task is ready when every consumed task is done; mirrors plan.ready_tasks + next_action ordering.
    pref = {"analyze": 0, "act": 1, "verify": 2}
    done_ids = {tk["id"] for tk in tasks if tk.get("status") == "done"}
    ready = [tk for tk in tasks if tk.get("status") != "done"
             and all(c in done_ids for c in tk.get("consumes", []))]
    cur_step = ""
    if ready:
        primary = sorted(ready, key=lambda tk: (pref.get(tk.get("bucket", ""), 3), tasks.index(tk)))[0]
        cur_step = primary.get("step", "")
    cur_idx = next((i for i, s in enumerate(stages) if s["id"] == cur_step), -1)
    chips = []
    for i, s in enumerate(stages):
        cls = "fw-stage"
        if cur_idx >= 0 and i < cur_idx:
            cls += " is-past"
        elif cur_idx >= 0 and i == cur_idx:
            cls += " is-current"
        chips.append(h("span", {"class_": cls, "title": s.get("what", "")}, s.get("name", s["id"])))
    cur_name = stages[cur_idx]["name"] if cur_idx >= 0 else ""
    label = (f"Stufe {cur_idx + 1}/{len(stages)}" if cur_idx >= 0 else "")
    return h("div", {"class_": "plan-fw"},
             h("div", {"class_": "plan-fw-hd"},
               h("span", {"class_": "plan-fw-name"}, raw(_icon("target")), " ", fw.get("name", key)),
               (h("span", {"class_": "plan-fw-cur"}, f"{label} · {cur_name}") if cur_idx >= 0 else "")),
             h("div", {"class_": "plan-fw-stages"}, fragment(*chips)))
