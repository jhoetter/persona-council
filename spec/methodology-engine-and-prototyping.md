# Methodology Engine & Agent-Usable Prototyping — Specification

> **Status:** DESIGN (authored 2026-06-03). **Substantial development**, staged M1–M5.
> **Supersedes** the facilitation-only framing in `spec/design-thinking-methodology.md`
> (kept for history; see §1 for why it was insufficient).
> **Decisions locked with the user:** (1) persona-agents use prototypes via a **headless
> browser (Playwright)** — they drive the *real running app*; (2) methodologies are a
> **data-driven registry** (declarative specs + an engine), so we can *choose from approaches*
> and add new ones without code; (3) this spec is written **before** implementation.
> **Leitsatz (unchanged):** nothing hardcoded as outcomes; MCP exposes capabilities; the host
> authors all *text* (`brief_* → author → record_*`); every claim traceable; personas
> non-directional (anti-steering). The persona **experience-driven** loop stays the foundation.

---

## 1. Why the first attempt failed (the lessons this spec encodes)

A facilitation-only attempt (one skill + phase tags on syntheses) was run end-to-end on a
Double Diamond. It produced a **chain, not two diamonds**, and a **prototype that no agent ever
ran**. Concretely:

1. **No divergence.** The defining property of the method is *fan out, then converge — twice*.
   The run did **one council per phase** → four nodes in a straight line. There was no broad
   problem exploration and no broad solution ideation. The shape (the literal screenshot: four
   boxes in a row) proves the method was *labelled*, not *applied*.
2. **No real software artifact.** The prototype was a static file *described in prose* to the
   personas; "the persona used it" was authored fiction. There was **no mechanism for an agent
   to invoke, drive, and observe a real running app** and react to what it actually did.
3. **Methodology was not first-class.** It was a hardcoded playbook + tags — not selectable, not
   shaping breadth/gates/graph-shape.
4. **The facilitator ventriloquized convergence** instead of the method producing it.

**What was sound and is kept:** the graph substrate (Project ⊃ Synthesis ⊃ Council, typed
edges, `voices`, meta-report), the host-authoring contract, anti-steering, and the
experience→memory seam *concept*. This spec keeps all of it and adds the two missing engines:
a **methodology engine** that produces real divergence/convergence, and an **agent-usable
prototype harness** that lets personas drive real apps.

**Definition of done that would have caught the failure** (every milestone is tested against
these): a diverge phase MUST yield ≥N distinct exploration nodes; a converge phase MUST record
a gate decision over them; a prototype reaction MUST cite a **real observed UI state** captured
from a Playwright snapshot (verifiable in the run log), not a prose paraphrase.

---

## 2. Architecture overview (three pillars over the unchanged foundation)

```
                 ┌──────────────────────────────────────────────────────────┐
                 │  FOUNDATION (unchanged)                                    │
                 │  personas · experience/memory · councils · syntheses ·     │
                 │  research graph · meta-report · host-authoring · anti-steer│
                 └──────────────────────────────────────────────────────────┘
   Pillar A  ───────────────────────┐        ┌─────────────────── Pillar B
   METHODOLOGY ENGINE                │        │   PROTOTYPE + AGENT HARNESS
   data-driven registry of methods; │        │   scaffold real apps; local runner;
   a driver that enforces           │        │   Playwright: agents OPEN/ACT/READ a
   diverge(fan-out)→converge(gate),│        │   real running app; reactions become
   per the chosen methodology       │        │   grounded experiences → councils
                 └───────────────┬───────────┘
                                 │ Pillar C (later, M5): HARNESS DEEP-DIVE
                                 │ how persona-subagents are spawned/grounded/parallelized
```

- **Pillar A** makes the *process* real and selectable (fixes failures #1, #3, #4).
- **Pillar B** makes the *artifacts* real and agent-usable (fixes failure #2).
- **Pillar C** is the explicitly-deferred harness investigation.

---

## 3. Pillar A — Methodology engine (data-driven, selectable)

### 3.1 A methodology is declarative data
Built-ins ship as specs in `persona_council/methodologies/*.json` (loaded into a registry at
import); user-defined methodologies persist in a `methodologies` table (same JSON-blob pattern).
A methodology spec:

```jsonc
{
  "key": "double_diamond",
  "name": "Double Diamond",
  "description": "Problem space (Discover→Define) then solution space (Develop→Deliver).",
  "when_to_use": "Frame an ambiguous problem and take it to a buildable solution.",
  "phases": [
    {
      "key": "discover", "name": "Discover", "mode": "diverge",
      "intent": "Surface the real, lived pains broadly — no solutions yet.",
      "council_strategy": "pain-discovery",
      "breadth": { "min_explorations": 4, "max_explorations": 8, "by": "persona_subset|angle" },
      "produces": "problem_cluster_set",
      "gate": { "type": "saturation", "window": 2, "min": 4 }       // stop when last 2 rounds add no new cluster
    },
    {
      "key": "define", "name": "Define", "mode": "converge",
      "intent": "Cluster the breadth into ONE core problem + a Point-of-View.",
      "council_strategy": "goal", "consumes": "problem_cluster_set",
      "produces": "point_of_view",
      "gate": { "type": "decision", "requires": "single_core_problem" }
    },
    {
      "key": "develop", "name": "Develop", "mode": "diverge",
      "intent": "Generate multiple solution candidates; build real prototypes.",
      "council_strategy": "positive-deepdive", "consumes": "point_of_view",
      "produces": "solution_candidate_set",
      "breadth": { "min_explorations": 3, "max_explorations": 6, "by": "solution_candidate" },
      "requires_artifacts": ["prototype"],                            // ≥1 candidate must be a real prototype (Pillar B)
      "gate": { "type": "saturation", "window": 2, "min": 3 }
    },
    {
      "key": "deliver", "name": "Deliver", "mode": "converge",
      "intent": "Personas USE the prototypes; converge to the buildable spec.",
      "council_strategy": "tension", "consumes": "solution_candidate_set",
      "requires_artifacts": ["prototype_session"],                    // real Playwright use (Pillar B)
      "produces": "spec",
      "gate": { "type": "decision", "requires": "fundable_spec" },
      "loop_back": { "if": "test_fails", "to": "develop" }            // DT iterates
    }
  ]
}
```

Other built-ins shipped at M1: **d.school micro-cycle** (Understand·Observe·POV·Ideate·
Prototype·Test·Reflect) and **Lean/JTBD** (Problem→Solution→MVP→Validate). The engine is
generic; these are *data*.

### 3.2 The engine drives diverge/converge (this is what makes it a diamond)
- **Diverge phase:** the driver fans out **N explorations** (per `breadth`) — each is a council
  (often a different persona subset or a different angle/solution-candidate) → a small synthesis
  = one **exploration node** tagged `phase:<k>`, `mode:diverge`. Many nodes at one graph depth =
  the diamond's wide part. The **saturation gate** stops fan-out when new councils add no new
  cluster (measured: cluster set stable over `window` rounds).
- **Converge phase:** the driver **clusters** the breadth (a synthesis-of-explorations) into the
  phase artifact (problem clusters → core problem/POV; solution candidates → chosen + spec) =
  one **convergence node** with `refines`/`answers`/`duplicates` edges *from* the breadth nodes.
  The **decision gate** requires a single, evidence-backed result.
- Result: the graph is genuinely **wide → narrow → wide → narrow** = two diamonds.

Gates are **partly measurable** (saturation = structural; the engine computes it from recorded
cluster sets) and **partly host-judged** (decision gates: the host reports the decision with
evidence; the engine validates that the breadth was actually explored and edges exist). The
engine **refuses to advance** a converge phase that has < `min` exploration nodes upstream — so
"four boxes in a row" becomes structurally impossible.

### 3.3 Data model (JSON-blob, schema bump v3→v4, idempotent — no migration scripts)
- `ResearchProject` gains: `methodology` (key), `phase` (current phase key), `methodology_state`
  (`{phase_key: {status, exploration_node_ids, gate: {...}, decided_at}}`).
- `Synthesis` (study node) gains: `phase`, `mode` (`diverge|converge`), `methodology`,
  `cluster_label?`. (All JSON-blob additions; backward compatible.)
- New `methodologies` table (user-defined specs); built-ins from repo files.
- New artifact-type vocabulary (validated): `problem_cluster_set`, `point_of_view`,
  `solution_candidate_set`, `spec`, `prototype`, `prototype_session`.

### 3.4 MCP / CLI surface (Pillar A)
gather→author→write-back preserved; the engine adds *structure*, never text.
- `list_methodologies()` · `get_methodology(key)` (gather: the spec, for the host to know the
  current phase's rules).
- `start_methodology_project(title, goal_hmw, methodology_key, persona_ids)` → project bound to
  methodology at phase[0]. (Also `set_project_methodology` for existing projects.)
- `brief_phase(project_id)` → gather: current phase, mode, breadth still required, consumed
  artifacts, the gate and its current status, instructions. **This is the driver's heartbeat.**
- `record_exploration(project_id, council_ids, payload)` → records one diverge exploration node
  (a synthesis) under the current phase; updates breadth/saturation state.
- `record_convergence(project_id, from_node_ids, payload)` → records the converge node + edges +
  the phase artifact; evaluates the decision gate.
- `advance_phase(project_id)` → validates the gate (structure + host decision) and moves on (or
  loops back per `loop_back`); errors if breadth/gate unmet.
- `get_methodology_state(project_id)` → phase progress, gate status, node counts.
- A thin **driver skill** `methodology-run` orchestrates: read `brief_phase` → fan out the
  required explorations (reusing `run-council`) → cluster/converge → `advance_phase`, looping
  until the methodology completes. Per-method playbooks become *data*, not skills.

---

## 4. Pillar B — Real, agent-usable prototypes (Playwright)

### 4.1 Prototype artifacts (scaffold · register · run · version)
- Host authors real app code into `prototypes/<slug>/` with normal file tools (host-authoring),
  then registers it. Minimal but real: static SPA (`index.html`) for v1; a declared run command
  for node/python apps later.
- New `prototypes` table → `Prototype{ id, slug, project_id?, name, version, kind:"web",
  path, entry, run:"static|node|python", run_cmd?, created_at, notes }`. Versioned (v0.1, v0.2…)
  so reactions can be compared across versions.
- MCP/CLI: `register_prototype(slug, name, path, entry, run, ...)`, `list_prototypes`,
  `get_prototype`, `delete_prototype`.

### 4.2 Local runner
- `run_prototype(id)` → starts the app on an ephemeral localhost port (static: a tiny local
  HTTP server rooted at `path`; node/python: the declared `run_cmd`), returns `{url, pid}`.
  `stop_prototype(id)`. Local-only, never bound to a public interface (never hosted for real
  users — per the standing decision).

### 4.3 The Playwright harness (the crux — agents drive the REAL app)
New optional dependency: **Playwright (Python)** + chromium (`playwright install chromium`,
documented; degrade gracefully with a clear error if absent). Headless by default.

A persona-agent interacts through **observation/action tools** (these are *not* text-generation;
they return real observations). An interaction **session** is in-process (not persisted); the
*reaction* is persisted as an experience (§4.4).

- `proto_open(prototype_id | url)` → launches headless chromium, navigates, returns a
  **snapshot**: an **accessibility tree** (role + name + a stable `ref` per actionable element)
  + page text + a screenshot path. The a11y tree is the agent-facing, token-efficient
  representation (same approach as computer-use / the official Playwright MCP).
- `proto_act(action)` → one of `click(ref)`, `type(ref, text)`, `select(ref, value)`,
  `scroll`, `key(...)`; returns the **new snapshot** (so the agent sees the real consequence).
- `proto_read()` → current snapshot/state (e.g. to re-read after an async update).
- `proto_close()`.

A persona-subagent is given a task ("you are <persona>, here is how to drive the app; use it as
you really would and report what you experienced") plus its loaded `persona-context`. It calls
`proto_open/act/read`, observes **real rendered state**, and reports a grounded reaction. Because
the agent acted on the real app, the reaction references **actual observed states** (verifiable
in the session log) — this is the hard fix for failure #2.

### 4.4 Reaction → experience → council (the seam, now fed by real use)
- `brief_prototype_session(persona_id, prototype_id)` → gather: persona context + how to drive
  the app + anti-steering instructions.
- The host runs the persona-subagent's Playwright session, then authors the lived experience and
  `record_prototype_session(...)` → writes it as an **experience/day activity** + memory deltas
  (reusing `record_day`/`record_memory_deltas`), with `artifacts_touched=[prototype ref]` and
  the **observed-state evidence** attached. Now `prepare_persona_agent_context` surfaces the real
  use in the Deliver/Test council — grounded testing, not prose.
- **Quality gate:** the eval critic gains a dimension **"prototype-reaction groundedness"** —
  a reaction that praises features the agent never actually exercised (no matching snapshot
  evidence) is flagged. This protects against the exact fiction the first attempt produced.

### 4.5 How A and B compose (a real Double Diamond)
Develop (diverge) scaffolds **several** candidate prototypes (breadth + `requires_artifacts:
prototype`). Deliver (converge) has personas **actually use** them via Playwright
(`requires_artifacts: prototype_session`), reactions feed a tension/decision council, and the
engine converges to the `spec` only when the decision gate is met. Breadth and real testing are
now *structurally required*, not optional narration.

---

## 5. UI (read-only, per the CRUD rule — create/run via MCP/CLI only)
- **Methodology display** on the project: which methodology, current phase, gate status.
- **Diamond view:** a phase/mode-aware layout — diverge phases render their exploration nodes as
  a fan (the wide part), converge phases as the waist → the genuine two-diamond silhouette
  (replacing today's flat chain). Reuse the existing interactive graph engine.
- **Prototype viewer:** list prototypes + versions; embed the running app (iframe) or its
  screenshot; show which personas used it and their grounded reactions (with observed-state
  evidence and version).

---

## 6. Milestones (substantial; each with a failure-proof acceptance test)

- **M1 — Methodology engine.** Registry + specs (`double_diamond`, `dschool_micro`, `lean_jtbd`);
  driver + `brief_phase`/`record_exploration`/`record_convergence`/`advance_phase`; v4 schema
  fields; the `methodology-run` driver skill. **Accept:** a Discover phase produces ≥4 distinct
  exploration nodes and Define refuses to converge until they exist; the graph for a run is
  measurably wide→narrow→wide→narrow.
- **M2 — Prototype artifacts.** `prototypes` table; register/list/get/delete; local runner
  (`run_prototype`/`stop_prototype`). **Accept:** a registered static app starts on a local port
  and is reachable.
- **M3 — Playwright harness.** Dependency + `proto_open/act/read/close`; session; `brief_/
  record_prototype_session`; critic groundedness dimension. **Accept:** a persona-subagent opens
  a real app, performs ≥1 click/type, and its recorded reaction cites an observed state present
  in the session snapshot log.
- **M4 — UI.** Methodology display, diamond view, prototype viewer.
- **M5 — Harness deep-dive (Pillar C).** Investigate persona-subagent spawning/grounding,
  parallelism, cost, and whether the loop wants a more capable harness.
- **Cross-cutting:** MCP-contract tests, CLI mirrors, anti-steering critic extension, docs.

---

## 7. Risks & open questions
- **Playwright weight/CI:** chromium download + headless run; make it an optional extra, skip
  harness tests when absent. Decide install ergonomics (`make playwright`).
- **Snapshot token cost:** a11y trees can be large; cap depth / prune to actionable nodes;
  screenshots optional.
- **Gate measurability:** saturation is computable; "single core problem" / "fundable spec" stay
  host-judged with structural guards (breadth existed, edges exist, evidence attached).
- **Methodology authoring UX:** built-ins as files now; a user-facing authoring flow later.
- **Loop-backs:** DT iterates (Deliver→Develop); keep loop counts bounded + logged.
- **Determinism of agent app-use:** real interaction is non-deterministic; record the full
  session log so reactions are auditable.

---

## 8. Relationship to existing specs
- Foundation specs unchanged: `mcp-tool-contract.md`, `memory-and-simulation-architecture.md`,
  `research-graph-and-meta-report.md`, `simulation-loop-contract.md`.
- `design-thinking-methodology.md` is **superseded**: Double Diamond is no longer a bespoke skill
  but **one data-driven methodology** in the engine of §3; its prototype phase is realized by §4.
