# Exploration depth & prototype variety — observation tracker

> **Status:** OBSERVATION LOG (build-ready findings accumulate here; not yet implemented).
> **Purpose:** while an autonomous agent runs a design-thinking project end-to-end, watch HOW it works
> and capture **generalizable** harness/spec improvements so the methodology can reach surprising,
> mechanism-level depth and build genuinely interesting prototypes — **not** collapse to "first council
> said they want a brief → here's a form".
>
> **Hard constraint (user, 2026-06-05):** do NOT hardcode design-thinking (or any methodology) into the
> harness/prompts. Design thinking is ONE methodology expressed as data (a constellation + the
> suggestion registries). Every fix below must be a DATA / capability improvement that any methodology
> can use, never a baked-in DT term or step. The harness should *enable* depth, the methodology *spec*
> should *encourage* it, and the agent should be *free* to generalize.

## Run under observation
- Project: `rproject_eb44851f4eb7fab5` — "KFZ → Lebensversicherung: junge Erstabschließer".
- HMW: *Wie können wir junge Menschen, die gerade eine KFZ-Versicherung abgeschlossen haben, dafür
  gewinnen, sich für eine Lebensversicherung zu begeistern?*
- Methodology: `double_diamond_deep` (8 tasks: discover→define→ideate(lofi)→lofi_select→refine(midfi)
  →deliver→build(hifi)→decide(hifi)). Cohort: the 18 retained personas.
- Worker transcript: `~/.claude/projects/-home-jhoetter-repos-persona-council/464fe359-…jsonl`.

## Quality rubric (what "good" vs "disappointing" looks like)
1. **Exploration depth, not premature convergence.** Discover genuinely diverges across segments &
   angles and *interrogates the premise* before any Define. Disappointing: 1 council → a form.
2. **Insight non-obviousness (mechanism-level).** Define/POV reaches a causal reframe ("they don't
   feel LV because they have no intuition for compounding / their future non-working self is
   invisible → make the invisible *experienceable*"), not a surface restatement ("they want simple
   info").
3. **Prototype variety & true fidelity ladder.** Concepts span genuinely different *kinds*
   (a tool, a comparison, a narrative, an interactive *model/simulation*, a deliberately provocative
   "dark-horse") across lo→mid→hi — not N near-identical forms/flows.
4. **Breadth before down-select.** Many distinct ideas in Ideate; the gate forces ≥2 angles; honest
   non-targets preserved (anti-steering).
5. **Generalization.** None of the above is hardcoded; an invented methodology + invented artifact
   types would get the same depth from the same primitives.

---

## Findings

### OBS-1 — Discover FRAME is deep and honestly anti-steering ✅ (keep)
The agent's `frame__discover` authored **9 problem-space questions, 7 hypotheses (all explicitly
"zu prüfen, nicht behauptet"), 11 memory-grounded refs**, differentiates sub-segments (Azubi/Student/
junge Familie/Solo-Selbstständig), and **Q6 interrogates the premise itself** ("is 'getting them
excited about LV' even a sensible goal, or a non-fit for FIRE/precarious/avoidant segments?").
*Why it matters:* this is exactly the non-shallow start the rubric wants — the deep-methodology seed's
framing intent + the `record_frame` gate (≥1 question + ≥1 memory ref) are doing real work.
*Spec implication:* none — preserve. Evidence that "understand before concluding" + memory-grounding
is landing.

### OBS-2 — Plan structure already encodes a real lo→mid→hi ladder ✅ (keep)
`double_diamond_deep` seeds a true three-diamond + hi-fi rung with premise-interrogation in the
discover intent and `session_of_tags` gates (lofi/midfi/hifi) forcing real proband tests at each rung.
*Spec implication:* the ladder is structurally sound; the gap is in what a "prototype" can BE (GAP-1).

### GAP-1 — Renderer ceiling: prototypes are static screens, no interactive/computational primitive ⚠️ (highest-leverage)
The artifact-type registry (`suggestions/artifact_types.json`) offers 6 archetypes — `prototype`
(lofi/midfi/hifi), `flow`, `dashboard`, `cards`, `comparison`, `survey` — all rendered as clickable
multi-screen SPAs. **Better than "just forms"** (a guided flow / comparison / dashboard are real
layouts). BUT the concept model supports only element kinds **text / input / select / link / button**
with `goto` navigation; inputs *store* `state[id]` but **nothing computes**. There is no slider/range,
no derived/calculated output, no chart/curve/timeline, no parametric model. So the single most
*exciting* design-thinking prototype class — an **interactive simulation** ("move a slider → see your
pension gap at 67", a compounding-growth curve, "your life when you stop working") — is **not
expressible**; an agent forced into this would fake it as static screens ("Schritt 2: Vermögen mit 67:
142.000 €"), which is a mock, not an experience. This caps the ceiling on rubric dims 2 & 3.
*Proposed (general, data-driven — NOT a DT term):*
- Add an **interactive/parametric renderer template** + a new artifact type (e.g. `model` /
  `simulation`) in `artifact_types.json` whose concept JSON carries a tiny declarative spec:
  inputs (incl. a `range`/`slider` kind) → a formula/derived field → an output element
  (number / bar / sparkline / curve). Pure data; any methodology can then build an experienceable
  model. (Keep it host-authored/static-renderable; no in-process LLM — the agent authors the
  parameters + formula, the template evaluates them client-side.)
- Add element kinds `range`, `computed` (a derived display bound to a small whitelisted expression
  over `state`), and a simple `chart`/`spark` block to the SPA concept schema so even existing
  templates gain one "live" rung.
*Generalization note:* this raises the prototype ceiling for EVERY methodology and every domain
(a budgeting tool, a what-if comparator, a forecast) — it is not insurance- or DT-specific.

### GAP-2 — No data-driven notion of a "provocative / dark-horse / experiential" concept, and Ideate doesn't surface the archetype palette ⚠️
Fidelity discriminators are only `lofi/midfi/hifi` (pure theming). There is no first-class, data-driven
way to mark a concept as a *deliberately extreme / unexpected* exploration (the design-thinking
"dark-horse"/"funky" prototype — a divergence technique the user named), and the `ideate` frame intent
("generate many distinct solution concepts … go broad before judging") does **not surface the
available artifact archetypes as a palette**. Risk: the agent defaults to the first obvious form/flow
and under-diversifies concept *kind*.
*Proposed (general, NOT hardcoded DT):*
- `next_action`/the act guidance for an ideate-style step should **read the artifact-type registry and
  present the palette** ("you can build a flow / comparison / dashboard / model / …") so concept-KIND
  diversity is prompted from DATA, plus a methodology-agnostic nudge: *"include ≥1 deliberately
  extreme/unexpected concept to stretch the space."*
- Allow a free **role/divergence discriminator tag** (e.g. `provocation`) as DATA in the registry an
  agent MAY apply — the engine stays tag-agnostic; the term lives in the suggestion JSON, not code.
*Generalization note:* surfacing "what kinds of artifacts can I build?" from the registry helps any
methodology avoid mono-form output; the dark-horse idea generalizes to "explore the extreme of the
space", which is valuable far beyond DT.

---

## Watch list (to confirm as the run proceeds)
- **WATCH-1 — Discover breadth shape.** The seed discover intent says "one exploration PER
  persona/segment". Does the agent run a FEW *rich multi-persona* councils per angle-cluster (good), or
  many THIN per-persona micro-interviews (the anti-pattern the user flagged)? If the latter, the deep
  seed's wording needs a breadth-semantics fix (breadth = angles × multi-persona, not 1:1 per persona).
- **WATCH-2 — Define reframe.** Does the POV reach a *mechanism-level* reframe (why the topic is
  invisible/irrelevant and what experience would change it) or restate the brief?
- **WATCH-3 — Ideate breadth.** ≥4–8 *distinct-kind* concepts before down-select, or premature collapse
  to one obvious idea?
- **WATCH-4 — Prototype distinctness.** Do lo-fi prototypes feel like different experiences, or
  near-identical screens? Does anything approach a simulation/experiential concept (and hit GAP-1)?
- **WATCH-5 — Hi-fi honesty.** Does the final spec keep deliberate non-targets + an honest
  validated-vs-open ledger (anti-steering survives to the end)?

_Last updated: 2026-06-05, during the live run (Discover frame done; at Define)._
