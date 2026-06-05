# UX / Information-Architecture structural review (2026-06-05)

> User: "structurally go through everything … it is so difficult to even understand how the project is
> set up, what was done … where are things missing?" This is the honest catalogue of what the web UI
> fails to communicate, from a deep render-and-inspect pass over every page type of a real finished
> project (`ESV-Showcase · KFZ→LV`). Fixes tracked as UX1–UXn.

## The core problem
The UI shows **mechanism, not narrative.** Every page renders its *data* (a graph, a vote tally, a
synthesis' blocks) but never the *story* a human needs: what was asked, what was done in what order,
and what the answer is. A first-time viewer lands on an abstract node graph with everything readable
hidden behind a button — so they're lost, exactly as reported.

## Findings (by page)

### A. Project page — graph-only, story hidden (UX2) — highest impact
- Renders: title + goal line + a big interactive **node graph**. Everything else — the **Pulse**
  (status), **Sections**, **Prototypes**, **Open questions**, edge legend — is in a **floating panel
  hidden behind one button**. There are **zero readable sections** (`<h2>` count = 0).
- Missing: a readable **overview** — the question as a question; a **phase flow** ("Discover (3
  councils) → Define (POV) → 5 Concepts → Prototype ladder → Deliver") with what each produced; and
  **THE ANSWER** (the Deliver conclusion + the runnable hi-fi) surfaced, not buried.
- The graph alone can't carry "what was done" — it's a spatial abstraction, not a narrative.

### B. Breadcrumbs — drop the project, nest backwards (UX1)
- Council page crumb: `Projekte > Define synthesis > Discover council`. Two bugs:
  1. **The project name is missing** — the code uses `parent_project_of_study(synthesis)`, which
     returns `None` for plan-based projects (the synthesis isn't linked by the old study-edge path),
     so the project crumb is dropped. `parent_project_of_council` *does* return it.
  2. **Backwards nesting** — a *Discover* council is shown *under* the *Define* synthesis it FEEDS.
     Discover is upstream of Define, not a child of it.
- Synthesis page crumb: `Projekte > Define synthesis` — also **missing the project** (same root cause).
- Target: every page reads `Projects > [Project] > [optional Phase] > [this page]`, consistently.

### C. Meta-report — an empty, incomplete shell (UX3)
- `scaffold_meta_report` seeds an outline of **only the FAN phases** (Discover/Ideate/Refine) — it
  **misses Define / Down-Select / Deliver** (the verify syntheses), i.e. half the story incl. the
  conclusion.
- The report renders with **0/3 sections authored** — headings with no body — yet
  `assess_project.finish.handed_off` is `true` (existence ≠ content). The "handover narrative" that
  should tell the story is empty.
- The project overview should fall back to the **Deliver synthesis** (which IS authored + rich) as the
  narrative when the meta-report is unauthored.

### D. Council page — fixed this pass
- The **motion** the personas respond to was buried in a collapsed accordion at the bottom; the votes
  (For/Conditional/Against) had no visible question. Now surfaced first + the exec-summary labelled as
  the finding. Vote tally made case-robust. (Done.)

### E. Smaller gaps (catalogue)
- **No phase legend / journey explanation** anywhere — the methodology (double-diamond) is never named
  or explained; the viewer must infer it from column positions.
- **Sections page** shows the member list but not "this is the Discover phase, it produced these 3
  councils which fed Define."
- **Prototype page** has a good crumb but no link back to the synthesis that evaluated it / the concept
  that produced it (the graph has these edges; the page doesn't expose them).
- **Open questions** (the honest unknowns) are hidden in the floating panel — they're a key honesty
  signal and should be visible.
- **Concepts** now render as nodes but their relationship ("became this prototype", "parked because…")
  isn't shown on the note page.
- **No "what is this methodology / what do the phases mean"** affordance for a non-expert viewer.

## Fix order
- **UX1 — breadcrumbs** (small, high clarity): correct project lookup + forward nesting, consistent
  `Projects > Project > [Phase] > page` everywhere.
- **UX2 — project overview** (largest clarity win): an always-visible story block — question, phase
  flow with counts + what each produced, and the answer (Deliver gesamtbild + hi-fi link).
- **UX3 — meta-report**: complete the outline (all phases), show authored-vs-pending honestly, and let
  the overview fall back to the Deliver synthesis when the report is unauthored.
- Then the smaller gaps (E) as a follow-up pass.
