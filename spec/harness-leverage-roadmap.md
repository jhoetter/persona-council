# Harness leverage roadmap — the few BIG improvements (2026-06-05)

> Question (user): what genuine improvements would be really high-leverage for the harness? This is a
> prioritized, honest answer grounded in what repeatedly goes wrong across real runs — not a wishlist.

## The recurring failure mode (the root cause)
Every shortfall we've hit — "shallow", "not exhaustive", "stops at a good starting point", "no
surfaced hi-fi/conclusion", "0/23 grounded", inconsistent quality — traces to **one structural fact:
a single agent drives the whole run inside one growing context, and judges its own work.** That agent
(a) fills its context and stops early, (b) makes one-pass shallow sweeps, (c) grades itself leniently
and declares "done", and (d) skips organizing/concluding. Quality therefore depends on one agent's
discipline in one long session. The fixes below remove that dependency.

## The 3 highest-leverage moves (in priority order)

### 1. A deterministic, RESUMABLE, multi-agent DRIVER (not one long agent) — the biggest lever
Replace "one agent runs until its context/judgment gives out" with a thin **deterministic orchestrator**
that runs the analyze→act→verify loop and dispatches a FRESH subagent per step (lean context each),
holding only ids + `assess_project` itself. This is the "one prompt → 50+ iterations" north star made
real. Why it's #1: it removes the **context-exhaustion ceiling** that causes early/shallow stops, so a
run can be genuinely exhaustive (dozens of councils, many concepts, full ladders) without degrading.
Pair it with **resumability** (content-addressed/keyed evidence ids — HX6, partly done) so a long run
survives interruption and replays deterministically, accreting depth across sessions/hours. *Status:*
`autonomous-research-run` is a manual skill version; the leverage is making it a real, resumable engine
(a Workflow-style script) that can't lose work and can't run out of room.

### 2. An adversarial COMPLETENESS / QUALITY critic as a hard gate (loop until it passes)
The driving agent grades itself leniently. Add an **independent critic agent** that, before a run may
call itself done, (a) scores the project against a rubric (exploration depth, segment/angle breadth,
concept novelty, evidence groundedness, honesty/anti-steering, finish) and (b) asks the generative
question *"what's missing — which segment, angle, risk, or concept class is unexplored?"* — and whatever
it finds becomes the next round of work. Loop until the critic finds nothing material (loop-until-dry).
Why it's #2: this is the single biggest lever for **exhaustiveness + consistent quality** — it converts
"one pass then stop" into "keep going until genuinely thorough", with an outside judge instead of the
author's own optimism. *Status:* the new `assess_project.finish` + `novelty` signals are the *structural*
seed of this; the dynamic LLM-critic loop is the real prize.

### 3. A richer EXPERIENCE / prototype layer (so hi-fi is genuinely impressive)
The interactive `model` (range/number→computed/bar with a live formula) was a step change — it made
"make the invisible experienceable" buildable. The next leverage is composing it into a real
experience: a **model embedded inside a multi-screen flow**, charts/timelines/curves, branching +
computed state together, and an optional Wizard-of-Oz data layer — so a hi-fi prototype is a
production-credible artifact, not a single computed screen. Why it matters: the *winning* concept of
most of these runs is itself an interactive tool; the deliverable is only as impressive as what we can
actually build + ground-test.

## Strong supporting moves (high value, lower than the top 3)
- **Auto-organization + an always-on deliverable.** Derive SECTIONS (Discover/Define/Solution/ladder/
  Deliver) and the meta-report automatically from the plan, so every run is organized + concluded *by
  construction* — not agent-dependent. (The finish-gate now *flags* this; auto-organize would *do* it.)
- **Deeper persona-memory grounding.** Councils are only as deep as the simulated lives behind them;
  longer, richer, evolving persona memory → deeper, more surprising exploration. The simulation loop
  exists; runs often sit on a thin memory base.
- **A quality/eval harness.** Score each finished run against the rubric and track it over time, so we
  catch regressions in the *methodology itself* and can compare approaches (a regression suite for
  output quality, not just code).

## Down-payments already made (the trajectory)
Structured syntheses persist+render (GAP-3); real groundedness, enforced (GAP-5); the interactive
`model` (GAP-1); nav validation (GAP-4); the connected diamond spine (GAP-6); the artifact palette +
ideation lenses + a `novelty` signal (innovation); and the **`finish` gate** (done = organized +
concluded + handed-off, not just gates-passed) with the autonomous-run skill wired to honor it.
These make each STEP good and each run *finishable*; the top-3 above make the whole RUN exhaustive,
self-critical, and impressive — which is the level the user is aiming for.

## If we did only ONE thing next
Build **#1 + #2 together**: a resumable multi-agent driver whose stop condition is a passing
adversarial critic (not the author's own "complete"). That single combination converts "a good
starting point" into "an exhaustive, finished, self-verified project" — every time.
