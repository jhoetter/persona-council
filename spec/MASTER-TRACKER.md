# MASTER TRACKER — Autonomous Overnight Program

> **Status:** SPEC (build-ready). This is the single, ordered tracker the autonomous runner
> executes end-to-end after the user writes **"go"**. It runs **R → Q → U → L → S**. Long runtime is
> expected and fine. **Operating contract (read first): §0.**
> **Phase R** (the research-plan engine) is fully specified in `spec/research-plan-engine.md`
> (milestones R1–R8); this doc summarizes R and then **fully specifies Q, U, L, S**.

---

## 0. Operating contract (applies to EVERY milestone)
1. **Run autonomously. Never ask the user a question.** Make the most reasonable decision, log it in
   the relevant sub-spec/commit, and continue. The user is asleep; there is no one to answer.
2. **Order is strict:** finish R fully, then Q, then U, then L, then S. Within a phase, do milestones
   in order. A phase's first milestone is usually a **SELF-SPEC** step (§ marked *self-spec*): analyze
   the live state, **write a detailed sub-spec file**, then implement against it as the authority.
3. **Definition of done per milestone:** implement → **full `pytest` suite green** → **commit + push**
   → mark the task done → move on. Never leave the suite red across a commit.
4. **Preserve all standing invariants** (verified by tests + grep gates): no in-process LLM
   text-generation (host/subagents author ALL text via MCP; OpenAI = embeddings + images only); **zero
   hardcoded methodology/artifact vocabulary** (buckets/capabilities/kinds/fidelities are tags with
   data-driven presentation); web UI is **read-only**; structure enforced, dynamics LLM-judged with
   evidence; honesty (no fabricated progress; "unknown" raises an open question).
5. **Use parallelism** (subagents / Workflow) for breadth-heavy steps (refactor targets, UX screens,
   Mobbin extraction, persona authoring, prototype building) — but persist/commit sequentially.
6. **Self-spec docs are authoritative** for their phase: once written, follow them; update them if
   reality diverges, noting why.
7. **Commit messages** end with the standard Co-Authored-By line; **push after every milestone** so
   progress is durable if interrupted.
8. **Quality bar mindset:** the user will judge the result asleep→awake on three things — the
   methodology works *extremely well*, the app is *absolutely beautiful with top UX*, and the example
   simulation *feels like a fantastic design-thinking project*. Optimize for those outcomes, not speed.

---

## PHASE R — Research-plan engine  *(spec: `spec/research-plan-engine.md`, R1–R8)*
Build the plan-driven analyze/act/verify engine: Plan/Task model + storage + `plan.md` render (R1);
methodology→plan seeding + freeform (R2); the dischargeable `frame` capability (R3); plan router +
lifecycle + gates (R4); decoupled first-class evidence + heterogeneous graph (R5); progress-to-goal
verify (R6); skills + a validation Pfefferminzia re-run (R7); migration + grep gate + green suite (R8).
**Exit R when:** R1–R8 acceptance tests all pass and the suite is green. Then proceed to Q.

---

## PHASE Q — Code quality & refactoring  *(after R8; foundation for U/L/S)*
**Goal:** a very clean codebase — no god-files, strong module boundaries, high component reuse, no
behavior change. This is where the post-engine state is cleaned before the big UI work.

- **Q1 — Code-quality self-audit *(self-spec)*.** Analyze the WHOLE codebase and **write
  `spec/refactor-plan.md`**. It must contain:
  - A measured inventory: LOC per source file, longest functions, obvious complexity/coupling
    hotspots. (Known god-files to expect: `services.py`, `web.py`, `storage.py`, `llm_simulation.py`,
    `mcp_server.py` — confirm/refresh with real numbers.)
  - Duplication + weak-boundary findings (e.g., validation scattered, presentation/render logic,
    council/synthesis/plan code, repeated DB-access patterns).
  - **Ranked refactor targets** (highest impact first), each with: the split/extraction, the new
    module layout, the public-API shims needed for back-compat, and a per-target checklist.
  - **Measurable quality bars**, e.g.: no source file > ~800 LOC (target; log justified exceptions),
    functions ideally < ~60 LOC, one clear responsibility per module, shared helpers deduped, the
    web routes/MCP tools/CLI commands **unchanged** (public surface stable). Define a characterization
    approach (snapshot key route HTML / MCP envelopes / CLI outputs before & after).
  **Accept Q1:** `refactor-plan.md` exists with ranked targets + measurable bars + per-target checklists.
- **Q2…Qn — Execute the refactor plan.** Implement each ranked target as an isolated change:
  - Split god-files into packages preserving import paths via re-export shims (e.g.
    `persona_council/web/` → `components.py`/`routes_*.py`/`graph.py`/`styles.py`;
    `persona_council/services/` split by domain: personas, councils, syntheses, plan, prototypes,
    research-graph, simulation). Centralize presentation (already `presentation.py`), validation, and
    shared DB helpers; remove duplication; improve reuse.
  - After EACH target: full suite green + characterization unchanged → commit + push.
  **Accept Q (overall):** every quality bar in `refactor-plan.md` met (or exceptions justified in the
  doc); duplication removed; suite green; **app + MCP + CLI behavior identical** (characterization
  diffs empty). Add a lightweight test asserting the top god-files are gone / under the LOC bar.

---

## PHASE U — UX deep audit & fixes  *(Linear-employee ≥9/10 bar)*
**Goal:** intuitive component placement, great consistency & navigation, no wasted/redundant
information — such that someone who works at Linear would rate the UX **9/10 or higher**. This phase
is about STRUCTURE & INTERACTION (information architecture, hierarchy, flows, states) — the visual
Linear *skin* is Phase L.

- **U1 — UX heuristic audit *(self-spec)*.** Inventory every screen/flow and **write
  `spec/ux-audit.md`** scoring each against a rubric (each dimension /10, with justification; target
  ≥9 average):
  - **Screens to cover** (confirm against the live app): projects list, project graph view,
    synthesis detail, council detail, personas list, persona detail, prototype/artifact viewer,
    meta-report, **plan view (new, from Phase R)**, global nav/sidebar, empty/loading/error states.
  - **Rubric dimensions:** navigation & wayfinding (breadcrumbs, back, keyboard, depth); information
    hierarchy (primary action obvious, progressive disclosure, scannability); **no redundant/wasted
    info**; consistency (components, spacing/type scale, terminology); density & whitespace;
    discoverability & affordances; feedback (hover/active/selected/loading/empty/error); content
    clarity. Per-screen findings + severity + concrete fix.
  **Accept U1:** `ux-audit.md` with per-screen rubric scores + a prioritized, concrete fix list.
- **U2…Un — Implement the UX fixes.** Apply the fixes: consistent reusable components, clearer
  hierarchy and primary actions, remove redundancy, add missing states (empty/loading/error),
  keyboard navigation, breadcrumbs, a command-palette-style quick-nav if warranted, sensible
  defaults. Keep the web UI read-only and data-driven.
  **Accept U (overall):** re-score the rubric in `ux-audit.md`; **average ≥9/10** with every fix
  verified in the rendered HTML; navigation is coherent and nothing is redundant.

---

## PHASE L — Linear design mimicry via Mobbin MCP  *(extensive; whole app)*
**Goal:** make the entire application look and feel like **Linear** — their exact design choices,
tokens, components, density, and interactions — as closely as possible. This is visual + interaction
styling layered on the now-clean (Q) and well-structured (U) app. Expect this to be large.

- **L1 — Extract Linear's design system via Mobbin *(self-spec)*.** Use the **Mobbin MCP**
  (`mcp__mobbin__search_screens`, `mcp__mobbin__search_flows`; load via ToolSearch) to pull real
  Linear references — sidebar, issue list, issue detail, project views, command palette (Cmd-K),
  settings, empty states, menus, tooltips. From these, **write `spec/linear-design-system.md`** with
  CONCRETE tokens + component specs (cite which Mobbin screens each came from):
  - Color tokens, **light AND dark**: bg, elevated surfaces, borders/dividers, text (primary/
    secondary/tertiary), accent (Linear indigo/violet), semantic (success/warn/danger), selection.
  - Typography: family (Inter-like), the size/weight/line-height/letter-spacing scale, UI vs content.
  - Spacing scale, corner radii, borders, shadows/elevation, focus rings.
  - Component specs: sidebar + nav rows, list rows (issue-row density/hover/selected), detail panels,
    headers/breadcrumbs, buttons (primary/secondary/ghost/icon), chips/badges/labels, inputs/menus/
    dropdowns, tabs, tooltips, the **command palette**, context menus, empty states, toasts.
  - Interaction/motion: hover/active/focus, transition timings/easing, keyboard model, density.
  **Accept L1:** `linear-design-system.md` with real-reference-derived tokens + component specs.
- **L2 — Gap analysis *(self-spec)*.** Compare current tokens/components to L1 and **write
  `spec/linear-gap.md`**: every divergence (color, type, spacing, radius, component shape, density,
  interaction) + the exact change to make.
- **L3…Ln — Restyle the WHOLE app to Linear-grade.** Rewrite the design tokens (`:root` light/dark
  vars) to match L1; restyle sidebar, lists, detail views, headers/breadcrumbs, buttons, chips,
  inputs, menus, tooltips, empty states, and the graph chrome; add a Linear-style **command palette**
  (Cmd-K quick nav, read-only navigation only); match typography, spacing, radii, density, focus
  rings; ensure **light + dark parity**. Apply across **every** screen for full consistency. Keep the
  presentation-from-data rule (methodology/artifact values stay data-driven; this phase styles the
  app *chrome*, which is legitimate design-system code).
  **Accept L (overall):** every screen visually reads as Linear-grade and matches
  `linear-design-system.md`; tokens/components consistent app-wide; light + dark both polished;
  `linear-gap.md` items all closed.

---

## PHASE S — Extensive Pfefferminzia showcase simulation  *(the grand finale)*
**Goal:** on the clean, beautiful app, run the new plan-driven double-diamond end-to-end as a
*fantastic* design-thinking project the user can explore on waking. **Purge first; do not ask.**

- **S0 — Purge all data.** `purge-runtime-data` + clear generated artifacts on disk. No confirmation.
- **S1 — Rich, non-form artifact renderers + fidelity ladder *(data-driven)*.** The user explicitly
  wants prototypes that **are not just forms**, and a **lofi → midfi → hifi** ladder. Extend the
  artifact-type registry (`suggestions/artifact_types.json`) + renderer templates so a prototype can
  be a real, varied, clickable app concept — e.g. a **guided flow**, an **overview/dashboard**, a
  **card/list interface**, an **interactive widget/decision flow**, a **comparison view** — each
  genuinely Playwright-drivable. Add a **`hifi`** discriminator with a polished renderer. All
  data-driven (no hardcoded values in code). **Accept S1:** ≥3 distinct non-form renderer templates
  + lofi/midfi/hifi discriminators exist and scaffold real clickable apps; an invented type still
  renders from data; suite green.
- **S2 — Detailed cohort.** Author **14–18 richly segmented personas** (young consumer segments
  across age × life-stage × attitude × channel × region × financial situation, plus 2–3 provider-side
  roles), deeper than prior runs — real backstories, current insurances, pension-gap posture,
  awareness, the KFZ-trigger context — via `record_persona`. Fan out authoring with subagents;
  persist sequentially. **Accept S2:** all personas validate; segments are distinct and realistic.
- **S3 — Detailed life simulation (arcs, not single days).** Simulate a **multi-day arc** per persona
  (a week, or a month bundle) so each has genuine lived memory around insurance / KFZ / pension /
  money — using the simulation loop (`record_day` or `record_month_bundle`), with the quality gates.
  **Accept S3:** each persona has multiple simulated days with experience events + memory facts + a
  digest; `persona-context` surfaces a coherent arc (verified for a sample).
- **S4 — Plan-driven double-diamond run on the HMW.** Drive the NEW plan engine (Phase R) through the
  full design-thinking project for
  *"Wie können wir junge Menschen, die gerade eine KFZ-Versicherung abschließen, dafür gewinnen, sich
  für eine Lebensversicherung zu begeistern?"*:
  - **Problem space:** `frame` (user-research questions grounded in lived memory: existing
    insurances, pension-gap prep, awareness, the KFZ-moment story) → a few **real multi-persona
    councils** (pain understanding + evaluation) → `synthesize` key problems + a sharp POV (incl. the
    surprising core segment). **No 14 micro-councils.**
  - **Solution space:** frame ideas → ideate councils → build **several VARIED lofi prototypes**
    (non-form, using S1 renderers) → **proband test sessions** (Playwright, grounded) → down-select.
  - **Fidelity iterations:** lofi → **midfi** (revised from proband feedback) → **hifi**, with real
    proband feedback + thoughts captured at each fidelity (feedback-driven iteration, not one-shot).
  - **Deliver:** `synthesize` the solution presentation + `assess_progress` = the HMW is answered,
    evidence-backed (who wins, deliberate non-targets, validated pain-solvers, the build spec).
  **Accept S4:** the rendered `plan.md` reads as a coherent analyze/act/verify design-thinking log;
  three diamonds emerge over act→verify; **several varied prototypes across lofi/midfi/hifi** with
  grounded, iterated proband feedback; a final, evidence-backed answer to the HMW.
- **S5 — Final showcase review *(self-spec + fix)*.** Self-evaluate the whole showcase against a
  "fantastic design-thinking project" rubric (depth of research, honesty of evidence, prototype
  variety/quality, iteration story, clarity of the answer) and against the Linear-grade UI; **write
  `spec/showcase-review.md`** with the score + gaps; fix the gaps. **Accept S5:** rubric ≥9/10; the
  project explores beautifully in the app; any gaps closed; suite green.

---

## Exit criterion for the whole program
All R/Q/U/S/L acceptance tests pass, the full suite is green, everything committed + pushed, and the
live app shows: a clean codebase (Q), ≥9/10 UX (U), a Linear-grade look across every screen (L), and
an exhaustive, beautifully-told Pfefferminzia design-thinking showcase (S) the user can explore on
waking — methodology working extremely well end-to-end.
