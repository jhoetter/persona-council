# Methodology & clarity redesign — question-led discovery, legible flow, consistent node-types

> **Status: ✅ IMPLEMENTED 2026-06-05 (Q1–Q4, suite green, pushed).** Q1+Q2 — councils carry a
> first-class `questions` field + three DERIVED modes (discovery = questions→answers, no vote;
> evaluation; decision); the council page + brief_council + the skill all branch on mode; showcase
> Discover councils re-run as open questions. Q4 — a TYPE filter row (= legend) with every node kind
> (incl. prototypes) filterable; capability tags on a muted secondary row. Q3 — numbered phase-column
> headers (1.Discover→6.Deliver, diverge/converge) make the left→right double-diamond explicit. The
> design below is the reference.

> User feedback (2026-06-05): "we start with statements and hypotheses already. I said you should
> naturally start with just user-research QUESTIONS — begin with a council where we ask them about
> things (what insurances do you have, how do you save money right now …); only LATER do hypotheses,
> and always stated conversationally / as questions, not as hypotheses. The graph flow must be much
> easier to understand. And what node types do we have — own pages? in the filters?" → investigate +
> spec. Tracked here as Q1–Q4.

## The core misframing
A council is being presented (and the harness nudges it) as **"put a hypothesis to a vote."** That is
the wrong shape for **discovery**, which is open, generative user research: you ASK, you LISTEN, you
find themes — you do not motion-and-vote. Hypotheses are an OUTPUT of discovery (the Define POV), not
the input to it. The fix runs through the data model, the briefing/skill, and the UI.

> Honest scoping: the methodology JSON is already right (`discover.intent` = "empathize broadly across
> distinct angles"; `frame` authors *research questions*). The hypothesis-with-votes framing came from
> (a) my showcase authoring and (b) a harness bias — `brief_council` says "author proposal, **votes**
> (SUPPORT/MAYBE/ABSTAIN/OPPOSE)" and the council model centers `proposal`+`votes`. So discovery gets
> squeezed into a decision-vote mould. Q1/Q2 remove that bias.

---

## Q1 — Question-led discovery (conversational, no hypotheses up front)
**Goal:** discovery councils are OPEN QUESTIONS asked of diverse personas; the value is what they say.
- A council gains a first-class **`questions: [str]`** — the open, conversational questions actually
  asked ("Welche Versicherungen hast du? Wie legst du gerade Geld zur Seite? Was war der letzte Moment,
  in dem du an Absicherung gedacht hast?"). These come from the `frame`'s research questions, phrased
  conversationally — NOT invented as hypotheses.
- For a discovery council, **`proposal` and `votes` are empty.** The turns are each persona's open
  answers. The "finding" is the synthesised insight, not a tally.
- Hypotheses/POV appear only in **Define** (already does: `payload.clusters` + `positionierung`) and may
  be probed in *later* councils — and even then phrased as questions ("Wie würdest du reagieren, wenn …?
  Was würde dir fehlen?"), never as a motion to ratify.
- **Acceptance:** a Discover council page shows "Fragen, die wir gestellt haben" + each persona's
  answers, with NO motion/vote UI; the run reads as user research, not a referendum.

## Q2 — Council MODES: discovery (questions) vs evaluation (reactions) vs decision (vote)
**Goal:** one council primitive, three honest shapes — the UI + briefing branch on what's present.
- **discovery** — has `questions`, no `proposal`/`votes`. UI: questions + answers + synthesised themes.
- **evaluation** — has a `proposal`/concept/prototype to REACT to (still asked conversationally: "Was
  löst das bei dir aus? Was fehlt?"); optional light sentiment (`stance`), no hard vote. UI: the thing
  reacted to + reactions + where it lands. (This is concept/prototype testing.)
- **decision** — has `proposal` + `votes` (the only place For/Against belongs). Rare; usually the host
  decides via synthesis. UI: the motion + the vote (today's layout).
- The mode is **derived** (questions ⇒ discovery; proposal+votes ⇒ decision; proposal only ⇒
  evaluation) — no new closed vocabulary. `brief_council` instructions + the run-council skill updated:
  default discovery to questions; introduce a proposal only when evaluating a concept; only emit votes
  for an explicit decision.
- **Acceptance:** the same council page renders correctly for all three; `brief_council` no longer
  pushes votes by default; the methodology's discover step briefs questions, not a motion.

## Q3 — Legible graph / flow (the "ultra confusing" graph)
**Goal:** a first read of the project shows the JOURNEY, not an abstract node cloud.
- **Default to a left→right PHASE-BAND flow:** labelled lanes (Discover · Define · Ideate · Down-Select
  · Refine · Deliver) as the backbone; each phase's nodes sit in its band; diverge phases fan, converge
  phases neck — the double-diamond is *visible*, not inferred. (The project OVERVIEW band — Q-link to
  UX2 — already gives the readable story; the graph should match it visually.)
- **Node types visually distinct + legended:** a fixed glyph+colour per kind (council / synthesis /
  concept / prototype / open-question), shown in an always-visible legend — not a hidden panel.
- **Prototypes are first-class nodes IN their phase band** (not a separate floating overlay) with their
  idea→prototype→tested-at edges (already computed) drawn plainly.
- **Edges read as the flow:** explored-in → clustered-into → ideated → prototyped → tested → concluded;
  consistent arrowheads + a legend.
- Keep the draggable force-graph as an *alternate* view (toggle), but the **default is the legible
  flow.** (Investigate: extend `_methodology_layout` band-rendering vs. a new flow renderer.)
- **Acceptance:** a non-expert opens the project and can trace question → research → insight → concepts
  → prototype → answer left-to-right without decoding.

## Q4 — Node-type consistency: pages + filters (the inventory)
**Goal:** every node type a viewer can see is navigable AND filterable, consistently.

Current state (showcase render):
| Type | Graph node? | Own page? | In filters? | Gap |
|---|---|---|---|---|
| Council | ✓ | ✓ `/councils/<id>` | ✓ `council` | — |
| Synthesis | ✓ | ✓ `/syntheses/<id>` | ✓ `synthesis` | — |
| Concept (note) | ✓ | ✓ `/notes/<id>` | ✓ `concept` | — |
| Prototype | ✗ overlay | ✓ `/prototypes/<slug>` | **✗** | not a node; not filterable |
| Section (phase/theme) | overlay | ✓ `/sections/<id>` | **✗** | not filterable |
| Open question | panel only | **✗ no page** | **✗** | invisible + unnavigable |
| Meta-report | — | ✓ `/projects/<id>/meta` | **✗** | fine (doc) |
| Frame (research questions) | ✗ plan-internal | ✗ | **`frame` chip exists** | filter for nothing |

Fixes:
- A consistent **TYPE filter row** (Council · Synthesis · Concept · Prototype · Open Q) — every visible
  type toggleable; separate from capability/phase tags. Today the chips mix kinds (`council`,
  `synthesis`, `concept`) with capabilities (`frame`, `decide`) in one undifferentiated row.
- **Prototypes filterable** (follows from Q3 making them nodes).
- **Drop the dead `frame` chip** (or make frames a real, visitable node — the research questions ARE
  content worth a page; cf. Q1).
- **Open questions get a presence** — at minimum a visible list/section with anchors; ideally a small
  page or a synthesis-attached view, since they're the honesty signal.
- **Acceptance:** the filter row groups by TYPE, every type in the graph is both filterable and has a
  destination page; no chip maps to nothing.

---

## Build order (each: spec-confirmed → implement → suite green → commit/push)
- **Q1 + Q2 first** (they're one change): add `questions` to the council model + brief/record/skill;
  derive the council mode; branch the council page (questions+answers | reaction | vote). Re-run the
  showcase Discover councils as open questions to prove it. *This is the heart of the user's feedback.*
- **Q4** (mechanical, high clarity): consistent TYPE filter row + prototypes/open-questions reachable;
  drop the dead frame chip.
- **Q3** (largest): the legible phase-band flow as the default project view.

## What this is NOT
Not a methodology rewrite — the double-diamond stays. It's removing the decision-vote bias from
discovery, making councils read as conversations, making the flow legible, and making every node type
consistently navigable + filterable.
