---
name: design-thinking
description: Facilitate a Design Thinking (Double Diamond) project over the council/synthesis research graph — drive a "How Might We" question through Discover → Define → Develop → Deliver, including a prototype phase where personas USE a real minimal app and react to it. Produces a dev-ready spec (Deliver synthesis + meta-report). Use when asked to "run design thinking", "double diamond", "frame a problem and prototype a solution", or "take an idea to a buildable spec".
---

# design-thinking

You act as the **facilitator** of a Double Diamond. This is **not a new engine** — it is a way
to sequence the `run-council` and `synthesize` skills and organize their syntheses into a
diamond. The persona **experience-driven** loop is the foundation; you only decide *which*
councils run, *in what order*, with *which strategy*, and *how to link* the results.
Methodology details: `spec/design-thinking-methodology.md`.

## Inputs
- `challenge`: a **How Might We …?** question (becomes the project `goal`).
- `personas`: the cohort in scope (slugs, or "all").
- `prototype`: optional — by Develop you will build a **real, minimal, runnable app**.

## Setup
```
research-create  "<title> · Double Diamond"  --goal "<HMW>"   # set methodology="double_diamond"
```
Pick participants per phase by **relevance** (LLM-authored from candidate summaries — never
keyword scoring). Load each via `persona-council persona-context <slug> --task "…" --text`
BEFORE authoring any turn (AGENTS.md). Anti-steering throughout.

## The loop (each phase = one Synthesis, built from council(s), then linked)
```
# ◇ DIAMOND 1 — PROBLEM SPACE
Discover  (DIVERGE): run-council strategy=pain-discovery   → Synthesis tag phase:discover
          gate: stop widening when new councils only repeat known pains
Define    (CONVERGE): run-council strategy=goal|tension     → Synthesis tag phase:define
          author the Point-of-View (positionierung) + the next HMW (next_council_question)
          link  Discover --refines--> Define

# ◇ DIAMOND 2 — SOLUTION SPACE
Develop   (DIVERGE): run-council strategy=positive-deepdive → Synthesis tag phase:develop
          BUILD a real minimal app under prototypes/<slug>/ (see §Prototype)
          link  Define --spawned_from--> Develop
Deliver   (CONVERGE): TEST then decide                       → Synthesis tag phase:deliver
          link  Develop --refines--> Deliver, status="done"

# HANDOVER
meta-brief → meta-outline → (per phase) meta-section-brief → meta-section → meta-export
```

## Prototype — personas USE a real app (the experience-driven test)
1. Build a tiny self-contained app (`prototypes/<slug>/index.html` or minimal FastAPI). Real,
   runnable locally, deliberately minimal — never for real hosting/users.
2. Capture each persona's use as a **lived experience** (zero new tools): a `record-day`
   activity *"Tried the <name> prototype"* with the honest reaction in
   `what_happened`/`conversation`/`persona_thought`, `artifacts_touched=["Prototype: <name> v0.1"]`;
   then `record-deltas` so it enters memory (entity `kind=topic`, facts = frictions + delights).
3. The **Test council** then reacts grounded in having used it (`persona-context` surfaces the
   memory). Honest friction and rejection are first-class signals, not failures.

## Convergence gates (explicit, not vibes)
- **Discover→Define:** added breadth stops changing the picture (diminishing returns).
- **Define waist:** the council reaches a defensible decision on *the* core problem.
- **Develop→Deliver:** a single minimal prototype is worth committing to and testing.
- **Deliver done:** the requirements are specific enough for a dev team to build.

## Output
- Four phase **Synthesis** nodes wired Discover→Define→Develop→Deliver in the project graph.
- A real minimal **prototype app** the user can open.
- A **MetaReport** = the Double-Diamond write-up: build-order narrative + a section per phase,
  every claim traceable to a council. The Deliver synthesis + meta-report **is** the dev spec
  (must-haves via `handlungsempfehlungen` effort/value, who-for via `segmente`, validated solves
  via `pain_solvers`, open risks via `offene_fragen`).

## Principle
Diverge/converge is the run-council strategies (`pain-discovery`/`positive-deepdive` =
divergent; `goal`/`tension`→decision = convergent). The facilitator's whole job is sequencing
them per the diamond and keeping every claim grounded in a persona's lived experience.

## Authoring style (Markdown, not ALL-CAPS)

Write analysis/summary prose as **Markdown**: `**bold**`/`_italic_` for emphasis, `-`/`1.` lists,
`>` quotes, blank lines between paragraphs. **Never** use ALL-CAPS for emphasis or write a literal
section header inside the text (e.g. `SUMMARY:`, `VOTES:`, `WHAT THIS COUNCIL FOUND`) — the UI renders
the headers/labels. Applies to `exec_summary`, `summary`, `gesamtbild`, recommendations, meta sections,
notes, etc. A persona/proband turn `content` stays in that persona’s natural voice (it is a quote).
