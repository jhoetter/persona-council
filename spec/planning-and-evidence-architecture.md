# Planning + Evidence Architecture — Analysis

> **Status:** ANALYSIS / DESIGN DIRECTION (no code yet). Responds to three linked proposals:
> (1) decouple councils from syntheses (synthesis = optional milestone, not a mandatory wrapper);
> (2) stop running the diverge phase as N single-persona micro-councils — start from a real council
> on the HMW; (3) give the orchestrator a **plan** (analyze / act / verify), modeled on how
> `~/repos/bim-agent` plans the labeling of houses in `~/repos/bim-database`.
> **Thesis:** these three are one architectural move — **a plan-driven analyze→act→verify loop with
> an evidence ledger, sitting above the methodology constellation (which becomes a plan *template*)**.
> Keeps every prior principle: host/subagents author all text (no in-process LLM), zero hardcoded
> vocabulary (analyze/act/verify are tags), structure enforced + dynamics LLM-judged with evidence.

---

## 1. What's wrong today (diagnosis)

### 1.1 Councils are second-class; the synthesis is the only graph citizen
A **council** = one multi-persona discussion (`record_council`: prompt, persona_ids, turns, votes).
A **synthesis** = a study arc over an *ordered chain of councils* (`council_ids[]`). In the project
graph, **nodes are syntheses**; councils are invisible except as a count (`_study_node` →
`council_count`). The methodology engine makes this worse: `record_node`/`record_decision` each
wrap their councils in a Synthesis, so *every* graph node is a synthesis. There is no way to "just
run a council," see it, and decide later whether to consolidate. Synthesis is mandatory packaging.

### 1.2 The diverge phase degenerates into one-council-per-persona
Because a diverge step wants "breadth = many nodes," and a node = a synthesis, the path of least
resistance (what the Pfefferminzia run did) is: **14 single-persona councils, each wrapped in its
own synthesis**. That is backwards. A council's whole value is *multiple personas reacting to each
other from lived memory*. Fourteen one-person "councils" are not councils — they're interviews
flattened into the graph, then a second pass of 14 nodes. Weird, redundant, and it buries the HMW.

### 1.3 There is no "understand before concluding" step
The methodology jumps straight from `start` to `explore` (run councils). Nothing forces the
orchestrator to first **frame** the inquiry: given the HMW, what do we actually need to learn before
we can diverge well? (Which insurances do they already have? How do they think about pension gaps?
What's their awareness? What happened at the real KFZ-moment?) Without this, we dive into conclusions
too early — exactly the failure mode the user named.

### 1.4 But we are closer to the fix than it looks
We already have most of the bim-agent primitives, just not wired as a plan:

| bim-agent concept | we already have |
|---|---|
| evidence ledger | councils + prototype sessions + recalled facts (provenance) |
| defects (open findings) | `research_open_questions` (open/answered) |
| verify artifact | `Synthesis` + `MetaReport` |
| gates | `methodology_judgments` (evidence-backed) + structural invariants |
| task graph | the methodology constellation (DAG of steps) |
| next-action router | `brief_next` (the ready frontier) |
| plan storage | `plans` table (`put_day_plan`/`put_period_plan`) — pattern exists |

What's missing is the **unifying plan object**, the **analyze bucket**, and **councils as
first-class evidence nodes** decoupled from syntheses.

---

## 2. What bim-agent actually does (the portable pattern)

bim-agent labels a house by driving a **plan state machine** (`scene_plan_state.py`), not a chat:

- **The plan is the source of truth** — a JSON sidecar (`<scene>.plan.json`) rendered to a human
  `.md`. It holds `tasks[]`, `defects[]`, `evidence[]`, `decision_log[]`, `current_state`.
- **Every task carries a `phase` ∈ {analysis, editing, verification}**, plus `gates[]`,
  `depends_on[]`, `invalidates[]`. A task only terminates when its gates pass (or are waived with a
  reason + evidence).
- **A singular next-action router** (`get_scene_plan_next_action`) hands the worker *exactly one*
  action with `allowed_tools`, `required_evidence`, `success_gates`. The worker can't free-form.
- **The loop is analyze → act → verify, per action:** ANALYZE (render/read a region, add
  `scene_view` evidence) → EDIT (one coherent write batch) → VERIFY (re-score, run topology/QA
  gates) → keep if metrics improved AND verify passes, else **reopen the task and return to
  analyze**. Failed repairs **transitively invalidate** dependent tasks.
- **Honesty guards:** unreadable → mark unreadable (never fabricate); uncertain → label uncertain
  with evidence; scores must be read fresh from the tool.

The essence to port: **a structured, evolving plan whose tasks are bucketed analyze/act/verify, each
gated by evidence, routed one action at a time, with the plan (not the transcript) as state.**

---

## 3. The unification — one model for all three proposals

### 3.1 A Research Plan is the orchestrator's source of truth
Introduce a first-class **plan per ResearchProject**: an ordered, editable set of **tasks**, each:
```
Task: { id, title,
        bucket: "analyze" | "act" | "verify",   # a TAG (open; not a code enum)
        capability,                              # frame | explore | cluster | decide | build | test | synthesize | …
        intent, status: todo|active|done|blocked,
        consumes:[task_ids], gate?:{kind},       # same DAG + gate grammar as the constellation
        produces:[evidence_refs],                # councils / syntheses / artifacts / sessions it created
        plan_note }                              # the orchestrator's rationale (the "plan.md" prose)
```
The plan is authored + updated by the orchestrator (host) via MCP, mirrored to a human `plan.md`
(rendered from the JSON, exactly like bim-agent). `brief_next` becomes the **plan's next-action
router**: it returns the next ready task, its bucket, what evidence is unmet, and which MCP tools
fit. The orchestrator can **insert/reorder tasks** as understanding grows (add more `analyze` tasks
if diving too early; add a `synthesize` milestone when enough councils have accrued).

### 3.2 The three buckets, mapped to our MCP capabilities
This is the analyze/act/verify decomposition, in design-research terms:

- **ANALYZE — understand before concluding.** Read persona **memory** (the lived simulated days!),
  prior syntheses, world context, open questions. Author the **frame**: the sub-questions / research
  angles / hypotheses to pursue so we don't conclude early. *New capability `frame` (a.k.a.
  `analyze`).* Output = framed council questions + hypotheses (not yet a council). Anti-steering is
  strongest here. For the Pfefferminzia HMW, the first analyze task would yield questions like:
  "which insurances do they already hold? how do they perceive their pension gap? what triggered
  the KFZ purchase? where did a LV-thought last appear and die?" — grounded in each persona's days.
- **ACT — do the work.** `run-council` (a *real* multi-persona council on a framed question),
  `scaffold_artifact` (build a prototype), `record_artifact_session` (a proband drives it and
  reports). Output = **evidence**: councils, artifacts, sessions. *(All existing.)*
- **VERIFY — consolidate + measure progress.** `record_synthesis` (OPTIONAL consolidation over a
  *selected* set of councils), `record_judgment` (the gate: explored enough? core problem chosen?),
  and a **progress assessment toward the HMW goal**. Output = synthesis (when useful) + a gate +
  a progress delta. *(synthesis/judgment exist; explicit HMW-progress is new.)*

### 3.3 This decouples councils from syntheses — and fixes the weird diverge
- **Councils, artifacts, sessions become first-class evidence nodes** in the graph (distinct node
  kinds, rendered from data per the presentation-from-data contract). They can run **one after
  another**. A **synthesis is an optional `verify` task** that consolidates a chosen subset — never
  a mandatory wrapper. (Exactly the user's framing: "a synthesis is always an optional milestone…")
- **The diverge phase stops being N micro-councils.** Discover becomes:
  `analyze (frame research questions from memory) → act (a FEW real multi-persona councils on those
  questions; breadth = diverse personas reacting + several angles) → verify (cluster into key
  problems = one synthesis; judge divergence_complete)`. Breadth comes from *angles × persona
  diversity within real councils*, not one-council-per-head. The first ACT council literally places
  the HMW to a representative council, as the user asked.

### 3.4 The methodology becomes a PLAN TEMPLATE (not a cage)
A methodology constellation (double_diamond_deep, …) **expands into a default plan**: each step
unfolds into its analyze/act/verify tasks. So the diamond shape is preserved — but the plan is
**adaptive**: the orchestrator edits it (more analyze, extra councils, a mid-stream synthesis,
loop-backs) as evidence dictates. A **freeform project = a plan with no template** — the orchestrator
just appends councils and drops a synthesis when needed. **One plan-driven model now subsumes both
the freeform `synthesize` flow and the rigid methodology flow.** The methodology engine's invariants
(breadth-before-decide, gate judgments, artifact-by-tag) become **gates on verify tasks** — same
grammar, same enforcement, no regression.

### 3.5 Gates, defects, honesty — carried over
- **Gates** = the existing evidence-backed `record_judgment` + structural invariants, now attached
  to `verify` tasks. A decide task can't close until its gate judgment + breadth + artifacts exist.
- **Defects** = `research_open_questions` promoted to first-class: an `analyze`/`verify` task can
  raise open questions; a later task `answers` them (edge already exists). Unanswered blockers keep
  the plan non-terminal — exactly bim-agent's defect terminality.
- **Honesty guards** (already enforced for prototype sessions: groundedness gate) generalize: a
  council/synthesis claim must cite evidence; "we don't know yet" is a first-class outcome that
  raises an open question instead of fabricating progress.
- **Progress-to-goal** = a lightweight `verify` assessment: given the HMW and the evidence so far,
  how much closer are we, and what's the next most-valuable uncertainty to reduce? This is the
  design-research analogue of bim-agent's `score_walls` — but LLM-judged with evidence, never a
  hardcoded metric.

---

## 4. Worked example — Pfefferminzia under the new model
```
PLAN for HMW "junge KFZ-Käufer:innen für LV begeistern"  (template: double_diamond_deep)

▸ DISCOVER
  [analyze] frame  — read the 14 personas' lived days + memory; author research questions:
                     existing insurances? pension-gap awareness? KFZ-trigger story? where LV died?
                     → produces: a research frame (hypotheses + 4–6 council questions)
  [act]    council — "Was ging euch beim KFZ-Abschluss durch den Kopf — und wo war Vorsorge?"
                     (8–10 mixed personas, reacting from memory)            → evidence: council#1
  [act]    council — "Wie bereitet ihr euch (nicht) auf später vor, und warum?" (different mix)
                                                                            → evidence: council#2
  [act]    council — provider-side: the KFZ-cross-sell conflict (Ralf/Carla/Bernd) → council#3
  [verify] synthesize + judge — cluster councils #1–3 into key problems + POV;
                     record divergence_complete (evidence = council ids)    → synthesis (key-problems)
▸ DEFINE  [verify] decide — consolidate to the sharp POV + the surprising core segment
▸ IDEATE  [analyze] frame ideas from the POV → [act] councils + [act] build 3 lo-fi → [verify] judge
▸ LO-FI   [act] proband sessions (Playwright) → [verify] decide (rank + shortlist)
▸ REFINE  [act] build mid-fi + councils → [verify] judge
▸ DELIVER [act] proband sessions → [verify] synthesize the solution presentation; progress=HMW-met
```
Compared to the old run: **a handful of real councils** (not 28 nodes), councils visible as
evidence, syntheses only where consolidation adds value, and an explicit *frame* step that stops us
concluding before we understand. Same three diamonds emerge — but the work inside each is honest.

---

## 5. Data-model implications (sketch, for a later spec)
- **New:** a `plan` per project (`tasks[]` JSON + rendered `plan.md`); reuse the `plans` table
  pattern. `brief_next` reads the plan frontier.
- **Promote councils (+ artifacts + sessions) to graph nodes:** the graph's node set becomes
  heterogeneous (`kind: council|synthesis|artifact`), each rendered from data (presentation-from-
  data). Edges: `council—consolidated_by→synthesis`, `synthesis—spawned→council`, existing
  refines/answers. `add_study_to_project` generalizes to `add_evidence_to_project`.
- **`frame`/`analyze` capability:** a new step/task capability producing a research-frame record
  (questions + hypotheses + cited memory). No new "node" required — it's a plan task with a note +
  evidence links; optionally surfaced as a faint node.
- **Backwards-compatible:** the methodology engine stays; it now *emits a plan* on
  `start_methodology_project`. Old syntheses/projects still render. analyze/act/verify are **tags**
  (no enum), consistent with `methodology-presentation-from-data.md`.

---

## 6. Why this is the right "next level"
- It removes the synthesis straitjacket → councils flow naturally, synthesis is a deliberate act.
- It adds the missing **understand-before-conclude** discipline → no premature conclusions.
- It turns the methodology from a fixed pipe into an **adaptive, gated plan** the orchestrator
  reasons about — the same thing that makes bim-agent powerful: *plan is state, work is gated by
  evidence, one action at a time, honest about uncertainty.*
- It unifies freeform research and methodology research under one model.
- It composes cleanly with everything already built: constellations (the template), presentation-
  from-data (node/plan rendering), the persona **lived days** (the substrate the analyze step reads),
  and the no-LLM/host-authoring contract (the orchestrator authors the plan + the text).

---

## 7. Open decisions (for the user)
1. **Scope of the first cut:** (a) *decouple-only* — councils as first-class nodes + optional
   synthesis, no plan object yet; (b) *plan-light* — add the plan + analyze/act/verify routing on
   top of the existing engine; (c) *full* — plan is the unified source of truth, methodology emits
   it, freeform + methodology converge. (Recommend **b → c**; b is shippable and de-risks c.)
2. **Is the `frame`/analyze step always required, or opt-in per methodology?** (Recommend: a default
   analyze task the orchestrator may discharge quickly, but never skip silently.)
3. **Plan surface:** a real `plan.md` per project committed to the repo (bim-agent style, inspectable
   + diffable) vs. DB-only with a rendered view. (Recommend: DB source of truth + rendered `plan.md`
   export, mirroring bim-agent's json→md.)
4. **Progress-to-goal:** keep it purely LLM-judged-with-evidence (recommended), or also expose a
   structural "evidence coverage" signal (councils/segments/artifacts touched) as a non-binding hint?

Next step after a direction is chosen: write the implementation spec (`spec/research-plan-engine.md`)
and migrate `brief_next`/the graph/the skills.
