# Evaluation — Is the agentic harness ready for one-prompt, 50+-iteration autonomous runs?

> **Status:** EVALUATION + improvement tracker. Grounded in the codebase and in the full
> design-thinking run just executed (18 personas → 13 councils → affinity clustering → 7 prototypes
> → grounded proband sessions → deliver + roadmap → sections). North star (user, 2026-06-04):
> *from a first prompt (e.g. an HMW), trigger a long-running simulation of 50+ iterations of
> councils / prototypes / exploration / synthesis / solution-spaces — well-organized, well-documented,
> end-to-end.* Question: are we there, and what must change?

## 0. Verdict (one paragraph)
**The PRIMITIVES are excellent and battle-tested; the ORCHESTRATION is not yet autonomous, and there
is engine duplication that blocks it.** Every low-level capability the north star needs exists and
works under real load: memory-grounded councils, decoupled syntheses, varied real prototypes,
grounded Playwright proband sessions, evidence-gated diamonds, and now methodology-independent
sections. But the run was driven **manually by the host** (hand-wired Python scripts + subagent
fan-out + ad-hoc scratch-file state). There is **no autonomous driver for the plan engine**, **no
real (subagent-dispatching) authoring backend**, **no project-level meta-assessment** ("what's
missing / are we done / is quality sufficient"), and **two overlapping engines** (methodology
constellation vs research plan). For 50+ iterations from one prompt we need a lean, well-documented
autonomous loop on **one** engine, a completeness/stop meta-assessment, and disciplined context
hygiene. We are ~60% there: the hard parts (primitives, gates, organization) are done; the
orchestration layer is the gap.

## 1. What the current run proves (evidence)
Worked, at real scale, with no in-process LLM (host/subagents authored all text):
- **Councils**: 13 multi-persona, memory-grounded, anti-steered (skeptics stayed skeptical).
- **Decoupled syntheses**: 9, incl. 2 **council-free** (affinity key-problems, roadmap) — the
  synthesis⟂council decoupling holds end-to-end.
- **Prototypes**: 7 varied non-form apps across lo→mid→hi-fi; **all proband sessions grounded**
  (Playwright snapshots verified).
- **Plan/gates**: 4 diamonds, every verify rejected until its fan + gate + sessions existed.
- **Organization**: plan.md, sections (4 themes + 4 derived phases), a navigable graph.
What was **manual** (the tell): I authored every frame, chose breadth, dispatched ~30 subagents,
remapped ids, and wired the plan via ~12 scratch scripts. None of that is a repeatable one-prompt
flow yet.

## 2. Dimension-by-dimension

### 2.1 Right tools? — *mostly yes, four gaps*
150+ MCP tools cover authoring, memory, simulation, councils, syntheses, prototypes, plan,
sections. **Missing for autonomy:**
- **(T1) A lean "next action" tool.** `brief_next` returns a compact instruction, but the host
  still has to gather persona memory, pick participants, frame the council, etc. A long loop needs
  one call that returns *everything to author the next step* (the frame's memory context, or the
  framed question + suggested diverse participants, or the verify fan to synthesize) so each
  iteration is **one gather → one author(subagent) → one persist**.
- **(T2) Project-level meta-assessment.** `assess_progress` is per-verify and honest (no metric);
  `coverage_hint` is counts. There is **no** "what's missing across the whole project / are we done
  / is quality sufficient / what should the next 3 moves be" — the single most important tool for a
  50-iteration run to stay purposeful and know when to stop.
- **(T3) A real AuthoringBackend.** `runtime.run_methodology` exists but only ships
  `StubAuthoringBackend`. There is no backend that dispatches a subagent to author a council/
  synthesis. So "autonomous" today = a human/host in the loop.
- **(T4) Idempotent re-run / id-stable authoring.** Council/synthesis ids embed a timestamp, so
  re-running requires id-remapping (I hit this in the E2E). A content-addressed or run-scoped id
  scheme would make long runs resumable and re-runnable.

### 2.2 Does the plan feature work as intended? — *yes, host-stepped; but no autonomous loop, and it's a second engine*
The plan engine (analyze→act→verify, dischargeable frames, evidence gates, diamonds, assess) works
exactly as designed — I exercised all of it. **Two problems for the north star:**
- **(P1) No autonomous driver for the plan engine.** `run_methodology` drives the *other* engine
  (methodology constellation: `record_node`/`record_decision`/`advance`). The plan engine
  (`record_frame`/`add_task`/`complete_task`) is host-stepped only.
- **(P2) Two engines.** Methodology-constellation (methodology.py + runtime.py) and research-plan
  (plan.py) model the same idea twice (steps/diamonds vs frames/tasks/verifies). `start_project`
  seeds the plan from the methodology; `get_project_graph` derives a methodology_state from the
  plan. This duplication is real cognitive + context cost and splits the autonomous driver from the
  engine people actually use. **Recommendation: make the plan engine canonical; express
  methodologies purely as plan seeds; retire/forward the constellation runtime.**

### 2.3 Context bloat? — *real risk; mitigations exist but aren't enforced*
The architecture is well-designed for this (subagents author then discard; the DB/plan.md hold
state; envelopes carry `next_recommended_tool`; a compaction hierarchy list_→status→summary→state).
**But:** in practice the host loop accumulates context (every dispatched result, every decision).
For 50+ iterations we need an **enforced lean loop**: brief_next → dispatch ONE subagent (author +
persist) → receive a *tiny* result (ids + 1-line) → never re-read full councils/syntheses in the
host; periodic re-grounding via `summary`/`state`/`coverage`, not full reads. Sections + plan.md +
the meta-report are the durable "external memory" that lets the host stay lean. This is a
**discipline + a documented skill**, plus T1/T2 to make each step a single compact call.

### 2.4 Right level of assessment each time? — *partial*
Good: `assess_progress` is evidence-cited and metric-free (honest); gates enforce breadth before
convergence; structural + critic evaluators exist for simulations. Missing: a **per-iteration and
per-project research-quality assessment** — coverage of the question space, evidence triangulation,
contradiction/▲saturation detection ("are new councils still surfacing new things?"), and a
principled **stop/continue/branch** recommendation. Without it a 50-iteration run either stops
arbitrarily or runs in circles. → **T2 (meta-assessment) + a saturation signal.**

### 2.5 Organization & documentation? — *strong and just got stronger*
plan.md (analyze/act/verify log), the project graph, decoupled syntheses, the meta-report, and now
**sections** (free themes + derived phases) give genuinely good organization. Gaps: a **run journal**
(what happened each iteration + why), and **auto-maintained sections** (the orchestrator should
create/extend sections as it goes, not only by hand). Sections are the right home for "Initial user
research", "Problem exploration", "Solution space" — wire the autonomous loop to populate them.

## 3. Improvement tracker (prioritized; each: implement → suite+characterization green → commit)

> **Implemented (2026-06-04):** ✅ **HX1** `assess_project` (computed meta-assessment: coverage /
> open gates / saturation hint / gaps / continue-converge-complete-blocked rec). ✅ **HX2**
> `next_action` (the ready step fully loaded — grounding / framed-questions+diverse-participants /
> fan+gate — one compact call per iteration). ✅ **HX4** the `autonomous-research-run` skill (the lean
> host/subagent loop) — folding in **HX5** (sections + a notes run-journal keep it self-organizing)
> and **HX7** (saturation/budget stop criteria, with the `saturation` hint from HX1). Remaining:
> ◑ **HX3** canonicalize the plan engine / retire the constellation runtime duplication; ◑ **HX6**
> resumable/re-runnable evidence ids (the E2E id-remap pain). These two are larger refactors.

- **HX1 — Project meta-assessment (`assess_project`).** A read-only, evidence-cited project digest:
  coverage by phase/kind, open questions, contradictions, **saturation signal** (are recent councils
  still adding new themes?), gaps ("no provider voice yet", "no lo-fi test"), and a
  **continue/branch/converge/stop** recommendation with rationale. Host-authored verdict layer on a
  computed evidence snapshot (mirrors brief_eval_critic). *The highest-leverage single tool.*
- **HX2 — Lean `next_action(project_id)`.** One call returns the next step fully loaded: for analyze
  → the frame's grounding (relevant persona memory refs, prior syntheses); for act → a framed
  question + **suggested diverse participants** (segment-spread, not keyword) + which renderer to
  build; for verify → the fan to consolidate + the gate to satisfy. Turns each iteration into one
  gather→author→persist. Build on `brief_next` + `coverage_hint` + memory recall.
- **HX3 — Canonicalize the plan engine; methodologies = plan seeds.** Make plan.py the single engine;
  express constellations as plan seeds (already do via `seed_plan_from_methodology`); add a plan-loop
  driver (HX4) and forward/retire the constellation runtime path. Remove the duplication that splits
  the autonomous driver from the used engine.
- **HX4 — Autonomous plan-loop skill + a subagent AuthoringBackend.** A documented skill (and/or a
  thin `PlanLoopBackend`) that: loops `next_action` → dispatches ONE subagent to author the step →
  persists → `assess_project` every K steps to decide continue/branch/converge → maintains sections
  + a run journal → stops on saturation or a budget. Keeps host context lean (tiny results only).
  This is what makes "one HMW prompt → 50+ iterations" real, within the no-in-process-LLM rule.
- **HX5 — Auto-organization: orchestrator maintains sections + a run journal.** As the loop runs,
  create/extend phase + theme sections and append a one-line journal entry per iteration (durable
  external memory; keeps the host lean and the project self-documented).
- **HX6 — Resumable, re-runnable ids.** Run-scoped or content-addressed evidence ids so a long run
  can resume after interruption and a project can be replayed deterministically (the E2E id-remap
  pain). 
- **HX7 — Saturation / stop criteria.** A concrete, evidence-based signal: K consecutive councils
  add < N new themes (theme-novelty), or all open questions answered, or budget hit → converge.
  Feeds HX1/HX4.

## 3b. The remaining ~30% — concrete path to the north star (updated 2026-06-04)

Three things stand between "primitives + lean tools" and "drop an HMW, walk away, get a great
50-iteration project":

1. **Self-composition (the agent decides what to run).** ✅ addressed via the **`compose-research-plan`**
   skill: from the prompt the agent classifies the inquiry, surveys `suggest_*` + the cohort, and
   either adopts a preset methodology or **composes a bespoke freeform plan** (`add_task` any
   analyze→act→verify shape with real gates), then hands off to `autonomous-research-run`. The engine
   already supports arbitrary composition (open tags, free add_task) — this skill makes the *decision*
   explicit and documented. Remaining polish: a tiny `plan_blueprint` convenience that returns a
   starting constellation for a chosen inquiry-type (options only; the agent still decides).

2. **HX3 — collapse the two engines.** The methodology-constellation engine (methodology.py +
   runtime.py) and the research-plan engine (plan.py) model the same thing twice; the only autonomous
   driver (`run_methodology`) is on the *unused* one, with a stub backend. **Plan: make plan.py
   canonical** — methodologies are *only* plan seeds (`seed_plan_from_methodology`, already the path);
   the autonomous loop is the `autonomous-research-run` skill over the plan engine (host/subagent —
   the locked rule forbids an in-process backend); forward `run_methodology`/`record_node`/
   `record_decision` to plan-engine equivalents and mark the constellation runtime legacy. This is the
   biggest debt: it removes duplicate concepts (steps/diamonds vs frames/tasks/verifies), shrinks
   context, and gives ONE loop. Medium-large refactor; gate with the full suite + characterization.

3. **HX6 — resumable / replayable runs.** Evidence ids embed a timestamp, so a long run can't be
   resumed cleanly and a project can't be replayed (the E2E needed id-remapping). **Plan:** optional
   deterministic `key` on `record_council`/`record_synthesis`/`scaffold_artifact` (id =
   stable_id(kind, key) when given) + idempotent upsert on that id, so re-running a step is a no-op
   and an interrupted run resumes from `assess_project`. Bounded but needs careful upsert semantics.

Plus quality-of-life from this session: ✅ synthesis is visibly decoupled (councils demoted to a
collapsed "Belege"); ✅ notes render (`/notes/{id}`, clickable); ✅ graph readability (phase bands vs
theme outlines, wider nodes, longer labels); ✅ project **Pulse** in the web.

**Sequence to "done":** ship `compose-research-plan` + `autonomous-research-run` as the front door
(done) → exercise a real autonomous long run end-to-end and fix what chafes → HX3 (one engine) → HX6
(resumable) → then a 50+-iteration run from one prompt is routine and well-documented.

## 4. Are we getting there?
**Yes on substance, not yet on autonomy.** The run demonstrates every primitive at quality and the
new sections make it well-organized. To reach the north star, build HX1 + HX2 first (assessment +
lean step), then HX4 (the documented lean autonomous loop) on the canonical plan engine (HX3), with
HX5/HX7 making long runs self-organizing and self-terminating. None of this needs an in-process LLM
— it needs a lean, well-documented host/subagent loop plus the assessment + next-action tools that
keep every iteration a single compact call.
