# Frameworks — the processes a study runs through

A **Framework** is the second layer of the [Job → Framework → Format taxonomy](job-framework-format.md):
*the process a run follows end-to-end.* A Job runs **through** a Framework **using** Formats.

Frameworks already exist in the core as the methodology specs under
[`sonaloop/methodologies/*.json`](../sonaloop/methodologies/) (keyed by `key`); starting a study with
one **seeds the plan engine** (`start_project(methodology=<id>)` / `set_project_methodology`). This
page documents each one in plain language so you can knowingly choose which Framework a study runs.

Every Framework shares the same **rhythm**: it alternates **diverge** (explore broadly) and
**converge** (narrow to a decision). Double Diamond does it twice — once in the problem space, once
in the solution space; the others are variations on that beat.

## Consume this as structured data

The descriptions below are not just prose — they are produced from one structured accessor so the
website "how it works" page and the job presets draw on a **single source**:

```python
from sonaloop import job_taxonomy

job_taxonomy.framework_descriptions()
# -> [{id, name, what, when, stages: [{id, name, what}]}, ...]   (in taxonomy order)

job_taxonomy.get_framework_description("double_diamond")
# -> one {id, name, what, when, stages} entry
```

The same shape is exposed over MCP as **`list_frameworks`** and **`describe_framework`** (see
[the MCP surface](../README.md)). `what` is the one-line "what shape it is", `when` is "when to use
it", and `stages` is the ordered diverge→converge shape. The data is read live from the methodology
specs and joined with the canonical [`taxonomy.json`](../sonaloop/taxonomy.json), so ids and labels
stay in lock-step across the core, the website IA and the tracker.

## The four Frameworks

### Double Diamond — `double_diamond`

- **What it is:** Problem space (Discover fan → Define waist) then solution space (Develop fan +
  prototype → Deliver waist). Frame an ambiguous problem and take it to a buildable solution.
- **When to use it:** When you have a "How Might We" question and want a rigorous problem framing
  plus a tested, buildable solution spec.
- **Stages (diverge → converge):**
  1. **Discover** *(diverge)* — surface the real, lived pains broadly across personas and angles.
  2. **Define** *(converge)* — cluster the breadth into ONE core problem and a sharp Point-of-View.
  3. **Develop** *(diverge)* — generate solution candidates and build at least one real prototype.
  4. **Deliver** *(converge)* — personas USE the prototype, then converge to a buildable spec.

### Double Diamond (Deep) — `double_diamond_deep`

- **What it is:** The full design-thinking process as three linked diamonds — problem space, solution
  exploration, and solution refinement — with broad empathy, affinity clustering, and a lo-fi → mid-fi
  fidelity ladder of real prototype tests.
- **When to use it:** When you want depth — many personas, broad problem exploration, clustered key
  problems, several lo-fi prototypes tested and down-selected, a refined mid-fi prototype tested, and
  a buildable solution presentation.
- **Stages (diverge → converge):**
  1. **Discover** *(diverge)* — empathize broadly across distinct angles.
  2. **Define** *(converge)* — affinity-cluster into themes; name the KEY PROBLEM(S) + a POV.
  3. **Ideate (Lo-Fi)** *(diverge)* — generate many distinct concepts; build several lo-fi prototypes.
  4. **Lo-Fi Test & Down-Select** *(converge)* — personas use the lo-fi prototypes, then down-select.
  5. **Refine (Mid-Fi)** *(diverge)* — build mid-fi prototype(s) of the shortlist + refinements.
  6. **Deliver (Solution Presentation)** *(converge)* — personas use the mid-fi prototype; synthesize
     the final solution presentation + buildable hand-off spec.

### d.school Micro-Cycle — `dschool_micro`

- **What it is:** The Stanford d.school micro-cycle: Understand/Observe (fan) → Define POV (waist) →
  Ideate (fan + prototype) → Prototype & Test (waist).
- **When to use it:** Human-centered design when you want empathy-first divergence and rapid
  prototype testing.
- **Stages (diverge → converge):**
  1. **Understand & Observe** *(diverge)* — build empathy; surface user needs, contexts, frictions.
  2. **Define POV** *(converge)* — consolidate observations into a single Point-of-View statement.
  3. **Ideate** *(diverge)* — generate many diverse concepts; build a prototype for the best.
  4. **Prototype & Test** *(converge)* — personas use the prototype; converge to refined requirements.

### Lean / Jobs-to-be-Done — `lean_jtbd`

- **What it is:** Problem-explore (fan) → Problem-pick (waist) → Solution-explore (fan + prototype) →
  Validate (waist). Lean-startup framing around the customer's job-to-be-done.
- **When to use it:** When you want to anchor on the customer's job, find the highest-value problem,
  then validate a minimal solution.
- **Stages (diverge → converge):**
  1. **Problem Explore** *(diverge)* — explore the jobs-to-be-done and the problems blocking them.
  2. **Problem Pick** *(converge)* — pick the single highest-value, most-underserved problem first.
  3. **Solution Explore** *(diverge)* — explore solution/MVP candidates and build a minimal prototype.
  4. **Validate** *(converge)* — personas use the MVP; validate the value prop and converge to a spec.

## Choosing a Framework

The [taxonomy](job-framework-format.md) maps each **Job** to a default Framework — e.g. *Positioning*
runs through Double Diamond, *Pricing* through Lean/JTBD, *Ideation (HMW)* through the d.school
Micro-Cycle. To run a study through one explicitly:

```text
start_project(title=…, goal=…, methodology="lean_jtbd")   # seed the plan from this Framework
set_project_methodology(project_id, "double_diamond")     # or (re)bind an existing project
```

In the inspector, a running study shows its Framework + current stage on the **Plan** drawer
(`/projects/{id}/plan`), and the **Documentation → Methodology** page lists every Framework with its
"what / when / stages".
