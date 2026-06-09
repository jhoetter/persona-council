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
| `head_to_head` | Head-to-Head | planned (sibling ticket) |
| `red_team` | Red-Team | planned (sibling ticket) |

`head_to_head` and `red_team` are being built in sibling tickets; they are referenced by stable
id here even though not yet implemented, so consumers can wire them ahead of time.

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
| **Churn Reasons** (`churn_reasons`) | Continuous discovery | `lean_jtbd` | `lean_jtbd` | `council`, `red_team` | 4 · churn-reason, tenure, current-alternative |

The **coverage** column is the persona spread a Job needs to be trustworthy: a minimum count
plus the axes the panel must span. The full notes (one per Job) live in `taxonomy.json`.

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
- **`sharpen-question-helper` presets** — seed each preset from a Job's framework + formats + coverage.
- **Methodology surface** — Frameworks here are the real `key`s already in `sonaloop/methodologies/`.

## Naming + stable ids

- **Job ids** are lower_snake_case and stable (`positioning`, `pricing`, `jtbd_demand`,
  `ideation_hmw`, `continuous_discovery`, `churn_reasons`). Never renumber or rename — add new
  Jobs instead.
- **Framework ids** equal the methodology `key` (`double_diamond`, …).
- **Format ids** are lower_snake_case (`council`, `prototype_test`, `head_to_head`, `red_team`).

Any repo or ticket tags itself with `layer` + the relevant id (e.g. `job:positioning`,
`format:red_team`) so cross-repo work stays aligned.
