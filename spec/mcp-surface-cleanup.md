# MCP surface cleanup — retire legacy, fix placement, signal the front door

> **Status: ✅ IMPLEMENTED 2026-06-05 (suite green, pushed).** M1 retired the 6 legacy study-graph
> tools (162→156). M2 demoted the 8 admin/maintenance tools to CLI-only (156→**148**). M3 relocated the
> `delete_*` CRUD to its domain file (rest scoped out — zero agent impact). M4 made the proto_*/
> prototype_* convention intentional in-code (no churn-rename). M5 rewrote the `research_guide` front
> door (it taught the RETIRED legacy flow!) to the canonical ESV path + pointed the entry docstrings
> (start_project/start_run) to the next step. Agent surface: 162 → 148, one graph engine, no
> destructive admin tools, a discoverable happy path. A contract-test guard keeps the retired/admin
> tools off the surface.

> User: "make the MCP genuinely cleaner, get rid of legacy. Analyze deeply, define a spec tracker."
> Findings from a full cross-reference of all **162** registered tools against actual skill/doc usage
> + their service functions + their module-file placement. Tracked as M1–M5.

## The picture
The MCP is **well-patterned** (`brief_*`/`record_*`, `get_*`/`list_*`/`delete_*`, `verb_noun`) and
modular, but it has accreted: **162 agent-facing tools**, a layer of **pre-HX3 legacy** (the old
constellation study-graph, replaced by the plan engine), a set of **admin/maintenance** tools that
don't belong in an authoring surface, **incoherent file placement** (tools live in the wrong module
files), some **naming drift**, and **no signaled happy path** (clarity depends entirely on the skills).

> Caveat from the analysis: skill-reference count flags candidates but has false positives — many
> "unreferenced" tools are legitimate and current (`derive_sections`, `score_run`,
> `brief_completeness_critic`, `simulate_day`, `recall_memory`, `get_project_graph`, …). Each item
> below was verified by its actual role, not just the grep.

---

## M1 — Retire the LEGACY constellation study-graph tools
The pre-HX3 engine built a graph of *studies* wired by *study-edges*; HX3 made the **plan** the single
engine (`add_task`/`link_evidence`/`record_frame`). These study-edge tools are referenced by **0**
skills and duplicate the plan engine — two ways to build a graph is the #1 confusion:
- `add_study_to_project`, `remove_study_from_project`, `link_studies`, `unlink_studies`,
  `set_study_themes`
- `start_methodology_project` — a pure back-compat **alias** for `start_project` (forwards verbatim).
**Action:** drop the `@mcp.tool()` registration (keep service fns only if still called internally;
otherwise delete them too — assess each). **Acceptance:** these names no longer appear in
`build_server().list_tools()`; suite + the mcp-contract test green; the plan engine is the *only*
graph-building path exposed.

## M2 — Demote ADMIN / MAINTENANCE tools to CLI-only (off the agent surface)
These are operator actions, not research authoring — they bloat the surface and a couple are dangerous
to hand an autonomous agent:
- `purge_runtime_data` (wipes personas too — known footgun), `clear_simulations`, `prune_memory`,
  `backfill_embeddings`, `backfill_project_from_syntheses`, `import_snapshot`, `export_snapshot`,
  `export_logs`.
**Action:** keep them as CLI commands / service functions; remove their `@mcp.tool()` registration (or
move behind an explicit opt-in "admin" server flag). **Acceptance:** the destructive/maintenance tools
are not in the default agent tool list; the CLI still exposes them; a test asserts the agent surface
excludes the purge/backfill family.

## M3 — Fix FILE→DOMAIN placement (tools live in the wrong module files)
The split scattered tools into unrelated files — hard to find, implies false grouping:
- `_tools_prototypes.py` currently holds `delete_council`, `delete_persona`, `delete_research_project`,
  `delete_synthesis`, `backfill_embeddings`, `prune_memory`, `remove_study_from_project`,
  `unlink_studies` — **none are prototype tools.**
- `_tools_council.py` holds `get_calendar`, `get_activity`, `export_persona`, `extract_pain_points`,
  `summarize_persona_period`, `get_current_state`, `attach_evidence` — **persona/activity tools.**
- `purge_runtime_data` sits in `_tools_simulation.py`.
**Action:** move each tool to the module that matches its domain (deletes → a single `_tools_crud.py`
or each into its domain file; persona/calendar tools → `_tools_personas.py`; etc.). Pure refactor — no
behaviour change. **Acceptance:** every tool's file matches its domain; tool count + names unchanged;
suite green. (This is dev-clarity, not user-facing, but it's why the surface *feels* accidental.)

> **Status (2026-06-05): DONE — every tool now lives in its domain file.** `delete_*` CRUD →
> `_tools_research`; `brief_month`/`record_month_bundle` → `_tools_simulation`; `brief_evidence_check`/
> `record_evidence_check` → `_tools_eval`; the persona timeline/activity reads (`get_current_state`/
> `get_calendar`/`get_calendar_period`/`get_activity`/`summarize_persona_period`/`extract_pain_points`)
> → `_tools_simulation`; `attach_evidence`/`export_persona` → `_tools_personas`. Result: `_tools_council`
> holds only council/synthesis (+ guides); `_tools_prototypes` only prototype tools. Names + count (148)
> unchanged; contract + suite green.

## M4 — Standardize NAMING drift
- Prototype tools mix prefixes: `proto_open`/`proto_read`/`proto_act`/`proto_close` +
  `list_proto_sessions` vs `run_prototype`/`scaffold_prototype`/`stop_prototype`/`get_prototype`/
  `list_prototypes`/`delete_prototype`.
- Confirm the entry verbs: `start_project` is canonical; `create_research_project` is the lower-level
  primitive it wraps.

> **Status (2026-06-05): convention MADE INTENTIONAL (not a churn-rename).** Investigation showed the
> two prefixes are actually **two coherent, deliberate families**, not drift: `proto_*` = the LIVE
> proband-SESSION verbs (`proto_open`→`proto_act`→`proto_read`→`proto_close`) a persona drives on a
> running app; `prototype_*` = the ARTIFACT lifecycle (`scaffold`/`run`/`stop`/`get`/`list`/`delete`).
> `proto_open` is a service fn AND an MCP tool AND is named in agent-facing instruction strings across
> ~10 files (plan.py, _engines.py, 3 skills, AGENTS, cli, _env, contract) — a cross-family rename of
> agent instructions is real risk for cosmetic gain, with no agent benefit (each family is already
> self-consistent and the skills name them consistently). **Action taken:** documented the convention
> in `register_prototypes`' banner so the distinction reads as intentional; `start_project` confirmed
> as the canonical entry (`create_research_project` is its lower-level primitive). **Acceptance:** the
> two families are each internally consistent + the convention is stated in-code; no rename churn.

## M5 — Signal the FRONT DOOR (the happy path, in the surface itself)
162 tools with no curated entry means clarity lives only in the skills. Make the path discoverable:
- A short, authoritative **"start here" grouping** — e.g. a `mcp_overview()`/`help` tool (or a
  docstring banner on `start_project`) listing the canonical ESV path: `start_project → start_run →
  loop run_step → derive_sections/scaffold_meta_report/score_run`, and "personas first via
  simulate-cohort".
- Tighten the **top-of-funnel docstrings** (`start_project`, `start_run`, `run_step`, `brief_council`)
  to point to the next step, so an agent can self-navigate without a skill.
**Acceptance:** from a cold start, the canonical sequence is discoverable from the tool docstrings
alone; the skills remain the richer path but are no longer the *only* source of the happy path.

> **Catalogue (2026-06-05):** added a `persona-council://guide/catalogue` resource — a browsable,
> by-domain index of EVERY tool, **auto-generated** by AST-parsing the live `_tools_*.py` modules at
> request time (so it can't drift). Domains in ESV-reading order (plan/run loop → councils →
> prototypes → … → eval), each tool with its one-line purpose; resources + prompts listed too.
> `research_guide` points to it. A contract test asserts it covers every registered tool.

---

## Net effect
Agent-facing surface drops from **162 → ~148** (M1 ≈ −6, M2 ≈ −8), the remaining tools sit in the
right files (M3), name consistently (M4), and announce their happy path (M5) — so a fresh session sees
one clear graph engine (the plan), no destructive admin tools, and a discoverable path.

## Build order
M1 (retire legacy — biggest clarity win, removes the "two engines" confusion) → M2 (demote admin) →
M3 (file placement) → M4 (naming) → M5 (front-door). Each: implement → `list_tools()` + mcp-contract +
full suite green → commit/push. Keep every change behaviour-preserving for the *kept* tools; only the
legacy/admin registrations are removed.

## Explicitly NOT touched (verified legitimate, despite low skill-references)
`attach_evidence` (attaches a SOURCE to a persona — unrelated to plan `link_evidence`),
`register_prototype` (point at an existing app vs `scaffold_prototype` which generates one),
`brief_completeness_critic`/`score_run`/`cohort_memory_depth`/`derive_sections`/`scaffold_meta_report`
(current ESV tools), the simulation authoring family (`simulate_day`/`record_day`/`recall_memory`/…),
and all `get_*`/`list_*` reads (cheap, harmless, useful for inspection).
