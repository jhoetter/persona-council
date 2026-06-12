# Architecture

Sonaloop is an MCP server for customer-persona simulation, councils, and design-research
synthesis. Personas are persistent agents with durable `SOUL.md` files, timestamped
calendars, experience logs, and a bi-temporal memory graph. The defining constraint:
**the host agent authors all text — there are no server-side text-LLM calls.** Every
generative step follows the same contract: `brief_*` (server gathers context) → host
authors JSON → `record_*` / `put_*` (server validates and persists).

This file is the orientation map for new developers. Deeper, evolving design notes live
in [`spec/`](spec/) (notably `memory-and-simulation-architecture.md`,
`planning-and-evidence-architecture.md`, `component-ssr-architecture.md`) and the
agent-facing contracts in [`docs/`](docs/README.md).

## Ecosystem

Sonaloop core is the open-core hub. Private packages plug in via Python entry-point
groups; sibling repos feed it data, design assets, and documentation.

```mermaid
flowchart TD
    subgraph plugins["Private plugins via entry points"]
        CLOUD[sonaloop-cloud<br/>tenancy, pro pages]
        RESEARCH[sonaloop-research<br/>research extensions]
    end

    subgraph assets["Data & design inputs"]
        DATA[sonaloop-data<br/>curated persona catalog]
        DESIGN[sonaloop-design<br/>tokens, icons, component CSS]
    end

    CORE["sonaloop core<br/>MCP server + CLI + web inspector"]

    subgraph surfaces["Public surfaces"]
        WEBSITE[sonaloop-website<br/>marketing SPA]
        DOCS[sonaloop-docs<br/>canonical user docs, mkdocs]
    end

    subgraph ops["Meta / ops"]
        TRACKER[sonaloop-tracker<br/>cross-repo ticket board + MCP]
        HETZNER[sonaloop-hetzner<br/>dev-box provisioning]
    end

    CLOUD -- "sonaloop.web.extensions<br/>sonaloop.hooks<br/>sonaloop.mcp.tools" --> CORE
    RESEARCH -- "same entry-point groups" --> CORE
    DATA -- "load_into / pull_remote<br/>catalog_search, catalog_recommend,<br/>catalog_status, catalog_pull" --> CORE
    DESIGN -- "vendored py modules + make icons<br/>_icons.py, _tokens.py, _charts.py, _deck.py" --> CORE
    DESIGN -- "shared React blocks + tokens" --> WEBSITE
    DATA -- "sync-personas script" --> WEBSITE
    CORE -- "product docs land here first" --> DOCS
    TRACKER -.-> CORE
    HETZNER -.-> CORE
```

Integration mechanics:

- **Entry-point groups** — core discovers plugins via `importlib.metadata`, never
  imports them directly: `sonaloop.mcp.tools` (loaded in `mcp_server/__init__.py`),
  `sonaloop.web.extensions` (loaded in `web/_ext.py`), `sonaloop.hooks` (loaded in
  `services/_hooks.py`).
- **sonaloop-data** is an optional lazy import. If absent, `mcp_server/_tools_catalog.py`
  falls back to a small stdlib-urllib client against the published catalog
  (`manifest.json`, `packs/<id>.json`, `personas/<slug>/…`), so browse + pull work
  from any install.
- **sonaloop-design** is vendored, not depended on: `make icons` syncs `_icons.py` /
  `_tokens.py` from `../sonaloop-design`; `make check-icons` runs as a pre-push hook
  to catch drift.

## Core repo layers

Three entry points share one service layer over one SQLite store.

```mermaid
flowchart TD
    subgraph entries["Entry points"]
        CLI["cli.py<br/>sonaloop console script"]
        MCP["mcp_server/<br/>stdio MCP, 31 tool modules"]
        WEB["web/<br/>FastAPI SSR inspector on :8787<br/>bilingual de/en, SSE live view"]
    end

    subgraph services["services/ — 39 domain modules"]
        CORE_SVC["personas · simulation · councils<br/>synthesis · surveys · hypotheses<br/>decisions · usability sessions"]
        RESEARCH_SVC["research plan engine<br/>_engines.py + _research.py<br/>analyze / act / verify DAG"]
        QUALITY_SVC["grounding · predictions<br/>calibration · coverage · evaluation"]
        STRUCT_SVC["sections · substrate<br/>project assets · snapshots · hooks"]
    end

    subgraph storage["storage/ — SQLite, WAL mode"]
        STORE["Store = StoreBase + 15 mixins<br/>42 tables: personas, runs, evidence,<br/>councils, syntheses, artifacts, events…"]
        DB[("data/sonaloop.db")]
    end

    subgraph side["Side subsystems"]
        MEMORY["memory graph<br/>entities · bi-temporal facts<br/>threads · embeddings"]
        BROWSER["browser.py<br/>Playwright harness<br/>screenshots + PDF"]
        ARTIFACTS["artifacts.py<br/>artifact validation"]
        AUTHORING["llm_simulation/<br/>authoring validators<br/>_prompts · _schemas · _validators"]
        EXPORT["export renderers<br/>_charts.py SVG · _deck.py + _pptx.py PPTX<br/>web/_synthesis.py HTML reports"]
    end

    CLI --> services
    MCP --> services
    WEB --> services
    services --> STORE
    STORE --> DB

    services --- MEMORY
    services --- ARTIFACTS
    MCP --- AUTHORING
    services --> EXPORT
    EXPORT --> BROWSER
    MEMORY --> STORE
```

Key points per layer:

- **Entry points.** `cli.py` (`sonaloop`), `mcp_server` (`sonaloop-mcp`, stdio), and
  `web` (`sonaloop-web`, FastAPI server-side-rendered inspector on `:8787`,
  `make dev-forwarded` exposes `:18787`). The inspector renders HTML in
  `web/_components.py` — no JS framework — and streams lifecycle events over SSE.
- **services/** holds all business logic; entry points stay thin. The research plan
  engine (`_engines.py`) dispatches deterministic analyze/act/verify steps;
  `_research.py` owns project graphs and open questions. `_hooks.py` is the
  extensibility seam (lifecycle event bus feeding SSE and plugin listeners).
- **storage/** is a single `Store` class composed from mixins (`PersonasMixin`,
  `SimulationMixin`, `CouncilsMixin`, `ResearchMixin`, `MemoryMixin`, …), 42 tables,
  WAL journal mode. No ORM.
- **Memory graph** spans `services/_memory.py` + `storage/_memory.py`: entities,
  bi-temporal facts (`t_valid` / `t_invalid` enable time-travel queries), threads
  (open loops), and optional embeddings for hybrid semantic recall
  (`OPENAI_API_KEY` enables embeddings + avatars only — never text generation).
- **Exports**: Markdown, JSON, self-contained HTML, PDF (via Playwright), and native
  PPTX with charts (`_deck.py`, `_pptx.py`, `_pptx_charts.py`); SVG charts in
  `_charts.py` use vendored design tokens.

## Governed research run loop

The end-to-end flow a host agent drives through MCP. The server returns deterministic
dispatches; the host authors every artifact.

```mermaid
sequenceDiagram
    participant Host as Host agent
    participant MCP as Sonaloop MCP server
    participant Store as SQLite store

    Host->>MCP: start_project(title, goal, methodology, persona_ids)
    MCP->>Store: create project + seed research plan
    MCP-->>Host: project_id + analyze/act/verify scaffolding

    Host->>MCP: start_run(project_id, budget)
    MCP-->>Host: run_id + journal

    loop until run_step returns kind=done
        Host->>MCP: run_step(run_id)
        MCP-->>Host: dispatch — kind analyze/act/verify, directive, key
        Note over Host: Host authors the step output<br/>brief_* gather → author JSON → record_*
        Host->>MCP: checkpoint_step(run_id, step)
        MCP->>Store: append step + evidence refs to journal
    end

    Host->>MCP: assess_project(project_id)
    MCP-->>Host: coverage, evidence gates, saturation hint, recommendation
    Host->>MCP: record_critic_round(run_id, passed, missing_count)
    Note over Host,MCP: independent completeness critic,<br/>loop-until-dry until threshold met

    Host->>MCP: synthesis tools — author sections, record synthesis
    Host->>MCP: export_synthesis(format = md/html/pdf/pptx)
    MCP-->>Host: report artifacts
    Note over Host: hand off to web inspector on :8787<br/>for human review
```

## Module map

| Path | Role |
| --- | --- |
| `sonaloop/cli.py` | CLI entry point (`sonaloop`), ~45 command handlers |
| `sonaloop/mcp_server/` | stdio MCP server, 31 tool modules, plugin loader |
| `sonaloop/web/` | FastAPI SSR inspector (`:8787`), SSE, bilingual docs hub (`_docs_content.py`) |
| `sonaloop/services/` | 39 domain modules — all business logic |
| `sonaloop/storage/` | SQLite WAL store, `StoreBase` + mixins, 42 tables |
| `sonaloop/llm_simulation/` | Authoring contract: prompts, JSON schemas, validators |
| `sonaloop/artifacts.py` | Artifact validation + lifecycle |
| `sonaloop/browser.py` | Playwright harness (optional, degrades gracefully) |
| `sonaloop/_charts.py` / `_deck.py` / `_pptx.py` | SVG charts and PPTX export (design-system vendored) |
| `sonaloop/_pptx_preview.py` | First-slide PPTX→PNG rasterizer (document file-card previews) |
| `sonaloop/prototype_templates/`, `methodologies/`, `suggestions/` | Static catalogs |
| `spec/` | Living design specs (architecture trackers) |
| `docs/` | Deep agent-facing contracts; canonical user docs live in sonaloop-docs |

## Data flow & portability

- **Data dir** resolution: `SONALOOP_DATA_DIR` env var → `./data/` in a source
  checkout → `~/.local/share/sonaloop` when installed. Everything user-generated
  lives there; it is git-ignored and never leaves the machine.
- **`sonaloop.db`** is a single SQLite file (WAL mode, so `.db-wal` / `.db-shm`
  sidecars appear while running).
- **Snapshots**: `export_snapshot` (`make snapshot`) writes a portable JSON + SOUL.md
  + embeddings tree to `data/export/`; `import_snapshot` (`make restore`) rebuilds the
  runtime DB, avatars, and SOULs on another machine — exact state moves without
  regeneration.
