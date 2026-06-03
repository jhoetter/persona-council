# Simulation Loop Contract

Model-neutral driver loop the MCP host runs. All text is host-authored; the server
gathers context and persists (see `mcp-tool-contract.md`).

## Per-day loop (A → D)
```
PLAN      brief_day(persona, date)            # gather memory + covering period plan
          -> author day_plan -> put_day_plan
SIMULATE  simulate_day(persona, date)         # author blocks + activities (plan-aware)
CONSOLIDATE brief_consolidation(persona, date)
          -> author memory_deltas             # entities/facts(status)/threads/links
          -> record_memory_deltas             # resolves dupes, writes bi-temporal facts,
                                              # invalidates superseded status, embeds
EVALUATE  evaluate_simulation(...)            # periodic quality gate (green/warn/red)
```

## Long-horizon loop (multi-resolution, §4A — trends without simulating every day)
```
brief_period(persona, "month"|"quarter"|"year", date)
  -> author period plan WITH sample_days (milestones + ordinary routine)
  -> put_period_plan
FOR each sample_day: run the per-day loop above
ROLL UP  brief_digest(persona, scope, date) -> author -> put_digest
ARC      between samples, advance project facts with INTERVAL validity
         (record_memory_deltas at the sampled dates); a fact can hold over a span
         even though intervening days were never simulated.
DRIFT    occasionally brief_persona_revision -> record_persona_revision (rare, evidence-backed)
```

## Invariants
- Nothing hardcoded: project outcomes/durations/status are the host's judgement; the
  store only records them. No fixed "project = N months".
- Bi-temporal valid time enables `get_state_at(date)` / `get_project(..., as_of)`.
- Selective recall, not narration: pull memory with `recall_memory` only when the
  moment calls for it; personas reference the past on demand.
- Anti-steering persists into planning, consolidation, digests, and drift.

## Definition of "top" (done criterion)
A simulated long horizon is "top" when `evaluate_simulation` returns no red checks:
no uniformity/repetition, projects move and some close, loops partly resolve, no
contradictions/duplicates, no unsupported product-thesis drift — and project/trend
timelines are coherently queryable over time.
