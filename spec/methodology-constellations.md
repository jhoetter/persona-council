# Methodology Constellations — Specification

> **Status:** DESIGN — build-ready. Supersedes the phase-grammar of
> `spec/methodology-engine-and-prototyping.md` §3–§4 and `deep-design-thinking-and-diamond.md` §4.
> **Goal:** make methodologies **fully declarative, non-hardcoded** — a methodology is a
> **constellation: a DAG of typed steps, each bound to an MCP capability** — so any number of
> methodologies (Double Diamond, d.school, Lean, Design Sprint, Jobs-to-be-Done, custom, …) are
> *data*, interpreted by a generic engine + generic UI, with **zero double-diamond assumptions in
> code**. **Locked with the user:** full capability-DAG model; spec-first.
> **Leitsatz (unchanged):** capabilities via MCP; the host (Claude)/subagents author ALL text
> (`brief_*→record_*`); **no in-process LLM text-generation**; OpenAI = embeddings + images only;
> structure enforced by the engine, dynamics LLM-judged-by-the-host with evidence.

---

## 1. What's hardcoded today (the actual problem)
Phase *specs* are already data (`methodologies/*.json` in a registry). But the **grammar** is
Double-Diamond-shaped — four baked-in assumptions:

| # | Hardcoded | Where | Blocks |
|---|---|---|---|
| 1 | phases must strictly alternate diverge,converge,… | `methodology.py:61` | branches, parallel tracks, 5-mode d.school, N-diamonds, loops |
| 2 | closed enums (`ROLES`, `JUDGMENT_KINDS`, `FIDELITIES`) | `methodology.py:23-27` | new roles/gate-kinds/fidelities need code edits |
| 3 | only `"prototype"`/`"prototype_session"` artifact types understood | `methodology.py:362,366` | surveys, journey-maps, canvases, A/B tests, … |
| 4 | UI layout maps literal phase keys (`ideate`/`refine`/`lofi_select`/`deliver`) | `web.py:1126-1159` | any other methodology's artifacts won't place/route |

The fix removes all four by replacing the phase grammar with a generic step grammar.

---

## 2. The model — a constellation of capability steps

A **Methodology** = `{key, name, description, when_to_use, steps: Step[]}`. The steps form a **DAG**
via `consumes` (incoming edges). No linear ordering, no parity.

### 2.1 Step schema (normative; `?` = optional)
```
Step:
  id            string   required   unique within the methodology
  name          string   required
  capability    string   required   one of the CAPABILITY CATALOG (§2.2)
  intent        string   required   prose for the author
  consumes?     string[]            ids of upstream steps it depends on (DAG edges); [] for roots
  breadth?      "fan" | "single"    default by capability (§2.2). fan = a diverge cloud of nodes;
                                     single = one node consolidating its inputs
  council_strategy? "pain-discovery"|"positive-deepdive"|"tension"|"goal"   (for explore/decide)
  diverge_by?   string              free hint, e.g. "persona" | "idea" | "angle"
  produces      { role: string, artifact_type?: string, fidelity?: string }   role/type are FREE strings
  requires_artifacts? string[]      free artifact-type names that must exist upstream before this step
  gate?         { kind: string }    the evidence-backed judgment required to leave a fan (free kind)
  loop_back?    string              a prior step id to revisit (LLM-judged)
```
**Open vocabularies.** `role`, `artifact_type`, `fidelity`, `gate.kind`, `diverge_by` are **free
strings declared by the spec** — there are **no code enums**. Validation checks *references*
(below), never membership in a hardcoded set.

### 2.2 Capability catalog (the only code-level extension point — added rarely)
A small set of primitives, each a thin binding over MCP tools that already exist. A methodology
*composes* these as data; a genuinely new capability is one new entry here.

| capability | default breadth | what it does (MCP) |
|---|---|---|
| `explore` | fan | run council(s) per persona/idea/angle → exploration node(s) (`run-council`/`record_*`) |
| `cluster` | single | affinity-cluster upstream exploration nodes → themes/`key-problems` |
| `decide` | single | converge upstream into one decision node (POV/shortlist/spec/presentation) |
| `build_artifact` | fan | scaffold real artifact(s) of `produces.artifact_type` (e.g. prototype, survey) |
| `test_artifact` | fan | personas USE an artifact (real session, e.g. Playwright) → grounded reactions |
| `synthesize` | single | second-order report / solution presentation (meta-report) |
| `judge` | — | record an evidence-backed gate judgment (not a node; a decision record) |

`build_artifact`/`test_artifact` may also be expressed **inline** on an `explore`/`decide` step
(`produces.artifact_type` / `requires_artifacts`) when that reads cleaner — both compile to the
same internal step graph.

### 2.3 Shape is DERIVED, never asserted
- "diverge" ⇔ a step whose effective breadth is `fan` (it emits multiple nodes).
- "converge"/"waist" ⇔ a `single`-breadth step consuming a fan.
- A "diamond" is simply `fan → single`. Two diamonds = `fan→single→fan→single`. Branches,
  parallel tracks, triple diamonds, and `loop_back` spirals are all just DAG shapes. The engine
  reads shape from `breadth` + `consumes` — **the alternation rule (#1) is deleted.**

---

## 3. Generic structural invariants (from capability, not phase keys)
Enforced by the engine for *any* constellation (replacing the DD-specific INV-*):

- **INV-DAG** `consumes` ids exist; the graph is acyclic except declared `loop_back` (logged).
- **INV-READY** a step is recordable only when all `consumes` steps are `complete`.
- **INV-BREADTH** a `single` step consuming a `fan` requires the fan to have **≥2 nodes**.
- **INV-GATE** if the consumed fan declares a `gate`, an evidence-backed judgment of that
  `gate.kind` (decided, rationale, ≥1 evidence_ref) must exist before the `single` step records.
- **INV-EDGES** a `single` step's `from_node_ids ⊆ nodes(consumed fans)`; the engine draws
  `refines` edges from each.
- **INV-ARTIFACT** generic over type T: a step with `requires_artifacts:[T]` needs ≥1 artifact of
  type T produced by an upstream `build_artifact` (and, for a `test_artifact`/`decide` that
  requires a *session* type, ≥1 recorded session of T). No literal `"prototype"` strings.
- **INV-CITE** every node cites ≥1 council; every artifact claim cites a session-log state.

A4 (no hardcoded dynamics) stands: "explored enough?", "which wins?", "ready?" are **LLM judgments
recorded with evidence**; the engine requires the judgment's *presence*, never a count.

---

## 4. Engine — a generic DAG interpreter
Replaces the linear phase cursor with a **topological frontier**.

### 4.1 State (project)
`methodology` (key), `step_log: {step_id: {status: pending|active|complete, node_ids:[],
decision_node_id?, judgments:[], artifacts:[], decided_at?}}`. No `phase` cursor.

### 4.2 Tool surface (generalized; old names kept as thin aliases for back-compat)
- `list_methodologies` · `get_methodology(key)` · `start_methodology_project(title, goal, key, persona_ids)`
- `brief_next(project_id)` → the **ready frontier**: the step(s) whose `consumes` are complete, each
  with capability, breadth, strategy, what's still unmet, consumed artifacts, instructions.
  *(alias: `brief_phase` returns the single next step when the graph is linear.)*
- `record_node(project_id, step_id, council_ids, payload)` → one node for a `fan`/`explore` step.
  *(alias: `record_exploration`.)*
- `record_judgment(project_id, step_id, kind, decided, rationale, evidence_refs)` → any gate kind.
- `record_decision(project_id, step_id, from_node_ids, payload)` → the `single` step's node + edges,
  validates INV-*. *(alias: `record_convergence`.)*
- `record_artifact_session(...)` → grounded artifact use (generalizes `record_prototype_session`).
- `advance(project_id, step_id)` → marks a step complete, recomputes the frontier; handles `loop_back`.
- `get_methodology_state(project_id)` → per-step status, counts, judgments, the DAG.

`Synthesis` nodes keep `step` (was `phase`), `breadth` (was `mode`), `role`, `methodology`, and the
converge enrichments (`clusters`/`key_problems`/`ranking`/`shortlist`). Artifacts gain `step` (the
build step that produced them) for generic placement.

---

## 5. Generic UI layout (from the DAG, no phase keys)
Replace `_methodology_layout`'s literal maps (#4) with a **graph-derived** layout:
- **x = longest-path depth** over `consumes` (topological columns).
- **fan steps** spread their nodes vertically symmetric around the axis; **single steps** sit on the
  axis → diamonds emerge wherever `fan→single` occurs (any number, any arrangement).
- **artifacts** are placed in the column of their **producing `build_artifact` step** (read from
  `artifact.step`), with a **solid** edge from that step and a **dashed** edge to the **first
  downstream step that consumes/tests that artifact type** — both found by walking the graph, not
  by `{lofi:ideate}` literals. (Generalizes the current prototype placement + edge-suppression.)
- faint diamond silhouettes drawn for every `fan→single` pair. Layout-version invalidation (`lv`)
  unchanged.

---

## 6. What stays vs changes
**Stays:** the MCP primitives (councils, syntheses, prototypes, Playwright, embeddings, images),
host-authoring, anti-steering, no-LLM-text-gen, the prototype fidelity ladder (now `fidelity` is a
free string on `build_artifact`), the diamond *visual* (now emergent).

**Changes / removed:** the alternation rule (#1), the `ROLES`/`JUDGMENT_KINDS`/`FIDELITIES` enums
(#2), the literal `"prototype"`/`"prototype_session"` special-casing (#3 → generic over
`artifact_type`), the phase-key layout maps (#4 → DAG layout). The `runtime.py` `StubAuthoringBackend`
+ structural loop generalize to the step frontier (still no LLM).

---

## 7. Migration & back-compat
- Re-express the four built-ins as **constellations** (`steps`), e.g. `double_diamond` =
  `discover(explore,fan) → define(decide) → develop(explore,fan,+build prototype) →
  deliver(decide,+requires prototype_session)`; `double_diamond_deep` = the 6-step graph; d.school
  and lean likewise.
- **Legacy loader:** a spec with the old `phases` key is auto-translated to `steps`
  (`mode:diverge→breadth:fan`, `converge→single`; `produces_role→produces.role`;
  `requires_artifacts`/`fidelity` carried over; `consumes` from the preceding phase). So any
  user-authored phase spec keeps working.
- Tests `test_methodology_engine`/`test_runtime` updated to the step API (aliases keep old call
  sites working during migration).

---

## 8. Milestones (each with a failure-proof acceptance test)
- **C1 — Step model + registry:** Step schema + capability catalog + legacy translator; reference
  validation (no enums). **Accept:** a 3-step *non-alternating* test methodology (e.g. a fan that
  feeds two parallel decides) validates and loads — impossible under today's parity rule.
- **C2 — Generic engine:** DAG frontier (`brief_next`/`record_node`/`record_decision`/`advance`) +
  generic INV-* (incl. artifact-type-generic INV-ARTIFACT) + aliases. **Accept:** a methodology
  declaring a **non-prototype** artifact type (e.g. `survey`/`survey_response`) enforces its
  artifact gate with zero code changes; grep shows no literal `"prototype"` in engine invariants.
- **C3 — Generic UI layout:** DAG topological layout + emergent diamonds + artifact attach/route
  from the graph. **Accept:** `double_diamond_deep` renders identically to today, AND a different
  methodology's artifacts place/route correctly — both with no phase-key literals (grep).
- **C4 — Migrate built-ins:** all four methodologies re-expressed as constellations; full suite
  green; the Pfefferminzia deep project still renders three diamonds.
- **C5 — Docs/skills:** update the driver skills + AGENTS.md to the constellation vocabulary;
  authoring guide for adding a methodology (data only).

---

## 9. Amendments to existing specs
`methodology-engine-and-prototyping.md` and `deep-design-thinking-and-diamond.md`: the **phase
grammar is superseded by the step/constellation grammar** here; their engines/invariants/layout
are generalized as above. Built-ins move from `phases` to `steps` (legacy `phases` still loads).
Everything else (host-authoring, no-LLM, prototype harness, fidelity ladder) is retained.
