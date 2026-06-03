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

## CLI

```bash
persona-council persona-create "Restaurantleiterin in Deutschland, mittelgroßes Team, plant Schichten, Lieferanten, Reklamationen und Tagesabschluss, nutzt Kassensystem, Dienstplan, E-Mail und Telefon."
persona-council persona-bulk personas.md
persona-council persona-list
persona-council persona-get <persona-id-or-slug>
persona-council persona-soul <persona-id-or-slug>
persona-council persona-context <persona-id-or-slug> --task "Evaluate this idea neutrally" --text
persona-council avatar-generate <persona-id-or-slug>

persona-council simulate-day <persona-id-or-slug> --date 2026-06-02
persona-council simulate-range <persona-id-or-slug> 2026-06-01 2026-06-30
persona-council simulate-continue --all --days 1
persona-council simulate-clear
persona-council purge-runtime-data

persona-council calendar <persona-id-or-slug> --date 2026-06-02 --view day
persona-council calendar <persona-id-or-slug> --date 2026-06-02 --view week
persona-council activity <activity-id>
persona-council state <persona-id-or-slug>
persona-council summary <persona-id-or-slug> --start 2026-06-01 --end 2026-06-30

persona-council council-run "Should we change the approval workflow?" --persona <id> --persona <id>
persona-council ask <persona-id-or-slug> "What would make this unacceptable in your week?"
persona-council compare "Which workflow breaks first?" <persona-id-or-slug> <persona-id-or-slug>

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

- `create_persona`, `bulk_create_personas`, `update_persona`
- `get_persona`, `list_personas`, `get_persona_soul`
- `prepare_persona_agent_context`
- `generate_avatar`
- `simulate_day`, `simulate_range`, `continue_simulation`, `clear_simulations`,
  `purge_runtime_data`
- `get_current_state`, `get_calendar`, `get_calendar_period`, `get_activity`
- `summarize_persona_period`, `extract_pain_points`
- `select_council`, `run_council`, `record_council`, `get_council`,
  `list_councils`, `ask_persona`, `compare_personas`
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

Every tool returns an envelope `{ok, data, next_recommended_tool, _meta}`; the
`next_recommended_tool` hints the decision DAG (simulate → consolidate → digest;
council → synthesis). Full surface + conventions: `spec/mcp-tool-contract.md`.

## Skills (Claude Code)

Run `make skills` once (symlinks `claude-skills/*` into gitignored
`.claude/skills/`). Skills are thin orchestration playbooks; the methodology
lives in `spec/`.

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
