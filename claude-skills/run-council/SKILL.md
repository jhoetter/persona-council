---
name: run-council
description: Run a memory-grounded council where each persona judiciously decides whether to research its own memory before reacting. Use when asked to have personas discuss/評価 a topic, product, or decision.
---

# run-council

A council where personas react to a prompt **grounded in their own lived memory**,
and — crucially — **decide for themselves whether the topic connects to something
specific they remember**, instead of always querying or never querying.

Spawn one subagent per participating persona (parallel). Each subagent:

## 1. Load self + topic
- Read the topic/briefing.
- `persona-council persona-context <slug> --task "<the council question>" --text`
  → SOUL + active projects + open threads + an initial task-keyed recall.

## 2. Reflect, then research ONLY if it pays off (the judicious step)
Look at the council question against the already-loaded active projects / open
threads / SOUL and ask: *"Does this genuinely connect to something concrete in my
work or memory?"*
- **If yes** → formulate 1–2 of your OWN sharp queries and look them up:
  `persona-council recall <slug> "<your specific question>"` (semantic+keyword),
  and `persona-council project <slug> <entity_id>` for an arc if relevant.
  Examples: a structural receiver looks up past IFC-import failures; a heritage
  architect looks up how long a Bestandsaufnahme actually took.
- **If no / only a generic link** → do NOT keep digging. Answer from the loaded
  context. Over-researching is as wrong as never researching.

Aim: 0–2 targeted lookups, driven by the persona's judgement — not a fixed ritual.

## 3. React in character (honest, anti-steering)
- Speak as the persona. Support, skepticism, indifference, rejection are all
  valid; never force approval; no vendor tone. Ground claims in concrete memory
  (cite the specific project/event you recalled).
- Output JSON: `{stance, headline, content, concerns[], would_use, memory_used[]}`
  where `memory_used` records what you looked up and why — or is `[]` if you
  judged that nothing specific applied (that is a valid, honest outcome).

## 3b. Moderated back-and-forth (optional, recommended for rich topics)
Instead of parallel monologues, run a directed debate:
1. **Round 1 — openings:** every participant states its position (steps 1–3).
2. **Mediator turn (host-authored):** read all openings; summarize the round's
   sentiment; identify the sharpest tensions/clusters; then **select who speaks
   next and to what** — pair opposites ("X doubts IFC, Y calls it the lever —
   respond to each other"), pull the undecided, or target a goal ("skeptics:
   what single thing flips you?"). Selection mechanisms: tension-driven,
   sentiment-driven, or goal-driven. Add this as a turn with speaker="Moderator".
3. **Round 2 — directed:** ONLY the selected personas respond (to the mediator's
   question and to each other's quoted points), again researching memory if it
   sharpens the reply. Not everyone speaks every round.
4. Repeat 2–3 while it stays productive (typically 1–2 directed rounds), then
   synthesize. Store all turns (openings + moderator + directed) in order.

## 3c. Mediator strategies (pass `strategy=` to the council)
The mediator's selection criterion is pluggable. Pick per goal:

- **`positive-deepdive`** (default for "how do we truly excite people"): each round
  the mediator picks the **positive points that MULTIPLE people named** and drives
  deeper on exactly those — "what would make you not just use it but *champion* it?
  paint the wow-moment; which concrete biggest problem of yours would it erase?"
  Keep mining the hottest positive threads, not the objections.
- **`pain-discovery`**: have each persona surface their **biggest problems that
  somehow touch the product** (even loosely) — to find new insight/opportunity
  *beyond* the current scope. Mediator deepens the pains with the most product-
  adjacent energy.
- **`tension`**: pair the sharpest disagreements and make them respond to each other.
- **`goal`**: drive toward a specific decision question.

## 3d. Hand-raising convergence loop (for deep-dive / pain-discovery)
Don't run a fixed number of rounds — run until the energy is spent:
1. Mediator opens a thread (per strategy) to the relevant personas.
2. Each addressed persona either **contributes something concrete** OR **passes**,
   and sets `raise_hand: true/false` = "I have MORE concrete to add if we go deeper."
   Everyone must be able to opt out honestly — passing is valid.
3. Mediator continues the next deepening round **only with the hand-raisers**, on
   the thread with the most energy. New, sharper sub-question each round (avoid
   repetition; if a persona only restates, treat as a pass).
4. **Stop** when ≤1 hand is raised (converged) OR `max_rounds` is hit (default 4) —
   then the mediator issues ONE explicit **"last call"** round, collects final
   concrete additions, and ends. Never loop unbounded.

## 4. Synthesize (host)
Collect turns → author a `proposal`, `votes` (SUPPORT/MAYBE/ABSTAIN/OPPOSE), a
short `summary`, and a rich Markdown `exec_summary` (verdict · spectrum of
who/why · cross-cutting conditions · tensions · bottom line). Persist via
`record_council(prompt, persona_ids, turns, votes, proposal, summary, exec_summary)`
(it carries `exec_summary`, shown in the web UI). Tip: `brief_council(prompt)`
returns candidate personas to choose from, and `brief_council(prompt, persona_ids)`
returns each participant's loaded context to author turns against.

When the council is recorded, point the user to the web inspector to read it:
**http://127.0.0.1:8787** (`make dev` if it is not running yet).

## Principle
A good harness lets the persona *reason about whether* the past is relevant —
cheap reflection first, targeted lookup only when it sharpens the answer. This
mirrors the agentic memory pattern: the agent decides when to check history.

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
