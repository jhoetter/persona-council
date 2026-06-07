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

## Cross-reference councils, NEVER copy their voices (required)
`brief_synthesis` returns, per council, the **per-persona statements and votes**. A
synthesis must **not** re-host those voices — it does not carry its own copy of the
personas' words. Instead, to reflect what a council said, author your OWN `finding`
text (your re-interpretation) and attach a **ref** that points at the source
statement; the persona's actual words resolve live, in the council, from that link.

```
findings: [{
  text,                                      # YOUR interpretation, in Markdown — not a paste of the quote
  kind: summary|key_problem|pain_solver|open_question|recommendation|cluster|segment|ranking|shortlist,
  score: {effort, value},
  refs: [{ kind: "council", id: "<council-id>", anchor: "<statement-id>", role: "derived_from" }]
}]
```
Rules (spec/artifact-cross-references.md): the finding `text` must be your real
synthesis point — grounded in the statements/votes but written by you, never a copied
quote. Use a finding per persona-segment / pain / recommendation / open question and
cross-ref the 1–3 source statements it derives from. To express a stance shift, write
it into the finding text and ref the before/after statements (the live link shows the
words). This is what powers "warum positiv?" and "was bewegte jemanden von neutral zu
positiv?" — the reader follows the ref chip into the council, the single source of truth.

## Output
One `Synthesis` (status done) = the report. Its `payload` is **primitives + prose
only**: `gesamtbild` / `positionierung` / `arc_narrative` (Markdown prose),
`references`, `citations`, `status`, plus `findings`, `statements` and `prompts`. The
analysis layers that used to be their own keys are now **findings with the matching
`kind`**: pain-solvers (`pain_solver`), recommendations (`recommendation`), segments
incl. deliberate non-targets (`segment`), open questions (`open_question`), key
problems (`key_problem`), clusters/rankings/shortlists. Every finding cross-refs its
source council statements (role `derived_from`), so every claim stays traceable and the
persona's words live once, in the council. Read it top-down (gesamtbild first, then the
findings, each chip deep-linking into the council it derives from); the councils sit
underneath as the log. Hand `export_synthesis` (md or json) to a downstream agent.

## Note
Each council is itself host-authored (run-council skill) and may be moderated with
hand-raising (positive-deepdive) or other strategies. The synthesize loop sits one
level above and chains them.

## Authoring style (Markdown, not ALL-CAPS)

Write analysis/summary prose as **Markdown**: `**bold**`/`_italic_` for emphasis, `-`/`1.` lists,
`>` quotes, blank lines between paragraphs. **Never** use ALL-CAPS for emphasis or write a literal
section header inside the text (e.g. `SUMMARY:`, `VOTES:`, `WHAT THIS COUNCIL FOUND`) — the UI renders
the headers/labels. Applies to `exec_summary`, `summary`, `gesamtbild`, recommendations, meta sections,
notes, etc. A persona/proband statement `text` stays in that persona’s natural voice (it is a quote, in a council).

## Primitives-only authoring contract

Author everything as the shared primitives (spec/unified-artifact-schema.md) so it renders through the
one consistent renderer. These are the ONLY accepted shapes — there is no
`key_problems`/`pain_solvers`/`handlungsempfehlungen`/`offene_fragen`/`clusters`/`segmente`/`ranking`/
`shortlist`/`voices` key, and a synthesis does NOT carry its own `statements` copy of council voices.

`record_synthesis(title, start_input, council_ids, payload={…}, goal, …)` where `payload` =

- prose: **`gesamtbild`** / **`positionierung`** / **`arc_narrative`** (Markdown), plus `status`,
  `references`, `citations`.
- **`findings`** — every analysis item: `{text (Markdown — your interpretation), kind:
  summary|key_problem|pain_solver|open_question|recommendation|cluster|segment|ranking|shortlist,
  score:{effort,value}, refs}`.
- **`statements`** / **`prompts`** — only for the synthesis's own framing; **never** to re-host council
  voices.

**Cross-reference, never copy** (spec/artifact-cross-references.md): to reflect a council statement,
author your own finding `text` and add a ref `{kind:"council", id:"<council-id>", anchor:"<statement-id>",
role:"derived_from"}`. The source words resolve live from the council. One positivity scale only
(oppose −2 … support +2) for every stance/sentiment.
