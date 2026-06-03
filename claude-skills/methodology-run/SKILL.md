---
name: methodology-run
description: Drive a data-driven methodology (e.g. Double Diamond, d.school micro-cycle, Lean/JTBD) over the council/synthesis graph — the host-stepped engine. Genuinely diverge (fan out explorations) then converge (cluster with an evidence-backed gate), per the chosen methodology, until it produces a buildable spec. Use for "run design thinking / a double diamond / a methodology", or "take a How-Might-We to a tested spec".
---

# methodology-run

You facilitate a **data-driven methodology**. The engine guarantees the SHAPE (diverge before
converge, real breadth, traceability); YOU author the text and make the gate judgments with
evidence. This is the host-stepped path; `run_methodology` (runtime) is the autonomous variant.
Spec: `spec/methodology-engine-and-prototyping.md`.

## Setup
```
list_methodologies                              # pick: double_diamond | dschool_micro | lean_jtbd | …
start_methodology_project <title> <goal=HMW> <methodology_key> [--persona …]
```

## The loop — repeat until brief_phase says complete
```
b = brief_phase(project_id)        # mode, strategy, what's still unmet, the consumed artifact
if b.complete: break

if b.mode == "diverge":
    # FAN OUT — genuinely go broad (this is what makes it a diamond, not a chain)
    for each angle / persona subset (run-council with b.council_strategy):
        record_exploration(project_id, title, council_ids, payload)   # one node per exploration
    # decide for yourself, with evidence, when the space is explored enough — NO fixed count:
    record_judgment(project_id, b.phase, "divergence_complete", true, rationale, evidence_refs=[council_ids…])
    advance_phase(project_id)

else:  # converge
    # if the phase requires a prototype_session, have personas USE the app first (see below)
    record_convergence(project_id, title, from_node_ids=[the explorations you consolidate], payload, role)
    advance_phase(project_id)
```
The engine REJECTS a convergence with < 2 explorations (`BREADTH_TOO_LOW`) or without a
`divergence_complete` judgment (`MISSING_DIVERGENCE_JUDGMENT`) — so you cannot produce a chain.

## Prototype phases (Develop/Ideate/Solution-explore + their converge)
A diverge phase with `requires_artifacts: [prototype]`:
```
scaffold_prototype(slug, name, concept)         # concept = {title, summary, start, screens:[{id,title,elements}]}
```
The converge phase with `requires_artifacts: [prototype_session]` — personas actually USE it:
```
run_prototype(prototype_id)                      # local-only
brief_prototype_session(persona_id, prototype_id)
proto_open(prototype_id) -> proto_act(click/type on refs from the latest snapshot) -> observe REAL state
record_prototype_session(persona_id, prototype_id, session_id, date, reaction)   # cite observed_state_refs
```
Reactions are grounded in the session log; ungrounded praise is rejected. The reaction enters the
persona's memory, so the test/converge council surfaces the real use.

## Output
The four (or more) phase nodes wired diverge→converge in the project graph (a real diamond), a
real prototype the user can open, and a converge `spec` node. Then `meta-brief → meta-outline →
meta-section → meta-export` for the dev-handover document. Watch progress with
`get_methodology_state`; see it in the web inspector's methodology strip + diamond view.

## Autonomous variant
`run_methodology(project_id)` drives the whole loop unattended (LLM backend when a key is set,
else a deterministic stub). It calls the same engine, so all invariants and anti-steering gates
still hold.
```
