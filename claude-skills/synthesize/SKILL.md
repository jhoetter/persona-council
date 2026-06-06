---
name: synthesize
description: Drive an iterative, agent-led synthesis — from a single statement, run councils, read each exec summary, decide whether a follow-up council is worth it, until the goal is reached or a cap. Produces one growing study-arc report. Use when asked to "understand X across iterated councils" / "synthesize" / "run councils until we have enough insight".
---

# synthesize

The autonomous study driver: you (the synthesis agent) start from a **statement +
goal**, run a council, read its result, and **decide for yourself** whether another
council would add material insight — formulating the next question yourself — until
you have enough. The final synthesis is the report the user reads (and can drill
into per council).

## Inputs
- `statement`: the thing under study (e.g., a product pitch).
- `goal`: what we want to learn (e.g., "how do we excite people + what to build + open unknowns").
- `max_councils`: hard cap (default 10).
- optional `strategy` per council (see run-council: positive-deepdive / pain-discovery / tension / goal).

## The loop
```
chain = []                      # ordered council ids
syn_id = None                   # the one growing synthesis
ask = a SELF-CONTAINED question derived from `statement` (round 1)
for i in range(max_councils):
    council = run-council(ask, strategy?)      # uses the run-council skill
    chain.append(council.id)
    brief = brief_synthesis(chain, title, start_input=statement, goal)
    syn   = author + record_synthesis(..., goal, synthesis_id=syn_id)  # interim
    syn_id = syn.id
    if syn.status == "done":  break            # goal reached / no productive follow-up
    ask = syn.next_council_question             # MUST be self-contained (see below)
export_synthesis(syn_id)        # the final report
```

## Hard rule — self-contained council questions
Personas are **stateless across councils**: after a council runs they remember
nothing of it. So every `next_council_question` you pass MUST stand alone — include
the essential product briefing + the precise new angle. Never write "building on
the last council…"; the personas never saw it. (Their *own* persona memory persists;
the council discussion does not.)

## Stop criteria (any)
- The synthesis judges the **goal reached** (status="done", stop_reason).
- A follow-up would only **repeat** prior insight (diminishing returns).
- `max_councils` hit → one final synthesis, status="done", stop_reason="cap".

## Author the per-persona `voices` (required)
`brief_synthesis` returns, per council, the **per-persona turns and votes**. Use them
to author the `voices` array — **one entry per distinct persona across the chain** —
the structured layer the UI filters/sorts and the export carries:
```
voices: [{
  persona_id, persona_name,
  segment,                                   # which `segmente` entry they belong to
  sentiment: positiv|bedingt|neutral|skeptisch|ablehnend,
  relevance: stark|teilweise|kaum|irrelevant,# how much the topic TOUCHES their work (independent of liking it)
  key_argument,                              # the ONE-LINE reason WHY, in their voice (grounded, not a label)
  shift: {from, to, trigger, council_id} | null,  # ONLY if their stance actually moved across councils
  evidence: [{council_id, quote}]            # 1–3 grounded quotes from their turns/votes
}]
```
Rules: `key_argument` must be their real point, grounded in the turns/votes. Set
`shift` only when the evidence shows a genuine change (e.g. neutral→positiv) and name
the concrete trigger + the council where it happened. `sentiment` and `relevance` are
**independent axes** — a skeptic can be `relevance: stark`. This is what powers
"warum positiv?" and "was bewegte jemanden von neutral zu positiv?" in the report.

## Output
One `Synthesis` (status done) = the report: arc/trajectory, gesamtbild,
handlungsempfehlungen, positionierung, validated pain-solvers, segmente (incl.
deliberate non-targets), offene_fragen, and the structured **voices** — every claim
traceable to a council. Read it top-down (answer first, then the Stimmen panel:
filter/sort by sentiment & relevance, expand for the shift + evidence); the councils
sit underneath as the log. Hand `export_synthesis` (md or json) to a downstream agent.

## Note
Each council is itself host-authored (run-council skill) and may be moderated with
hand-raising (positive-deepdive) or other strategies. The synthesize loop sits one
level above and chains them.

## Authoring style (Markdown, not ALL-CAPS)

Write analysis/summary prose as **Markdown**: `**bold**`/`_italic_` for emphasis, `-`/`1.` lists,
`>` quotes, blank lines between paragraphs. **Never** use ALL-CAPS for emphasis or write a literal
section header inside the text (e.g. `SUMMARY:`, `VOTES:`, `WHAT THIS COUNCIL FOUND`) — the UI renders
the headers/labels. Applies to `exec_summary`, `summary`, `gesamtbild`, recommendations, meta sections,
notes, etc. A persona/proband turn `content` stays in that persona’s natural voice (it is a quote).

## Unified primitives (preferred shape)

Author content as the shared primitives (spec/unified-artifact-schema.md) so it renders through the one
consistent renderer: **`statements`** (one per persona utterance: `{persona_id, text, stance:{value -2..2,
label}, about:{kind:"prompt",id}, refs}`), **`findings`** (analysis items: `{text, kind:
summary|key_problem|recommendation|open_question|…, score, refs}`), **`prompts`** (`{text, kind, id}`).
One positivity scale only (oppose −2 … support +2) for every stance/vote/sentiment. Legacy fields
(turns/votes/voices/key_problems/…) still work in parallel.
