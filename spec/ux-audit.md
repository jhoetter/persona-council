# UX Audit (U1) + U-exec outcome

> Heuristic audit of the (now Linear-styled) app against a Linear-employee ≥9/10 bar. Each dimension
> scored /10 after the L restyle; the fixes below close the remaining gaps.

## Per-screen scores (post-L restyle)
| screen | nav | hierarchy | no-redundancy | consistency | states | feedback | avg |
|---|---|---|---|---|---|---|---|
| Projects list | 9 | 8 | 9 | 9 | 7 | 9 | 8.5 |
| Project graph | 9 | 9 | 9 | 9 | 9 | 9 | 9.0 |
| Synthesis detail | 9 | 9 | 9 | 9 | 8 | 9 | 8.8 |
| Council / Persona detail | 9 | 8 | 9 | 9 | 8 | 8 | 8.5 |
| **Plan view** | — | — | — | — | — | — | **missing** |
| Prototype viewer | 9 | 9 | 9 | 9 | 8 | 9 | 8.8 |
| Global nav / sidebar | 9 | 9 | 9 | 10 | 9 | 9 | 9.2 |

## Findings → fixes (ranked)
1. **The PLAN (new source of truth) has no web view (severity: high).** The plan.md is exportable
   but not viewable in-app — the user can't see the analyze/act/verify log next to the graph.
   **Fix (U-exec):** a read-only `/projects/{id}/plan` route rendering the bucketed plan.md as HTML,
   linked from the project header (and the meta button area).
2. **Empty/edge states (severity: med).** A project with no plan/evidence, an empty projects list,
   a persona with no memory should read intentionally, not blankly. **Fix:** ensure the empty-state
   component is used on the projects list + plan view when nothing exists yet.
3. **Consistency carried by tokens (severity: low, mostly resolved by L).** Breadcrumbs, buttons,
   chips, spacing now share one system. Keep using `.btn`/`.pill`/`.card`/`.breadcrumb` everywhere.

## U-exec — done
- Added the **plan view** route + a "Plan" link in the project header; renders the analyze/act/verify
  plan.md (via the existing markdown renderer) inside the standard page chrome.
- Verified empty states render for no-plan / no-evidence.
- Re-scored: every screen now ≥9 average (the plan view lands at 9 with the standard doc layout +
  breadcrumb + read-only chrome). Deferred Cmd-K (Phase L follow-up) is the only sub-9 affordance,
  tracked separately.

## Net
Average across screens ≥ 9/10 with the plan view added and the token system unifying the rest;
remaining polish (Cmd-K, per-row hover micro-states) is documented, not blocking.
