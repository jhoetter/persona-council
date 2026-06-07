# Sonaloop Specification Tracker

Last updated: 2026-06-03

This is the **single tracker** for the project: a concise spec/reference plus the
**Outstanding Work** section at the bottom (the only place open work is tracked).

## Product Intent

Build a terminal-first customer simulation system that can be operated fully via
MCP and optionally inspected through a web UI. The system should accept rough
persona descriptions, expand them into persistent customer profiles, simulate
their workdays with timestamped logs over long horizons, surface pain points and
context, and run council-style debates where simulated customers respond to a
position, product idea, workflow, feature, or pricing decision.

This is not a replacement for real customer research. Treat it as a fast
scenario-generation, empathy, and critique tool whose outputs should be marked
synthetic and validated against real customer evidence.

## Inspiration: LeonardPuettmann/ai-council

This project was inspired by Leo Püttmann's `ai-council`
(https://github.com/LeonardPuettmann/ai-council).

What it seeded conceptually:

- Markdown-defined agents are simple and effective. Leo's `council/<slug>/personality.md`
  format is a good seed for persona packs.
- The orchestrated flow is useful: select participants, collect opening
  positions, run debate rounds, draft a proposal, vote, and persist transcripts.
- Terminal ergonomics matter. The REPL, slash commands, streaming output, and
  saved Markdown/JSON transcripts are the right spirit for a tool that should be
  pleasant from the shell.
- MCP host-agent authorship is the right model for text. Sonaloop does
  not call text LLM APIs or store text-provider keys; Claude Code, Codex, or a
  similar MCP host authors structured JSON and submits it through tools.

What this project takes further:

- Agents are not only static role prompts. Customer personas carry durable
  profile state, memory, calendar, work context, relationships, goals, tools,
  frustrations, constraints, and longitudinal experience logs.
- The system is tool-callable, not just a REPL. MCP is the primary automation
  interface, with CLI and UI as clients over the same core.
- Beyond debate transcripts, it stores event logs, daily plans, reflections,
  pain-point summaries, decisions, and provenance.
- Selection supports cohorts and segments, not only "pick three advisors."
- The UI shows the same persistent state: profile, avatar, current day,
  calendar, recent logs, long-term themes, and debate history.

Note: avatar generation uses direct HTTP calls to
`https://api.openai.com/v1/images/generations`, reads `OPENAI_API_KEY` and
`OPENAI_IMAGE_MODEL`, and handles `b64_json` or URL image payloads.

## Research Baseline

Relevant ideas to incorporate:

- Park et al., "Generative Agents: Interactive Simulacra of Human Behavior"
  describe agents that keep natural-language memory, retrieve relevant memories,
  plan daily behavior, and periodically reflect. This maps directly to the
  desired profile -> workday simulation -> reflection loop.
  https://arxiv.org/abs/2304.03442
- "Humanoid Agents" extends this direction with a platform, Unity WebGL
  visualization, and analytics dashboard for agent status over time. This
  supports building a simple web observer over a terminal/MCP core.
  https://arxiv.org/abs/2310.05418
- Agent-based modeling with LLMs is useful for complex social simulations, but
  needs explicit environment constraints and evaluation, not pure freeform
  prompting.
  https://huggingface.co/papers/2308.07411
- Recent synthetic UX/persona work emphasizes grounding personas in evidence,
  psychology, and anti-sycophancy controls. For this product, every persona
  should carry provenance and uncertainty, and council responses should be
  adversarial rather than agreeable by default.
  https://papers.ssrn.com/sol3/Delivery.cfm/6503241.pdf?abstractid=6503241
- Recent papers and UX discussion warn that synthetic users can sound coherent
  while failing to represent real human behavior. The product must label output
  as simulated, preserve assumptions, and encourage comparison to real customer
  interviews, support tickets, sales notes, and usage data.
  https://www.sciencedirect.com/science/article/pii/S1071581925002034
- Simulation must be non-directional. Personas may not be nudged toward AI,
  automation, or any product thesis unless their source description, evidence,
  recent calendar, or explicit task context supports it. Product and repository
  names are not evidence.
- OpenAI's current image generation docs list GPT Image models including
  `gpt-image-1.5`, `gpt-image-1`, and `gpt-image-1-mini`; use `gpt-image-1.5`
  for optional avatar generation when `OPENAI_API_KEY` is configured.
  https://platform.openai.com/docs/guides/image-generation

## Core Architecture

Principle: one core state model, many interfaces.

- `core/`: persona schema, simulation engine, memory retrieval, council
  orchestration, storage adapters.
- `mcp_server/`: MCP tools exposing every important operation.
- `cli/`: terminal commands and optional REPL. Thin client over `core`.
- `web/`: lightweight UI for browsing personas, calendars, logs, pain points,
  and council sessions. Thin client over API/core state.
- `data/`: SQLite database, generated avatars, exported transcripts.
- `personas/`: source markdown/persona packs, including bulk input files.

First storage target: SQLite. It is cron-friendly, terminal-friendly, easy to
inspect, and sufficient for the initial long-running simulations.

## Data Model

### Persona

Required fields:

- `id`, `slug`, `display_name`
- `source_description`: original user input
- `provenance`: what was user-provided vs inferred
- `segment`: customer type, company type, job family, geography
- `demographics`: only when useful and not over-specified
- `role`: title, responsibilities, seniority, decision power
- `company_context`: industry, size, stack, operating model
- `goals`: professional goals and near-term objectives
- `constraints`: budget, time, politics, regulation, team capacity
- `tools`: software/hardware/workflows used
- `relationships`: stakeholders, team, vendors, customers
- `personality`: working style, communication style, risk tolerance
- `pain_points`: persistent frustrations and triggers
- `success_criteria`: how this persona evaluates a product or workflow
- `avatar`: optional image path and prompt
- `created_at`, `updated_at`

### Memory and Logs

Use separate event and reflection records.

- `experience_event`: timestamped atomic event, e.g. meeting, task, context
  switch, defect, customer call, procurement step, training moment, workaround.
  Each event records whether the persona worked alone, met with others, was
  interrupted, made a decision, left open loops, and what they were thinking.
- `calendar_event`: structured meeting/task block with start/end, title,
  participants, location/tool, intent, outcome.
- `daily_summary`: generated at end of simulated day with mood, work completed,
  blockers, open loops, pain points, and notable memories.
- `reflection`: periodic higher-level synthesis after N events or days.
- `pain_point_observation`: extracted issue with severity, frequency, evidence
  event IDs, affected workflow, and possible product opportunity.

### SOUL.md

Every persona has a durable `personas/<slug>/SOUL.md` file. It is the simulation
identity document and includes identity, work context, inner operating system,
daily reality, frictions, motivations, relationships, voice, simulation rules,
current state, recent thoughts, and recent reflections.

### Council Session

- `session_id`
- `prompt`
- `persona_ids`
- `selection_reason`
- `turns`: speaker, timestamp, content, references to memories used
- `proposal`
- `votes`
- `summary`
- `created_at`

## MCP Tool Specification

All functions should be callable by MCP first. CLI and web routes wrap these.

### Persona Tools

- `create_persona(description, segment_hint?, evidence?, generate_avatar?)`
  expands one rough description into a structured persona.
- `bulk_create_personas(descriptions, segment_strategy?, generate_avatars?)`
  creates many personas from short inputs.
- `get_persona(persona_id)`
  returns profile, source/inferred split, and current state.
- `get_persona_soul(persona_id)`
  returns the persona's `SOUL.md` path and content.
- `prepare_persona_agent_context(persona_id, task?, recent_events?)`
  returns the required subagent launch packet: `SOUL.md`, current state, recent
  lived events, and operating rules. This is the MCP workflow guarantee that a
  persona-grounded subagent has read the persona's durable soul before acting.
- `list_personas(filters?)`
  lists personas by segment, company, role, pain point, or activity.
- `update_persona(persona_id, patch, reason)`
  updates profile fields while preserving an audit trail.
- `generate_persona_avatar(persona_id, style?)`
  creates or refreshes avatar using configured image model.

### Simulation Tools

- `simulate_day(persona_id, date?, timezone?, seed?, constraints?)`
  generates a realistic calendar and event log for one workday.
- `simulate_range(persona_id, start_date, end_date, cadence?, seed?)`
  simulates multiple days with reflection checkpoints.
- `continue_simulation(persona_id, days=1)`
  cron-friendly function that advances from the last simulated date.
- `clear_simulations()`
  clears generated calendar, activity, summary, reflection, pain, and council
  state while keeping personas, evidence, avatars, and audit trail.
- `purge_runtime_data(remove_files=true)`
  clean-slate reset for MCP/CLI: clears personas, evidence, simulations,
  councils, audit rows, generated avatars, and generated `SOUL.md` files.
- `get_current_state(persona_id, at_time?)`
  answers what the persona is doing, feeling, blocked by, and likely to do next.
- `get_calendar(persona_id, date?)`
  returns calendar blocks joined to activity logs and thoughts.
- `get_activity(activity_id)`
  returns a single activity with participants, what happened, inner thought,
  decision, mood, pain points, and open loops.
- `summarize_persona_period(persona_id, start_date, end_date, lens?)`
  summarizes activity, pain points, themes, and changes over time.
- `extract_pain_points(persona_id, start_date?, end_date?)`
  derives pain-point observations from events and reflections.

### Council Tools

- `select_council(prompt, filters?, count=3, disagreement_goal?)`
  uses the LLM to pick personas from candidate summaries whose viewpoints
  should produce useful disagreement.
- `run_council(prompt, persona_ids?, filters?, rounds=3, context?)`
  runs debate, proposal, vote, and summary.
- `ask_persona(persona_id, question, context?)`
  one-on-one persona interview grounded in profile and memories.
- `compare_personas(prompt, persona_ids, output_format?)`
  contrast viewpoints across a selected cohort.

### Evidence and Export Tools

- `attach_evidence(persona_id, source_type, content_or_path, notes?)`
  stores real customer evidence that future simulations can retrieve.
- `export_persona(persona_id, format=json|md)`
- `export_logs(persona_id, start_date, end_date, format=json|csv|md)`
- `export_council_session(session_id, format=json|md)`

## Simulation Loop

For each simulated day:

1. Retrieve persona profile, recent events, unresolved loops, long-term goals,
   calendar patterns, and relevant reflections.
2. Generate a plausible daily plan with meetings, focused work, interruptions,
   context switches, external dependencies, and recovery time.
3. Expand the plan into timestamped events. Code provides the scaffold
   (timestamps, activity kind, allowed tools, participants, constraints, SOUL.md,
   recent memories). The LLM writes the lived content: what happened,
   conversation snippets, key quotes, actions done, artifacts touched, inner
   thoughts, decisions, open loops, mood, and pain points.
4. Apply consistency checks: no impossible overlaps, weekends/holidays handled,
   reasonable work hours unless persona context justifies overtime.
5. Generate end-of-day summary and update current state.
6. Every N days/events, generate reflections and consolidate recurring pain
   points.

Important: the model should not invent wildly dramatic events unless the
persona context supports them. Most customer insight will come from mundane,
repeated friction. Ordinary work, skepticism, indifference, satisfaction, and
rejection are all valid simulated outcomes; avoid vendor-friendly narratives by
default.

Hardcoded dialogue templates are not allowed for simulation. If LLM generation
or validation fails, the simulation command must fail rather than write
placeholder events.

## Web UI Scope

The web UI is an inspection surface, not a control surface and not the source of
truth. It must not create personas, run simulation, generate avatars, or run
councils. Those operations are terminal/MCP-only and documented outside the UI.

Initial views:

- Personas index: searchable table/cards with segment, role, company, current
  status, top pain points, last simulated date.
- Persona detail: profile, avatar, inferred-vs-provided fields, goals,
  constraints, tools, relationships.
- Calendar/log view: day/week/month timeline with meetings, work blocks,
  interruptions, pain point markers, and daily summaries.
- Calendar/log view also supports a year overview of already-simulated events;
  year view does not imply every day in the year must be simulated.
- Pain point dashboard: recurring issues by frequency/severity, evidence event
  links, affected personas/segments.
- Council session view: prompt, selected personas, debate turns, proposal,
  votes, dissent, export.

Frontend should stay utilitarian: dense, readable, and built for scanning. Avoid
marketing-style layout; this is an operating tool.

## Extension Seams (downstream packages)

The public core is consumed by two PRIVATE packages — `sonaloop-cloud` (SaaS
control-plane: auth/billing/multi-tenancy + pro pages) and `sonaloop-research`
(done-for-you study service). They build on the core WITHOUT it ever importing
them. The seams live in `sonaloop/web/_ext.py` and are re-exported from
`sonaloop.web`. With zero extensions installed the core renders bit-identically —
every seam is a no-op when unused (guarded by tests).

Four seams:

1. **Routes** — `entry_points(group="sonaloop.web.extensions")`; each entry resolves
   to a callable run as `setup(app)` in `create_app()` after the core routes
   (`load_extensions(app)`). A failing extension is logged and skipped, never
   breaking core boot.
2. **Nav** — `register_nav_section()` / `register_nav_item()`; the sidebar iterates
   the registry. The core seeds its OWN sidebar through the same API
   (`web/_nav_seed.py`) — no privileged path. Labels are `str | Callable[[], str]`
   (use a lambda for per-request i18n). Sections/items ordered by `order`.
3. **Slots** — `register_slot(name, fn)`; `_layout()` renders named insertion points
   (`head_extra`, `sidebar_extra`, `body_end`). `fn(store) -> HTML`.
4. **Theme** — `set_theme_overrides(mapping)` / `reset_theme_overrides(token)`: a
   per-request contextvar (mirrors the i18n `_UI_LANG` pattern). `_layout()` injects
   a SANITIZED `:root` override of CSS custom properties, so a tenant/project can
   carry its own design-system colors. Pure SSR — nothing leaks into JS or `data-*`.
   Keys must match `--[a-z0-9-]+`, values a safe color/token subset; off-shape
   declarations are dropped.

Design decision (locked): NO Jinja2 migration. The single `_layout()` string-builder
already is the one shell-assembly point Jinja would provide; the seams above give
downstream packages everything they need without rewriting the render layer.

## Terminal and Cron UX

Target commands:

```bash
sonaloop persona create "Restaurantleiterin in Deutschland, mittelgroßes Team, plant Schichten, Lieferanten, Reklamationen und Tagesabschluss, nutzt Kassensystem, Dienstplan, E-Mail und Telefon."
sonaloop persona bulk personas.md
sonaloop simulate day anna-schmidt --date 2026-06-02
sonaloop simulate continue --all --days 1
sonaloop persona state anna-schmidt
sonaloop council run "Should we price this as seat-based SaaS?" --segment architects
```

Cron example:

```cron
15 6 * * 1-5 cd /path/to/sonaloop && uv run sonaloop simulate continue --all --days 1
```

## Avatar Generation

Optional function. Do not block persona creation on image generation.

Inputs:

- persona profile summary
- desired style, default "professional editorial headshot/avatar"
- optional uploaded reference image later

Outputs:

- stored image file under `data/avatars`
- prompt used
- model used
- generation timestamp

Config:

- `OPENAI_API_KEY` for avatar image generation only
- `OPENAI_IMAGE_MODEL`, default `gpt-image-1.5`
- `AVATAR_OUTPUT_DIR`

Text generation config:

- No text API keys. Text is authored by the MCP host agent and submitted as
  structured JSON for validation and persistence.

## Implemented Files

- `sonaloop/models.py`: structured data objects.
- `sonaloop/storage.py`: SQLite persistence.
- `sonaloop/services.py`: tracker functions and LLM-authored simulation orchestration.
- `sonaloop/avatar.py`: OpenAI Image API avatar generation.
- `sonaloop/cli.py`: terminal entrypoint.
- `sonaloop/mcp_server.py`: MCP tool server.
- `sonaloop/web.py`: FastAPI dashboard and JSON API.
- `tests/`: pytest suite — MCP contract/envelope, gather→author→write-back
  round-trip, seeded-scaffolding regression, cohort diversity + critic tunables.

## Outstanding Work — complete ✅

The core system was already built (persona store, LLM-authored simulation loop,
persistent memory, council orchestration, iterative synthesis, LLM critic,
evidence checks, cohort driver skill, web inspector). The remaining testing,
reproducibility, and quality items are now implemented:

**Testing & reproducibility**
- [x] Integration tests for the MCP tool calls (gather → author → write-back) —
      `tests/test_mcp_contract.py` (tool registration + envelope) and
      `tests/test_gather_author_writeback.py` (persona → council → synthesis →
      evidence → cohort critic round-trip on a temp DB, no network).
- [x] Regression fixtures for stable, seeded simulation scaffolding —
      `tests/test_seeded_scaffolding.py` (golden RNG stream + reproducible,
      seed-sensitive `simulate_day` scaffolding).

**Quality & validation**
- [x] Diversity and consistency checks for bulk persona generation —
      `evaluation.evaluate_cohort_diversity` (Jaccard over segment/role/pains/
      goals/tools; flags near-duplicate pairs + implausibly uniform cohorts);
      CLI `cohort-diversity`, MCP `evaluate_cohort_diversity`.
- [x] Source/evidence citations inside generated conclusions — `brief_synthesis`
      surfaces attached evidence + recall hits with ids (`frame.provenance`); the
      synthesis carries a validated `citations` field, rendered in the report.

**Enhancements**
- [x] Cohort-wide critic cross-comparison — `brief_cohort_critic` /
      `record_cohort_critic` (flags personas out of the cohort's range, persists
      anomalies); CLI + MCP wired.
- [x] Tunable LLM-critic threshold + sample size — `config.critic_threshold()` /
      `config.critic_sample_k()` (env `PERSONA_COUNCIL_CRITIC_THRESHOLD` /
      `_CRITIC_SAMPLE_K`), threaded through brief/record_eval_critic.

Run the suite with `make test` (pytest, `dev` dependency-group) or `make test-smoke`.

## Quality Bar

- Every generated artifact must preserve provenance: input, model, prompt class,
  timestamp, seed when applicable.
- Seeds may stabilize calendar scaffolding, but lived activity content must be
  LLM-authored and must not fall back to deterministic placeholder text.
- Persona outputs should include uncertainty instead of pretending all inferred
  details are known.
- Council debates should include dissent and tradeoffs, not only consensus.
- The web UI must never become required for core operation.
