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

### OBS-3 — Discover councils are deep, spectrum-sampled, and memory-grounded ✅ (keep) — resolves WATCH-1
The agent ran **3 rich MULTI-persona Discover councils** (5–6 personas each) on distinct angle-clusters
— (a) the KFZ-moment vs present-money, (b) comprehension/language ("can you even decode
'Lebensversicherung/Rentenlücke'?"), (c) trust & sales-pressure — NOT thin 1:1 per-persona
micro-interviews. The comprehension council (`council_5b87a0f6`) is exemplary:
- personas **deliberately sampled along a spectrum** ("Begriff löst nichts aus" → "Begriff selbst
  erschlossen"), per its `selection_reason`;
- each reaction **cites that persona's specific lived memory** (Steuerberater's "Basisrente";
  Verbraucherzentrale commission video; Riester Standmitteilung; the WhatsApp question-list);
- a **vote-motion** ("I could explain in my own words what an LV does for me" → OPPOSE 3 / MAYBE 2 /
  SUPPORT 1) crystallizes a measurable position;
- the synthesis reaches a **mechanism-level reframe**: the *word* fails in 3 ways (empty / mis-framed
  as "commission-sale" / hides Risiko-vs-Kapital), while lived "Sicherheit" is **relational &
  present-tense** and the product language never reaches it.
*Why it matters:* this is the non-shallow exploration the rubric wants, and it confirms WATCH-1 is
fine for THIS run. *Spec implication:* the quality came from agent discipline + the
`prepare_persona_agent_context`/council/memory primitives — **not** hardcoding — so the architecture is
working at the council layer. Keep; the remaining risk is downstream (Ideate/prototype = GAP-1/GAP-2).
*Open nuance:* the user's specific "they lack compounding intuition → simulate their non-working life"
mechanism hasn't explicitly surfaced yet; the adjacent "abstract future vs concrete present" tension
has. Watch whether Define/Ideate makes the "make the invisible future *experienceable*" move (→ GAP-1).

### OBS-4 — Anti-steering held AND produced a premise-REFUTING, non-obvious insight ✅✅ (resolves WATCH-2 strongly)
The agent ran **5** Discover councils (beyond the min-2 gate), including a dedicated **premise-check /
disconfirmation council** (`council_1934c7c29fef8c16`) that deliberately loaded the *skeptics &
Non-Fit candidates* (its `selection_reason`: "Ziel war NICHT, dass sie sich zur LV warmreden, sondern
ehrlich zu prüfen, für wen LV strukturell ein Non-Fit ist") and a **provider-insider** council on the
<1% conversion + Frühstorno root-cause. Result: **6/6 SUPPORT "Non-Fit"**, with a mechanism-level,
*premise-refuting* finding that is exactly the "detail you wouldn't first expect":
- It is **not** an awareness/explanation gap that more education fixes — it is a **structural product
  mismatch** (cost-drag, decades-long lock-in, liquidity, values), and the rejection reasons are
  *"Voraussetzungen, keine Verhandlungsmasse"*.
- **The compounding insight appears — inverted.** The financially-literate reject LV *because* they
  understand compounding ("Kosten wirken über den Zinseszins jahrzehntelang nach — das Argument GEGEN
  teure lange Verträge"; Niklas computed opportunity cost in Interactive Brokers). The naïve
  hypothesis ("teach them compounding → they'll want LV") is **falsified by the evidence**; the real
  cleavage is structural-Non-Fit (literate) vs word/relational-security barrier (illiterate).
- The agent honestly concludes "begeistern für LV" is the **wrong goal for 4/6** and reframes toward
  the underlying need (flexible/transparent/pausable provision; liquidity buffer; honest
  Risiko-vs-Kapital distinction). Anti-steering survived a leading HMW.
*Why it matters:* this is the strongest possible evidence against premature/shallow convergence — the
methodology let the agent *reject the brief's premise on evidence* rather than rationalize it. WATCH-2
resolves very positively.

### SPEC-A — Generalizable: surface a "disconfirmation / load-the-skeptics" council as a DATA-driven angle ✅ (small, high-value)
What made OBS-4 possible was the agent *choosing* to run a council that deliberately samples the
**disconfirming** voices against a vote-motion. This is a reusable anti-steering technique for ANY
methodology/ inquiry — not a DT term. *Proposed (data, not code):* add it to the suggestion registry
(e.g. a suggested capability/angle "disconfirm: load the segments most likely to reject the premise
and test a Non-Fit motion") and have `next_action`'s act-guidance mention it when a step's intent is
exploratory. The engine stays tag-agnostic; the technique lives in suggestion DATA. Generalizes to any
domain (stress-test any thesis with its most likely refuters).

### GAP-3 — DEFECT: the synthesis payload validator silently drops the methodology's structured convergence fields ⚠️⚠️ (highest-priority harness fix)
**Observed live:** the Define answer node (`synthesis_6eec08bfbceca0fb`) is an **empty shell** —
`clusters`, `key_problems`, `gesamtbild`, `positionierung`, `segmente` all empty — even though the **5
cited Discover councils are deep** (OBS-3/OBS-4). Root cause is a harness defect, not (only) agent
discipline: `llm_simulation/_validators.py::validate_synthesis_payload` returns a **fixed whitelist**
(`arc_narrative, gesamtbild, positionierung, handlungsempfehlungen, segmente, references, voices,
citations`) that **omits `clusters`, `key_problems`, `ranking`, `shortlist`** — the exact structured
fields the deep seed intents instruct the agent to author:
- `verify__define.intent`: *"Author payload.clusters [{label, member_node_ids, insight}] +
  payload.key_problems."*
- `verify__lofi_select.intent`: *"Author payload.ranking [{prototype_id, score_rationale}] +
  payload.shortlist."*
These fields **exist on the Synthesis model** (get_synthesis returns `clusters:[] key_problems:[]
ranking:[] shortlist:[]`, so they *render*), but `record_synthesis` runs the payload through
`validate_synthesis_payload`, which **discards them on write**. So a methodology's affinity map /
key-problems / lo-fi ranking / shortlist — its core convergence outputs — are silently lost; the
ANSWER artifact is hollow while the substance is stranded in council exec-summaries. This is the
"thin synthesis" anti-pattern resurfacing **structurally**, and it is methodology-agnostic damage.
*Compounding agent-discipline note:* the agent ALSO left `gesamtbild`/`positionierung` empty (those DO
survive validation), so it under-authored the prose POV too — but even a perfectly disciplined agent
following the intent would lose its clusters/key_problems to the validator.
*Proposed (general — NOT hardcoded DT):*
- **FIX-A (harness, do first):** stop dropping structured blocks. Either extend the validator to pass
  `clusters/key_problems/ranking/shortlist` through (they already exist + render), or — more general —
  give the synthesis payload an extensible `structured`/`blocks` object the methodology defines,
  validated *loosely* (size caps, no vocabulary). Then ANY methodology's convergence output survives,
  regardless of its tags. This is the single highest-leverage fix found so far.
- **FIX-B (honesty gate):** `record_synthesis` should **soft-warn** (and/or the verify gate flag) when
  a synthesis payload is near-empty (no prose AND no structured blocks) — promote the existing
  `assess_project` thin-synthesis signal onto the WRITE path so a hollow answer can't silently pass a
  converge step. (Matches `harness-run-observations.md`'s proposed record_synthesis soft-warning.)
- **FIX-C (contract):** add a "seed-intent ↔ payload-schema" consistency check — a seed intent must
  only instruct payload fields the schema persists. Today they disagree.
*Why it matters:* this is precisely the gap between "deep understanding" (present, in councils) and a
"rich, explorable answer" (absent). Without FIX-A, even an excellent run renders thin POV/deliverable
nodes — the user-visible disappointment, despite good work underneath.

### OBS-5 — Ideate produced 8 distinct, insight-driven concepts incl. a real dark-horse ✅ (resolves WATCH-3)
The agent (via a subagent) authored an 8-concept cloud, each tied to a specific Discover insight, then
selected **5 varied NON-form types** for lo-fi ("flow / comparison / mapper / trigger-card / dashboard
— no forms", the agent's own words):
1. "Brauchst du das überhaupt?" — honest self-check that can end in **NO**; 2. "Risiko vs. Kapital, in
deinen Worten" — jargon-killer (language-barrier insight); 3. "Später, nicht jetzt" — trigger that
**refuses the KFZ moment**; 4. "Null Provision" — €-commission transparency (distrust insight); 5.
"Flexibler Sicherheits-Puffer" — reframes to pausable liquidity (precarious-present insight); 6. "Wer
hängt von dir ab?" — relational **mapper visualizing the €-gap if income stops**; 7. **"Das ist nichts
für dich"** — explicit **self-disqualification verdict** for non-targets (a genuine dark-horse/
provocation); 8. "Peer-Verbraucherzentrale" — neutral second-opinion.
*Why it matters:* this is the variety + boldness the user wanted — concept-KIND diversity, an explicit
"no forms" stance, and an unprompted provocation. *Evidence-discipline highlight:* the seductive
"compounding simulation / teach them early-investing" concept is **correctly ABSENT** — Discover
refuted that premise (the literate already grasp compounding and reject LV), so chasing it would be
anti-evidence. The agent stayed honest. WATCH-3 resolves positively.
*Bearing on GAP-2:* a STRONG agent diversified kind + produced a provocation **without** harness help,
so GAP-2 is less acute than feared — but it's currently **agent-dependent**. The proposed fix (surface
the artifact palette + invite ≥1 provocation, as DATA) would make this *reliable* rather than luck of
a disciplined agent.
*Bearing on GAP-1:* concept C6 ("visualize the €-gap if your income stopped") and C4 (€-commission
breakdown) *want* live computation/visualization — exactly the renderer ceiling. The acid test is how
they get BUILT next (real interactive viz vs. faked static cards). → WATCH-4.

### OBS-6 (method) — observability caveats for this monitoring
Two things to keep honest while watching: (a) my MCP server and the worker's are **separate processes
on one SQLite file**, so `list_*` reads lag the worker's writes by seconds — I verify ground truth via
a fresh `Store()` and on-disk `concept.json`. (b) the `tail | grep` monitor matches tool *names* in
ANY new line, so an agent `ToolSearch`/skill-load line that merely NAMES `scaffold_prototype` fires a
false "prototype built" event — every milestone is reconciled against the DB/disk before I record it.
*(Not a product finding; a note so the tracker's claims stay grounded.)*

### OBS-7 — Lo-fi prototypes are varied + on-insight + genuinely non-form ✅ (resolves WATCH-4 positively)
5 lo-fi prototypes across **4 distinct templates**, each tied to a Discover insight: `lofi-honest-check`
(spa-flow, 8-screen branching triage that can end in NO), `lofi-risiko-vs-kapital` (spa-comparison,
real side-by-side `columns` for the language-barrier insight), `lofi-dependents-map` (spa-cards,
tap-who-depends-on-you → verdict, can end "0 € — spar dir die Beiträge"), `lofi-zero-commission`
(spa-dashboard, €-commission breakdown), `lofi-later-trigger` (spa-cards, "refuse the KFZ moment"
trigger). No questionnaire/forms. The agent delivered concept-KIND variety + boldness.

### GAP-1 — CONFIRMED IN PRACTICE (concrete evidence) ⚠️⚠️
`lofi-dependents-map` is the proof. The concept aspires to "tippe an, wer eine Lücke hätte … wir zeigen
DIE EURO-LÜCKE" — a personalized model. Because the renderer can't compute, it degraded into **4 static
result screens with HARDCODED euro figures** (`~1.400 €` Partner, `~1.100 €` Kind, `0 €` Niemand) — the
gap is pre-baked per branch, not derived from any user input. A real version needs income input → a
computed gap → a bar/curve. This is exactly the ceiling FIX-A targets; the run *wanted* the simulation
and was forced to fake it. (The seductive "compounding simulation" never appeared — correctly, since
Discover refuted that premise — but the SAME missing primitive would have blocked it too.)

### GAP-4 — DEFECT: concept↔template navigation-key mismatch isn't validated; a "dead" prototype still scaffolds + gets proband-tested ⚠️
`lofi-later-trigger` (the trigger-card concept) was scaffolded with **spa-cards**, whose card renderer
reads only `card.goto`. But the concept's cards navigate via `card.action` (a key only **spa-dashboard**
honors). Net: its core interaction — arming a "later" trigger — **does not navigate** in the assigned
template, yet a `record_prototype_session` was recorded against it. So a proband "tested" a prototype
whose main action is dead, and nothing caught it.
*Proposed (general):* (a) **normalize card navigation** — every card-bearing template should accept
both `goto` and `action` (and a single canonical key going forward); (b) **scaffold_artifact validates
nav reachability** — every interactive element's target must resolve to a screen, else reject/warn
(no silent dead interactions); (c) optionally, the proband-session groundedness check could note when
the observed states never advanced past the start screen. Methodology-agnostic (any prototype).

### PREDICT-1 — the next converge (lofi_select) will hit GAP-3 again
`verify__lofi_select.intent` says "Author payload.ranking + payload.shortlist" — both are in the set
`validate_synthesis_payload` DROPS (GAP-3). Expect another hollow down-select synthesis (ranking/
shortlist lost). Watching to confirm the defect is systemic across converge steps, not a one-off.

## Watch list (to confirm as the run proceeds)
- **WATCH-1 — Discover breadth shape.** ✅ resolved positively (see OBS-3): a few rich multi-persona
  councils per angle, spectrum-sampled, memory-grounded. (Kept on the list as a regression check for
  the seed's "one exploration per persona/segment" wording, which could still mislead a future run.)
- **WATCH-2 — Define reframe.** ✅ resolved strongly (see OBS-4): a premise-refuting, mechanism-level
  reframe (structural Non-Fit vs word/relational barrier; compounding inverted). Still want to read the
  Define *synthesis* artifact itself to confirm the POV is authored rich (not stranded in councils).
- **WATCH-3 — Ideate breadth.** ≥4–8 *distinct-kind* concepts before down-select, or premature collapse
  to one obvious idea?
- **WATCH-4 — Prototype distinctness.** ✅ resolved positively (OBS-7): 5 varied non-form prototypes
  across 4 templates. Surfaced GAP-1 (faked simulation) + GAP-4 (dead-nav) concretely.
- **WATCH-5 — Hi-fi honesty.** Does the final spec keep deliberate non-targets + an honest
  validated-vs-open ledger (anti-steering survives to the end)?

_Last updated: 2026-06-05, during the live run (Discover frame done; at Define)._
