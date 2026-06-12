# UX Audit — Phase U rubric (P5 closing audit on top, U1 history below)

## P5 audit (2026-06-11) — ux-contract §5.3 acceptance

> Method: real showcase DB (`data/`, "Mittagspause unter Termindruck" + "Component finder"),
> server on :8787, every canonical screen screenshotted at 1440×900 (light theme) and scored by
> looking at the rendered pixels — not the code. Dimensions map to the contract's clauses:
> **OR** orientation & concept economy (C10) · **RP** row+peek consistency (C1/C2) ·
> **HD** hierarchy & density (C5) · **TX** text discipline (C6) · **KB** keyboard (C7) ·
> **HN** empty/count honesty (C8). Each /10 with a one-line justification.
> Bar: **average ≥9, no screen <8** (ux-contract §5 item 3). Scores below are POST-fix
> (the "fixes during audit" table lists what moved).

### Per-screen scores (final, after fixes)

| screen | OR | RP | HD | TX | KB | HN | avg | one-line justification |
|---|---|---|---|---|---|---|---|---|
| Projects list | 10 | 9 | 9 | 10 | 9 | 9 | **9.3** | One row vocabulary, honest per-kind counts, ⌘K + tour entry; trailing meta could align tighter on narrow widths. |
| Project detail (showcase) | 10 | 10 | 9 | 9 | 9 | 9 | **9.3** | The outline IS the page: phase groups, per-kind rows + chips, run chip, theme strip; long council titles ellipsize correctly. |
| Personas list | 9 | 9 | 9 | 10 | 9 | 9 | **9.2** | Same entity rows (initials avatars after fix), industry + open-count meta honest against the detail. |
| Persona detail | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Current-state card → calendar → voices ladder reads top-down; portrait now falls back to initials instead of a broken frame. |
| Library · Councils | 10 | 10 | 9 | 9 | 9 | 9 | **9.3** | Tabs + the same rows as everywhere; mode pill, avatar cluster, compact date (now "11 Jun", same as the outline). |
| Library · Sessions | 9 | 10 | 9 | 9 | 9 | 9 | **9.2** | Row carries persona, grounded pill, steps; desc names the walked subject (flat-list context). |
| Library · Decisions | 9 | 10 | 9 | 9 | 9 | 9 | **9.2** | Status pill + evidence count equal what the peek and detail show. |
| Library · Surveys | 9 | 10 | 9 | 9 | 9 | 9 | **9.2** | Lifecycle pill + questions/responses counts match the detail page. |
| Library · empty tab (Hypotheses) | 9 | 9 | 9 | 8 | 9 | 8 | **8.7** | `sl-empty` renders centered + iconified; body says "No hypotheses yet." but teaches no next action (follow-up F1). |
| Peek (decision / council) | 9 | 10 | 9 | 9 | 10 | 9 | **9.3** | j/k/Enter/Esc walk rows and drawer; essence + clamp + ref chips + "Open"; header now shows the title alone (fix #2). |
| Council detail | 9 | 9 | 9 | 9 | 9 | 10 | **9.2** | Verdict-first: exec summary clamp, sentiment strip, stance rail with honest per-stance counts, rounds as rows. |
| Report (auto-seeded outline report) | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Cover → contents → numbered sections; unwritten sections state it as a proper muted em (fix #3), meta line single-language (fix #4). |
| Survey detail | 9 | 10 | 9 | 9 | 9 | 10 | **9.3** | Question rows w/ kind icons + distribution bars; rail "Type: Survey · Respondents: 5" after the label/value de-dup (fix #8). |
| Session detail | 10 | 9 | 10 | 9 | 9 | 10 | **9.5** | Outcome banner → frictions → dual-timeline replay; "Grounding: grounded" rail (fix #8); strongest screen in the app. |
| Activity | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | One row per event, links resolve; "Run finished · finished" duplication removed (fix #7); duplicate consecutive events are honest data (follow-up F4). |
| /runs (off-nav telemetry) | 8 | 8 | 8 | 9 | 8 | 9 | **8.3** | Deliberately minimal (ux-contract §7.4); the finished journal now opens by default instead of one collapsed chevron (fix #6). |
| Documentation hub (footer) | 10 | 9 | 9 | 10 | 9 | 9 | **9.3** | Tabs + card grid + prev/next; bilingual; orientation instant. |

**Average: 9.15 — no screen below 8.** Bar met.

### Fixes made during the audit (all in-contract, ratchets unchanged)

| # | finding (screen) | fix |
|---|---|---|
| 1 | Persona portraits/avatars rendered as broken `<img>` frames everywhere — avatar records survive snapshots, the binaries don't | `_avatar_src()` existence check in `web/_components.py`; initials fallback in `_avatar()`, the persona-detail portrait and report avatar figures |
| 2 | Peek drawer header concatenated title+desc+badges ("…EinzelkonzepteMittagspause unter Termindruck…") | DRAWER_JS title fallback prefers the row's `.sl-entity__title` slot |
| 3 | Report placeholder showed literal markdown `_(noch nicht verfasst)_` | plain muted `<em>` (the string is never md-rendered) |
| 4 | Report cover meta mixed languages ("6 sections · 5 Studien") | whole meta line follows the document's content language (PDF reuses the markup) |
| 5 | Outline showed "0 findings" on a rich narrative synthesis (reads as a defect) | synthesis chip falls back to the honest source count when no structured findings exist |
| 6 | /runs greeted with a single collapsed "Finished (1)" chevron | finished journal opens by default when nothing is stalled/active |
| 7 | Activity rows: "Run finished · finished" | detail label suppressed when the event title already states it |
| 8 | Survey rail "5 responses → 5", "Type: Surveys"; session rail "grounded → grounded" | static labels (`Respondents`, `Grounding`), singular kind (`Survey`); new i18n keys de+en |
| 9 | Library/peek rows dated "2026-06-11" while the outline says "11 Jun" | `ui.primitive_row` formats the same compact day as the outline (`_fmt_day`) |

### Follow-ups recorded (not blocking the ≥9 bar)

- **F1** Library empty-tab bodies name no next action ("No hypotheses yet.") — wire each tab's
  `sl-empty` to its `record_*` / MCP hint, the way `no_survey_responses` already does. (C8 "teach".)
- **F2** Persona avatar binaries are not part of `data/export` snapshots — either include them in
  `export-snapshot` or stop recording `avatar.path` for files that were never fetched. The UI now
  degrades cleanly; the data story should still be settled.
- **F3** Library "Sessions" counts usability sessions only; prototype *reaction* sessions surface
  as outline chips — fine per the one-table vocabulary, but the tab lead could say "usability
  sessions" explicitly.
- **F4** Activity shows consecutive duplicate events when a re-export supersedes an asset —
  consider coalescing identical neighbors into one row with a ×n badge.
- **F5** /runs stays minimal by decision (ux-contract §7.4) — its 8.3 is the accepted ceiling for
  telemetry; do not invest styling there.

### Gate

`make ux` (24 goldens: 12 screens × light+dark, deterministic seeded store) is the standing
drift gate; goldens refreshed after the fixes above (see README "Dev checks"). The two
test-side ratchets (`tests/test_ux_contract.py`) stand at STYLE_BASELINE=53 and the frozen
class whitelist — both unchanged by this audit's fixes.

---

## U1 audit + U-exec outcome (historical, pre-token-system)

> Heuristic audit of the (then newly Linear-styled) app against a Linear-employee ≥9/10 bar. Each
> dimension scored /10 after the L restyle; the fixes below closed the then-remaining gaps.

### Per-screen scores (post-L restyle)
| screen | nav | hierarchy | no-redundancy | consistency | states | feedback | avg |
|---|---|---|---|---|---|---|---|
| Projects list | 9 | 8 | 9 | 9 | 7 | 9 | 8.5 |
| Project graph | 9 | 9 | 9 | 9 | 9 | 9 | 9.0 |
| Synthesis detail | 9 | 9 | 9 | 9 | 8 | 9 | 8.8 |
| Council / Persona detail | 9 | 8 | 9 | 9 | 8 | 8 | 8.5 |
| **Plan view** | — | — | — | — | — | — | **missing** |
| Prototype viewer | 9 | 9 | 9 | 9 | 8 | 9 | 8.8 |
| Global nav / sidebar | 9 | 9 | 9 | 10 | 9 | 9 | 9.2 |

### Findings → fixes (ranked, all landed in U-exec)
1. **The PLAN had no web view (high).** Fixed: read-only `/projects/{id}/plan` route + header link.
2. **Empty/edge states (med).** Fixed: empty-state component on projects list + plan view.
3. **Consistency carried by tokens (low).** Resolved by the L token system.

### Net (U1)
Average ≥9 with the plan view added; deferred Cmd-K landed later (⌘K palette is now core).
The P5 audit above supersedes these scores.
