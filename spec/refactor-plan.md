# Refactor Plan (Q1 self-audit)

> **Status:** SPEC (authored by the Q1 self-audit). Authority for Phase Q execution (Q-exec).
> **Principle:** every split is **behavior-preserving** — public API (web routes, MCP tools, CLI
> commands, `services.*` names) stays identical via re-export shims; the full `pytest` suite + a
> render/characterization check must pass before each commit. Where a split is too risky to do
> safely in one pass, it is logged as a scoped exception rather than half-done.

## 1. Measured inventory (LOC)
| file | LOC | nature |
|---|---|---|
| services.py | 3360 | **god-file** — many domains (personas, simulation, memory, councils, exports, research-graph, methodology/plan/prototype re-exports) |
| web.py | 2683 | **god-file** — CSS + JS asset strings, render helpers, graph layout, routes (`create_app` 464 LOC) |
| mcp_server.py | 1089 | one 996-LOC `build_server` registering ALL MCP tools |
| llm_simulation.py | 1089 | prompt builders + payload validators |
| storage.py | 1071 | one `Store` class (schema + all accessors) |
| cli.py | 724 | `build_parser` (379) + `main` dispatch (310) |
| methodology.py 699 · plan.py 490 · others | <500 | acceptable |

Longest functions: `mcp_server.build_server` (996), `web.create_app` (464), `cli.build_parser`
(379), `cli.main` (310), `services.simulate_day` (206), `web._methodology_layout` (128).

## 2. Quality bars (targets; justified exceptions logged in §5)
- No source file > **1500 LOC** (pragmatic target for this codebase + overnight risk budget; the
  aspirational ~800 is a follow-up, not forced tonight).
- No single function > **~220 LOC** (the tool/parser registrars are the offenders → split per domain).
- Public surface **unchanged**: `services.*`, web routes, MCP tool names, CLI commands identical.
- Duplication removed where mechanical; shared helpers centralized.
- Characterization: full suite green + key route HTML renders + `--help`/tool-list snapshot stable.

## 3. Ranked refactor targets (impact ÷ risk — do in this order)
1. **web.py → extract assets + graph (LOW risk, HIGH value).** Move the big CSS string(s) and
   `_RGRAPH_JS` (+ pure graph helpers `_convex_hull`/`_expand_hull`/`_methodology_layout`/
   `_graph_interactive`/`_graph_svg`/`_graph_layout`) into `web_assets.py` + `web_graph.py`.
   web.py keeps `create_app` + render helpers, importing from them. Pure strings + pure functions →
   safe. Target: web.py < 1800, assets/graph modules carry the rest.
2. **mcp_server.py → per-domain tool registrars (LOW risk).** Split the 996-LOC `build_server`
   into `register_persona_tools(mcp, …)`, `register_memory_tools`, `register_council_tools`,
   `register_research_tools`, `register_methodology_tools`, `register_plan_tools`,
   `register_prototype_tools`, `register_harness_tools` (in `mcp_tools/` modules). `build_server`
   just constructs `mcp`, wires shared deps, and calls the registrars. Tool names/behaviour identical.
3. **cli.py → per-domain parser+handler modules (LOW risk).** Split `build_parser`/`main` into
   `cli_cmds/` modules each adding its subparsers + handling its commands; `main` dispatches.
4. **services.py → `services/` package by domain (MEDIUM risk, HIGHEST value).** Split into
   `services/personas.py`, `services/simulation.py` (day/range/calendar/plans/digests),
   `services/memory.py` (consolidation/deltas/recall/retrieval/evaluation/world/evolution),
   `services/councils.py`, `services/research.py` (projects/graph/syntheses/meta/open-questions),
   `services/exports.py`. `services/__init__.py` re-exports ALL public names (so `from .services
   import X` is unchanged) and keeps the methodology/plan/suggestions/prototype re-export block.
   Verify with the full suite + a render of every route. **If cross-module coupling makes a clean
   split unsafe in one pass, extract the cleanly-separable domains (simulation, memory, research)
   and log the remainder (§5).**
5. **Dedup / reuse (LOW risk).** Centralize: the repeated `store = store or Store()` is fine; the
   repeated payload-validation lives in `llm_simulation` (ok); ensure presentation goes through
   `presentation.py` (done). Extract any duplicated render snippets in web into `web_components`.

## 4. Characterization approach (run before/after EACH target)
- `pytest -q` must stay green (61 tests cover engine/plan/web-layout/mcp-contract/prototypes/etc).
- Render snapshot: build the app, GET the key routes (`/projects`, a project graph, a synthesis, a
  persona, a prototype) and assert non-empty + `rgdata`/expected markers present (a tiny
  `test_web_smoke` added in Q-exec).
- MCP tool-list + CLI `--help` snapshot stable (tool/command names unchanged).

## 5. Scoped exceptions log (filled during Q-exec)
- _(to be appended: any target deferred for safety, with the reason + the follow-up.)_
