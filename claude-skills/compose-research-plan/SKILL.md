---
name: compose-research-plan
description: From a single prompt (an HMW or any research goal), DESIGN the research plan yourself — decide which methods (councils, prototypes, affinity clustering, proband sessions, syntheses, sections) to stitch together and in what analyze→act→verify shape — then seed it so an autonomous run can execute. Use when the user just drops a question ("how might we …") and expects the agent to figure out the approach. Hands off to autonomous-research-run.
---

# compose-research-plan

The user gives you a question; **you decide the methodology and the moves**. The plan engine is
fully composable — `capability` / `artifact_type` / `gate_tag` are FREE tags and you `add_task`
any analyze→act→verify shape you want — so you are not limited to a preset. Choose the simplest
shape that genuinely answers the question, then seed it and run.

## 1. Read the question, classify the inquiry
Decide what kind of work the prompt needs (often a mix):
- **Problem exploration** (an HMW, "understand X"): emphasize Discover councils + affinity clustering
  + a sharp POV. (Double Diamond / d.school.)
- **Solution design** ("design/prototype Y"): light discover, heavy Develop — ideation councils,
  varied prototypes, proband sessions, fidelity ladder. 
- **Evaluation/validation** ("does Z work / which option"): councils to react + prototypes to test +
  a comparison synthesis. (Lean/JTBD.)
- **Pure analysis** ("what do our personas think about W"): a few councils → one synthesis, no build.

## 2. Survey what you have (don't guess)
- `suggest_methodologies` (preset constellations), `suggest_capabilities`, `suggest_artifact_types`,
  `suggest_section_kinds` — the data-driven building blocks (adopt / tweak / invent tags).
- `list_personas` + their simulated memory — your evidence base (run `simulate-cohort` if thin).

## 3. Decide the plan — pick OR compose
- **Adopt a preset** when one fits: `start_project "<title>" "<HMW>" --methodology <key> --persona …`
  (seeds analyze/act/verify diamonds).
- **Compose freeform** when the question needs a bespoke shape: `start_project … ` (no methodology →
  one root frame), then `add_task` the constellation you designed — e.g.
  `frame__discover` → N act councils → `verify__define` (gate `divergence_complete`) →
  `frame__affinity` → cluster syntheses → `verify__keyproblems` → `frame__develop` → ideation +
  prototypes → `verify__shortlist` (gate, `session_of_tags:["lofi"]`) → `frame__refine` → mid/hi-fi →
  `verify__deliver` (gate, `session_of_tags:["prototype"]`). Wire `consumes` to order the diamonds;
  put real `requires` gates so the run can't shortcut.
- **Stitch methods per step**: a step's `produces.artifact_type` decides whether it builds a
  prototype; a verify's `requires.session_of_tags` forces a proband test; affinity = act tasks
  producing council-free cluster syntheses (synthesis⟂council is decoupled). Mix freely.
- **Justify the design** in the frames' intents and a first `create_note` ("plan rationale: …") — so
  the choice is documented, not implicit.

## 4. Hand off
Once the plan is seeded, run **autonomous-research-run**: it loops `assess_project` + `next_action`
→ one subagent authors each step → maintains sections + a run-journal → stops on saturation/budget.
You designed the shape; that skill executes it lean.

## Principles
You own the methodology choice — make it from the question + the evidence, not from the repo name or
a product thesis (anti-steering). Prefer the smallest shape that answers the question; add diamonds
only when the question's breadth warrants. Gates are the quality floor — always put real ones. No
in-process LLM (you/subagents author via MCP).
