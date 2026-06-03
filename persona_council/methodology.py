"""Methodology engine — tag-driven constellations (spec/methodology-constellations.md).

A methodology is a CONSTELLATION: a DAG of steps, each carrying OPEN TAGS. There are NO
hardcoded vocabularies — capability ("explore"/"cluster"/"decide"/…), role, artifact_type,
gate and strategy are all free strings the spec declares. The engine is TAG-AGNOSTIC: its
only fixed concepts are the DAG (`consumes`), an integer `min_inputs`, tag-equality between
a producer and a requirer, and the PRESENCE of an evidence-backed judgment. It never compares
a tag to a closed set.

Shape (diverge/converge/diamonds/branches/loops) is DERIVED from the graph + recorded node
counts, never asserted. Common building blocks are SUGGESTED as data (see suggestions.py /
suggestions/*.json) — suggestions, not constraints.

DYNAMICS are LLM-judged-by-the-host with evidence (record_judgment); the engine requires only
the judgment's presence, never a number. No in-process LLM text-generation: the host/subagents
author every word via the brief_*→record_* contract. The autonomous loop (runtime.py) calls
these same functions.

Back-compat: legacy `phases` specs auto-translate to `steps`; the old tool names
(brief_phase/record_exploration/record_convergence/advance_phase) remain as thin aliases.
"""
from __future__ import annotations

import json
from typing import Any

from .config import methodologies_dir, utc_now_iso
from .models import MethodologyJudgment
from .storage import Store

COMPLETE = "__complete__"
# The structural breadth invariant: a waist consuming a fan needs at least this many upstream
# nodes (identical to the legacy INV-BREADTH). Used only as the default when a step does not
# declare its own `requires.min_inputs`; it is NOT a dynamics threshold.
_DEFAULT_FAN_MIN = 2


class MethodologyError(Exception):
    """Carries a stable code (§8.4) so callers/tests can assert the exact violation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# ----------------------------------------------------------------- spec normalization

def _as_list(v: Any) -> list:
    if v is None:
        return []
    return list(v) if isinstance(v, (list, tuple)) else [v]


def _norm_step(raw: dict[str, Any]) -> dict[str, Any]:
    """Canonical step dict. All domain words are open tags; nothing checked against a set."""
    produces = dict(raw.get("produces") or {})
    requires = dict(raw.get("requires") or {})
    return {
        "id": raw.get("id") or raw.get("key"),
        "name": raw.get("name", raw.get("id") or raw.get("key") or ""),
        "tags": list(raw.get("tags") or []),
        "intent": raw.get("intent", ""),
        "consumes": [str(c) for c in _as_list(raw.get("consumes"))],
        "strategy": raw.get("strategy") or raw.get("council_strategy") or "",
        "diverge_by": raw.get("diverge_by", ""),
        "produces": {
            "role": produces.get("role", ""),
            "artifact_type": produces.get("artifact_type", ""),
            "more_tags": list(produces.get("more_tags") or []),
        },
        "requires": {
            "min_inputs": int(requires["min_inputs"]) if requires.get("min_inputs") is not None else None,
            "gate_tag": requires.get("gate_tag", ""),
            "artifact_tags": list(requires.get("artifact_tags") or []),
            "session_of_tags": list(requires.get("session_of_tags") or []),
        },
        "loop_back": raw.get("loop_back", ""),
    }


def _phases_to_steps(phases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Translate a legacy phase list (mode diverge/converge, alternating) to a step DAG.

    A linear chain: each step consumes the previous one. Converge phases gain the structural
    breadth + gate requirement; prototype/prototype_session requirements become tag references
    (matched by tag-equality, no literal artifact string survives)."""
    steps: list[dict[str, Any]] = []
    for i, p in enumerate(phases):
        key = p.get("key")
        mode = p.get("mode")
        prev = phases[i - 1] if i > 0 else None
        consumes = [prev["key"]] if prev else []
        req_arts = list(p.get("requires_artifacts") or [])
        raw: dict[str, Any] = {
            "id": key, "name": p.get("name", key), "intent": p.get("intent", ""),
            "consumes": consumes, "strategy": p.get("council_strategy", ""),
            "diverge_by": p.get("diverge_by", ""),
            "produces": {"role": p.get("produces_role", ""), "more_tags": []},
            "requires": {}, "loop_back": p.get("loop_back", ""),
        }
        if mode == "diverge":
            raw["tags"] = ["explore"] + ([p["produces_role"]] if p.get("produces_role") else [])
            if "prototype" in req_arts:
                raw["tags"].append("build")
                raw["produces"]["artifact_type"] = "prototype"
                if p.get("fidelity"):
                    raw["produces"]["more_tags"] = [p["fidelity"]]
        else:  # converge — a waist: needs breadth + a divergence gate
            raw["tags"] = ["decide"] + ([p["produces_role"]] if p.get("produces_role") else [])
            raw["requires"] = {"min_inputs": _DEFAULT_FAN_MIN, "gate_tag": "divergence_complete"}
            if "prototype_session" in req_arts:
                # require a recorded session of the prototype the consumed step built, keyed by
                # the most specific tag available (fidelity if set, else "prototype").
                disc = (prev or {}).get("fidelity") or "prototype"
                raw["requires"]["session_of_tags"] = [disc]
        steps.append(_norm_step(raw))
    return steps


def _normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the spec with a canonical `steps` list (translating legacy `phases`)."""
    out = dict(spec)
    if out.get("steps"):
        out["steps"] = [_norm_step(s) for s in out["steps"]]
    elif out.get("phases"):
        out["steps"] = _phases_to_steps(out["phases"])
    else:
        out["steps"] = []
    return out


def validate_methodology_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate a methodology spec (steps OR legacy phases). Tag-agnostic: only graph mechanics
    and references are checked — never tag membership."""
    if not isinstance(spec, dict):
        raise MethodologyError("BAD_SPEC", "methodology spec must be an object")
    for k in ("key", "name", "description", "when_to_use"):
        if not spec.get(k):
            raise MethodologyError("BAD_SPEC", f"methodology spec missing '{k}'")
    if not (spec.get("steps") or spec.get("phases")):
        raise MethodologyError("BAD_SPEC", "methodology needs `steps` (or legacy `phases`)")
    steps = _normalize_spec(spec)["steps"]
    if len(steps) < 2:
        raise MethodologyError("BAD_SPEC", "methodology needs >= 2 steps")
    ids = [s["id"] for s in steps]
    if not all(ids) or len(set(ids)) != len(ids):
        raise MethodologyError("BAD_SPEC", "step ids must be present and unique")
    idset = set(ids)
    roots = 0
    for s in steps:
        if not s["name"]:
            raise MethodologyError("BAD_SPEC", f"step '{s['id']}' needs a name")
        for c in s["consumes"]:
            if c not in idset:
                raise MethodologyError("BAD_SPEC", f"step '{s['id']}' consumes unknown step '{c}'")
            if c == s["id"]:
                raise MethodologyError("BAD_SPEC", f"step '{s['id']}' cannot consume itself")
        if not s["consumes"]:
            roots += 1
        mi = s["requires"]["min_inputs"]
        if mi is not None and (not isinstance(mi, int) or mi < 0):
            raise MethodologyError("BAD_SPEC", f"step '{s['id']}' requires.min_inputs must be a non-negative int")
        if s["loop_back"] and s["loop_back"] not in idset:
            raise MethodologyError("BAD_SPEC", f"step '{s['id']}' loop_back target '{s['loop_back']}' is not a step")
    if roots < 1:
        raise MethodologyError("BAD_SPEC", "methodology needs >= 1 root step (consumes [])")
    # INV-DAG: the `consumes` graph must be acyclic (loop_back is a separate, logged back-edge).
    _assert_acyclic(steps)
    return spec


def _assert_acyclic(steps: list[dict[str, Any]]) -> None:
    by_id = {s["id"]: s for s in steps}
    state: dict[str, int] = {}  # 0=visiting, 1=done

    def visit(sid: str) -> None:
        if state.get(sid) == 1:
            return
        if state.get(sid) == 0:
            raise MethodologyError("BAD_SPEC", f"`consumes` graph has a cycle at '{sid}'")
        state[sid] = 0
        for c in by_id[sid]["consumes"]:
            visit(c)
        state[sid] = 1

    for s in steps:
        visit(s["id"])


# --------------------------------------------------------------------------- registry

def _load_builtin_specs() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    d = methodologies_dir()
    if not d.exists():
        return out
    for path in sorted(d.glob("*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        validate_methodology_spec(spec)
        out[spec["key"]] = _normalize_spec(spec)
    return out


def registry(store: Store | None = None) -> dict[str, dict[str, Any]]:
    """Built-in specs (package files) overlaid with user-defined ones (DB), all normalized."""
    store = store or Store()
    specs = _load_builtin_specs()
    for spec in store.list_methodologies():
        specs[spec["key"]] = _normalize_spec(spec)
    return specs


def list_methodologies(store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    out = []
    for s in registry(store).values():
        keys = [st["id"] for st in s["steps"]]
        out.append({"key": s["key"], "name": s["name"], "description": s["description"],
                    "when_to_use": s["when_to_use"], "step_keys": keys, "phase_keys": keys})
    return out


def get_methodology(key: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    spec = registry(store).get(key)
    if not spec:
        raise MethodologyError("UNKNOWN_METHODOLOGY", f"No methodology '{key}'")
    return spec


def register_methodology(spec: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    validate_methodology_spec(spec)
    spec = dict(spec)
    spec.setdefault("created_at", utc_now_iso())
    store.upsert_methodology(spec)
    return spec


# --------------------------------------------------------------------------- helpers

def _step(spec: dict[str, Any], sid: str) -> dict[str, Any] | None:
    return next((s for s in spec["steps"] if s["id"] == sid), None)


# legacy alias used by runtime/tests
def _phase(spec: dict[str, Any], sid: str) -> dict[str, Any] | None:
    return _step(spec, sid)


def _is_decide(step: dict[str, Any]) -> bool:
    """A 'waist' step: it consolidates inputs behind a gate. Derived from structure, not a tag."""
    r = step["requires"]
    return bool(r["min_inputs"] is not None or r["gate_tag"] or r["session_of_tags"] or r["artifact_tags"])


def _mode(step: dict[str, Any]) -> str:
    """Display label only — the engine never branches on this."""
    return "converge" if _is_decide(step) else "diverge"


def _consumers(spec: dict[str, Any], sid: str) -> list[dict[str, Any]]:
    return [s for s in spec["steps"] if sid in s["consumes"]]


def _slog(project: dict[str, Any]) -> dict[str, Any]:
    return project.setdefault("phase_log", {})


def _entry(project: dict[str, Any], sid: str) -> dict[str, Any]:
    return _slog(project).setdefault(
        sid, {"status": "pending", "node_ids": [], "decision_node_id": None, "decided_at": None})


def _nodes(project: dict[str, Any], sid: str) -> list[str]:
    return list((project.get("phase_log") or {}).get(sid, {}).get("node_ids", []))


def _is_complete(project: dict[str, Any], sid: str) -> bool:
    return (project.get("phase_log") or {}).get(sid, {}).get("status") == "complete"


def _ready(project: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    """The topological frontier: steps whose `consumes` are all complete and not yet complete."""
    out = []
    for s in spec["steps"]:
        if _is_complete(project, s["id"]):
            continue
        if all(_is_complete(project, c) for c in s["consumes"]):
            out.append(s["id"])
    return out


def _judgments(store: Store, project_id: str, step_id: str | None = None,
               gate_tag: str | None = None) -> list[dict[str, Any]]:
    out = store.list_methodology_judgments(project_id)
    if step_id:
        out = [j for j in out if j["phase_key"] == step_id]
    if gate_tag:
        out = [j for j in out if j["kind"] == gate_tag]
    return out


def _artifact_tags(proto: dict[str, Any]) -> set[str]:
    """An artifact's open tags — its type plus any discriminators (e.g. fidelity)."""
    tags = {"prototype"}
    if proto.get("fidelity"):
        tags.add(proto["fidelity"])
    for tg in (proto.get("tags") or []):
        tags.add(tg)
    return tags


def _ensure_methodology_project(store: Store, project_id: str) -> tuple[dict, dict]:
    p = store.get_research_project(project_id)
    if not p:
        raise MethodologyError("UNKNOWN_PROJECT", f"Unknown research project: {project_id}")
    if not p.get("methodology"):
        raise MethodologyError("NO_METHODOLOGY", f"Project {project_id} has no methodology bound")
    return p, get_methodology(p["methodology"], store)


def _primary(project: dict[str, Any], spec: dict[str, Any]) -> str:
    ready = _ready(project, spec)
    return ready[0] if ready else COMPLETE


# --------------------------------------------------------------------------- engine

def start_methodology_project(title: str, goal: str, methodology_key: str,
                              persona_ids: list[str] | None = None, description: str = "",
                              store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    spec = get_methodology(methodology_key, store)
    from . import services as svc
    project = svc.create_research_project(title, goal=goal, persona_ids=persona_ids,
                                          description=description, store=store)
    project["methodology"] = methodology_key
    project["phase_log"] = {}
    for s in spec["steps"]:
        _entry(project, s["id"])
    for sid in _ready(project, spec):
        project["phase_log"][sid]["status"] = "active"
    project["phase"] = _primary(project, spec)
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    return project


def set_project_methodology(project_id: str, methodology_key: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    spec = get_methodology(methodology_key, store)
    p = store.get_research_project(project_id)
    if not p:
        raise MethodologyError("UNKNOWN_PROJECT", f"Unknown research project: {project_id}")
    p["methodology"] = methodology_key
    p["phase_log"] = {}
    for s in spec["steps"]:
        _entry(p, s["id"])
    for sid in _ready(p, spec):
        p["phase_log"][sid]["status"] = "active"
    p["phase"] = _primary(p, spec)
    p["updated_at"] = utc_now_iso()
    store.upsert_research_project(p)
    return p


def _gate_tag_for_fan(spec: dict[str, Any], sid: str) -> str:
    """The gate a fan step should close: the gate_tag any downstream consumer requires."""
    for c in _consumers(spec, sid):
        if c["requires"]["gate_tag"]:
            return c["requires"]["gate_tag"]
    return ""


def brief_next(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """GATHER what the topological frontier needs now. Returns the primary ready step plus the
    full ready set; tag-agnostic instructions derived from the step's structure."""
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    ready = _ready(project, spec)
    if not ready:
        return {"project_id": project["id"], "complete": True, "ready": [],
                "instructions": "The constellation is complete. Export the meta-report for the handover."}
    sid = ready[0]
    step = _step(spec, sid)
    decide = _is_decide(step)
    consumed_nodes = [n for c in step["consumes"] for n in _nodes(project, c)]
    consumed_decisions = [d for d in (
        (project.get("phase_log") or {}).get(c, {}).get("decision_node_id") for c in step["consumes"]) if d]
    unmet: list[str] = []
    if decide:
        req = step["requires"]
        eff_min = req["min_inputs"] if req["min_inputs"] is not None else (
            _DEFAULT_FAN_MIN if any(not _is_decide(_step(spec, c)) for c in step["consumes"]) else 1)
        if len(consumed_nodes) < eff_min:
            unmet.append(f"need >= {eff_min} upstream nodes from {step['consumes']} (have {len(consumed_nodes)})")
        if req["gate_tag"] and not any(j.get("decided") for c in step["consumes"]
                                       for j in _judgments(store, project["id"], c, req["gate_tag"])):
            unmet.append(f"a decided `{req['gate_tag']}` judgment must exist on {step['consumes']}")
        for tg in req["artifact_tags"]:
            if not _project_artifacts_with(store, project["id"], tg):
                unmet.append(f"need >= 1 artifact tagged `{tg}`")
        for tg in req["session_of_tags"]:
            if not _sessions_of(store, project["id"], tg):
                unmet.append(f"need >= 1 recorded session of an artifact tagged `{tg}`")
        instr = (f"DECIDE step '{step['name']}' (strategy={step['strategy']}). Consolidate the "
                 f"{step['consumes']} fan into one `{step['produces']['role'] or 'decision'}` node via "
                 f"record_decision(from_node_ids=the nodes you consolidate), then advance.")
    else:
        gate = _gate_tag_for_fan(spec, sid)
        n = len(_nodes(project, sid))
        gate_clause = (f"record an evidence-backed `{gate}` judgment, then advance." if gate
                       else "advance when the space is explored enough.")
        if gate and not _judgments(store, project["id"], sid, gate):
            unmet.append(f"record a `{gate}` judgment (evidence-backed) before the consumer can decide")
        instr = (f"EXPLORE step '{step['name']}' (strategy={step['strategy']}). Fan out — run a council "
                 f"per {step.get('diverge_by') or 'angle'} and record_node each (have {n}). "
                 f"Decide WHEN enough with your own evidence; {gate_clause}")
        if step["produces"]["artifact_type"]:
            instr += (f" Build artifact(s) of type `{step['produces']['artifact_type']}`"
                      + (f" ({', '.join(step['produces']['more_tags'])})" if step['produces']['more_tags'] else "") + ".")
    return {
        "project_id": project["id"], "step": sid, "ready": ready, "name": step["name"],
        "mode": _mode(step), "tags": step["tags"], "intent": step["intent"],
        "council_strategy": step["strategy"], "strategy": step["strategy"],
        "diverge_by": step.get("diverge_by"), "consumes": step["consumes"],
        "produces": step["produces"], "produces_role": step["produces"]["role"],
        "requires": step["requires"], "unmet": unmet, "complete": False, "instructions": instr,
        "frame": {"goal": project.get("goal", ""), "persona_ids": project.get("persona_ids", []),
                  "methodology": project["methodology"],
                  "consumed_nodes": consumed_nodes, "consumed_decisions": consumed_decisions},
    }


def brief_phase(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """Legacy alias for brief_next, shaped like the old single-phase brief."""
    b = brief_next(project_id, store=store)
    if b.get("complete"):
        return {"project_id": b["project_id"], "complete": True, "instructions": b["instructions"]}
    b["phase"] = b["step"]
    # legacy `consumes` was a single string
    b["consumes"] = b["consumes"][0] if b["consumes"] else None
    return b


def _project_artifacts_with(store: Store, project_id: str, tag: str) -> list[dict[str, Any]]:
    return [p for p in store.list_prototypes(project_id) if tag in _artifact_tags(p)]


def _sessions_of(store: Store, project_id: str, tag: str) -> list[dict[str, Any]]:
    out = []
    for s in store.list_prototype_sessions():
        proto = store.get_prototype(s.get("prototype_id", "")) or {}
        if proto.get("project_id") == project_id and tag in _artifact_tags(proto):
            out.append(s)
    return out


def _node_payload(title: str, start_input: str, council_ids: list[str], payload: dict[str, Any],
                  project: dict, step: dict, mode: str, store: Store) -> dict[str, Any]:
    from . import services as svc
    rec = svc.record_synthesis(title=title, start_input=start_input, council_ids=council_ids,
                               payload=payload, goal=project.get("goal", ""), store=store)
    rec["phase"] = step["id"]
    rec["mode"] = mode
    rec["role"] = step["produces"]["role"]
    rec["methodology"] = project["methodology"]
    if isinstance(payload, dict):
        for k in ("clusters", "key_problems", "ranking", "shortlist"):
            if payload.get(k):
                rec[k] = payload[k]
    store.upsert_synthesis(rec)
    return rec


def record_node(project_id: str, title: str, council_ids: list[str], payload: dict[str, Any],
                start_input: str = "", step_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Record one exploration node against a ready FAN step (the host authored it)."""
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    ready = _ready(project, spec)
    sid = step_id or next((s for s in ready if not _is_decide(_step(spec, s))), None)
    step = _step(spec, sid) if sid else None
    if not step or sid not in ready or _is_decide(step):
        raise MethodologyError("PHASE_OUT_OF_ORDER", "record_node is only valid on a ready explore (fan) step")
    if not council_ids:
        raise MethodologyError("NO_COUNCIL_CITED", "an exploration must cite >= 1 council")
    rec = _node_payload(title, start_input or project.get("goal", ""), council_ids, payload,
                        project, step, "diverge", store)
    from . import services as svc
    svc.add_study_to_project(project["id"], rec["id"], store=store)
    project = store.get_research_project(project["id"])
    # waist -> fan: link each consumed step's decision node into this exploration
    for c in step["consumes"]:
        dnode = (project.get("phase_log") or {}).get(c, {}).get("decision_node_id")
        if dnode:
            try:
                svc.link_studies(project["id"], dnode, rec["id"], "spawned_from",
                                 rationale=f"{c} -> {sid} (waist to fan)", store=store)
            except Exception:
                pass
    project = store.get_research_project(project["id"])
    _entry(project, sid)["node_ids"].append(rec["id"])
    project["phase_log"][sid]["status"] = "active"
    project["phase"] = _primary(project, spec)
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    return rec


def record_exploration(project_id: str, title: str, council_ids: list[str], payload: dict[str, Any],
                       start_input: str = "", store: Store | None = None) -> dict[str, Any]:
    """Legacy alias for record_node."""
    return record_node(project_id, title, council_ids, payload, start_input, store=store)


def record_judgment(project_id: str, step_id: str, gate_tag: str, decided: bool, rationale: str,
                    evidence_refs: list[str] | None = None, store: Store | None = None) -> dict[str, Any]:
    """Record an evidence-backed gate judgment on a step. `gate_tag` is a FREE tag."""
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    if not (gate_tag or "").strip():
        raise MethodologyError("BAD_JUDGMENT", "a judgment needs a gate_tag")
    if _step(spec, step_id) is None:
        raise MethodologyError("BAD_JUDGMENT", f"unknown step '{step_id}'")
    refs = [str(r) for r in (evidence_refs or []) if str(r).strip()]
    if decided and not rationale.strip():
        raise MethodologyError("BAD_JUDGMENT", "a decided judgment needs a rationale")
    if decided and not refs:
        raise MethodologyError("BAD_JUDGMENT", "a decided gate judgment needs >= 1 evidence_ref")
    now = utc_now_iso()
    j = MethodologyJudgment(
        id=_judgment_id(project["id"], step_id, gate_tag, now), project_id=project["id"],
        phase_key=step_id, kind=gate_tag, decided=bool(decided), rationale=rationale.strip(),
        evidence_refs=refs, created_at=now,
    ).to_dict()
    store.insert_methodology_judgment(j)
    return j


def _judgment_id(project_id: str, step_id: str, gate_tag: str, now: str) -> str:
    from .services import stable_id
    return stable_id("judgment", project_id, step_id, gate_tag, now)


def record_decision(project_id: str, title: str, from_node_ids: list[str], payload: dict[str, Any],
                    start_input: str = "", step_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Consolidate a fan into one decision node on a ready DECIDE step (validates INV-*)."""
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    ready = _ready(project, spec)
    sid = step_id or next((s for s in ready if _is_decide(_step(spec, s))), None)
    step = _step(spec, sid) if sid else None
    if not step or sid not in ready or not _is_decide(step):
        raise MethodologyError("PHASE_OUT_OF_ORDER", "record_decision is only valid on a ready decide step")
    req = step["requires"]
    upstream = [n for c in step["consumes"] for n in _nodes(project, c)]
    eff_min = req["min_inputs"] if req["min_inputs"] is not None else (
        _DEFAULT_FAN_MIN if any(not _is_decide(_step(spec, c)) for c in step["consumes"]) else 1)
    # INV-INPUTS / INV-BREADTH
    if len(upstream) < eff_min:
        raise MethodologyError("BREADTH_TOO_LOW",
                               f"decide needs >= {eff_min} upstream nodes in {step['consumes']} (have {len(upstream)})")
    # INV-GATE
    if req["gate_tag"]:
        decided = [j for c in step["consumes"]
                   for j in _judgments(store, project["id"], c, req["gate_tag"]) if j.get("decided")]
        if not decided:
            raise MethodologyError("MISSING_GATE_JUDGMENT",
                                   f"need a decided `{req['gate_tag']}` judgment on {step['consumes']}")
    # INV-EDGES
    chosen = [n for n in (from_node_ids or []) if n in upstream]
    if not chosen:
        raise MethodologyError("EDGES_NOT_FROM_FAN", f"from_node_ids must be nodes of {step['consumes']}")
    # INV-ARTIFACT (tag-equality; no literal artifact string)
    for tg in req["artifact_tags"]:
        if not _project_artifacts_with(store, project["id"], tg):
            raise MethodologyError("MISSING_ARTIFACT", f"step '{sid}' requires >= 1 artifact tagged `{tg}`")
    for tg in req["session_of_tags"]:
        if not _sessions_of(store, project["id"], tg):
            raise MethodologyError("MISSING_ARTIFACT", f"step '{sid}' requires >= 1 recorded session of `{tg}`")
    # INV-CITE
    cited: list[str] = []
    for nid in chosen:
        syn = store.get_synthesis(nid) or {}
        for c in syn.get("council_ids", []):
            if c not in cited:
                cited.append(c)
    if not cited:
        raise MethodologyError("NO_COUNCIL_CITED", "consumed nodes cite no councils")
    rec = _node_payload(title, start_input or project.get("goal", ""), cited, payload,
                        project, step, "converge", store)
    from . import services as svc
    svc.add_study_to_project(project["id"], rec["id"], store=store)
    for nid in chosen:
        try:
            svc.link_studies(project["id"], nid, rec["id"], "refines",
                             rationale=f"{step['consumes']} fan -> {sid} waist", store=store)
        except Exception:
            pass
    project = store.get_research_project(project["id"])
    e = _entry(project, sid)
    e["decision_node_id"] = rec["id"]
    e["status"] = "decided"
    project["phase"] = _primary(project, spec)
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    return rec


def record_convergence(project_id: str, title: str, from_node_ids: list[str], payload: dict[str, Any],
                       start_input: str = "", store: Store | None = None) -> dict[str, Any]:
    """Legacy alias for record_decision."""
    return record_decision(project_id, title, from_node_ids, payload, start_input, store=store)


def advance(project_id: str, step_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Mark a step complete and recompute the frontier. Handles loop_back."""
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    ready = _ready(project, spec)
    if not ready:
        project["phase"] = COMPLETE
        store.upsert_research_project(project)
        return {"project": project, "step": COMPLETE, "phase": COMPLETE, "complete": True}
    sid = step_id or ready[0]
    step = _step(spec, sid)
    if step is None or sid not in ready:
        raise MethodologyError("PHASE_OUT_OF_ORDER", f"step '{sid}' is not on the ready frontier")
    e = _entry(project, sid)
    if _is_decide(step):
        if not e.get("decision_node_id"):
            raise MethodologyError("PHASE_OUT_OF_ORDER", f"record_decision for '{sid}' before advancing")
        # loop_back: a decided, unconsumed loop_back judgment reopens a prior step
        pending_lb = [j for j in _judgments(store, project["id"], sid, "loop_back")
                      if j.get("decided") and not j.get("_consumed")]
        if step["loop_back"] and pending_lb:
            target = step["loop_back"]
            j = pending_lb[-1]; j["_consumed"] = True; store.insert_methodology_judgment(j)
            _entry(project, target)["status"] = "active"
            _entry(project, target)["decision_node_id"] = None
            project["phase"] = target
            project["updated_at"] = utc_now_iso()
            store.upsert_research_project(project)
            return {"project": project, "step": target, "phase": target, "complete": False, "looped_back": True}
    e["status"] = "complete"
    # activate any steps that just became ready
    for nxt in _ready(project, spec):
        if project["phase_log"][nxt]["status"] == "pending":
            project["phase_log"][nxt]["status"] = "active"
    project["phase"] = _primary(project, spec)
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    complete = project["phase"] == COMPLETE
    return {"project": project, "step": project["phase"], "phase": project["phase"], "complete": complete}


def advance_phase(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """Legacy alias for advance."""
    return advance(project_id, store=store)


def get_methodology_state(project_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    plog = project.get("phase_log") or {}
    judg = store.list_methodology_judgments(project["id"])
    ready = set(_ready(project, spec))
    steps = []
    for s in spec["steps"]:
        log = plog.get(s["id"], {})
        raw = log.get("status", "pending")
        # surface a strip-friendly status: complete/decided -> "converged"; ready -> "active"
        if raw in ("complete", "decided"):
            status = "converged"
        elif s["id"] in ready and (log.get("node_ids") or raw == "active"):
            status = "active"
        elif s["id"] in ready:
            status = "active"
        else:
            status = "pending"
        steps.append({
            "key": s["id"], "name": s["name"], "mode": _mode(s), "role": s["produces"]["role"],
            "tags": s["tags"], "consumes": s["consumes"], "status": status,
            "produces": s["produces"], "requires": s["requires"],
            "exploration_count": len(log.get("node_ids", [])),
            "convergence_node": log.get("decision_node_id"),
            "judgments": [{"kind": j["kind"], "decided": j["decided"], "rationale": j["rationale"]}
                          for j in judg if j["phase_key"] == s["id"]],
        })
    complete = not ready
    return {"project_id": project["id"], "methodology": project["methodology"],
            "phase": COMPLETE if complete else _primary(project, spec),
            "complete": complete, "steps": steps, "phases": steps}
