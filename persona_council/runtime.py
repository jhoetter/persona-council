"""Orchestration runtime (spec/methodology-constellations.md §4 / §6).

The engine (methodology.py) is always-present and host-stepped. This module adds a STRUCTURAL
orchestration loop: `run_methodology` walks the constellation's topological frontier, delegating
text authoring to a pluggable AuthoringBackend while calling the SAME engine functions — so the
structural invariants and gates apply identically.

IMPORTANT (locked principle): there is NO in-process LLM text-generation backend. Real runs are
driven by the HOST (Claude) or its subagents authoring text via the MCP brief_*→record_* contract
(see the design-thinking-deep / methodology-run skills). The only backend shipped here is
`StubAuthoringBackend` — deterministic, for tests and as the AuthoringBackend reference. The
OpenAI key is embeddings + image generation only; it is never used for authoring.
"""
from __future__ import annotations

from typing import Any, Protocol

from . import methodology as M
from .config import utc_now_iso
from .storage import Store


class AuthoringBackend(Protocol):
    """The runtime owns deterministic orchestration; the backend authors the text."""

    def author_exploration(self, project: dict, step: dict, index: int, store: Store) -> dict[str, Any]:
        """Return {title, council_ids, payload} for one fan exploration node."""

    def divergence_decision(self, project: dict, step: dict, explorations: list[dict], store: Store) -> dict[str, Any]:
        """Return {decided, rationale, evidence_refs} — 'have we explored enough?' (LLM-judged)."""

    def before_decide(self, project: dict, step: dict, store: Store) -> None:
        """Hook to satisfy a decide step's prerequisites (e.g. record a required session)."""

    def author_decision(self, project: dict, step: dict, fan_node_ids: list[str], store: Store) -> dict[str, Any]:
        """Return {title, from_node_ids, payload} for the decision (waist) node."""


def run_methodology(project_id: str, backend: AuthoringBackend | None = None,
                    max_steps: int = 60, store: Store | None = None) -> dict[str, Any]:
    """Autonomously walk a constellation's frontier to completion via `backend`."""
    store = store or Store()
    if backend is None:
        backend = StubAuthoringBackend()
    project, spec = M._ensure_methodology_project(store, project_id)
    steps = 0
    while steps < max_steps:
        steps += 1
        b = M.brief_next(project_id, store=store)
        if b.get("complete"):
            break
        sid = b["step"]
        step = M._step(spec, sid)
        project = store.get_research_project(project_id)
        if not M._is_decide(step):
            explorations: list[dict] = []
            inner = 0
            while inner < max_steps:
                inner += 1
                decision = backend.divergence_decision(project, step, explorations, store)
                if decision.get("decided") and len(explorations) >= 2:
                    gate = M._gate_tag_for_fan(spec, sid)
                    if gate:
                        M.record_judgment(project_id, sid, gate, True,
                                          decision.get("rationale", "explored enough"),
                                          decision.get("evidence_refs") or _all_councils(explorations), store=store)
                    break
                ex = backend.author_exploration(project, step, len(explorations), store)
                node = M.record_node(project_id, ex["title"], ex["council_ids"], ex["payload"],
                                     ex.get("start_input", ""), step_id=sid, store=store)
                explorations.append(node)
                project = store.get_research_project(project_id)
            M.advance(project_id, sid, store=store)
        else:
            backend.before_decide(project, step, store)
            project = store.get_research_project(project_id)
            fan = [n for c in step["consumes"] for n in M._nodes(project, c)]
            conv = backend.author_decision(project, step, fan, store)
            M.record_decision(project_id, conv["title"], conv["from_node_ids"], conv["payload"],
                              conv.get("start_input", ""), step_id=sid, store=store)
            M.advance(project_id, sid, store=store)
    return M.get_methodology_state(project_id, store=store)


def _all_councils(explorations: list[dict]) -> list[str]:
    out: list[str] = []
    for e in explorations:
        for c in e.get("council_ids", []):
            if c not in out:
                out.append(c)
    return out or ["auto"]


# --------------------------------------------------------------------------- stub backend

def _payload(text: str) -> dict[str, Any]:
    return {"gesamtbild": text, "arc_narrative": text}


class StubAuthoringBackend:
    """Deterministic backend that drives a full constellation offline (no LLM). Used by tests and
    as a reference implementation of the AuthoringBackend contract."""

    def __init__(self, explorations_per_phase: int = 2) -> None:
        self.n = max(2, explorations_per_phase)

    def author_exploration(self, project, step, index, store):
        from . import services as svc
        cid = svc.record_council(
            project_id=project["id"],
            prompt=f"[{step['id']}] exploration {index + 1}",
            persona_ids=(project.get("persona_ids") or ["p1"])[:1],
            turns=[{"speaker": "Auto", "persona_id": "p1", "content": f"{step['intent']} (exploration {index + 1})"}],
            votes=[], proposal="", summary="auto", exec_summary="auto", selection_reason="auto", store=store)["id"]
        # a build step produces a real artifact of its declared type
        if step["produces"].get("artifact_type") == "prototype" and index == 0:
            fid = (step["produces"].get("more_tags") or [None])[0]
            self._ensure_prototype(project, store, fidelity=fid)
        return {"title": f"{step['name']} · option {index + 1}", "council_ids": [cid],
                "payload": _payload(f"{step['name']} exploration {index + 1}")}

    def divergence_decision(self, project, step, explorations, store):
        decided = len(explorations) >= self.n
        return {"decided": decided, "rationale": f"{len(explorations)} explorations cover the space",
                "evidence_refs": _all_councils(explorations)}

    def before_decide(self, project, step, store):
        for tg in step["requires"].get("session_of_tags") or []:
            self._record_session(project, store, tag=tg)

    def author_decision(self, project, step, fan_node_ids, store):
        role = step["produces"].get("role") or "decision"
        return {"title": f"{step['name']} · {role}",
                "from_node_ids": fan_node_ids[:max(2, len(fan_node_ids))],
                "payload": _payload(f"{step['name']} decision ({role})")}

    # ----- prototype helpers -----
    def _proto_slug(self, project, fidelity=None) -> str:
        suffix = f"-{fidelity}" if fidelity else ""
        return f"auto-{project['slug']}{suffix}"[:60]

    def _ensure_prototype(self, project, store, fidelity=None) -> dict[str, Any]:
        from . import services as svc
        want = {"prototype"} | ({fidelity} if fidelity else set())
        for p in store.list_prototypes(project["id"]):
            if want <= M._artifact_tags(p):
                return p
        concept = {"title": project.get("title", "Prototype"), "summary": project.get("goal", ""),
                   "start": "home",
                   "screens": [{"id": "home", "title": "Start", "elements": [
                       {"kind": "button", "id": "go", "label": "Try it", "goto": "result"}]},
                       {"id": "result", "title": "Result", "elements": [
                           {"kind": "text", "id": "t", "label": "It worked."}]}]}
        return svc.scaffold_prototype(self._proto_slug(project, fidelity), "Auto prototype", concept,
                                      project_id=project["id"], fidelity=fidelity, store=store)

    def _record_session(self, project, store, tag="prototype") -> None:
        from . import services as svc
        protos = [p for p in store.list_prototypes(project["id"]) if tag in M._artifact_tags(p)]
        if not protos:
            from . import presentation as _pres
            fid = tag if tag in _pres.discriminator_tags("prototype") else None
            protos = [self._ensure_prototype(project, store, fidelity=fid)]
        proto = protos[0]
        persona = (project.get("persona_ids") or ["auto"])[0]
        observed = ["It worked."]
        session_id = "offline"
        try:
            from . import browser
            if browser.available():
                run = svc.run_prototype(proto["id"], store=store)
                opened = browser.open_session(run["url"], proto["id"], persona)
                session_id = opened["session_id"]
                tree = opened["snapshot"]["tree"]
                nodes = tree if isinstance(tree, list) else [tree]
                ref = next((n["ref"] for n in nodes if n.get("ref")), None)
                if ref:
                    out = browser.act(session_id, {"type": "click", "ref": ref})
                    observed = ["It worked." if "It worked." in out["snapshot"]["text"] else (out["snapshot"]["text"][:40] or "state")]
        except Exception:
            pass
        try:
            svc.record_prototype_session(persona, proto["id"], session_id, utc_now_iso()[:10],
                                         {"summary": "auto session", "liked": observed,
                                          "observed_state_refs": observed, "verdict": "ok"}, store=store)
        finally:
            try:
                from . import browser
                if session_id != "offline":
                    browser.close(session_id)
                svc.stop_prototype(proto["id"], store=store)
            except Exception:
                pass
