# Deep Design Thinking, Fidelity Ladder & Diamond Visualization — Specification

> **Status:** **IMPLEMENTED — D1–D5 shipped 2026-06-03** (design below).
> **Built:** deep methodology `double_diamond_deep` (6 phases) + expanded roles/clustering/ranking;
> prototype `fidelity` ladder + `spa-sketch` lo-fi template; retired the in-process LLM backend
> (host/subagents author all text); methodology-aware **diamond layout** (fan/waist + silhouettes);
> the `design-thinking-deep` driver skill. **Validated by a real re-run** of Pfefferminzia: 14
> segmented personas → a 12-node Discover fan → 2 key problems (incl. the under-served high-need
> segment) → 5 ideas + 3 lo-fi prototypes tested via Playwright → down-select → mid-fi built +
> tested → solution presentation. Three real diamonds (discover 12 / ideate 5 / refine 2 fans).
> Builds on (and amends) `spec/methodology-engine-and-prototyping.md`.
> **Trigger:** the first Pfefferminzia run came out as a *line, not a diamond* — too few personas,
> 2 explorations/phase, one prototype, no lo-fi→mid-fi ladder, no clustering, and no diamond layout.
> **Decisions locked with the user:**
> 1. **No server-side text generation, ever.** The host (Claude) or subagents author ALL text via
>    the MCP `brief_*→author→record_*` contract. The OpenAI key is **embeddings + image generation
>    only**. ⇒ the M5 in-process `LLMAuthoringBackend` is **RETIRED** (§3). "At scale / autonomous"
>    = **host-driven parallel subagent fan-out**, never an in-process LLM loop.
> 2. **Full deep DT process** (broad empathy → cluster → key problems → ideate → lo-fi test →
>    down-select → mid-fi test → synthesis → solution presentation), with a **fidelity ladder**.
> 3. **A real diamond layout** in the UI.
> 4. **Engine + UI first, then re-run** Pfefferminzia at full depth.
> **Leitsatz (unchanged):** capabilities via MCP; structure enforced by the engine, dynamics
> LLM-judged-by-the-host; every claim traceable; anti-steering; persona experience-driven.

---

## 1. What "really getting there" requires (the gap)
| Need | Today | Required |
|---|---|---|
| Looks like a diamond | longest-path layout → near-line | **phase/mode-aware fan/waist layout** + faint diamond silhouettes (§6) |
| Breadth | 2 explorations/phase, 5 personas | **12–16 segmented personas**, **one exploration per persona/segment/idea** → wide fans (§5, §7) |
| Problem → key problem | one converge node | **affinity clustering** → themes → key problem(s) (§4) |
| Solution fidelity | one prototype | **lo-fi (several) → down-select → mid-fi** ladder (§4–§5) |
| Process depth | 4 phases | **6 phases** = three diamonds (§4) |
| Scale of execution | hand-stitched | **host-driven parallel subagent fan-out** (§3) |
| Final artifact | spec + meta-report | + **solution presentation** (§8) |

---

## 2. Reaffirmed contract (and one retirement)
- The engine enforces **structure** (diverge-before-converge, ≥N explorations, edges, traceability,
  artifact requirements). The **dynamics** (saturation, "this is the key problem", "this prototype
  wins") are judged by **the host**, recorded as evidence-backed judgments. No numeric thresholds.
- **No LLM text-generation backend.** `runtime.py`: delete `LLMAuthoringBackend`; keep
  `run_methodology` (structural loop) + `StubAuthoringBackend` (tests only). Real runs are driven by
  the host via the driver skill (§3). Remove the `PERSONA_COUNCIL_LLM_*` config + `make`/docs that
  imply LLM authoring. OpenAI stays: embeddings (`memory.py`) + avatar images (`avatar.py`) only.

---

## 3. Execution model — host-driven parallel subagents
The breadth comes from the host spawning many grounded persona subagents **in parallel batches**,
each authoring one reaction, which the host folds into councils + exploration nodes via MCP.

- A **driver skill** `design-thinking-deep` (extends `methodology-run`): per diverge phase, fan out
  one subagent **per persona (Discover) / per idea (Ideate) / per prototype (test rounds)**, run them
  in parallel, then `record_exploration` for each; record a host `divergence_complete` judgment;
  `advance_phase`. Per converge phase: cluster/down-select (host-authored), `record_convergence`.
- No new server capability is required for parallelism — it is the **calling harness** (Claude Code
  Agent tool) running subagents concurrently. The engine only validates the resulting structure.
- Cost/scale guidance lives in the skill (batch size, when to stop fanning out — host judgment).

---

## 4. The deep methodology (data-driven, new built-in `double_diamond_deep`)
Six phases, strict diverge/converge alternation = **three linked diamonds** (problem · solution-explore ·
solution-refine). Shipped as `persona_council/methodologies/double_diamond_deep.json`.

| # | key | mode | strategy | produces_role | fidelity | requires_artifacts | notes |
|---|---|---|---|---|---|---|---|
| 1 | `discover` | diverge | pain-discovery | `problem-landscape` | — | — | one exploration **per persona/segment** |
| 2 | `define` | converge | tension | `key-problems` | — | — | **affinity-cluster** the fan → themes → key problem(s) + POV |
| 3 | `ideate` | diverge | positive-deepdive | `solution-options` | — | — | many solution concepts (one exploration per idea) |
| 4 | `lofi_select` | converge | goal | `solution-shortlist` | `lofi` | `prototype`,`prototype_session` | build **several lo-fi** prototypes, test, **down-select** |
| 5 | `refine` | diverge | positive-deepdive | `solution-options` | `midfi` | `prototype` | build **mid-fi** prototype(s) of the shortlist; explore refinements |
| 6 | `deliver` | converge | tension | `solution-presentation` | `midfi` | `prototype_session` | test mid-fi, synthesize, **solution presentation** + spec |

`double_diamond` (the 4-phase one) is kept for quick runs. New schema keys: `fidelity`
(`lofi|midfi`, optional) on a phase; `produces_role` vocabulary expanded.

### 4.1 Engine changes (`methodology.py`)
- **Roles** expanded: `ROLES = {problem-landscape, key-problems, point-of-view, solution-options,
  solution-shortlist, solution-presentation, spec}`. Relax `validate_methodology_spec`: diverge →
  any "exploration" role (`problem-landscape|solution-options`); converge → any "decision" role
  (`key-problems|point-of-view|solution-shortlist|solution-presentation|spec`). Drop the hard
  `{point-of-view, spec}` restriction.
- **Down-select** is an ordinary converge that `consumes` a diverge fan of prototype tests; the
  engine's existing INV-ARTIFACT (`prototype_session` on the converge) already forces real testing.
  The convergence payload carries a `ranking` (ordered prototype_ids + rationale) — see §4.3.
- **`fidelity`** passes through to scaffolded prototypes (§5).

### 4.2 Affinity clustering (Define)
A converge phase may carry **clusters** in its payload:
`clusters: [{label, member_node_ids:[explorations], insight}]` and `key_problems: [string]`.
- Stored on the convergence `Synthesis` (new optional fields `clusters`, `key_problems`).
- The host authors clusters from the Discover fan (group the per-persona problem nodes into themes).
- UI renders clusters as labeled groupings at the waist; the report lists key problems.
- Optional (later): materialize each cluster as its own node between fan and waist for an even
  richer many→themes→one shape. v1 keeps clusters as convergence metadata.

### 4.3 Down-select (lofi_select)
Convergence payload carries `ranking: [{prototype_id, score_rationale}]` (host-authored from the
lo-fi `prototype_session` reactions) and `shortlist: [prototype_id]` → the brief for `refine`.

---

## 5. Prototype fidelity ladder
- `Prototype` gains `fidelity: "lofi"|"midfi"` (JSON field; default `midfi`). `scaffold_prototype`
  accepts `fidelity` and `register_prototype` too.
- **lo-fi template `spa-sketch`**: the same clickable SPA but visibly low-fidelity (sketch styling,
  "SKIZZE/Lo-Fi" banner, monochrome, no polish) — cheap to make several. **mid-fi** = the existing
  `spa-min` (clean, branded). Both are real, runnable, Playwright-drivable.
- Flow: Ideate proposes N concepts → build N **lo-fi** prototypes → personas test each (sessions) →
  `lofi_select` down-selects 1–2 → build **mid-fi** of the winner(s) in Refine → test in Deliver.
- All prototype use stays **real** via the Playwright harness; reactions grounded in the session log.

---

## 6. Diamond layout (UI) — the visible fix
When `graph.methodology_state` is present, the interactive graph uses a **methodology layout**
instead of longest-path:
- **x by phase index:** `x = MARGIN + phase_index * COL_W`.
- **Diverge phase:** its K exploration nodes are **fanned vertically, symmetric around the centre
  axis** `y0`: node i at `y = y0 + (i - (K-1)/2) * ROW_H`. Wide K ⇒ tall fan.
- **Converge phase:** single node **on the axis** (`y = y0`); cluster labels (if any) stack beside it.
- **Silhouette:** behind the nodes, draw faint filled diamonds connecting each diverge fan's
  top/bottom extents to the adjacent converge waists (one diamond per diverge→converge pair) → the
  classic multi-diamond outline.
- Edges unchanged (refines fan→waist, spawned_from waist→next fan). Drag/zoom/minimap still work;
  the methodology layout only sets the **initial** positions (saved positions still override).
- Implementation: `get_project_graph` already exposes `phase`/`mode`; add `phase_index` per node +
  an ordered `phases` list to the graph JSON; `_RGRAPH_JS` computes positions when `D.methodology`
  is set; CSS for the silhouette.

---

## 7. Cohort scale (host-authored, segmented)
- Target **12–16 personas** for a real run, spanning explicit **segments** (age band × life-stage ×
  attitude × channel × region). For Pfefferminzia e.g.: Azubi-Single, Studi-knapp, Aufsteiger-Paar,
  Familienplaner, Frischgebackene-Eltern, Späteinsteiger-Skeptiker, Gutverdiener-Digital,
  Migrationsbiografie, Land-vs-Stadt, plus 2–3 provider-side (Produkt, Vertrieb, Compliance).
- Authored **by the host/subagents** via `record_persona` (host-authoring; no LLM API). A bulk
  helper/skill batches profile authoring; profiles must pass `validate_profile_payload`.
- Discover then fans **one exploration per persona** (12–16 nodes) ⇒ a genuinely wide first diamond.

---

## 8. Solution presentation artifact
- Deliver's convergence `role=solution-presentation`: the winning mid-fi concept, the segments it
  wins (and deliberate non-targets), the validated pain-solvers, the evidence trail (sessions), open
  risks, and the dev hand-off spec.
- The **Meta-Report** is extended/retitled per methodology: a `double_diamond_deep` project's
  meta-report is a **Solution Presentation** (build-order narrative + per-phase sections + the final
  recommendation). Optional later: a dedicated slide-style HTML export.

---

## 9. Milestones (each with a failure-proof acceptance test)
- **D1 — Engine depth:** expanded roles + relaxed validation; `double_diamond_deep` built-in;
  `fidelity` on phases/prototypes; clustering/ranking payload fields; retire `LLMAuthoringBackend`.
  **Accept:** a `double_diamond_deep` project runs through all 6 phases honoring invariants; engine
  has **zero** LLM-text-gen code paths (grep); Define stores `clusters`+`key_problems`.
- **D2 — Fidelity prototypes:** `spa-sketch` lo-fi template; scaffold/register carry `fidelity`.
  **Accept:** a lo-fi and a mid-fi prototype both scaffold, run, and are Playwright-drivable.
- **D3 — Diamond layout:** methodology-aware fan/waist layout + silhouette. **Accept:** a run with
  ≥10 Discover explorations renders a visibly wide first diamond (fan height ≫ node height), waists
  on-axis — verified live.
- **D4 — Deep run skill:** `design-thinking-deep` driver (parallel subagent fan-out). **Accept:**
  drives Discover with one grounded subagent per persona in parallel batches.
- **D5 — Rich re-run:** Pfefferminzia end-to-end on `double_diamond_deep` with 12–16 personas, lo-fi
  + mid-fi prototypes, clustering, solution presentation. **Accept:** the graph shows three real
  diamonds; lo-fi tested → down-select → mid-fi tested; presentation exported.

---

## 10. Open questions
- Cluster nodes as first-class graph nodes (richer many→themes→one) vs payload metadata — start with
  metadata (§4.2), upgrade if the diamond needs it.
- Down-select scoring: pure host judgment (with session evidence) — no numeric auto-scoring.
- Parallel subagent batch size / cost ceiling — host judgment, documented in the skill.
- Slide-style presentation export — deferred until the graph + report read well.

---

## 11. Amendments to existing specs
- `methodology-engine-and-prototyping.md`: §5 autonomous `LLMAuthoringBackend` is **retired** (no
  in-process LLM text-gen, per the locked principle); the runtime keeps structural orchestration +
  the test stub only. Roles/validation generalized (§4.1). Prototype gains `fidelity`.
