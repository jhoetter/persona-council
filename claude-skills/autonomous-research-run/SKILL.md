---
name: autonomous-research-run
description: Drive a LONG, autonomous design-research run from a single prompt (an HMW or any framing) to a well-organized, well-documented result — 10s of iterations of councils, prototypes, exploration, synthesis and solution-spaces over the research-PLAN engine. Lean context per step via next_action + assess_project; one subagent authors each step; sections + a run-journal keep it self-organizing. Use for "kick off a full long-running design-thinking simulation from this question and let it run".
---

# autonomous-research-run

You are the LEAN ORCHESTRATOR of a long run. The locked rule holds: **no in-process LLM** — YOU and
your SUBAGENTS author every word via MCP; the engine enforces structure + gates. The whole point of
this skill is to run **many iterations without bloating your context**: each iteration is one
`next_action` → one subagent authors+persists the step → you receive a *tiny* result (ids + 1 line).
You almost never read a full council/synthesis yourself — you steer from `assess_project`,
`coverage`, and `sections`. Specs: `spec/harness-evaluation-and-autonomy.md`,
`spec/research-plan-engine.md`, `spec/sections-and-composable-graph.md`.

## Setup (once)
1. **Cohort**: ensure richly-segmented personas exist with simulated memory (use `simulate-cohort`
   if not). Reuse an existing cohort when present.
2. **Project**: `start_project "<title>" "<HMW>" --methodology <key> --persona …` (double_diamond /
   double_diamond_deep / d.school / lean_jtbd, or freeform). The plan seeds analyze/act/verify.
3. **Set a budget**: a max iteration count (e.g. 50) and/or "stop when saturated".

## The lean loop (repeat)
```
a = assess_project(project)                  # the pulse: recommendation + gaps + saturation + open gates
if a.recommendation == "complete": break
if budget exhausted: converge & break

n = next_action(project)                     # the ready step, FULLY loaded — your only per-step read
dispatch ONE subagent to author n (below); it persists via MCP and returns ONLY ids + 1 line
# you never read the authored text; the DB + plan.md + sections hold it
```
Authoring per bucket (always a SUBAGENT, grounded in `n`):
- **analyze (frame)** → subagent reads cited persona memory + prior syntheses (from `n.grounding`),
  authors research questions, calls `record_frame`. Returns the frame id.
- **act** → for each ANGLE in `n.act.framed_questions`, subagent runs a REAL multi-persona council
  (`n.act.suggested_participants` — segment-diverse, NOT keyword) via the run-council flow, or
  `scaffold_artifact` + a grounded Playwright proband session; then `add_task`+`link_evidence`+
  `complete_task`. Breadth = angles × persona diversity, **never one council per persona**.
- **verify** → subagent consolidates the fan (`n.verify.fan_evidence`) into a synthesis
  (`record_synthesis` — councils OPTIONAL/decoupled; for affinity, synthesize over notes/other
  syntheses with `council_ids=[]`), records the gate judgment, `assess_progress`, `complete_task`.

## Stay organized & documented (every few iterations — HX5)
- **Sections**: maintain methodology-independent groupings as the run grows — `create_section` /
  `set_section_members` for emerging themes ("Initial user research", "Trust & honest non-option",
  "Solution space"); the methodology PHASES render as derived sections automatically. This is the
  primary "well-organized" surface.
- **Affinity**: capture sharp observations as `create_note` nodes, then `set_section_members` to
  **promote a cluster** into a named theme section (the KJ-method move) — and synthesize the cluster
  council-free.
- **Run journal**: append a one-line `create_note` per milestone ("iter 12: develop diamond gated;
  winner = honest check") and keep them in a "Run-Journal" section. This is durable external memory
  so YOU stay lean.

## Stop criteria (HX7 — don't run forever, don't stop arbitrarily)
Converge/stop when ANY: `assess_project.recommendation == "complete"`; `saturation.hint ==
"converging"` AND open_questions empty; K consecutive councils add no new theme (theme-novelty
saturation); or the iteration budget is hit (then drive the remaining verifies to a Deliver synthesis
+ roadmap and finish honestly, noting what was capped).

## Output
`export_plan_md` (the analyze→act→verify log) + the section overlays (themes + phases) + the Deliver
synthesis + a roadmap + (optionally) a meta-report. The graph reads as a well-organized, multi-diamond
project; `export_section`/`export_synthesis` hand any part to a downstream agent.

## Context hygiene (the discipline that makes 50+ iterations possible)
- One `next_action` and one `assess_project` read per iteration — nothing else in your context.
- Subagents author + persist + return ids only; their context is discarded.
- Re-ground via `assess_project` / `coverage` / `list_sections`, never by re-reading evidence.
- Persist ALL state in the project (plan, sections, notes) — keep no scratch state in your head.

## Hard rules
No in-process LLM authoring (host/subagents only). No one-council-per-persona. Understand before
concluding (never skip the frame). Honest uncertainty raises an open question, not fake progress.
Gates are not skippable — they are the quality floor.
