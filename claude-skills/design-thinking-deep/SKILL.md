---
name: design-thinking-deep
description: Run the FULL deep design-thinking process (double_diamond_deep) at depth — many personas, broad problem exploration, affinity clustering to key problems, a lo-fi→mid-fi prototype ladder with real Playwright tests, and a solution presentation. Drives breadth via PARALLEL subagent fan-out (never an in-process LLM). Use for "run a deep/full design thinking project", "do it in way more detail", "three diamonds".
---

# design-thinking-deep

The deep variant of `methodology-run`, on the `double_diamond_deep` **constellation** (three linked
diamonds). A methodology only SEEDS the **research PLAN** — the single engine: a DAG of tasks bucketed
**analyze / act / verify** (since HX3 there is one engine; the old constellation runtime was retired
— see `spec/hx3-engine-collapse.md`). The plan enforces the SHAPE + gates and is tag-agnostic;
**I (the host) and my subagents author every word** via MCP — **never call an LLM API for text**
(OpenAI = embeddings + images only). "At scale" = **parallel subagent fan-out**, not a server-side
loop. Specs: `spec/research-plan-engine.md` + `spec/methodology-constellations.md` +
`spec/deep-design-thinking-and-diamond.md`.

## Setup — a real cohort
Author **12–16 segmented personas** (record_persona; host-authored) spanning age × life-stage ×
attitude × channel × region + 2–3 provider-side roles. Then seed the plan:
```
start_project "<title>" "<HMW>" --methodology double_diamond_deep --persona … (all of them)
# seeds a `frame` analyze task per fan step + a gated `verify` task per decide step.
```

## The loop (`next_action`/`brief_next` drives it; one Synthesis per converge; six steps)
For each ready task, `next_action`; then by bucket:

**analyze (frame) — understand before concluding:**
- `frame__discover` / `frame__ideate` / `frame__refine`: read persona memory (their simulated days)
  + prior evidence, author the research questions/angles → `record_frame(questions, hypotheses,
  memory_refs)` (≥1 question + ≥1 memory ref). This opens the diamond.

**act — FAN OUT WIDE (this is the diamond; breadth = angles × persona diversity):**
- discover: spawn subagents (parallel batches) each loading its own `persona-context` and reacting
  (pain-discovery); assemble a FEW **real multi-persona councils** per angle → `add_task("act",
  "explore", "<angle>", consumes=[frame__discover])` + `link_evidence(kind="council")` +
  `complete_task`. (Several councils of many personas — NOT one council per persona.)
- ideate: one act task per solution angle; build **several lo-fi prototypes** (`scaffold_artifact(...,
  type="prototype", tags=["lofi"])`, consuming `frame__ideate`) + `link_evidence(kind="artifact")`.
- refine: build **mid-fi** prototype(s) of the shortlist (`tags=["midfi"]`, consuming `frame__refine`).
- Stop fanning out by your own judgment (evidence-backed) — never a fixed count.

**verify — cluster / decide behind an evidence gate (one synthesis per waist):**
- `verify__define`: **affinity-cluster** the discover fan; author a synthesis payload with
  `clusters:[{label, member_node_ids, insight}]` + `key_problems:[…]` → `record_synthesis` +
  `link_evidence(kind="synthesis")` + `record_judgment("divergence_complete", …)` + `complete_task`.
- `verify__lofi_select`: personas **USE each lo-fi prototype** via Playwright (`run_prototype` →
  `brief_prototype_session` → `proto_open`/`proto_act` → `record_prototype_session`); then a synthesis
  with `ranking:[{prototype_id, score_rationale}]` + `shortlist:[…]`; judge + complete. (Its
  `requires.session_of_tags:["lofi"]` is matched by tag-equality to the lo-fi prototypes' sessions.)
- `verify__deliver`: personas **USE the mid-fi** prototype (`session_of_tags:["midfi"]`); synthesize
  the **solution presentation** (winning concept, who-wins + non-targets, validated pain-solvers,
  evidence trail, open risks, spec); `assess_progress(delta="beantwortet")` + `complete_task`.

A verify task is **gated**: it cannot complete until its act fan has ≥`min_inputs` distinct act
tasks with evidence, a decided `gate_tag` judgment exists, and any required artifacts/sessions exist.
So you cannot skip the work or conclude early.

## Parallelism & cost (host judgment)
- Fan out subagents in **parallel batches** (e.g. 4–6 at a time). Each subagent does its OWN
  `persona-context` load + reaction; you assemble the multi-persona councils + act tasks.
- Breadth target: discover ≈ a few real councils across the segments; ideate ≈ 4–8 ideas; lo-fi ≈
  3–5 prototypes; mid-fi ≈ 1–2. Adjust to the problem; `log`/note when you cap.

## Real prototypes (lo-fi → mid-fi)
- Lo-fi: `scaffold_artifact(slug, name, concept, type="prototype", tags=["lofi"])` — cheap, several.
- Mid-fi: `scaffold_artifact(... tags=["midfi"])` of the shortlisted concept.
- Always tested for real via the Playwright harness; reactions grounded in the session log.

## Output
Three real diamonds in the project graph (wide discover fan → key problems → wide ideate fan →
shortlist → refine → solution presentation), real lo-fi + mid-fi prototypes, `export_plan_md` as the
analyze/act/verify log, and a Meta-Report = the **solution presentation**. See it in the web
inspector's methodology strip + diamond view.

## Hard rule
No LLM text-generation, ever. Host/subagents author all text via MCP. OpenAI key = embeddings +
images only. (See the project memory + `spec/deep-design-thinking-and-diamond.md` §2.)
