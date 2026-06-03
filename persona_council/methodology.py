"""Methodology engine (spec/methodology-engine-and-prototyping.md, Pillar A + §5 engine).

Data-driven methodologies (registry) + a structure-enforcing, LLM-judged engine. The
engine guarantees SHAPE (diverge-before-converge, breadth exists, traceability) and never
hardcodes DYNAMICS: "explored enough?", "is this the core problem?" are LLM judgments
recorded with evidence (record_judgment), which the engine only requires the PRESENCE of.

This module is the always-present, host-stepped engine. The optional autonomous loop lives
in runtime.py (M5) and calls these same functions.
"""
from __future__ import annotations

import json
from typing import Any

from .config import methodologies_dir, utc_now_iso
from .models import MethodologyJudgment
from .storage import Store

MODES = {"diverge", "converge"}
# Exploration (diverge) roles vs decision (converge) roles. Expanded for the deep
# methodology (spec/deep-design-thinking-and-diamond.md §4.1).
DIVERGE_ROLES = {"problem-landscape", "solution-options"}
CONVERGE_ROLES = {"key-problems", "point-of-view", "solution-shortlist", "solution-presentation", "spec"}
ROLES = DIVERGE_ROLES | CONVERGE_ROLES
FIDELITIES = {"lofi", "midfi"}
JUDGMENT_KINDS = {"divergence_complete", "core_problem_chosen", "spec_ready", "loop_back"}
COMPLETE = "__complete__"


class MethodologyError(Exception):
    """Carries a stable code (§8.4) so callers/tests can assert the exact violation."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# --------------------------------------------------------------------------- registry

def validate_methodology_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise MethodologyError("BAD_SPEC", "methodology spec must be an object")
    for k in ("key", "name", "description", "when_to_use", "phases"):
        if not spec.get(k):
            raise MethodologyError("BAD_SPEC", f"methodology spec missing '{k}'")
    phases = spec["phases"]
    if not isinstance(phases, list) or len(phases) < 2:
        raise MethodologyError("BAD_SPEC", "methodology needs >= 2 phases")
    keys = [p.get("key") for p in phases]
    if len(set(keys)) != len(keys) or not all(keys):
        raise MethodologyError("BAD_SPEC", "phase keys must be present and unique")
    if phases[0].get("mode") != "diverge":
        raise MethodologyError("BAD_SPEC", "first phase must be mode=diverge")
    for i, p in enumerate(phases):
        mode = p.get("mode")
        if mode not in MODES:
            raise MethodologyError("BAD_SPEC", f"phase {p.get('key')} mode must be diverge|converge")
        # modes alternate diverge,converge,...
        if mode != ("diverge" if i % 2 == 0 else "converge"):
            raise MethodologyError("BAD_SPEC", "phase modes must alternate diverge,converge,...")
        if p.get("produces_role") not in ROLES:
            raise MethodologyError("BAD_SPEC", f"phase {p.get('key')} produces_role invalid")
        if mode == "diverge" and p["produces_role"] not in DIVERGE_ROLES:
            raise MethodologyError("BAD_SPEC", "diverge phase role must be problem-landscape|solution-options")
        if mode == "converge":
            if p["produces_role"] not in CONVERGE_ROLES:
                raise MethodologyError("BAD_SPEC", "converge phase role must be point-of-view|spec")
            consumes = p.get("consumes")
            if consumes != keys[i - 1]:
                raise MethodologyError("BAD_SPEC", f"converge phase {p['key']} must consume the preceding diverge phase")
        if not p.get("council_strategy"):
            raise MethodologyError("BAD_SPEC", f"phase {p.get('key')} needs a council_strategy")
        if p.get("fidelity") and p["fidelity"] not in FIDELITIES:
            raise MethodologyError("BAD_SPEC", f"phase {p.get('key')} fidelity must be lofi|midfi")
        lb = p.get("loop_back")
        if lb and lb not in keys:
            raise MethodologyError("BAD_SPEC", f"loop_back target '{lb}' is not a phase key")
    return spec


def _load_builtin_specs() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    d = methodologies_dir()
    if not d.exists():
        return out
    for path in sorted(d.glob("*.json")):
        spec = json.loads(path.read_text(encoding="utf-8"))
        validate_methodology_spec(spec)
        out[spec["key"]] = spec
    return out


def registry(store: Store | None = None) -> dict[str, dict[str, Any]]:
    """Built-in specs (from package files) overlaid with user-defined ones (from DB)."""
    store = store or Store()
    specs = _load_builtin_specs()
    for spec in store.list_methodologies():
        specs[spec["key"]] = spec
    return specs


def list_methodologies(store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    return [
        {"key": s["key"], "name": s["name"], "description": s["description"],
         "when_to_use": s["when_to_use"], "phase_keys": [p["key"] for p in s["phases"]]}
        for s in registry(store).values()
    ]


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

def _phase(spec: dict[str, Any], key: str) -> dict[str, Any] | None:
    return next((p for p in spec["phases"] if p["key"] == key), None)


def _phase_index(spec: dict[str, Any], key: str) -> int:
    return next((i for i, p in enumerate(spec["phases"]) if p["key"] == key), -1)


def _judgments(store: Store, project_id: str, phase_key: str | None = None,
               kind: str | None = None) -> list[dict[str, Any]]:
    out = store.list_methodology_judgments(project_id)
    if phase_key:
        out = [j for j in out if j["phase_key"] == phase_key]
    if kind:
        out = [j for j in out if j["kind"] == kind]
    return out


def _explorations(project: dict[str, Any], phase_key: str) -> list[str]:
    return list((project.get("phase_log") or {}).get(phase_key, {}).get("exploration_node_ids", []))


def _ensure_methodology_project(store: Store, project_id: str) -> tuple[dict, dict]:
    p = store.get_research_project(project_id)
    if not p:
        raise MethodologyError("UNKNOWN_PROJECT", f"Unknown research project: {project_id}")
    if not p.get("methodology"):
        raise MethodologyError("NO_METHODOLOGY", f"Project {project_id} has no methodology bound")
    return p, get_methodology(p["methodology"], store)


# --------------------------------------------------------------------------- engine

def start_methodology_project(title: str, goal: str, methodology_key: str,
                              persona_ids: list[str] | None = None, description: str = "",
                              store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    spec = get_methodology(methodology_key, store)
    from . import services as svc
    project = svc.create_research_project(title, goal=goal, persona_ids=persona_ids,
                                          description=description, store=store)
    first = spec["phases"][0]["key"]
    project["methodology"] = methodology_key
    project["phase"] = first
    project["phase_log"] = {first: {"status": "active", "mode": "diverge",
                                     "exploration_node_ids": [], "convergence_node_id": None,
                                     "decided_at": None}}
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    return project


def set_project_methodology(project_id: str, methodology_key: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    spec = get_methodology(methodology_key, store)
    p = store.get_research_project(project_id)
    if not p:
        raise MethodologyError("UNKNOWN_PROJECT", f"Unknown research project: {project_id}")
    first = spec["phases"][0]["key"]
    p["methodology"] = methodology_key
    p["phase"] = first
    p.setdefault("phase_log", {})
    p["phase_log"].setdefault(first, {"status": "active", "mode": "diverge",
                                      "exploration_node_ids": [], "convergence_node_id": None,
                                      "decided_at": None})
    p["updated_at"] = utc_now_iso()
    store.upsert_research_project(p)
    return p


def brief_phase(project_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    cur = project.get("phase")
    if cur == COMPLETE or not cur:
        return {"project_id": project["id"], "complete": True,
                "instructions": "The methodology run is complete. Export the meta-report for the handover."}
    phase = _phase(spec, cur)
    consumed_node = None
    if phase.get("consumes"):
        cid = (project.get("phase_log") or {}).get(phase["consumes"], {}).get("convergence_node_id")
        if cid:
            consumed_node = store.get_synthesis(cid)
    unmet: list[str] = []
    if phase["mode"] == "diverge":
        n = len(_explorations(project, cur))
        if n < 2:
            unmet.append(f"record >= 2 distinct explorations (have {n})")
        if not _judgments(store, project["id"], cur, "divergence_complete"):
            unmet.append("record an evidence-backed `divergence_complete` judgment, then advance_phase")
        instr = (f"DIVERGE phase '{phase['name']}' (strategy={phase['council_strategy']}). Fan out — "
                 f"run a council per {phase.get('diverge_by', 'angle')} and `record_exploration` each. "
                 f"Decide WHEN to stop with your own evidence ('have we explored enough?'), then "
                 f"`record_judgment(kind=divergence_complete)` and `advance_phase`.")
    else:
        consumed = phase["consumes"]
        n = len(_explorations(project, consumed))
        if n < 2:
            unmet.append(f"the consumed diverge phase '{consumed}' needs >= 2 explorations (have {n})")
        if not _judgments(store, project["id"], consumed, "divergence_complete"):
            unmet.append(f"a `divergence_complete` judgment for '{consumed}' must exist")
        instr = (f"CONVERGE phase '{phase['name']}' (strategy={phase['council_strategy']}). Cluster the "
                 f"'{consumed}' fan into one {phase['produces_role']} via `record_convergence` "
                 f"(from_node_ids = the explorations you consolidate), then `advance_phase`.")
    return {
        "project_id": project["id"], "phase": cur, "name": phase["name"], "mode": phase["mode"],
        "intent": phase["intent"], "council_strategy": phase["council_strategy"],
        "diverge_by": phase.get("diverge_by"), "consumes": phase.get("consumes"),
        "requires_artifacts": phase.get("requires_artifacts", []),
        "produces_role": phase["produces_role"], "unmet": unmet, "complete": False,
        "instructions": instr,
        "frame": {
            "goal": project.get("goal", ""), "persona_ids": project.get("persona_ids", []),
            "methodology": project["methodology"], "consumed_artifact": consumed_node,
        },
    }


def _node_payload(title: str, start_input: str, council_ids: list[str], payload: dict[str, Any],
                  project: dict, phase: dict, mode: str, store: Store) -> dict[str, Any]:
    """Create a Synthesis node via the existing synthesis path, then stamp engine metadata."""
    from . import services as svc
    rec = svc.record_synthesis(title=title, start_input=start_input, council_ids=council_ids,
                               payload=payload, goal=project.get("goal", ""), store=store)
    rec["phase"] = phase["key"]
    rec["mode"] = mode
    rec["role"] = phase["produces_role"]
    rec["methodology"] = project["methodology"]
    # converge-node enrichments (affinity clusters, key problems, down-select ranking)
    if isinstance(payload, dict):
        for k in ("clusters", "key_problems", "ranking", "shortlist"):
            if payload.get(k):
                rec[k] = payload[k]
    store.upsert_synthesis(rec)
    return rec


def record_exploration(project_id: str, title: str, council_ids: list[str], payload: dict[str, Any],
                       start_input: str = "", store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    cur = project.get("phase")
    phase = _phase(spec, cur) if cur else None
    if not phase or phase["mode"] != "diverge":
        raise MethodologyError("PHASE_OUT_OF_ORDER",
                               "record_exploration is only valid during a diverge phase")
    if not council_ids:
        raise MethodologyError("NO_COUNCIL_CITED", "an exploration must cite >= 1 council")
    rec = _node_payload(title, start_input or project.get("goal", ""), council_ids, payload,
                        project, phase, "diverge", store)
    from . import services as svc
    svc.add_study_to_project(project["id"], rec["id"], store=store)
    # link the prior phase's convergence into this exploration (waist -> fan)
    project = store.get_research_project(project["id"])
    plog = project.setdefault("phase_log", {})
    if cur not in plog:
        plog[cur] = {"status": "active", "mode": "diverge", "exploration_node_ids": [],
                     "convergence_node_id": None, "decided_at": None}
    idx = _phase_index(spec, cur)
    if idx >= 1:
        prev_conv = plog.get(spec["phases"][idx - 1]["key"], {}).get("convergence_node_id")
        if prev_conv:
            try:
                svc.link_studies(project["id"], prev_conv, rec["id"], "spawned_from",
                                 rationale=f"{spec['phases'][idx-1]['key']} -> {cur} (waist to fan)", store=store)
            except Exception:
                pass
        project = store.get_research_project(project["id"])
        plog = project.setdefault("phase_log", {})
    plog[cur].setdefault("exploration_node_ids", []).append(rec["id"])
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    return rec


def record_judgment(project_id: str, phase_key: str, kind: str, decided: bool, rationale: str,
                    evidence_refs: list[str] | None = None, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    if kind not in JUDGMENT_KINDS:
        raise MethodologyError("BAD_JUDGMENT", f"judgment kind must be one of {sorted(JUDGMENT_KINDS)}")
    if _phase(spec, phase_key) is None:
        raise MethodologyError("BAD_JUDGMENT", f"unknown phase '{phase_key}'")
    refs = [str(r) for r in (evidence_refs or []) if str(r).strip()]
    if decided and not rationale.strip():
        raise MethodologyError("BAD_JUDGMENT", "a decided judgment needs a rationale")
    if decided and kind == "divergence_complete" and not refs:
        raise MethodologyError("BAD_JUDGMENT", "divergence_complete needs >= 1 evidence_ref")
    now = utc_now_iso()
    j = MethodologyJudgment(
        id=_judgment_id(project["id"], phase_key, kind, now), project_id=project["id"],
        phase_key=phase_key, kind=kind, decided=bool(decided), rationale=rationale.strip(),
        evidence_refs=refs, created_at=now,
    ).to_dict()
    store.insert_methodology_judgment(j)
    return j


def _judgment_id(project_id: str, phase_key: str, kind: str, now: str) -> str:
    from .services import stable_id
    return stable_id("judgment", project_id, phase_key, kind, now)


def record_convergence(project_id: str, title: str, from_node_ids: list[str], payload: dict[str, Any],
                       start_input: str = "", store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    cur = project.get("phase")
    phase = _phase(spec, cur) if cur else None
    if not phase or phase["mode"] != "converge":
        raise MethodologyError("PHASE_OUT_OF_ORDER",
                               "record_convergence is only valid during a converge phase")
    consumed = phase["consumes"]
    fan = _explorations(project, consumed)
    # INV-BREADTH
    if len(fan) < 2:
        raise MethodologyError("BREADTH_TOO_LOW",
                               f"converge needs >= 2 explorations in '{consumed}' (have {len(fan)})")
    # INV-JUDGE
    dj = [j for j in _judgments(store, project["id"], consumed, "divergence_complete") if j.get("decided")]
    if not dj:
        raise MethodologyError("MISSING_DIVERGENCE_JUDGMENT",
                               f"need a decided divergence_complete judgment for '{consumed}'")
    # INV-EDGES
    chosen = [n for n in (from_node_ids or []) if n in fan]
    if not chosen:
        raise MethodologyError("EDGES_NOT_FROM_FAN",
                               f"from_node_ids must be explorations of '{consumed}'")
    # INV-ARTIFACT (prototype on the consumed diverge phase; prototype_session on this converge phase)
    consumed_phase = _phase(spec, consumed)
    if "prototype" in (consumed_phase.get("requires_artifacts") or []):
        if not store.list_prototypes(project["id"]):
            raise MethodologyError("MISSING_ARTIFACT",
                                   f"phase '{consumed}' requires >= 1 prototype linked to the project")
    if "prototype_session" in (phase.get("requires_artifacts") or []):
        sessions = [s for s in store.list_prototype_sessions()
                    if (s.get("reaction") or {}).get("project_id") == project["id"]
                    or store.get_prototype(s.get("prototype_id", "")) and
                    (store.get_prototype(s["prototype_id"]) or {}).get("project_id") == project["id"]]
        if not sessions:
            raise MethodologyError("MISSING_ARTIFACT",
                                   f"phase '{phase['key']}' requires >= 1 recorded prototype_session")
    # INV-CITE: convergence cites the union of its fan's councils
    cited: list[str] = []
    for nid in chosen:
        syn = store.get_synthesis(nid) or {}
        for c in syn.get("council_ids", []):
            if c not in cited:
                cited.append(c)
    if not cited:
        raise MethodologyError("NO_COUNCIL_CITED", "consumed explorations cite no councils")
    rec = _node_payload(title, start_input or project.get("goal", ""), cited, payload,
                        project, phase, "converge", store)
    from . import services as svc
    svc.add_study_to_project(project["id"], rec["id"], store=store)
    for nid in chosen:
        try:
            svc.link_studies(project["id"], nid, rec["id"], "refines",
                             rationale=f"{consumed} fan -> {cur} waist", store=store)
        except Exception:
            pass
    project = store.get_research_project(project["id"])
    plog = project.setdefault("phase_log", {})
    plog.setdefault(cur, {"status": "active", "mode": "converge", "exploration_node_ids": [],
                          "convergence_node_id": None, "decided_at": None})
    plog[cur]["convergence_node_id"] = rec["id"]
    plog[cur]["status"] = "converged"
    if consumed in plog:
        plog[consumed]["status"] = "converged"
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    return rec


def advance_phase(project_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    cur = project.get("phase")
    if cur == COMPLETE or not cur:
        return {"project": project, "phase": COMPLETE, "complete": True}
    phase = _phase(spec, cur)
    idx = _phase_index(spec, cur)
    plog = project.setdefault("phase_log", {})
    if phase["mode"] == "diverge":
        # cursor may advance freely; the work-gate is enforced at record_convergence.
        nxt = spec["phases"][idx + 1]["key"]
    else:
        if not plog.get(cur, {}).get("convergence_node_id"):
            raise MethodologyError("PHASE_OUT_OF_ORDER",
                                   f"record_convergence for '{cur}' before advancing")
        # loop_back: a decided, unconsumed loop_back judgment sends us back to a prior diverge phase
        pending_lb = [j for j in _judgments(store, project["id"], cur, "loop_back")
                      if j.get("decided") and not j.get("_consumed")]
        if phase.get("loop_back") and pending_lb:
            target = phase["loop_back"]
            j = pending_lb[-1]; j["_consumed"] = True; store.insert_methodology_judgment(j)
            plog.setdefault(target, {"status": "active", "mode": "diverge",
                                     "exploration_node_ids": [], "convergence_node_id": None,
                                     "decided_at": None})
            plog[target]["status"] = "active"
            project["phase"] = target
            project["updated_at"] = utc_now_iso()
            store.upsert_research_project(project)
            return {"project": project, "phase": target, "complete": False, "looped_back": True}
        nxt = spec["phases"][idx + 1]["key"] if idx + 1 < len(spec["phases"]) else COMPLETE
    if nxt != COMPLETE:
        plog.setdefault(nxt, {"status": "active", "mode": _phase(spec, nxt)["mode"],
                              "exploration_node_ids": [], "convergence_node_id": None, "decided_at": None})
    project["phase"] = nxt
    project["updated_at"] = utc_now_iso()
    store.upsert_research_project(project)
    return {"project": project, "phase": nxt, "complete": nxt == COMPLETE}


def get_methodology_state(project_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    project, spec = _ensure_methodology_project(store, project_id)
    plog = project.get("phase_log") or {}
    judg = store.list_methodology_judgments(project["id"])
    phases = []
    for p in spec["phases"]:
        log = plog.get(p["key"], {})
        phases.append({
            "key": p["key"], "name": p["name"], "mode": p["mode"], "role": p["produces_role"],
            "status": log.get("status", "pending"),
            "exploration_count": len(log.get("exploration_node_ids", [])),
            "convergence_node": log.get("convergence_node_id"),
            "judgments": [{"kind": j["kind"], "decided": j["decided"], "rationale": j["rationale"]}
                          for j in judg if j["phase_key"] == p["key"]],
        })
    return {"project_id": project["id"], "methodology": project["methodology"],
            "phase": project.get("phase"), "complete": project.get("phase") == COMPLETE,
            "phases": phases}
