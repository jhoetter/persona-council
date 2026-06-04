# Live autonomous-run observations (self-analysis)

> Monitoring a real `compose-research-plan → autonomous-research-run` session driven only by the
> prompt *"How might we get young people who just took out car insurance interested in life
> insurance?"*. Goal: verify the agent uses the concepts correctly, find what to improve, fix the
> clear ones live, spec the complex ones. Session: `c4bfb45c…`. Project:
> `Cross-sell: car → life insurance for young buyers` (double_diamond).

## ✅ Working as designed (concepts used correctly)
- **Front door**: the bare HMW auto-triggered `compose-research-plan` (no command). ✓
- **Self-composition**: surveyed `list_personas` + `suggest_methodologies` + `suggest_capabilities`,
  then made an explicit, justified design decision (standard Double Diamond, not the deep variant)
  and wrote a **`Plan rationale` note**. ✓ Exactly the intended behavior.
- **Hand-off**: seeded the project, then invoked `autonomous-research-run`. ✓
- **Lean loop**: as orchestrator it loaded the loop tools, called `assess_project` (→ `frame`), then
  `next_action` (→ `frame__discover` fully loaded), then dispatched **one subagent** to author the
  Discover frame returning ids only. ✓ Lean context per step is happening.
- **MCP path**: after adding `.mcp.json`, the `mcp__persona-council__*` tools are connected and used. ✓

## Issues found → fixes

### F1 — `list_personas` dumped full profiles (FIXED, committed)
First tool call returned **91,631 chars → "exceeds maximum allowed tokens"**; the agent had to work
around it with `jq`. Context bloat the harness imposed. **Fix:** lean summary projection;
MCP `list_personas` now compact by default (94k→5.6k). Drill in via `get_persona`.

### (running — appended as observed)
