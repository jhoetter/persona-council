# Persona Council Agent Guide

Persona Council is terminal-first and MCP-first. The web UI is an inspection
surface only.

## Principles

- Do not infer product interest from the repository name, app name, or the fact
  that this is a council tool.
- Do not steer profiles toward AI, automation, or any other product thesis
  unless the profile source description, attached evidence, recent calendar, or
  explicit task context supports it.
- Treat synthetic details as hypotheses. Prefer ordinary work, skepticism,
  indifference, satisfaction, and rejection when those are plausible.
- Before speaking from a profile perspective, load `SOUL.md` through
  `prepare_persona_agent_context` or `persona-council persona-context`.
- Use CLI/MCP for all mutations: create profiles, generate avatars, simulate
  days, attach evidence, run councils, clear simulations, and export logs.
- Point the user to the web inspector as soon as there is something to see. Once
  personas/councils/syntheses exist, tell them to open **http://127.0.0.1:8787**
  (start it with `make dev`, or `persona-council-web`, which prints the URL). The
  web UI is read-only; all authoring still happens through CLI/MCP.
- Language: generated CONTENT follows the language the user writes in, auto-
  detected on first input and persisted (de|en). Do not switch languages
  mid-stream. The web UI language is independent (toggle in the top bar, or
  `set_language`/`set-language`). Override content language only if asked.

## CLI

```bash
# Persona creation is host-authored (no server-side text generation):
# gather -> you author the profile JSON -> persist.
persona-council brief-persona "Restaurantleiterin in Deutschland, mittelgroßes Team, plant Schichten, Lieferanten, Reklamationen und Tagesabschluss, nutzt Kassensystem, Dienstplan, E-Mail und Telefon."
persona-council record-persona profile.json   # JSON: {description, profile, segment_hint?, evidence?, generate_avatar?}
persona-council persona-list
persona-council persona-get <persona-id-or-slug>
persona-council persona-soul <persona-id-or-slug>
persona-council persona-context <persona-id-or-slug> --task "Evaluate this idea neutrally" --text
persona-council avatar-generate <persona-id-or-slug>

# Single day, host-authored: brief-day -> author {day_plan, plan, activities} -> record-day.
persona-council brief-day <persona-id-or-slug> --date 2026-06-02
persona-council record-day <persona-id-or-slug> 2026-06-02 day.json
persona-council simulate-continue --all --days 1
persona-council simulate-clear
persona-council purge-runtime-data

persona-council calendar <persona-id-or-slug> --date 2026-06-02 --view day
persona-council calendar <persona-id-or-slug> --date 2026-06-02 --view week
persona-council activity <activity-id>
persona-council state <persona-id-or-slug>
persona-council summary <persona-id-or-slug> --start 2026-06-01 --end 2026-06-30

# Councils & interviews are host-authored (see the run-council skill):
#   brief-council <prompt>                 -> candidate personas to choose from
#   brief-council <prompt> --persona <id>… -> each participant's loaded context
#   (author turns + synthesis) -> record-council council.json
persona-council brief-council "Should we change the approval workflow?" --persona <id> --persona <id>
persona-council brief-ask <persona-id-or-slug> "What would make this unacceptable in your week?"

# Language: content is auto-detected from what you write, then persisted (de|en).
persona-council language
persona-council set-language --content de --ui en

persona-council evidence-attach <persona-id-or-slug> interview notes/interview-01.md --notes "Customer interview"
persona-council export-logs <persona-id-or-slug> --format md --out exports/logs.md
persona-council export-council <session-id> --format md --out exports/council.md
```

## MCP

Run:

```bash
persona-council-mcp
```

Core MCP tools:

- `brief_persona` (gather) → `record_persona` (persist authored profile), `update_persona`
- `get_persona`, `list_personas`, `get_persona_soul`
- `prepare_persona_agent_context`
- `generate_avatar`
- `brief_day` → `record_day` (host-authored single day); `record_month_bundle` for
  months; `continue_simulation`, `clear_simulations`, `purge_runtime_data`
- `get_current_state`, `get_calendar`, `get_calendar_period`, `get_activity`
- `summarize_persona_period`, `extract_pain_points`
- `brief_council` (gather candidates/contexts) → `record_council` (persist authored
  turns + synthesis), `get_council`, `list_councils`, `brief_ask`
- `get_language`, `set_language` (UI + generated-content language, de|en)
- `attach_evidence`
- `export_persona`, `export_logs`, `export_council_session`

Memory & multi-resolution simulation (gather → author → write-back):

- Planning: `brief_day`/`put_day_plan`/`get_day_plan`,
  `brief_period`/`put_period_plan`/`get_period_plan`/`list_period_plans`
- Consolidation: `brief_consolidation`/`record_memory_deltas`
- Digests: `brief_digest`/`put_digest`/`list_digests`
- Retrieval/inspection: `recall_memory` (hybrid: keyword + OpenAI embeddings),
  `list_active_projects`, `get_project`, `get_state_at` (time-travel),
  `get_timeline`, `search_entities`, `get_open_loops`, `resolve_entity`,
  `get_persona_memory`
- World/evolution/quality: `set_world_context`/`get_world_context`,
  `brief_persona_revision`/`record_persona_revision`/`list_persona_revisions`,
  `evaluate_simulation`, `brief_eval_critic`/`record_eval_critic`/
  `evaluate_simulation_full`, `list_memory_anomalies`, `backfill_embeddings`,
  `prune_memory`
- Driver: `brief_month`/`record_month_bundle`
- Synthesis (study arc over a council chain = an **analysis**: question → council
  loop → synthesis report): `brief_synthesis`/`record_synthesis`/`get_synthesis`/
  `list_syntheses`/`export_synthesis`. `brief_synthesis` returns per-persona turns +
  votes per council; author the structured **`voices`** array in the payload (one per
  persona: `sentiment`, `relevance`/tangiert, `key_argument`, `shift`{from,to,trigger,
  council_id}, `evidence`[{council_id,quote}]) — this powers the report's filterable
  Stimmen panel and the self-contained `export_synthesis` (md/json) for downstream agents.
- Portability: `export_snapshot`/`import_snapshot` (data/export is the one
  portable artifact; it is gitignored/local-only, as is the SQLite DB runtime)
- Research-plan engine — the SINGLE runtime engine (structure-enforcing + LLM-judged; ZERO hardcoded
  vocabularies): a per-project DAG of analyze→act→verify **tasks**, each bound to a free `capability`
  and referencing the evidence it produced. `start_project` (freeform: one root `frame` task; or
  `methodology=…`: seed the constellation), then the per-iteration loop `next_action`/`brief_next` →
  author the step → `add_task`/`record_frame`/`link_evidence`/`record_judgment`(free `gate_tag`) →
  `complete_task`, with `assess_project`/`assess_progress` for the read-only meta-assessment.
  Tag-agnostic: it enforces only the DAG (`consumes`), integer `min_inputs`, tag-equality references,
  and evidence-backed judgment PRESENCE — never tag membership. Shape (diverge/converge/diamonds/
  branches/loops) is DERIVED from the task DAG + recorded evidence.
- ESV — exhaustive, self-verifying runs (`spec/exhaustive-self-verifying-runs.md`). The autonomous loop
  is a **deterministic RunLoop engine** the host skill executes: `start_run`(resumable run object +
  journal) → loop `run_step` (the brain: assess + next_action + the deterministic finish work + the
  critic gate) → spawn ONE subagent per dispatch → `checkpoint_step`. "Done" ≠ "gates passed": a run is
  only `complete` when `assess_project.finish` is **finished** (organized via `derive_sections` +
  concluded + handed-off via `scaffold_meta_report`/meta-report) AND an INDEPENDENT
  **completeness critic** (`brief_completeness_critic`→`record_completeness_critic`, rubric in
  `suggestions/critic_rubric.json`) passes — it lists concrete `missing` work (un-sampled segments,
  un-prototyped concepts, untested risks, missing fidelity rungs), the driver injects each as real work
  (`inject_work`) and re-runs until dry (K=2, hard cap 4). `assess_project` also surfaces `novelty`,
  `memory_depth` (thin cohorts → deepen via simulate-cohort), and `score_run` tracks quality over time.
  Concepts are first-class (`create_note kind="concept"` {lens, artifact_kind, prototype_id}). Resumable
  via deterministic keys; a killed run replays its journal with zero lost work.
- Methodologies = tag-driven CONSTELLATION **plan seeds**: a methodology is a DAG of steps carrying
  OPEN TAGS (capability/role/artifact-type/gate are free strings). `list_methodologies`/
  `get_methodology`/`start_methodology_project`/`set_project_methodology` SEED a plan from the
  constellation (a `frame` analyze task per fan step, a gated `verify` task per decide step); the plan
  engine then drives it. Common building blocks are SUGGESTED as data via `suggest_capabilities`/
  `suggest_roles`/`suggest_artifact_types`/`suggest_methodologies` — recommendations, not constraints;
  adopt, tweak, or invent your own tags. Authoring a new methodology = author a constellation of
  tagged steps in JSON (no code). Since HX3 there is ONE engine (the plan); the old constellation
  runtime (`record_node`/`record_decision`/`advance`/`get_methodology_state`) was retired — see
  `spec/hx3-engine-collapse.md`. Specs: `spec/methodology-constellations.md`, `spec/research-plan-engine.md`.
- Prototypes (real, minimal, local apps agents can use): `scaffold_prototype` (concept→clickable
  SPA), `register_prototype`, `list_prototypes`, `run_prototype`/`stop_prototype`; the Playwright
  harness `proto_open`/`proto_act`/`proto_read`/`proto_close` lets a persona drive the REAL app,
  and `brief_prototype_session`/`record_prototype_session` fold the grounded reaction into memory.
  Artifact archetypes are DATA (`suggestions/artifact_types.json`, surfaced as the `artifact_palette`
  in `next_action`): a guided `flow`, a `comparison`, a `dashboard`, a `cards` interface, or an
  interactive **`model`** (range/number inputs feeding `computed`/`bar` elements whose `formula` is
  evaluated live — a steerable pension-gap/compounding simulation, not a static screen), or a
  **`journey`** (a model embedded in a multi-screen flow with cross-screen state + `chart` live curves
  + `verdict` data-driven conditional text — the production-credible hi-fi class) — diversify the KIND,
  don't default to a form. `record_prototype_session` returns an `UNVERIFIED_SESSION`
  warning (and a session_of_tags gate requires a GROUNDED session) when a reaction isn't verified
  against real observed usage — the session log is retained past `proto_close` so a real drive verifies.
  Install with `make playwright` (optional; degrades gracefully without chromium).
- Composable graph — the graph is a canvas of composable LOW-LEVEL primitives (council · synthesis ·
  prototype · **note** · edge · **section**); the methodology/plan engine is ONE optional orchestrator,
  not the only structure (spec/sections-and-composable-graph.md):
  - **Sections** = methodology-INDEPENDENT labeled overlay groupings of nodes ("Initial user research",
    "Problem exploration"). Explicit set-membership (overlap allowed), a pure overlay (never alters the
    DAG layout), reference-not-containment (deleting a section never deletes nodes), `kind` an open tag
    (theme/phase/invented, data-driven via `section_kinds.json`). `create_section`/`update_section`/
    `add_to_section`/`remove_from_section`/`set_section_members` (promote-a-cluster)/`reorder_sections`/
    `list_sections`/`get_section`/`delete_section`/`get_section_members`/`export_section` (md/json,
    self-contained) + `suggest_section_kinds`. Methodology phases render as DERIVED `phase` sections.
  - **Notes** = lightweight first-class observation nodes (the atomic unit for affinity), creatable with
    NO methodology: `create_note`/`list_notes`/`delete_note`. They are normal graph nodes (groupable
    into sections, linkable by edges).
  - **Syntheses are DECOUPLED from councils**: a synthesis can have zero councils (affinity over notes,
    a synthesis over other syntheses, a standalone analysis); councils are cited, not owned.

Every tool returns an envelope `{ok, data, next_recommended_tool, _meta}`; the
`next_recommended_tool` hints the decision DAG (simulate → consolidate → digest;
council → synthesis). Full surface + conventions: `spec/mcp-tool-contract.md`.

## Skills (Claude Code)

Run `make skills` once (symlinks `claude-skills/*` into gitignored
`.claude/skills/`). Skills are thin orchestration playbooks; the methodology
lives in `spec/`.

- `methodology-run` — drive a plan-based methodology constellation (Double Diamond, d.school
  micro-cycle, Lean/JTBD, … or any you author) over the graph via the analyze→act→verify plan loop:
  genuinely fan out act tasks (real councils / built+tested prototypes) then converge behind an
  evidence-backed gate (`record_judgment` + a `record_synthesis`), incl. build/test steps where
  personas USE a real app via Playwright. The plan engine enforces the shape; you author the text.
  Specs: `methodology-constellations.md`, `research-plan-engine.md`.
- `simulate-cohort` — run the day/period loop for personas over months (sampling).
- `run-council` — memory-grounded council; judicious self-research (recall only
  when it sharpens the answer); optional moderated back-and-forth with mediator
  strategies (`positive-deepdive`, `pain-discovery`, `tension`, `goal`) and a
  hand-raising convergence loop + upper bound.
- `synthesize` — iterative driver: one statement → councils → read each exec
  summary → decide a follow-up (self-contained question, personas are
  council-stateless) or stop (goal reached / no follow-up / max 10) → report.

## Persona-Subagent Workflow

1. Call `prepare_persona_agent_context(persona_id, task, recent_events)`.
2. Verify `soul_loaded=true`.
3. Use the returned `agent_context` as the launch context for the subagent.
4. Ground responses in the loaded SOUL, recent events, evidence, and task.
5. If the context does not support a product-friendly answer, the profile should
   be skeptical, neutral, or rejecting.

## Simulation Quality

- Good simulations include timestamped activities, concrete tools/artifacts,
  realistic conversations, internal thoughts, decisions, unresolved loops, and
  emotional/energy shifts.
- Persona answers and council turns are LLM-authored through MCP/service calls;
  they must load `SOUL.md` via `prepare_persona_agent_context`.
- Council selection is LLM-authored from candidate persona summaries. Do not
  choose participants with fixed keyword scoring or product-topic assumptions.
- A meeting should contain enough conversation to understand what happened, not
  just one summary quote.
- A workday should include mundane friction and normal progress, not only
  problems.
- Calendar continuity matters: unresolved loops should influence later days.
