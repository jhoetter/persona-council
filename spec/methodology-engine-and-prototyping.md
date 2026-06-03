# Methodology Engine, Orchestration Runtime & Agent-Usable Prototyping — Specification

> **Status:** DESIGN (authored 2026-06-03, rev. 2). **Substantial development**, staged M1–M5.
> **Supersedes** `spec/design-thinking-methodology.md` (kept for history; see §1).
> **Decisions locked with the user:**
> 1. The methodology engine is **structure-enforcing + LLM-judged** — it guarantees *shape*
>    (diverge-before-converge, breadth exists, full traceability) but **never hardcodes the
>    dynamics**; "are we saturated?", "is this the core problem?", "is the spec ready?" are
>    LLM judgments recorded with evidence. (Honors the no-hardcoding / LLM-simulation principle.)
> 2. Prototypes come into being via **first-class app generation** — a guided scaffold spins up a
>    real, minimal, runnable web app on demand (host-authored content, repeatable skeleton).
> 3. Persona-agents use prototypes through a **headless browser (Playwright)** — they drive the
>    *real running app* and react to *real observed state*.
> 4. Methodologies are a **data-driven registry** (declarative specs + engine), so we can *choose
>    from approaches* and add new ones without code.
> 5. The **harness/orchestration runtime is a design input now** (§5), not a final afterthought.
> **Leitsatz (unchanged):** nothing hardcoded as *outcomes/dynamics*; MCP exposes capabilities;
> the host (or the runtime's authoring backend) authors all *text* (`brief_*→author→record_*`);
> every claim traceable; personas non-directional (anti-steering). The persona
> **experience-driven** council loop stays the foundation.

---

## 1. Why the first attempt failed (the lessons this spec encodes)

A facilitation-only attempt (one skill + phase tags) was run end-to-end on a Double Diamond. It
produced a **chain, not two diamonds**, and a **prototype no agent ever ran**:

1. **No divergence.** One council per phase → four nodes in a straight line (the literal
   screenshot). The method was *labelled*, not *applied* — no broad problem exploration, no broad
   solution ideation.
2. **No real software artifact.** The prototype was a static file *described in prose*; "the
   persona used it" was authored fiction. No mechanism for an agent to invoke/drive/observe a
   real running app.
3. **Methodology not first-class.** A hardcoded playbook + tags; not selectable; not shaping
   breadth/gates/graph-shape.
4. **Ventriloquized.** A single ambient orchestrator (the coding agent) improvised every turn —
   non-reproducible, and the reason the "diamonds" were narrative rather than structural.

**Kept (sound):** the graph substrate (Project ⊃ Synthesis ⊃ Council, typed edges, `voices`,
meta-report), host-authoring, anti-steering, the experience→memory seam *concept*. **Added:** a
methodology *engine*, an orchestration *runtime*, and an agent-usable *prototype harness*.

**Failure-proof acceptance tests** (every milestone is checked against these): a diverge phase
MUST yield ≥2 distinct exploration nodes and an evidence-backed *divergence-complete* judgment
before its converge phase can be recorded; a converge node MUST carry edges from the explorations
it consumed; a prototype reaction MUST cite a **real observed UI state** present in the Playwright
session log — not a paraphrase.

---

## 2. Architecture — three pillars + a runtime, over the unchanged foundation

```
   FOUNDATION (unchanged): personas · experience/memory · councils · syntheses ·
                           research graph · meta-report · host-authoring · anti-steering
        ▲                              ▲                                  ▲
        │ capabilities (MCP)           │ capabilities (MCP)               │ capabilities (MCP)
 ┌──────┴───────┐            ┌─────────┴──────────┐            ┌──────────┴───────────┐
 │  PILLAR A    │            │  PILLAR B          │            │  PILLAR C (§5)        │
 │  methodology │            │  prototypes:       │            │  ORCHESTRATION RUNTIME│
 │  ENGINE      │            │  generate · run ·  │            │  spawns persona-agents│
 │  data-driven │            │  Playwright drive  │            │  fans out explorations│
 │  structure + │            │  (real app use)    │            │  drives Playwright    │
 │  LLM-judged  │            │                    │            │  steps the methodology│
 └──────┬───────┘            └─────────┬──────────┘            └──────────┬───────────┘
        └───────────────── the runtime ORCHESTRATES A and B per the chosen methodology ─┘
```

- **Pillar A** makes the *process* real and selectable (fixes #1, #3).
- **Pillar B** makes the *artifacts* real and agent-usable (fixes #2).
- **§5 Runtime** makes it *reproducible and engine-controlled* rather than improvised (fixes #4).

---

## 3. Pillar A — Methodology engine (data-driven, structure-enforcing, LLM-judged)

### 3.1 A methodology is declarative data
Built-ins ship as specs in `persona_council/methodologies/*.json` (loaded into a registry at
import); user-defined ones persist in a `methodologies` table (JSON-blob pattern). A spec:

```jsonc
{
  "key": "double_diamond",
  "name": "Double Diamond",
  "description": "Problem space (Discover→Define) then solution space (Develop→Deliver).",
  "when_to_use": "Frame an ambiguous problem and take it to a buildable solution.",
  "phases": [
    { "key": "discover", "name": "Discover", "mode": "diverge",
      "intent": "Surface the real, lived pains broadly — no solutions yet.",
      "council_strategy": "pain-discovery",
      "diverge_by": "persona_subset|angle",          // HOW to widen (guidance, not a count)
      "produces_role": "problem-landscape" },
    { "key": "define", "name": "Define", "mode": "converge",
      "intent": "Cluster the breadth into ONE core problem + a Point-of-View.",
      "council_strategy": "goal", "consumes": "discover",
      "produces_role": "point-of-view" },
    { "key": "develop", "name": "Develop", "mode": "diverge",
      "intent": "Generate multiple solution candidates; build real prototypes.",
      "council_strategy": "positive-deepdive", "consumes": "define",
      "diverge_by": "solution_candidate",
      "requires_artifacts": ["prototype"],            // ≥1 candidate is a real generated app (Pillar B)
      "produces_role": "solution-options" },
    { "key": "deliver", "name": "Deliver", "mode": "converge",
      "intent": "Personas USE the prototypes; converge to the buildable spec.",
      "council_strategy": "tension", "consumes": "develop",
      "requires_artifacts": ["prototype_session"],    // real Playwright use (Pillar B)
      "produces_role": "spec",
      "loop_back": "develop" }                         // DT iterates if a test fails (LLM-judged)
  ]
}
```

No `window`, no `min` counts anywhere. `diverge_by` is *how to widen*; `requires_artifacts` is a
*structural* requirement; `produces_role` is a *light* label (see §3.3). Other built-ins at M1:
**d.school micro-cycle** and **Lean/JTBD** — pure data.

### 3.2 What the engine ENFORCES vs what the LLM DECIDES
This is the heart of the corrected design.

**Structural invariants (deterministic, validated — about *shape*, never *outcome*; safe to
encode, like "a synthesis must cite its councils"):**
- A converge phase cannot be recorded until its diverge phase has **≥2 distinct exploration
  nodes** *and* an explicit **`divergence_complete` judgment** is on record for it.
- A convergence node must carry **edges from the explorations it consumed** (`refines`/`answers`/
  `duplicates`/`contrasts`).
- Phases run in the methodology's declared order; **loop-backs are allowed and logged**.
- Every node and claim is **traceable** to councils; every prototype claim to a session log.

**Dynamic judgments (LLM-made, evidence-backed, recorded — never counted by the engine):**
- *"Have we explored the problem/solution space enough — keep diverging or stop?"* → the runtime
  asks the model with the explorations-so-far as evidence; records a `divergence_complete`
  judgment `{decided: bool, rationale, evidence_refs}`. **No saturation window.**
- *"Is this THE core problem / is the spec fundable?"* → an LLM decision with evidence at the
  converge gate, recorded as the phase artifact's rationale.

The engine **requires the presence** of these judgments (you can't converge without an
evidence-backed divergence-complete decision) but **never dictates their content or a number**.
That makes "four boxes in a row" structurally impossible *and* keeps the dynamics LLM-driven.

### 3.3 Artifacts stay emergent (lightly typed)
Phase outputs are ordinary syntheses, carrying a **light `role` tag** (`problem-landscape`,
`point-of-view`, `solution-options`, `spec`) — *not* a rigid typed schema. The role tells the UI
and the next phase what to consume; the *content* is emergent, host-authored, free-form. We do
**not** invent `problem_cluster_set`-style structured objects (that was over-engineering).

### 3.4 Data model (JSON-blob, schema bump v3→v4, idempotent — no migration scripts)
- `ResearchProject` += `methodology` (key), `phase` (current), `phase_log`
  (`{phase_key: {status, exploration_node_ids, judgments:[...], decided_at}}`).
- `Synthesis` (study node) += `phase`, `mode` (`diverge|converge`), `methodology`, `role`.
- New `methodologies` table (user-defined specs); built-ins from repo files.

### 3.5 MCP / CLI surface (Pillar A)
- `list_methodologies()` · `get_methodology(key)` (gather: the spec for the current phase's rules).
- `start_methodology_project(title, goal_hmw, methodology_key, persona_ids)` · `set_project_methodology`.
- `brief_phase(project_id)` → gather: current phase, mode, how to diverge/converge now, consumed
  roles, the structural requirements still unmet, instructions. (The runtime's heartbeat.)
- `record_exploration(project_id, council_ids, payload)` → one diverge exploration node.
- `record_judgment(project_id, phase_key, kind, decided, rationale, evidence_refs)` →
  e.g. `divergence_complete`. (The LLM-judged gate, persisted with evidence.)
- `record_convergence(project_id, from_node_ids, payload, role)` → converge node + edges + artifact
  (validated against the structural invariants).
- `advance_phase(project_id)` → moves on or loops back; errors if invariants unmet.
- `get_methodology_state(project_id)`.

---

## 4. Pillar B — Real, agent-usable prototypes

### 4.1 First-class app generation (your "very easily prototype applications")
- `scaffold_prototype(slug, concept, kind="web")` → generates a **runnable minimal app skeleton**
  from a known-good template (single-file SPA for v1; a declared run-command for richer apps
  later) and fills it from the solution `concept`. Host-authored content (contract preserved) but
  from a **guided, repeatable scaffold** so spinning up *several* candidates per Develop phase is
  cheap. Returns the registered prototype.
- New `prototypes` table → `Prototype{ id, slug, project_id?, name, version, kind:"web", path,
  entry, run:"static|node|python", run_cmd?, created_at, notes }`. **Versioned** (v0.1, v0.2…) so
  reactions compare across versions.
- `register_prototype` (for hand-authored apps), `list_prototypes`, `get_prototype`,
  `delete_prototype`.

### 4.2 Local runner
- `run_prototype(id)` → starts the app on an ephemeral **localhost** port (static: tiny local HTTP
  server; node/python: declared `run_cmd`), returns `{url, pid}`. `stop_prototype(id)`. Local-only,
  never bound to a public interface (never hosted for real users).

### 4.3 The Playwright harness — agents drive the REAL app
Optional dependency **Playwright (Python)** + chromium (`make playwright` to install; graceful
error if absent). Headless. The persona-agent interacts via observation/action tools (not
text-gen); the session is owned by the runtime (§5):
- `proto_open(prototype_id|url)` → launch chromium, navigate, return a **snapshot**: an
  **accessibility tree** (role + name + stable `ref` per actionable element) + page text +
  optional screenshot path. (a11y tree = token-efficient, agent-facing; same approach as
  computer-use / the official Playwright MCP.)
- `proto_act(action)` → `click(ref)`|`type(ref,text)`|`select(ref,value)`|`scroll`|`key(...)`;
  returns the **new snapshot** (the real consequence).
- `proto_read()` · `proto_close()`.

### 4.4 Reaction → experience → council (the seam, now fed by *real* use)
- `brief_prototype_session(persona_id, prototype_id)` → gather: persona context + how to drive +
  anti-steering.
- The runtime runs the persona-agent's Playwright session, then authors the lived experience and
  `record_prototype_session(...)` → writes it as an **experience/day activity + memory deltas**
  (reusing `record_day`/`record_memory_deltas`), with `artifacts_touched=[prototype ref]` and the
  **observed-state evidence** attached. `prepare_persona_agent_context` then surfaces the real use
  in the Deliver/Test council.
- **Quality gate:** the eval critic gains a **"prototype-reaction groundedness"** dimension — a
  reaction praising features with no matching snapshot evidence is flagged. (Directly prevents the
  first attempt's fiction.)

### 4.5 How A + B compose (a real Double Diamond)
Develop (diverge) **generates several candidate apps** (`requires_artifacts: prototype`); Deliver
(converge) has personas **actually use** them via Playwright (`requires_artifacts:
prototype_session`); reactions feed a tension/decision council; the engine records the
evidence-backed decision and converges to the `spec`. Breadth and real testing are *structurally
required*, not optional.

---

## 5. Pillar C — Harness & orchestration runtime (the design input)

**Finding (from the codebase):** persona-council has **no native runtime, no concurrency, no
browser**. The MCP server exposes *capabilities*; **the ambient coding-agent (Claude Code/Codex)
does all orchestration** — it spawns persona-subagents, runs them in parallel, loops, and would
drive Playwright. The skills *assume* "the host spawns one subagent per persona." So today,
divergence, parallelism, looping and app-driving all depend on whoever is calling — which is
precisely why the first run was improvised, ventriloquized, and non-reproducible.

**The decision (recommended — to confirm):** a **hybrid thin runtime**. persona-council grows a
small orchestration runtime that owns the **deterministic** parts:
- fan-out of explorations in diverge phases (the structural divergence the engine requires),
- **persona-agent sessions** (a first-class concept: a persona + loaded context that can produce a
  reaction and, when needed, drive a Playwright session),
- Playwright session lifecycle,
- methodology stepping + invariant/gate validation.

…and delegates the **text authoring** (persona reactions, syntheses, judgments) to a **pluggable
authoring backend**, in one of two modes:
- **Interactive mode:** authoring flows back to the ambient harness via the existing
  `brief_*→record_*` contract (today's behaviour — a human-driven coding agent fills the text).
- **Autonomous mode:** an LLM client inside the runtime authors it directly (so a single
  `run_methodology(project_id)` call can drive a whole diamond unattended).

This preserves MCP-first + host-authoring, makes the methodology **reproducible** and divergence
**guaranteed** (not caller-dependent), and is what lets a persona-agent *really* drive an app
under the engine's control. The two rejected poles: **capability-only** (status quo — quality
stays caller-dependent, the failure recurs) and **full built-in agent platform** (too heavy, and
it competes with the coding-agent harness). The hybrid is the smallest thing that makes it real.

**Open items folded in for M5:** persona-agent grounding quality, parallelism/cost controls,
autonomous-mode safety, and whether autonomous councils need the same anti-steering critic gates
as interactive ones (yes — applied in the runtime).

> **This runtime model is the one decision still to confirm.** Everything else above is locked.

---

## 6. UI (read-only — create/run via MCP/CLI only)
- **Methodology display:** which methodology, current phase, gate/judgment status.
- **Diamond view:** a phase/mode-aware layout — diverge phases render explorations as a fan (the
  wide part), converge phases as the waist → a genuine two-diamond silhouette (replacing the flat
  chain). Reuse the interactive graph engine.
- **Prototype viewer:** prototypes + versions; embed the running app (iframe) or screenshot; show
  which personas used it, their grounded reactions, and the observed-state evidence.

---

## 7. Milestones (each with a failure-proof acceptance test)
- **M1 — Runtime skeleton + methodology engine.** The hybrid thin runtime (interactive mode
  first) + registry/specs (`double_diamond`, `dschool_micro`, `lean_jtbd`) + `brief_phase`/
  `record_exploration`/`record_judgment`/`record_convergence`/`advance_phase` + v4 fields.
  **Accept:** Discover yields ≥2 distinct explorations and Define **refuses** to converge without
  them + a recorded `divergence_complete`; the run's graph is measurably wide→narrow→wide→narrow.
- **M2 — First-class prototype generation.** `scaffold_prototype` + registry + local runner.
  **Accept:** one call scaffolds a runnable app reachable on a local port.
- **M3 — Playwright persona app-use.** Dependency + `proto_open/act/read/close` driven by a
  runtime persona-agent session; `brief_/record_prototype_session`; groundedness critic.
  **Accept:** a persona-agent opens a real app, performs ≥1 click/type, and its recorded reaction
  cites an observed state present in the session log.
- **M4 — UI:** methodology display, diamond view, prototype viewer.
- **M5 — Autonomous mode + harness hardening:** LLM-client authoring backend, parallelism/cost
  controls, anti-steering gates in the runtime; more methodologies.
- **Cross-cutting:** MCP-contract tests, CLI mirrors, docs.

---

## 8. Risks & open questions
- **Runtime scope creep:** keep the runtime *thin* — orchestration + sessions only; resist
  becoming an agent platform.
- **Playwright weight/CI:** optional extra; skip harness tests when chromium absent.
- **Snapshot token cost:** prune a11y trees to actionable nodes; screenshots optional.
- **LLM-judged gates:** must always carry evidence_refs; the critic audits them like any claim.
- **Loop-backs:** bounded + logged.
- **Determinism of app-use:** non-deterministic by nature → full session log makes reactions
  auditable.

---

## 9. Relationship to existing specs
- Foundation specs unchanged: `mcp-tool-contract.md`, `memory-and-simulation-architecture.md`,
  `research-graph-and-meta-report.md`, `simulation-loop-contract.md`.
- `design-thinking-methodology.md` is **superseded**: Double Diamond is **one data-driven
  methodology** in the engine of §3, run by the runtime of §5, with prototypes realized by §4.
