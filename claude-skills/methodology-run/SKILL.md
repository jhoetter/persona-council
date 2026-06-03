---
name: methodology-run
description: Drive a tag-driven methodology constellation (e.g. Double Diamond, d.school micro-cycle, Lean/JTBD, or any you author) over the council/synthesis graph — the host-stepped engine. Genuinely fan out (record_node) then decide behind an evidence-backed gate (record_decision), per the chosen constellation, until it produces a buildable spec. Use for "run design thinking / a double diamond / a methodology", or "take a How-Might-We to a tested spec".
---

# methodology-run

You facilitate a **tag-driven methodology constellation** — a DAG of steps carrying OPEN TAGS.
The engine guarantees the SHAPE (fan out before deciding, real breadth, traceability) and is
**tag-agnostic** (it never checks a tag against a fixed list); YOU author the text and make the
gate judgments with evidence. This is the host-stepped path; `run_methodology` (runtime) is the
autonomous variant. Spec: `spec/methodology-constellations.md`.

## Setup
```
list_methodologies                              # pick: double_diamond | dschool_micro | lean_jtbd | …
# (optional) browse building blocks — suggestions, NOT constraints:
suggest_methodologies / suggest_capabilities / suggest_roles / suggest_artifact_types
start_methodology_project <title> <goal=HMW> <methodology_key> [--persona …]
```

## The loop — repeat until brief_next says complete
```
b = brief_next(project_id)         # the ready frontier: primary step (+ b.ready set), tags,
if b.complete: break               # strategy, unmet `requires`, consumed nodes

if b.mode == "diverge":            # a FAN step (no min_inputs)
    # FAN OUT — genuinely go broad (this is what makes it a diamond, not a chain)
    for each angle / persona subset (run-council with b.strategy):
        record_node(project_id, title, council_ids, payload [, step_id=b.step])   # one node each
    # decide for yourself, with evidence, when explored enough — NO fixed count. The gate_tag is
    # whatever the downstream decide step requires (b tells you; usually "divergence_complete"):
    record_judgment(project_id, b.step, "<gate_tag>", true, rationale, evidence_refs=[council_ids…])
    advance(project_id, b.step)

else:                              # a DECIDE step (has min_inputs / gate_tag / session reqs)
    # if requires.session_of_tags is set, have personas USE the artifact first (see below)
    record_decision(project_id, title, from_node_ids=[the nodes you consolidate], payload)
    advance(project_id, b.step)
```
The engine REJECTS a decision with < `min_inputs` upstream nodes (`BREADTH_TOO_LOW`) or without
the required decided `gate_tag` judgment (`MISSING_GATE_JUDGMENT`) — so you cannot produce a chain.
Branches/parallel tracks: `b.ready` may list several steps at once — pass `step_id` to target one.

## Build / test steps (artifacts)
A fan step that declares `produces.artifact_type` BUILDS a real artifact:
```
scaffold_prototype(slug, name, concept)         # concept = {title, summary, start, screens:[{id,title,elements}]}
```
A decide step with `requires.session_of_tags: ["<tag>"]` — personas actually USE the artifact
carrying `<tag>` (e.g. "prototype", or a fidelity like "lofi"/"midfi"):
```
run_prototype(prototype_id)                      # local-only
brief_prototype_session(persona_id, prototype_id)
proto_open(prototype_id) -> proto_act(click/type on refs from the latest snapshot) -> observe REAL state
record_prototype_session(persona_id, prototype_id, session_id, date, reaction)   # cite observed_state_refs
```
Reactions are grounded in the session log; ungrounded praise is rejected. The reaction enters the
persona's memory, so the test/decide council surfaces the real use. Matching is by tag-EQUALITY
(produces.artifact_type / more_tags on the build step ↔ requires.session_of_tags on the decide step).

## Output
The step nodes wired fan→waist in the project graph (real diamonds emerge), real artifact(s) the
user can open, and a decide `spec`/`solution-presentation` node. Then `meta-brief → meta-outline →
meta-section → meta-export` for the dev-handover document. Watch progress with
`get_methodology_state`; see it in the web inspector's methodology strip + diamond view.

## Authoring a NEW methodology (data only, no code)
A methodology is JSON: `{key, name, description, when_to_use, steps:[…]}`. Each step:
`{id, name, tags:[…], intent, consumes:[ids], strategy?, produces:{role?, artifact_type?, more_tags?},
requires:{min_inputs?, gate_tag?, artifact_tags?, session_of_tags?}, loop_back?}`. Draw on
`suggest_*` for common tags or invent your own — the engine treats them all identically. Register
via `register_methodology` (DB) or drop a file in `persona_council/methodologies/`.

## Autonomous variant
`run_methodology(project_id)` walks the whole frontier unattended via a deterministic stub (NO
in-process LLM text-generation — host/subagents author all text). It calls the same engine, so all
invariants and anti-steering gates still hold.
```
