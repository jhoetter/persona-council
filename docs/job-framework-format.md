# Job → Framework → Format — the three-layer taxonomy

**This is the source of truth.** The whole Sonaloop product (core app, website IA, and the
tracker) aligns on the three orthogonal layers below. The machine-readable companion is
[`sonaloop/taxonomy.json`](../sonaloop/taxonomy.json), loaded via `sonaloop.job_taxonomy`;
keep the two in lock-step. Every repo and ticket tags itself with the layer (and id) it serves.

## The doctor analogy

> You walk into a doctor's office because **your stomach hurts** — that is the **Job**: *why
> does my stomach hurt?* The doctor runs a **process** — history → exam → tests → diagnose —
> that is the **Framework**. Along the way the doctor reaches for individual **tests** — a
> blood test, an X-ray — each of those is a **Format**.
>
> You arrive with a Job; the doctor runs a Framework; reaches for Formats inside it.

The three are **orthogonal axes, not competing lists**: a Job runs *through* a Framework
*using* Formats. The same Format (a council) shows up inside many Frameworks serving many Jobs.

## The three layers

| Layer | One-liner | What it is |
|-------|-----------|------------|
| **Job** | What the user wants — the use case they buy. | The outcome a customer walks in for ("how is my positioning?", "what should I charge?"). The thing sold and the thing measured. The core has **no first-class concept of it today** — the host (Claude) improvises it from a free-text goal; this taxonomy gives Jobs stable ids. |
| **Framework** | The process the run follows end-to-end. | A constellation of steps (a DAG) taking a run from ambiguity to a buildable answer. Frameworks **already exist** in core as [`sonaloop/methodologies/*.json`](../sonaloop/methodologies/) (keyed by `key`) and seed the plan engine. |
| **Format** | A single move inside a run. | One concrete research move at a plan step: a council, a prototype test, a head-to-head, a red-team. |

### Mislabels this model fixes

- **How-Might-We is a Format-shaped move**, not a Job — though it is often sold as one. Here
  it is folded into the **ideation** Job.
- **"JTBD" is a Job**, whose core engine is the `lean_jtbd` **Framework** of the same name.
  Keep the two layers distinct: the Job (`jtbd_demand`) *runs through* the Framework
  (`lean_jtbd`).

## Frameworks (real methodology keys)

Each Framework id maps 1:1 to a methodology `key` shipped under `sonaloop/methodologies/`.

| Framework id / `key` | Name |
|----------------------|------|
| `double_diamond` | Double Diamond |
| `double_diamond_deep` | Double Diamond (Deep) |
| `dschool_micro` | d.school Micro-Cycle |
| `lean_jtbd` | Lean / Jobs-to-be-Done |

Each Framework is documented in plain language (what it is, when to use it, its diverge→converge
stages) in [`docs/frameworks.md`](frameworks.md). The structured descriptions
(`{id, name, what, when, stages}`) are exposed via `sonaloop.job_taxonomy.framework_descriptions()`
and the `list_frameworks` / `describe_framework` MCP tools, so the website "how it works" page and
the job presets draw on one source.

## Formats

| Format id | Name | Status |
|-----------|------|--------|
| `council` | Council | implemented |
| `prototype_test` | Prototype Test | implemented |
| `head_to_head` | Head-to-Head | implemented |
| `red_team` | Red-Team | implemented |

`head_to_head` ships as a Format on top of the artifacts/variant plumbing: it compares two (or more)
concrete options (captured A/B variants or plain text options) side-by-side and the server tallies a
reasoned, *segmented* preference (preference + margin + segment-splits). Drive it via
`brief_head_to_head` / `record_head_to_head` (MCP) — Job presets compose it.

`red_team` ships as a **falsification** Format on top of the council plumbing: it deliberately argues the
NEGATIVE case — *why would this segment NOT adopt / NOT pay / churn?* — to stress-test an idea instead of
flattering it. It re-frames a normal council toward disconfirmation and assigns each persona an explicit
adversarial lens (skeptic / blocker / switching-cost / status-quo / risk); the server groups their
concrete objections by theme into a structured **case-against** (how many personas raise each blocker +
worst severity), optionally beside the **case-for** when run with `stance="both"` (the same question in
both directions). Drive it via `brief_red_team` / `record_red_team` (MCP) — Job presets compose it.

## The mapping table — Job → Framework(s) → Formats → coverage

Each named Job resolves to a concrete default Framework, a set of Formats, and the persona
**coverage** it needs.

| Job (`id`) | Sells as | Default Framework | Frameworks | Formats | Coverage (min personas · axes) |
|------------|----------|-------------------|------------|---------|--------------------------------|
| **Positioning** (`positioning`) | Positioning | `double_diamond` | `double_diamond` | `council`, `head_to_head`, `red_team` | 4 · segment, buying-stage, current-alternative |
| **Pricing / Price-Sensitivity** (`pricing`) | Pricing | `lean_jtbd` | `lean_jtbd` | `council`, `head_to_head`, `red_team` | 4 · willingness-to-pay, budget-authority, current-alternative |
| **Demand / Jobs-to-be-Done** (`jtbd_demand`) | Demand/JTBD | `lean_jtbd` | `lean_jtbd` | `council`, `prototype_test` | 5 · segment, trigger-moment, current-alternative |
| **Ideation (How-Might-We)** (`ideation_hmw`) | Ideation (HMW) | `dschool_micro` | `dschool_micro`, `double_diamond_deep` | `council`, `prototype_test`, `head_to_head` | 4 · segment, expertise-level, extreme-user |
| **Continuous Discovery** (`continuous_discovery`) | Continuous discovery | `dschool_micro` | `dschool_micro` | `council`, `prototype_test` | 3 · segment, lifecycle-stage, recency-of-use |
| **Churn Reasons** (`churn_reasons`) | Churn reasons | `lean_jtbd` | `lean_jtbd` | `council`, `red_team` | 4 · churn-reason, tenure, current-alternative |
| **A/B Test** (`ab_test`) | A/B test | `lean_jtbd` | `lean_jtbd` | `head_to_head`, `prototype_test`, `red_team` | 4 · segment, current-alternative, buying-stage |

The **coverage** column is the persona spread a Job needs to be trustworthy: a minimum count
plus the axes the panel must span. The full notes (one per Job) live in `taxonomy.json`.

## Job protocols — the run discipline a Job carries

Some Jobs are only trustworthy when run with a specific **discipline** — not just the right
Framework and Formats, but rules about *ordering and commitment* (what must be frozen before
what). Those Jobs carry a `protocol` block in `taxonomy.json`:

```json
"protocol": {
  "name": "…",
  "summary": "…",
  "steps": [{"id": "…", "rule": "…", "tooling": "…"}]
}
```

Each step is a **rule** (what the discipline demands) plus the **tooling** that makes it
checkable (the MCP tools / fields that carry it). The protocol rides verbatim into the Job's
preset (`get_job_preset`), so the host sees the discipline exactly where it plans the run. As
everywhere in core: the host authors all text; a protocol constrains *structure and order* —
the server validates and persists, it never generates.

### A/B test (`ab_test`)

> *Which variant wins — and for whom?*

**Framework: `lean_jtbd`** — the decide-fast loop. An A/B test arrives with the variants
already in hand, so the empathy-first front half of `dschool_micro` (Understand & Observe →
Define POV) would be ceremony; `lean_jtbd`'s spine — state the bet, expose the thing, validate
at a hard waist, loop back if refuted — *is* the A/B discipline (hypothesis before exposure,
verdict at the gate). A run typically enters at `solution_explore` (the variants are the
solution options) and converges at `validate`.

The protocol (`taxonomy.json` → `jobs[ab_test].protocol`):

1. **`variants_up_front`** — all variants defined and FROZEN before any persona sees them; a
   changed variant is a new test. Tooling: `add_artifact` (captured variants) or text options.
2. **`hypothesis_before_exposure`** — exactly ONE falsifiable hypothesis + success metric
   stamped before exposure (`record_hypothesis`); the recording carries its ref
   (`variant_meta.hypothesis_id`), so the verdict answers a pre-registered bet, never a
   post-hoc story.
3. **`randomized_order`** — variant presentation order is randomized per persona (the
   position-bias guard). `brief_head_to_head` hands each participant a deterministic
   `option_order`; the order actually shown is recorded back via `variant_meta.order_shown`
   (validated: each entry must be a permutation of the option labels).
4. **`forced_preference`** — every persona states a forced preference plus intensity (a
   per-option stance −2..2 and one choice with a reason). A genuine "torn" is an
   **abstention** and is counted as one — never silently dropped.
5. **`segmented_verdict`** — the verdict is overall AND per-segment: winner, margin,
   abstentions per segment (`head_to_head.result.segment_splits` +
   `services.segmented_verdict(session_id)`), never one blended number.

The `head_to_head` Format persists all of this on the recorded session
(`head_to_head.variant_meta` = variant ids + per-persona order shown + hypothesis ref) and
stays **backward-compatible**: recordings made before the metadata existed still load, and
`segmented_verdict` derives per-segment margins from their stored tallies.

## How to consume it

```python
from sonaloop import job_taxonomy

job_taxonomy.jobs()                # all Jobs (id, frameworks, formats, coverage)
job_taxonomy.get_job("positioning")
job_taxonomy.framework_keys()      # {"double_diamond", "lean_jtbd", ...} — real methodology keys
job_taxonomy.format_ids()          # {"council", "prototype_test", "head_to_head", "red_team"}
```

Downstream tickets reference this artifact directly:

- **Website IA** — Jobs are the products sold; the `sells_as` field is the navigation label.
- **Job presets + sharpen-the-question** — shipped in `sonaloop/job_presets.py`: one preset per Job
  (framework + formats + coverage, derived live from this taxonomy) plus the deterministic
  `sharpen_question` helper that turns a fuzzy goal into a well-formed study spec. MCP surface:
  `list_job_presets` / `get_job_preset` / `sharpen_question` / `start_job_study`.
- **Methodology surface** — Frameworks here are the real `key`s already in `sonaloop/methodologies/`.

## Naming + stable ids

- **Job ids** are lower_snake_case and stable (`positioning`, `pricing`, `jtbd_demand`,
  `ideation_hmw`, `continuous_discovery`, `churn_reasons`, `ab_test`). Never renumber or
  rename — add new Jobs instead.
- **Framework ids** equal the methodology `key` (`double_diamond`, …).
- **Format ids** are lower_snake_case (`council`, `prototype_test`, `head_to_head`, `red_team`).

Any repo or ticket tags itself with `layer` + the relevant id (e.g. `job:positioning`,
`format:red_team`) so cross-repo work stays aligned.
