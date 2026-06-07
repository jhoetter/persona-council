---
name: simulate-cohort
description: Drive Sonaloop's full simulation loop for one or more personas over a span of months, with memory, sampling, and quality gates. Use when asked to simulate/continue a cohort over time (e.g. "simulate Q4 for all personas", "run 3 more months for Carla").
---

# simulate-cohort

Model-neutral driver for the agentic loop in
`spec/memory-and-simulation-architecture.md`.
The life-simulation is HOST-AUTHORED: there is NO in-process simulation engine —
YOU (the MCP host) author every day/month; the server only gathers context,
persists, and gates. Tools are MCP (`mcp__sonaloop__*`) or the equivalent
CLI (`.venv/bin/sonaloop …`).

## Inputs
- personas: one slug, a list, or "all" (→ `list_personas`).
- months: e.g. `2026-09 … 2026-11` (process oldest → newest so each chains).

## One day (host-authored, no engine)
For a single concrete day: `brief_day(slug, date)` → gathers active projects, open
threads, recall + world context and returns a `day_bundle_hint`. YOU author the
`day_plan` + per-block `activities` + `deltas`, then
`record_day(slug, date, day_plan, plan, activities, deltas, workday_start_hour, seed)`
persists it end-to-end. (There is no `simulate_day`/`simulate_range`/
`continue_simulation` — the host authors the day.)

## Loop (per persona, per month, oldest first)
1. **Gather:** `brief_month(slug, month)` → returns SOUL, active projects, open
   threads, the prior month's digest, world context.
2. **Author a month bundle** grounded in that briefing — JSON:
   ```
   {period_plan:{summary,intentions,expected_milestones,mood_trajectory,sample_days[3-4]},
    days:[{date, workday_start_hour, seed, day_plan{...}, plan{mood_forecast,blocks[5-8]},
           activities{<title>:{what_happened,conversation,key_quotes,actions_done,
           artifacts_touched,persona_thought,decision,open_loops,mood,energy_delta,pain_points}},
           deltas{entities,facts,threads,event_links}}],
    digest:{text,themes,project_arcs,trends}}
   ```
   Rules (hard): continue the SAME projects with progressing status (set
   `invalidates` on status change); use EXACT persona `tools`/`pain_points`; vary
   start hours + block counts; realistic done/open mix; pick sample_days that show
   an arc (routine + conflict + milestone, not only drama); **anti-steering** — no
   ungrounded product/tool enthusiasm.
3. **Persist:** `record_month_bundle(slug, month, bundle)` — host-authored, no
   engine: runs `put_period_plan` → per sample day `record_day` (put_day_plan +
   the authored activities) → `brief_consolidation`/`record_memory_deltas` per day
   → `put_digest` → embeddings. (For a freestanding consolidation pass:
   `brief_consolidation(slug, date)` → author deltas → `record_memory_deltas`.)
4. **Quality gate (after each persona's span):**
   - `evaluate_simulation(slug)` — structural (must be 0 reds).
   - `brief_eval_critic(slug)` → author verdict → `record_eval_critic` (semantic).
   - `evaluate_simulation_full(slug)` → require `top=true`. If not, regenerate the
     flagged month(s)/day(s) and re-gate.
5. Optional drift: `brief_persona_revision`/`record_persona_revision` (rare,
   evidence-backed).

## Scale / parallelism
Within one month, persona bundles are independent → author them in parallel
(subagents), then persist sequentially. Across months, go oldest→newest so
`brief_month` sees the prior digest. Idempotent: stable IDs make re-runs safe.

## Done
Every targeted persona returns `evaluate_simulation_full(slug).top == true`
(structural 0 reds AND all critic dimensions ≥ 4). Report project arcs via
`get_state_at` / `get_project` at period ends.
