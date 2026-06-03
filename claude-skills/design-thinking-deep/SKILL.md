---
name: design-thinking-deep
description: Run the FULL deep design-thinking process (double_diamond_deep) at depth — many personas, broad problem exploration, affinity clustering to key problems, a lo-fi→mid-fi prototype ladder with real Playwright tests, and a solution presentation. Drives breadth via PARALLEL subagent fan-out (never an in-process LLM). Use for "run a deep/full design thinking project", "do it in way more detail", "three diamonds".
---

# design-thinking-deep

The deep variant of `methodology-run`, on the `double_diamond_deep` methodology (three linked
diamonds). The engine enforces the SHAPE; **I (the host) and my subagents author every word** via
MCP — **never call an LLM API for text** (OpenAI = embeddings + images only). "At scale" =
**parallel subagent fan-out**, not a server-side loop. Spec: `spec/deep-design-thinking-and-diamond.md`.

## Setup — a real cohort
Author **12–16 segmented personas** (record_persona; host-authored) spanning age × life-stage ×
attitude × channel × region + 2–3 provider-side roles. Then:
```
start_methodology_project "<title>" "<HMW>" double_diamond_deep --persona … (all of them)
```

## The loop (brief_phase drives it; one Synthesis per node; six phases)
For each phase, `brief_phase`; then:

**Diverge phases — FAN OUT WIDE (this is the diamond):**
- `discover`: spawn **one subagent per persona** (in parallel batches), each loads its own
  `persona-context` and reacts (pain-discovery) → `record_exploration` per persona. 12–16 nodes.
- `ideate`: spawn **one subagent per solution idea** → `record_exploration` per idea; build
  **several lo-fi prototypes** (`scaffold_prototype --template spa-sketch`, fidelity=lofi).
- `refine`: build **mid-fi** prototype(s) of the shortlist (`--template spa-min`, fidelity=midfi);
  one exploration per refinement angle.
- Then a host `record_judgment(divergence_complete, evidence_refs=[council_ids])` and `advance_phase`.
- Stop fanning out by your own judgment (evidence-backed) — never a fixed count.

**Converge phases — cluster / decide:**
- `define`: **affinity-cluster** the discover fan into themes; author payload with
  `clusters:[{label, member_node_ids, insight}]` + `key_problems:[…]`; `record_convergence` (role
  key-problems).
- `lofi_select`: personas **USE each lo-fi prototype** via Playwright (`run_prototype` →
  `brief_prototype_session` → `proto_open`/`proto_act` → `record_prototype_session`); then
  down-select: author `ranking:[{prototype_id, score_rationale}]` + `shortlist:[…]`; `record_convergence`.
- `deliver`: personas **USE the mid-fi** prototype; synthesize the **solution presentation**
  (winning concept, who-wins + non-targets, validated pain-solvers, evidence trail, open risks, spec);
  `record_convergence` (role solution-presentation), `advance_phase` → complete.

## Parallelism & cost (host judgment)
- Fan out subagents in **parallel batches** (e.g. 4–6 at a time). Each subagent does its OWN
  `persona-context` load + reaction; you assemble councils + exploration nodes.
- Breadth target: discover ≈ one node per persona; ideate ≈ 4–8 ideas; lo-fi ≈ 3–5 prototypes;
  mid-fi ≈ 1–2. Adjust to the problem; log when you cap.

## Real prototypes (lo-fi → mid-fi)
- Lo-fi: `scaffold_prototype(slug,name,concept,template="spa-sketch")` — sketchy, cheap, several.
- Mid-fi: `scaffold_prototype(... template="spa-min")` of the shortlisted concept.
- Always tested for real via the Playwright harness; reactions grounded in the session log.

## Output
Three real diamonds in the project graph (wide discover fan → key problems → wide ideate fan →
shortlist → refine → solution presentation), real lo-fi + mid-fi prototypes, and a Meta-Report =
the **solution presentation**. See it in the web inspector's methodology strip + diamond view.

## Hard rule
No LLM text-generation, ever. Host/subagents author all text via MCP. OpenAI key = embeddings +
images only. (See the project memory + `spec/deep-design-thinking-and-diamond.md` §2.)
