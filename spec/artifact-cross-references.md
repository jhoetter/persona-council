# Artifact cross-references — addressable parts, typed links, live resolution

Status: **DESIGN** (2026-06-07). Foundational. Supersedes the ad-hoc relation mechanisms below.

## 1. The problem (whole-app, not just councils)

The app is a **graph of artifacts** (councils, syntheses, notes, prototypes, sessions, personas,
meta-reports, open questions, sections). But the way artifacts relate to each other is **coarse and
duplicative**:

- A `Ref` can only point at a **whole record** (`council:id`), never at a *part* (a specific statement,
  finding, or prose block).
- Statements and findings have **no stable id**, so nothing can address them.
- Because you can't *point* at a council statement, a synthesis that wants to reflect it **copies/
  paraphrases** the persona's words into its own `statements` — re-hosting a mini-council inside the
  synthesis, with no link back and no single source of truth. (This is the bug the user found.)
- There are **six different, overlapping relation mechanisms**, each ad-hoc:

  | relationship | today's mechanism |
  | --- | --- |
  | statement → the question it answers | `statement.about` (prompt id, same artifact) |
  | statement → memory it's grounded in | `statement.refs` (kind=memory) |
  | synthesis → councils it consolidates | `synthesis.council_ids` + `references` + `citations` |
  | synthesis voice → council evidence | `voice.evidence` `[{council_id, quote}]` (now removed) |
  | note → the prototype it became | `note.data.prototype_id` |
  | open question → the study that answers it | `open_question.answered_by_study_id` |
  | node → node typed relation | `StudyEdge` (spawned_from/refines/contrasts/…) |
  | meta-report → its sources | `outline.source_study_ids` + section `citations` |

  These are **all the same thing**: a typed, directional reference from one artifact (or part) to
  another (or part), sometimes carrying the referrer's own interpretation.

## 2. The model — one primitive for every relationship

**Address.** Every meaningful part of every artifact has a stable URI:

```
<kind>:<artifact_id>              the whole artifact            e.g. council:c_ab12
<kind>:<artifact_id>#<part_id>    a part within it             e.g. council:c_ab12#st3
```

Parts that get a stable `id` (unique within their parent): **statement, finding, prompt, event,
session**, and named **prose blocks** (`#gesamtbild`, `#positionierung`, `#arc`). `kind` ∈
council|synthesis|note|prototype|persona|memory|external (data-driven, same vocab as `ref_href`).

**Ref v2.** The one reference primitive gains an `anchor` and a typed `role`:

```python
ref(kind, *, id=None, anchor=None, role=None, quote=None, text=None)
```
- `id` — the artifact; `anchor` — the part within it (None = whole artifact).
- `role` — the SEMANTIC of the link, an OPEN tag (data-driven `suggestions/ref_roles.json`):
  `cites · reinterprets · supports · refutes · refines · answers · derived_from · realized_as ·
  evaluates · contrasts · duplicates · grounded_in`.
- `quote` — an OPTIONAL cached display hint, **never the source of truth**.
- `text` — only for anchor-less observed-state strings (existing prototype_state use).

**Live resolution.** `resolve_ref(ref, store) -> {address, kind, artifact_id, anchor, title, text,
persona_id?, href, exists}` pulls the **current** content of the addressed part. A synthesis citing
`council:c#st3` always shows what the persona *actually said now* — if the source is edited or deleted,
the ref renders stale/broken **honestly** (never a silent stale copy).

**The core rule — reference + re-interpret, never duplicate.** When artifact A reflects content from
artifact B, A authors *its own* analysis text and attaches a `Ref(role=…)` to B's part. A never copies
B's words; the words are resolved live from B. (A council is held in ONE place; a synthesis *points* at
it and interprets it.)

## 3. How every existing relationship collapses into Ref v2

| relationship | Ref v2 |
| --- | --- |
| statement answers a question | `ref(prompt, anchor=qid, role=answers)` (already `about`) |
| statement grounded in memory | `ref(persona, anchor=event_id, role=grounded_in)` |
| synthesis finding ← council statement | `ref(council, id, anchor=stmt_id, role=derived_from)` |
| note built into a prototype | `ref(prototype, id, role=realized_as)` (was `data.prototype_id`) |
| open question answered | `ref(synthesis, id, anchor=finding_id, role=answers)` |
| node → node typed edge (`StudyEdge`) | `ref(kind, id, role=<edge_type>)` (anchor-less) |
| meta-report section ← synthesis finding | `ref(synthesis, id, anchor=finding_id, role=cites)` |
| prototype session ← observed state | `ref(prototype, id, anchor=state, role=evaluates)` |

`StudyEdge`, `references`, `citations`, `evidence`, `answered_by_study_id`, `data.prototype_id` all
become **one** thing: a list of typed Refs. The project graph's edges are then **derived** from the
refs (node-level refs = node edges; part-level refs = fine-grained provenance).

## 4. Backlinks — the project knowledge graph

Because refs are directional + typed, an index gives every part its **"referenced by"** set:
- on a council statement → "cited by *Define synthesis* (derived_from); by *note X* (contrasts)"
- on a synthesis finding → "answers *open question Q*; cited by *Meta-report*"
- project-wide → a real provenance graph of **parts** and typed links, not just nodes.

This is the holistic payoff: one model powers provenance, the project graph, "what uses this?",
and honest single-sourcing — everywhere.

## 5. UI — one cross-ref renderer

`render_ref` resolves then renders, consistently everywhere:
- whole-artifact ref → a link chip (today's behaviour).
- part ref → a `↩ <persona/title> · <role> · in <artifact>` chip; **hover/expand shows the live
  resolved text**; click navigates to the artifact and **deep-links to the part** (`#part_id` → the DOM
  id of the statement/finding, highlighted on arrival).

Statements/findings render with `id="<part_id>"` so they are deep-linkable + highlightable.

## 6. Synthesis after this (the immediate fix)

- A synthesis **no longer carries persona `statements`** (no re-hosted council).
- Its per-persona insight lives in **findings**: the synthesis's own analysis text + `refs` to the
  council statements it derives from (role=derived_from). The UI shows the analysis + an expandable
  live source.
- The "voices" banner stops reusing the council's question. The council pages remain the ONE place a
  persona's verbatim words live; the synthesis interprets and links.

## 7. Authoring contract (methodology / MCP)

- `brief_synthesis` / `brief_meta_report` return the candidate **source parts WITH their addresses**
  and instruct: "reference parts via refs and re-interpret in your own words; do NOT copy."
- `record_*` **validates** every ref resolves to a real part (broken ref = warning, like SYNTHESIS_THIN).
- Optional later: a check that flags authored text near-identical to a referenced part (anti-copy).

## 8. Phasing

- **P0 — Addressing**: stable `id` on statement/finding/prompt/event/session + named prose blocks;
  address parse/build helpers; `resolve_ref`. (additive, no behaviour change)
- **P1 — Ref v2 + renderer**: `anchor` + `role` on `ref`; `render_ref` resolves live (chip + expand +
  deep-link); statements/findings render with DOM ids. (back-compat: whole-artifact refs unchanged)
- **P2 — Synthesis**: drop duplicated voices; findings carry part-refs; brief/record updated; demo
  re-seeded. **(closes the reported issue)**
- **P3 — Generalize**: meta-report, open-questions, note→prototype, and `StudyEdge` all migrate to
  refs; project-graph edges derived from refs.
- **P4 — Backlinks**: the "referenced by" index + UI on every part.

Test gates per phase; suite green throughout; demo re-seeded at P2.
