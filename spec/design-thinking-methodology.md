# Design Thinking as a Facilitation Methodology — Specification

> **Status:** Methodology **DESIGN** (authored 2026-06-03). Implemented as a **facilitation
> playbook over the existing research graph** — *no new engine, no new core tables*. The
> council → synthesis → persona-experience loop is unchanged; this spec only defines **how a
> mediator sequences and organizes** that loop into a Double Diamond.
> **Scope:** Add **one** methodology — Design Thinking (Double Diamond / d.school micro-cycle) —
> as a way for the host (acting as facilitator) to drive a research project from a *How Might We*
> question to a **specification a development team can build from**, including a **prototype**
> phase where personas *use a real (minimal) app* as a lived experience and react to it.
> **Leitsatz (unchanged):** nothing hardcoded; MCP exposes capabilities; the host authors all
> text (`brief_* → author → record_*`); every claim traceable to a council; personas
> non-directional (anti-steering — no nudging toward a product thesis without evidence). The
> persona **experience-driven** approach is the foundation and stays primary.

---

## 0. TL;DR

The research graph (Project ⊃ Synthesis ⊃ Council, typed edges, open questions, voices,
meta-report) is **already a design-thinking graph**. Design Thinking does not need a new
system — it needs a **facilitator** who decides *which* councils to run, *in what order*,
with *which mediator strategy*, and *how to name and link* the resulting syntheses so the
graph takes the shape of a **Double Diamond**.

```
PROJECT (methodology="double_diamond", goal = a "How Might We …?" question)
│
│  ◇ DIAMOND 1 — PROBLEM SPACE
├─ Synthesis  Discover   councils, strategy=pain-discovery     DIVERGE  (go broad on lived pains/needs)
│        │ refines
├─ Synthesis  Define     councils, strategy=goal | tension     CONVERGE (core problem → Point-of-View + next HMW)
│        │ spawned_from
│  ◇ DIAMOND 2 — SOLUTION SPACE
├─ Synthesis  Develop    councils, strategy=positive-deepdive  DIVERGE  (explore solutions; build a minimal prototype)
│        │ refines
└─ Synthesis  Deliver    Test council (personas USE the app)   CONVERGE (spec of what the solution must fulfill)
         ↓
   MetaReport = the Double-Diamond write-up handed to the dev team
```

Each **phase is one growing Synthesis** (your "study"), built from one or more **Councils**.
Diverge/converge is **literally the run-council mediator strategies** you already have
(`pain-discovery`/`positive-deepdive` are divergent; `goal`/`tension`→decision are
convergent). The "groan zone" is the mediator's strategy switch at a diamond's waist.

---

## 1. Mapping (every DT concept already exists)

| Design Thinking | Realized as | Notes |
|---|---|---|
| Project / *How Might We* challenge | `ResearchProject` (`goal` = the HMW) | `methodology="double_diamond"` JSON key |
| Phase result (Discover/Define/Develop/Deliver) | a **Synthesis** node | `study_tags` carry `phase:discover` … |
| The deliberation behind a phase | one or more **Councils** | host-authored, grounded, anti-steering |
| Diverge → converge transition | a typed **edge** (`refines`) | waist of a diamond |
| Diamond 1 → Diamond 2 hand-off | a typed **edge** (`spawned_from`) | Define's POV spawns the solution search |
| Empathy / lived pain (the heart) | persona **experience + memory** | `prepare_persona_agent_context` |
| Point-of-View statement | Define synthesis `positionierung` + `gesamtbild` | the reframed problem |
| Next *How Might We* | Define synthesis `next_council_question` | self-contained (personas are council-stateless) |
| Ideas / solution concepts | Develop synthesis `pain_solvers` + `handlungsempfehlungen` | effort/value matrix |
| Prototype | a **real, minimal, runnable app** (artifact) | personas *use* it as an experience |
| Test learnings | a **Test council** + its reactions in memory | grounded; feeds Deliver |
| Open unknowns / risks | `OpenQuestion` frontier | carried across phases |
| Per-person stance & shift | `voices` (sentiment/relevance/shift/evidence) | who moved, why, with quotes |
| **Handover spec for devs** | Deliver synthesis + **MetaReport** | the deliverable |

Nothing above is invented; it is the existing graph, *facilitated*.

---

## 2. The four phases (mediator playbook)

Each phase: pick the participants by relevance (LLM-authored from candidate summaries — never
keyword scoring), load each via `prepare_persona_agent_context`, run the council with the named
strategy, then author **one Synthesis** for the phase and link it into the diamond.

### 2.1 Discover — *diverge, problem space*
- **Goal:** widen. Surface the real, lived frictions around the HMW — *before* assuming any
  solution. Anti-steering is strongest here: mundane work, indifference and rejection are valid.
- **Council strategy:** `pain-discovery` (each persona surfaces their biggest problems that
  even loosely touch the theme; mediator deepens the most energetic, product-adjacent pains).
- **Synthesis (`phase:discover`):** the landscape of pains/needs, who has which, and the open
  questions worth converging on. `status="in_progress"`; `next_council_question` frames Define.
- **Gate to Define (waist):** stop diverging when new councils only repeat known pains
  (diminishing returns) — the classic "enough breadth" signal.

### 2.2 Define — *converge, problem space*
- **Goal:** narrow to **the** core problem. Author a sharp **Point-of-View**: *who* + *needs
  what* + *surprising insight/why*. Produce the second HMW (the solution question).
- **Council strategy:** `goal` or `tension` — drive to a decision about which problem matters
  most; pair disagreements so the framing earns its edges.
- **Synthesis (`phase:define`):** `positionierung` = the POV; `gesamtbild` = the reframed
  problem; `offene_fragen` = what the solution must answer. Edge **Discover → Define** = `refines`.
- **First diamond closed:** a defensible, evidence-traceable problem framing.

### 2.3 Develop — *diverge, solution space*
- **Goal:** widen again on **solutions**. Explore directions; converge enough to commit to **one
  minimal prototype** worth testing.
- **Council strategy:** `positive-deepdive` (mine the solution threads multiple personas get
  excited about — "what would make you *champion* it?") balanced with honest skepticism.
- **Prototype:** build a **real, minimal, locally-runnable app** (see §3). It is a genuine
  artifact the user can open, not a paper mockup — but deliberately tiny.
- **Synthesis (`phase:develop`):** candidate solution(s), the chosen prototype's premise,
  `pain_solvers` it claims to address. Edge **Define → Develop** = `spawned_from`.

### 2.4 Deliver — *converge, solution space*
- **Goal:** converge to a **specification** a dev team can build: what the solution **must
  fulfill**, for **whom**, with what **must-haves vs nice-to-haves**, and the **known risks**.
- **Test first (the experience-driven core):** personas **use the real prototype** as a lived
  experience (§3), then a **Test council** reacts — grounded in having actually used it. Honest
  friction and rejection are first-class signals.
- **Synthesis (`phase:deliver`):** `handlungsempfehlungen` (effort/value) = the requirements;
  `segmente` = who it's for (incl. deliberate non-targets); `pain_solvers` = validated solves;
  `offene_fragen` = open risks/unknowns; `status="done"`. Edge **Develop → Deliver** = `refines`.
- **Handover:** a **MetaReport** over the four phase-nodes = the Double-Diamond document the dev
  team reads: build-order narrative (how understanding was built) + section per phase, every
  claim traceable down to a council turn.

---

## 3. Prototype = a real, minimal app the personas *experience*

The persona experience-driven approach **is** the test method. A persona "trying a prototype"
is a **lived experience**, not a survey:

1. **Build a real, minimal app.** A tiny, self-contained, locally-runnable web app (e.g. a
   single `index.html` with inline JS, or a minimal FastAPI+HTML page) under `prototypes/<slug>/`.
   Real enough to open and click; deliberately minimal; never intended for real hosting/users.
   It exists so the user can run it *and* so personas can react to a concrete thing.
2. **Persona uses it (experience seam — zero new tools).** Capture the session as an
   experience/activity: a `record-day` activity titled e.g. *"Tried the kantrik diff prototype"*,
   with the honest reaction in `what_happened` / `conversation` / `persona_thought`,
   `artifacts_touched=["Prototype: <name> v0.1"]`; then consolidate
   (`record-deltas`) into memory — entity `kind=topic` "Prototype <name>", facts = the concrete
   frictions and the genuine delights.
3. **Test council reads from memory.** Because the reaction now lives in the persona's memory,
   `prepare_persona_agent_context` surfaces it automatically — the Test-council feedback is
   *grounded in having used it*, in character, with anti-steering intact.
4. **Versioning (optional, later).** Tag the artifact `Prototype <name> v0.2` to compare
   reactions across versions via `recall`. A thin first-class **prototype registry** (name /
   version / kind=`spec|html|url` / path) is a *future* nicety — earn it; start with orchestration.

**Boundary (per the design decision):** prototypes are *actual apps* runnable outside the
simulation, but **absolutely minimal** and never hosted for real users.

---

## 4. What's new vs unchanged

**Unchanged (the foundation):** persona model, experience/day simulation, memory, council
authoring, synthesis schema (`voices` etc.), research graph, meta-report, anti-steering, the
host-authoring contract. None of it changes.

**New, and deliberately tiny:**
1. **This methodology spec** (`spec/design-thinking-methodology.md`).
2. **A thin facilitator skill** (`claude-skills/design-thinking/`) — the Double-Diamond
   orchestration over today's tools (sibling of `synthesize` / `run-council`).
3. **Two optional JSON keys, zero migration** (tables are JSON blobs): `ResearchProject.methodology`
   and a `phase:<name>` entry in a synthesis's `study_tags`. Backward-compatible; lets the UI
   draw the diamond.
4. **(Later, only if earned)** a Double-Diamond *view* in the read-only UI (phases as the two
   diamonds) and a prototype artifact registry.

No new MCP engine. Other methodologies (Lean/JTBD, Systems Thinking, the book's "Quadruple
Diamond") would each be **another playbook over the same graph** — free, precisely because we
did not build an abstraction.

---

## 5. Guardrails (why this stays trustworthy)

- **Anti-steering is sharpest in Discover and Test.** A prototype reaction that is enthusiastic
  about features the persona never used, or ungrounded in their real pains, is a red flag — the
  eval critic should catch "prototype enthusiasm not grounded in experience."
- **Convergence gates are explicit**, not vibes: a diamond closes when added breadth stops
  changing the picture (Discover) or when the council reaches a defensible decision (Define).
- **Every phase node is traceable** to its councils, and every council turn to a persona's
  loaded memory — so the dev-handover spec is auditable end-to-end.
- **The facilitator never invents consensus.** Deliberate non-targets and honest rejection
  belong in `segmente`/`voices`; a "no" from a segment is a finding, not a failure.
