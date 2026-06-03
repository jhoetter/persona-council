---
name: methodology-run
description: Drive a plan-based design-research project (any methodology constellation, e.g. Double Diamond, d.school, Lean/JTBD — or freeform) via the analyze→act→verify plan loop. Frame the inquiry first (understand before concluding), run a FEW real multi-persona councils, build & test prototypes, then consolidate behind evidence gates. Use for "run design thinking / a methodology / take a How-Might-We to a tested, evidence-backed answer".
---

# methodology-run

You drive a **research PLAN** — the orchestrator's source of truth: a DAG of tasks bucketed
**analyze / act / verify**. The engine enforces structure + gates; **you (host) + subagents author
every word via MCP** — never an in-process LLM (OpenAI = embeddings + images only). Specs:
`spec/research-plan-engine.md` (+ `methodology-constellations.md`, `methodology-presentation-from-data.md`).

## The golden rule (read this)
**Do NOT run one council per persona.** A council's value is *several personas reacting to each
other from their lived memory*. Discover = **1 frame + a FEW real multi-persona councils + 1
synthesis** — not 14 micro-interviews. Breadth = angles × persona diversity within real councils.

## Setup
```
start_project "<title>" "<HMW>" [--methodology double_diamond_deep] [--persona …]
# methodology -> the plan is seeded analyze/act/verify per step; freeform -> one root frame task.
```

## The loop — repeat until brief_next says complete
```
b = brief_next(project_id)        # the ready frontier: a task with bucket + capability + unmet gates
if b.complete: break

if b.bucket == "analyze":         # FRAME — understand before concluding
    # read persona memory (their simulated days), prior evidence; author research questions.
    record_frame(project_id, b.task, questions=[…], hypotheses=[…], memory_refs=[…])   # >=1 q + >=1 ref

elif b.bucket == "act":           # DO THE WORK (breadth = angles × persona diversity)
    # add an act task per angle, run a REAL multi-persona council on a framed question,
    # or scaffold_artifact / record_artifact_session (proband test). Then link + complete:
    t = add_task(project_id, "act", "explore", "<angle>", consumes=[the frame task])
    cid = run-council(framed question, several persona_ids)         # the run-council skill
    link_evidence(project_id, t.id, "council", cid);  complete_task(project_id, t.id)

else:                             # VERIFY — consolidate + gate
    # optionally synthesize the fan into key-problems / shortlist / solution-presentation:
    syn = record_synthesis(title, council_ids=[the fan], payload)   # the synthesize skill
    link_evidence(project_id, b.task, "synthesis", syn.id)
    record_judgment(project_id, b.task, "divergence_complete", true, rationale, evidence_refs=[…])
    assess_progress(project_id, b.task, rationale, evidence_refs, delta)   # progress toward the HMW
    complete_task(project_id, b.task)            # rejected until breadth + gate + artifacts/sessions
```
A verify task is **gated**: it cannot complete until its act fan has ≥`min_inputs` evidence, a
decided `gate_tag` judgment exists, and any required artifacts/sessions exist. So you cannot skip
the work or conclude early.

## Build / test (artifacts)
Build varied, real, clickable prototypes (NOT just forms): `scaffold_artifact(slug, name, concept,
type="prototype", tags=["lofi"|"midfi"|"hifi"])`. Test them: `run_prototype` → `proto_open`/
`proto_act` (Playwright) → `record_artifact_session` (grounded in the observed state) → `link_evidence`.
A verify task with `session_of_tags:["lofi"]` needs a recorded session of a lofi artifact, etc.

## Output
`export_plan_md(project_id)` renders the analyze/act/verify log. The project graph shows councils +
syntheses as first-class nodes with diamonds emerging over act→verify; artifacts placed + routed.
The final verify `assess_progress(delta="beantwortet")` is the evidence-backed answer to the HMW.

## Hard rules
No LLM text-generation, ever (host/subagents author all text via MCP). No one-council-per-persona.
Understand before concluding (the frame is never silently skipped). Honest uncertainty raises an
open question instead of fabricating progress.
