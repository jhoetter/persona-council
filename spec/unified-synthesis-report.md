# Unified synthesis & report — one artifact, scoped

Status: **SPEC (in progress)** (2026-06-07). Author: "ist Synthese das gleiche wie Report? … ich denke,
dass es letztlich eins sein sollte, nur sehr sauber und gut strukturiert." → migrate **A + B** fully.

Builds on `spec/unified-artifact-schema.md` (the 5 primitives — synthesis findings already use them),
`spec/research-graph-and-meta-report.md`, and `spec/meta-report-presentation-and-pdf.md` (the report
renderer + figures + PDF). Preserves the standing invariants: host authors all text, web is read-only,
**kinds are tags** (data-driven presentation, nothing hardcoded), one rendering path.

## 1. The decision

`Synthesis` and `MetaReport` are **the same family at different scopes** — the codebase already says so:
the synthesis docstring is *"a study arc … the report is the exported document"* and the library calls
synthesis *"the report node"*; the meta-report is *"a cross-study project report that distills the whole
graph."* A synthesis folds **councils** → big picture; a meta-report folds **the whole graph** → big
picture. The only real differences are **scope** and whether the node is **wired into the plan** — both
properties, not types.

→ **Collapse `MetaReport` into `Synthesis`.** One entity, discriminated by a `scope` tag. This matches
the repo principle "kinds are tags" and removes the redundancy. The **name stays `Synthesis`** in
code/storage (it is deeply wired into the plan/graph/gates/MCP/specs; renaming would be churn + would
risk conflicts with the parallel work in sonaloop-cloud/-research). The **UI labels by scope** — a
project-scope synthesis is shown as *"Report" / "Meta-Report"*. That is exactly "eine Entität, anders
getaggt."

## 2. The unified model

`Synthesis` gains a `scope` and the meta-report's narrative layer (all new fields optional, default to
today's behaviour):

```
Synthesis:
  # identity / methodology wiring (unchanged)
  id, title, created_at, goal, status, methodology, phase, mode, role
  # NEW — what it folds / its role:
  scope: "convergence" | "project" | "custom"     # default "convergence" (today's synthesis)
  # inputs it folds (unchanged + generalised):
  council_ids, references, citations               # convergence cites councils; project cites graph refs
  # STRUCTURED analysis layer (unchanged — the 2×2 lives here):
  gesamtbild, positionierung, arc_narrative
  findings, statements, prompts                    # primitives → effort·impact 2×2, recommendations, …
  next_council_question, stop_reason, iterations
  # NEW — NARRATIVE document layer (from MetaReport):
  lead: str                                        # the report lead (was build_order_narrative)
  sections: [ {id, heading, markdown, citations, figures, theme_tags, source_study_ids, intent} ]
  graph_snapshot: Json                             # project-scope keeps the graph it summarised
```

- **scope = convergence** (default): a methodology graph node (a diamond waist). Emphasises the
  structured layer (findings → 2×2). May also carry `sections` if the author wants prose. Wired into
  the plan; counts for gates.
- **scope = project**: the former meta-report. Emphasises `sections` + figures. NOT a plan node — a
  hand-off document that summarises the whole graph (`source_study_ids` per section, `graph_snapshot`).
- **scope = custom** (future): an arbitrary slice. Not built now; the tag space is open.

The two layers compose: a synthesis renders **whatever it has** — findings (incl. the 2×2) and/or
narrative sections.

## 3. One renderer, one export

A single report-grade renderer (the `web/_report.py` pipeline, generalised) renders **any** synthesis:
cover (title + scope label + date + `lead`) → structured blocks (the 2×2 / recommendations when
`findings` present) → narrative `sections` (markdown + callouts + figures) → citations/sources. The
old `_synthesis_html` structured view and the meta-report renderer **converge into this one**.

- **Export** is unified: `export_synthesis(id, format="md"|"pdf")` for every scope. The PDF path is the
  Phase-3 headless-Chromium route, now at `/syntheses/{id}.pdf` (the former `/meta-reports/{id}.pdf`).
  → **every synthesis is exportable** (a hard requirement), not just project reports.
- **Figures**: the figure manifest moves onto `sections`. Implement the **`chart` figure-kind** (specced
  but unbuilt): `{kind:"chart", of:"effort_impact", source_id:<synthesis_id>}` renders that synthesis's
  2×2 as a standalone figure — so a project report **embeds a convergence synthesis's 2×2**. This is the
  concrete payoff of unification.

## 4. Routes, lists, nav

- **One detail route** `/syntheses/{id}` serves every scope (the report renderer). `/syntheses/{id}.pdf`
  exports. `/meta-reports/{id}` and `/meta-reports/{id}.pdf` **redirect** to the synthesis equivalents
  (back-compat). `/projects/{id}/meta` keeps redirecting to the project's latest project-scope synthesis.
- **One list** `/syntheses` shows all syntheses with a **scope label** (Synthese / Report). The separate
  `/meta-reports` list + its sidebar entry are removed (redirect `/meta-reports` → `/syntheses`); the
  former `report` icon is reused for project-scope rows. (One artifact ⇒ one nav home.)
- **Outline**: convergence syntheses already render as methodology rows; project-scope syntheses render
  as the inline "report" rows added earlier — now both come from the SAME entity, tagged by scope.

## 5. Plan-graph

`plan_graph` builds nodes from plan tasks' `produces` — those are **convergence** syntheses only, so it
naturally never lists project-scope ones. Guard explicitly anyway: graph node-building and gate counting
consider only `scope == "convergence"` (or unset = legacy convergence). Project-scope syntheses are
exposed via `_attach_meta_reports` (renamed `_attach_project_reports`) for the outline rows.

## 6. Migration

One-time, idempotent, on storage open (or an explicit `migrate_meta_reports_to_syntheses`):
- For each `meta_reports` row → write a `Synthesis` with `scope="project"`, `title`, `sections` (from the
  meta-report `outline` joined with authored `sections`), `lead` = `build_order_narrative`,
  `graph_snapshot`, `created_at`, `references`/`citations` from the sections' `source_study_ids`. Keep the
  **same id** so existing `/meta-reports/{id}` links resolve after redirect.
- After migration the `meta_reports` table is dead; keep reading it one release for safety, then drop.
- `record_meta_outline`/`record_meta_section`/`brief_meta_report`/`export_meta_report`/`scaffold_meta_report`
  become thin wrappers that operate on a `scope="project"` synthesis (so existing MCP callers + skills
  keep working) — and `record_synthesis(scope="project", sections=…)` is the native path.

## 7. Phasing (A then B, shipped green at each step)

- **Phase A — shared render/export/chart (additive, no storage change).**
  A1 generalise the report renderer to take a synthesis (findings + sections). A2 add
  `export_synthesis(format="pdf")` + `/syntheses/{id}.pdf`. A3 implement the `chart` figure-kind. Now
  syntheses are report-grade + exportable and reports can embed a 2×2 — with MetaReport still separate.
- **Phase B — collapse the entity.**
  B1 extend the `Synthesis` model (`scope`, `sections`, `figures`, `lead`, `graph_snapshot`). B2 migrate
  `meta_reports` → `syntheses(scope=project)`. B3 point the meta-report services/MCP tools at Synthesis.
  B4 unify routes + list + nav (redirects). B5 plan-graph scope guard. B6 seed + tests + i18n + burndown.
  B7 retire the `MetaReport` model + table.

## 8. Invariants & risks

- Host authors all text; figures/2×2 are rendered/captured, never generated. Web read-only. Kinds = tags
  (scope is a tag; presentation data-driven). One rendering path (web + PDF share the renderer).
- **Parallel work** (sonaloop-cloud/-research): Phase A is purely additive (low conflict). Phase B
  changes storage/services — land it in tight, green commits and pull before each push.
- Back-compat: old `/meta-reports/*` URLs + all meta-report MCP tools keep working (redirects + wrappers),
  so external callers and skills don't break.
