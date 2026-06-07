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
- **MCP path**: after adding `.mcp.json`, the `mcp__sonaloop__*` tools are connected and used. ✓

## Issues found → fixes

### F1 — `list_personas` dumped full profiles (FIXED, committed)
First tool call returned **91,631 chars → "exceeds maximum allowed tokens"**; the agent had to work
around it with `jq`. Context bloat the harness imposed. **Fix:** lean summary projection;
MCP `list_personas` now compact by default (94k→5.6k). Drill in via `get_persona`.

### (running — appended as observed)

### F2 — Council turn/vote SCHEMA mismatch broke rendering (FIXED, committed)
The councils were RICH and grounded (Leon cited his real Check24 memory; exec_summary/summary
substantive), but the subagent stored the turn body under `text` (canonical = `content`) and votes
as `stance/label/rationale` (canonical = the SUPPORT/MAYBE/ABSTAIN/OPPOSE `vote`). The council page
does `_esc(tn["content"])` → empty/KeyError, so good content didn't render. **Fix:** `record_council`
now normalizes turns (`content` ← content|text|message) + votes (`vote` ← vote|stance|label); the
council renderer reads `content||text` defensively (+ memory_refs||memory_used). Skill now pins the
canonical turn/vote schema. Root cause: the council schema wasn't enforced, so subagents improvise.

### F3 — Verify "converged" with an ORPHANED, EMPTY synthesis; gate didn't notice
`verify__define` was marked done, but: (a) its synthesis was never `link_evidence`'d to the task
(produces empty → orphaned), and (b) the synthesis payload is entirely empty (gesamtbild/
positionierung/voices all 0) — the real insight was in 8 rich journal NOTES instead. The verify gate
checks structure (fan ≥ min_inputs, judgment, sessions) but NOT that the converging synthesis is
linked or substantive, so a hollow convergence passes. A hard gate would break existing tests
(some complete a verify with judgment-only), so the fix is the RIGHT-LEVEL assessment signal:
`assess_project` now flags (a) a done verify with no linked synthesis ("orphaned answer artifact")
and (b) a thin/empty synthesis — and the skill instructs the verify step to author a RICH synthesis
(gesamtbild/positionierung/voices) and treats notes as observation atoms, not a substitute.
**Open spec item:** consider promoting (a) to a soft gate or an explicit "converge" sub-step that
records+links the synthesis before `complete_task`.

### Positive: the agent journals well + composes correctly
8 substantive run-journal notes captured the real insight ("wrong clock/wrong word", insider
conversion ≈ 0, four textures of resistance, the one LV-shaped opening). The problem isn't thinking —
it's that the substance landed in notes, not the synthesis. The lean loop + segment-diverse councils
+ self-composition all worked.

### F4 — Develop phase was THIN (1 prototype, 0 ideation councils)
The run completed a full Double Diamond (9/9) but Develop = a single prototype + 4 proband sessions
(3 grounded) and NO ideation councils / no varied prototypes. The skill calls for ideation + several
varied prototypes; the agent went minimal. Root cause = F5 (the breadth gate was satisfiable by one
angle), plus the agent satisficing the gate.

### F5 — breadth gate satisficing loophole (FIXED, committed)
`verify__deliver` (min_inputs=2) passed with a fan of **one** act task (the prototype) because its
artifact + 4 sessions = 5 evidence REFS ≥ 2. The breadth gate counted refs, not angles — so a phase
could "diverge" on a single solution. **Fix:** `verify_unmet` now counts DISTINCT act TASKS (angles)
that produced evidence, not raw refs. A single prototype no longer satisfies min_inputs=2 → the loop
must add a 2nd angle (a 2nd prototype or an ideation council) → genuine breadth. (Tests create ≥2 act
tasks, so unaffected; 78 passed.)

## FINAL VERDICT (this run)
**The autonomy works end-to-end from one prompt** — front-door auto-trigger, self-composition, lean
loop, segment-diverse grounded councils, 4 proband sessions, sections + journal, autonomous
completion. The gaps were about OUTPUT QUALITY, now fixed for the next run:
- **Critical (F3):** both answer syntheses (Define POV, Deliver spec) were EMPTY shells — substance
  stranded in notes/exec-summaries. Fixed via skill ("synthesis IS the answer, author it rich; notes
  are atoms") + `assess_project` flags thin/orphaned syntheses.
- **F2:** council schema mismatch (text/stance vs content/vote) broke rendering — normalized on
  write + tolerant render.
- **F4/F5:** thin Develop because the breadth gate counted refs not angles — now counts distinct act
  tasks, forcing real divergence.
- **F1:** list_personas context bloat — compact mode.
The running session won't pick up these (its MCP server + loaded skill are fixed); they land on the
NEXT run. Recommended: re-run the same HMW and re-verify the four syntheses render rich answers,
Develop has ≥2 prototypes/angles, and councils render their turns.

## Still to spec (deliberate, not done)
- ~~**HX3** collapse the two engines (the last big refactor).~~ ✅ DONE (2026-06-05) —
  plan.py is the single engine; the constellation runtime is retired (`spec/hx3-engine-collapse.md`).
- A possible explicit **"converge" sub-step** that records+links a non-trivial synthesis before a
  verify can complete (promote F3's soft signal to a guided step), and a `record_synthesis`
  soft-warning on a near-empty payload.
- charz is unreliable during a live run (the DB mutates); the unit suite (temp DBs) is the real gate.
