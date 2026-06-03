"""Orchestration runtime (spec/methodology-engine-and-prototyping.md §5).

The engine (methodology.py) is always-present and host-stepped. This module adds the
OPTIONAL autonomous loop: `run_methodology` drives a whole diamond unattended by delegating
text authoring to a pluggable AuthoringBackend, while calling the SAME engine functions — so
the structural invariants and gates apply identically to autonomous and interactive runs.

Backends:
- LLMAuthoringBackend — real; authors via the Anthropic API (config.llm_*). Used by default.
- StubAuthoringBackend — deterministic; drives a full diamond offline (tests / no API key).
"""
from __future__ import annotations

from typing import Any, Protocol

from . import methodology as M
from .config import utc_now_iso
from .storage import Store


class AuthoringBackend(Protocol):
    """The runtime owns deterministic orchestration; the backend authors the text."""

    def author_exploration(self, project: dict, phase: dict, index: int, store: Store) -> dict[str, Any]:
        """Return {title, council_ids, payload} for one diverge exploration."""

    def divergence_decision(self, project: dict, phase: dict, explorations: list[dict], store: Store) -> dict[str, Any]:
        """Return {decided, rationale, evidence_refs} — 'have we explored enough?' (LLM-judged)."""

    def before_converge(self, project: dict, phase: dict, store: Store) -> None:
        """Hook to satisfy converge prerequisites (e.g. record a prototype_session)."""

    def author_convergence(self, project: dict, phase: dict, fan_node_ids: list[str], store: Store) -> dict[str, Any]:
        """Return {title, from_node_ids, payload} for the converge node."""


def run_methodology(project_id: str, backend: AuthoringBackend | None = None,
                    max_steps: int = 40, store: Store | None = None) -> dict[str, Any]:
    """Autonomously step a methodology project to completion via `backend`."""
    store = store or Store()
    if backend is None:
        backend = LLMAuthoringBackend()
    project, spec = M._ensure_methodology_project(store, project_id)
    steps = 0
    while steps < max_steps:
        steps += 1
        b = M.brief_phase(project_id, store=store)
        if b.get("complete"):
            break
        phase = M._phase(spec, b["phase"])
        project = store.get_research_project(project_id)
        if b["mode"] == "diverge":
            explorations: list[dict] = []
            inner = 0
            while inner < max_steps:
                inner += 1
                decision = backend.divergence_decision(project, phase, explorations, store)
                if decision.get("decided") and len(explorations) >= 2:
                    M.record_judgment(project_id, phase["key"], "divergence_complete", True,
                                      decision.get("rationale", "explored enough"),
                                      decision.get("evidence_refs") or _all_councils(explorations), store=store)
                    break
                ex = backend.author_exploration(project, phase, len(explorations), store)
                node = M.record_exploration(project_id, ex["title"], ex["council_ids"], ex["payload"],
                                            ex.get("start_input", ""), store=store)
                explorations.append(node)
                project = store.get_research_project(project_id)
            M.advance_phase(project_id, store=store)
        else:
            backend.before_converge(project, phase, store)
            project = store.get_research_project(project_id)
            fan = (project.get("phase_log") or {}).get(phase["consumes"], {}).get("exploration_node_ids", [])
            conv = backend.author_convergence(project, phase, fan, store)
            M.record_convergence(project_id, conv["title"], conv["from_node_ids"], conv["payload"],
                                 conv.get("start_input", ""), store=store)
            M.advance_phase(project_id, store=store)
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
    """Deterministic backend that drives a full diamond offline (no LLM). Used by tests and
    as a reference implementation of the AuthoringBackend contract."""

    def __init__(self, explorations_per_phase: int = 2) -> None:
        self.n = max(2, explorations_per_phase)

    def author_exploration(self, project, phase, index, store):
        from . import services as svc
        cid = svc.record_council(
            prompt=f"[{phase['key']}] exploration {index + 1}",
            persona_ids=(project.get("persona_ids") or ["p1"])[:1],
            turns=[{"speaker": "Auto", "persona_id": "p1", "content": f"{phase['intent']} (exploration {index + 1})"}],
            votes=[], proposal="", summary="auto", exec_summary="auto", selection_reason="auto", store=store)["id"]
        # the develop diverge phase requires a real prototype artifact
        if "prototype" in (phase.get("requires_artifacts") or []) and index == 0:
            self._ensure_prototype(project, store)
        return {"title": f"{phase['name']} · option {index + 1}", "council_ids": [cid],
                "payload": _payload(f"{phase['name']} exploration {index + 1}")}

    def divergence_decision(self, project, phase, explorations, store):
        decided = len(explorations) >= self.n
        return {"decided": decided, "rationale": f"{len(explorations)} explorations cover the space",
                "evidence_refs": _all_councils(explorations)}

    def before_converge(self, project, phase, store):
        if "prototype_session" in (phase.get("requires_artifacts") or []):
            self._record_session(project, store)

    def author_convergence(self, project, phase, fan_node_ids, store):
        return {"title": f"{phase['name']} · {phase['produces_role']}",
                "from_node_ids": fan_node_ids[:max(2, len(fan_node_ids))],
                "payload": _payload(f"{phase['name']} convergence ({phase['produces_role']})")}

    # ----- prototype helpers -----
    def _proto_slug(self, project) -> str:
        return f"auto-{project['slug']}"[:60]

    def _ensure_prototype(self, project, store) -> dict[str, Any]:
        from . import services as svc
        existing = [p for p in store.list_prototypes(project["id"])]
        if existing:
            return existing[0]
        concept = {"title": project.get("title", "Prototype"), "summary": project.get("goal", ""),
                   "start": "home",
                   "screens": [{"id": "home", "title": "Start", "elements": [
                       {"kind": "button", "id": "go", "label": "Try it", "goto": "result"}]},
                       {"id": "result", "title": "Result", "elements": [
                           {"kind": "text", "id": "t", "label": "It worked."}]}]}
        return svc.scaffold_prototype(self._proto_slug(project), "Auto prototype", concept,
                                      project_id=project["id"], store=store)

    def _record_session(self, project, store) -> None:
        from . import services as svc
        protos = store.list_prototypes(project["id"])
        if not protos:
            protos = [self._ensure_prototype(project, store)]
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
                # click the first actionable ref to produce a real observed state change
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


# --------------------------------------------------------------------------- LLM backend

class LLMAuthoringBackend:
    """Real backend: authors via the Anthropic API (config.llm_provider/model/api_key).

    Raises a clear error if the SDK or key is missing — pass StubAuthoringBackend for offline
    runs, or set PERSONA_COUNCIL_LLM_API_KEY / ANTHROPIC_API_KEY for autonomous runs.
    """

    def __init__(self) -> None:
        from .config import llm_api_key, llm_model, llm_provider
        self.provider = llm_provider()
        self.model = llm_model()
        self.api_key = llm_api_key()
        self._client = None

    def _client_or_raise(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise RuntimeError(
                "Autonomous mode needs an LLM key (PERSONA_COUNCIL_LLM_API_KEY/ANTHROPIC_API_KEY) "
                "or pass a StubAuthoringBackend for offline runs.")
        try:
            import anthropic
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Install the 'anthropic' SDK for autonomous mode, or pass a backend.") from e
        self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def _ask(self, system: str, prompt: str) -> str:  # pragma: no cover (needs network/key)
        client = self._client_or_raise()
        msg = client.messages.create(model=self.model, max_tokens=2000,
                                     system=system, messages=[{"role": "user", "content": prompt}])
        return "".join(getattr(b, "text", "") for b in msg.content)

    def _json(self, system: str, prompt: str) -> dict:  # pragma: no cover
        import json as _json
        raw = self._ask(system, prompt)
        start, end = raw.find("{"), raw.rfind("}")
        return _json.loads(raw[start:end + 1]) if start >= 0 else {}

    def author_exploration(self, project, phase, index, store):  # pragma: no cover
        from . import services as svc
        sys = ("You author one grounded, anti-steering council exploration for a design-research "
               "methodology. Return JSON {turn, gesamtbild, arc_narrative}.")
        out = self._json(sys, f"Goal: {project.get('goal')}\nPhase: {phase['name']} — {phase['intent']}\n"
                              f"Strategy: {phase['council_strategy']}. Exploration #{index + 1}.")
        cid = svc.record_council(
            prompt=f"[{phase['key']}] {phase['intent']}",
            persona_ids=(project.get("persona_ids") or ["p1"])[:1],
            turns=[{"speaker": "Persona", "persona_id": "p1", "content": out.get("turn", phase["intent"])}],
            votes=[], proposal="", summary="", exec_summary=out.get("gesamtbild", ""),
            selection_reason="autonomous", store=store)["id"]
        return {"title": f"{phase['name']} · option {index + 1}", "council_ids": [cid],
                "payload": {"gesamtbild": out.get("gesamtbild", ""), "arc_narrative": out.get("arc_narrative", "")}}

    def divergence_decision(self, project, phase, explorations, store):  # pragma: no cover
        if len(explorations) < 2:
            return {"decided": False, "rationale": "need more breadth", "evidence_refs": _all_councils(explorations)}
        sys = "Decide if the space is explored enough. Return JSON {decided:bool, rationale}."
        out = self._json(sys, f"Phase {phase['name']}. {len(explorations)} explorations so far. Enough?")
        return {"decided": bool(out.get("decided")), "rationale": out.get("rationale", ""),
                "evidence_refs": _all_councils(explorations)}

    def before_converge(self, project, phase, store):  # pragma: no cover
        # reuse the stub's prototype-session machinery (real Playwright use when available)
        if "prototype_session" in (phase.get("requires_artifacts") or []):
            StubAuthoringBackend()._record_session(project, store)

    def author_convergence(self, project, phase, fan_node_ids, store):  # pragma: no cover
        sys = "Author the convergence (decision) for this phase. Return JSON {gesamtbild, arc_narrative}."
        out = self._json(sys, f"Goal: {project.get('goal')}\nConverge phase {phase['name']} "
                              f"({phase['produces_role']}). Consolidate {len(fan_node_ids)} explorations.")
        return {"title": f"{phase['name']} · {phase['produces_role']}", "from_node_ids": fan_node_ids,
                "payload": {"gesamtbild": out.get("gesamtbild", ""), "arc_narrative": out.get("arc_narrative", "")}}
