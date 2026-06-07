# Meta-report presentation & PDF — report-grade output with figures, export-ready

Status: **Phase 1-3 DONE + artifact model** (2026-06-07). Author: design brainstorm triggered by "make
the meta-report almost presentation-like (Notion-quality), able to embed prototype screenshots/images,
and later export to a proper PDF."

**Update (2026-06-07): meta-reports are now first-class artifacts** — arbitrarily many per project,
like syntheses/councils (per the request "diese sind einfach dann teil der projekt-elemente … eine art
artefakt"). Each report has a `title` (host-authored in the outline payload; default `"<project> —
Meta-Report"`), its own page `/meta-reports/{id}` + PDF `/meta-reports/{id}.pdf`, a library list
`/meta-reports` + sidebar nav (`report` icon), and is surfaced in the project panel alongside
prototypes. `/projects/{id}/meta` redirects to the project's latest report (back-compat). Modelled on
the prototype-artifact pattern (a parallel artifact list, not a plan-graph node).

Builds on `spec/research-graph-and-meta-report.md` (the meta-report data model + authoring loop),
`spec/markdown-authoring-harness.md` (host authors Markdown), and `spec/linear-design-system.md` /
`spec/design-system.md` (the visual language). Preserves all standing invariants: **the host authors
all text** (no in-process LLM generation), the **web UI is read-only**, and **no methodology/artifact
vocabulary is hardcoded**.

## 1. Goal

Turn the meta-report from "markdown in a `.doc` div" into a **report-grade document** — the kind of
thing a stakeholder reads or a team hands off: a cover, typographic hierarchy, callouts, pull-quotes,
**embedded figures (prototype screenshots, charts, avatars)**, and clean citations. It must be built
so that a **high-fidelity PDF export** drops in later with no second rendering path.

Three independently-shippable phases:
1. **Report design system** — the renderer + stylesheet (biggest visual jump, no new data).
2. **Figures & embeds** — asset store + prototype screenshots + chart figures + a figure manifest.
3. **Proper PDF** — headless-Chromium pagination over the exact same HTML/CSS.

## 2. Current state (what we're replacing)

- `services.export_meta_report(project_id, format="md")` assembles the report as **one Markdown
  string** (title, a `*meta-synthesis · N sections · M studies · date*` line, the build-order
  narrative, then per-section `## heading` + authored markdown + `*Belege:*` + `_Sources:_`).
- `web/pages/projects.py::project_meta` renders `raw(_md(md))` inside `<div class="page"><div
  class="doc">…</div></div>` and offers an `Export PDF` button = `window.print()`.
- Authoring: `brief_meta_outline → record_meta_outline` (sections), then per section
  `brief_meta_section → record_meta_section({markdown, citations})`. A `MetaReport` stores `outline`
  (sections w/ heading/theme_tags/source_study_ids/intent), `sections` (authored markdown+citations),
  `build_order_narrative`, `graph_snapshot`, `created_at`.

Limits: Markdown can't express a cover / callouts / figures / page-breaks; there's no report stylesheet
(it inherits app chrome); citations render as a raw list; no images.

## 3. Architecture decisions

**D1 — Authoring stays Markdown + a thin figure layer (NOT a JSON block model).** The host already
authors Markdown well; Markdown stays the single source of truth (portable, diff-able, PDF-friendly).
We add: (a) a few fenced **directives** the renderer understands — `:::insight`, `:::recommendation`,
`:::risk` callouts, native `>` pull-quotes; (b) a per-section **`figures` manifest** — typed references
to artifacts the renderer resolves to visuals. A JSON block model (Notion-style) is a *non-goal* for
now (revisit only if we ever build a WYSIWYG editor).

**D2 — A dedicated report renderer + stylesheet, separate from app chrome.** Report-quality is mostly
typography, whitespace, and restraint. The report is rendered as **clean semantic HTML** (`<article
class="report">…`) with its own co-located CSS — independent of the inspector chrome.

**D3 — Print-first HTML now, Chromium-PDF later.** Build the report as semantic HTML + a print
stylesheet from the start. The eventual "proper PDF" is just `page.pdf()` over that same HTML via the
Playwright we already depend on — **no LaTeX/Typst/WeasyPrint** (a second rendering path is the thing
to avoid).

**D4 — One asset store for embeddable media.** A small content-addressed store (`data/assets/`) +
`/assets/{id}` route; figures reference assets (or live artifacts) by id. The report never inlines
giant base64.

---

## Phase 1 — Report design system

The renderer + visual system. No new data; works on today's authored markdown.

### 1.1 Renderer
- New `web/_report.py::render_meta_report(report, store) -> str` (semantic HTML), replacing the
  `_md(export_meta_report())` call in `project_meta`. `export_meta_report(format="md")` stays as the
  **plain-text/portable** export (and the PDF source-of-record text); the *web* view uses the rich
  renderer. (Keep both consistent — same content, two presentations.)
- Structure produced:
  - **Cover**: project title, "Meta-Report" eyebrow, date, `N sections · M studies`, and a **hero
    pull-quote** = the single sharpest line (the build-order narrative's lead, or the terminal
    synthesis's positioning). Optional hero image slot (filled in Phase 2).
  - **Table of contents**: auto from `outline` headings, section-numbered.
  - **Body**: per section → numbered `<h2>`, the authored markdown (via `_md`), callouts/pull-quotes
    (1.2), then citations as **footnotes/endnotes** (not a raw inline list).
- Section numbering + ToC anchors are derived, never authored.

### 1.2 Markdown directives (extend `_md` or post-process)
- `:::insight … :::`, `:::recommendation … :::`, `:::risk … :::` → callout boxes (icon + tinted
  border, color-restrained per the Linear language: accent / green / amber).
- `>` blockquote → styled **pull-quote** (large, accented rule).
- Citations: `record_meta_section` already carries `citations[]`; render them as numbered footnotes
  with backlinks, and a per-report "Sources" endnote list (titles, resolved as in `export_meta_report`).

### 1.3 Stylesheet (`register_css`, report-scoped)
- `.report` container: measure ~`720px`, generous line-height, a refined type scale (lead / h1 22-26 /
  h2 / h3 / body 15-16 / caption). Calm, Notion-like.
- Cover, ToC, callout, pull-quote, figure+caption, footnote styles. Restrained palette (greyscale + one
  accent), hairline rules, small radii — consistent with `spec/linear-design-system.md`.
- **Print stylesheet** (`@media print`): hide app chrome, white background, A4 measure, `break-inside:
  avoid` on callouts/figures/blockquotes, `break-before: page` option on sections, running content via
  CSS where supported. This makes the existing `window.print()` button already produce a respectable
  PDF, and is the foundation Phase 3 reuses verbatim.

### 1.4 Acceptance
- The demo meta-report renders with a cover, ToC, numbered sections, callouts, pull-quotes, and
  footnote citations — visibly "a report", not a doc dump.
- `window.print()` produces a clean, chrome-free, paginated PDF.
- `pytest` green; LOC bar respected (split `_report.py` out of `_components.py`).

---

## Phase 2 — Figures & embeds (images, prototype screenshots, charts)

Make the report show the work, not just describe it.

### 2.1 Asset store
- `data/assets/` (git-ignored runtime, mirrored into `data/export/` snapshot) + a `/assets/{id}` route
  serving the file. `services.put_asset(bytes, kind, meta) -> asset_id` (content-hash id).
- Storage table `assets(id, kind, mime, path, meta, created_at)`.

### 2.2 Prototype screenshots (the headline embed)
- We already drive prototypes with Playwright (proband sessions). Add
  `services.capture_prototype_shot(prototype_id, …) -> asset_id` — render the prototype, screenshot,
  store as an asset; optionally attach to the proband session as observed-state evidence (so grounded
  sessions become *visible*).
- Triggered by the host during a session (MCP) or on demand; **the harness captures, it does not
  generate** — no invariant broken.

### 2.3 Figure manifest + chart figures
- `record_meta_section(content)` gains an optional `figures: [Figure]` where `Figure` is one of:
  - `{kind:"asset", id, caption}` — a stored image (prototype shot, uploaded screenshot).
  - `{kind:"prototype", id, caption}` — resolve to the prototype's latest shot (capture if missing).
  - `{kind:"chart", of:"effort_impact"|"sentiment", source_id, caption}` — render an existing component
    (the effort·impact matrix / sentiment donut already exist) as a standalone SVG figure.
  - `{kind:"avatar", persona_id}` / `{kind:"graph", project_id}` — persona avatar / project outline.
- Inline placement: `![[fig:1]]` placeholders in the markdown, resolved to the manifest figure;
  unreferenced figures append at section end as a figure block. Each figure = framed image + numbered
  caption ("Abb. 2 — …").
- `brief_meta_section` frame gains **`available_figures`** (the prototypes/charts/avatars in scope) so
  the host knows what it can embed — same gather→author pattern as the rest.

### 2.4 Acceptance
- A section can embed a prototype screenshot and a chart, each as a captioned figure, rendered inline
  and in print.
- Demo: the Deliver section shows the Wochenplan-Starter v0.2 screenshot + the effort·impact matrix.

---

## Phase 3 — Proper PDF (headless Chromium)

High-fidelity, server-side, one-click — reusing the Phase 1/2 HTML+CSS exactly.

### 3.1 Pipeline
- `services.export_meta_report(format="pdf")` → render the report HTML (the Phase-1 renderer, print
  CSS) → **Playwright `page.pdf()`** → bytes. `web` adds a real **Download PDF** action (replacing the
  `window.print()` fallback, which stays as a no-Playwright degrade).
- `page.pdf({format:'A4', printBackground:true, margin, displayHeaderFooter:true, headerTemplate,
  footerTemplate})` → running header (project · "Meta-Report") + **page numbers**.
- Pagination polish: `break-before:page` on sections, `break-inside:avoid` on figures/callouts, repeat
  nothing awkwardly; cover on its own page; ToC with (later) page numbers.
- Playwright is already an optional dep (`prototyping` extra / `make playwright`); degrade gracefully to
  the print button when chromium is absent (mirror the proband-session grounding gate).

### 3.2 Acceptance
- One click downloads an A4 PDF with cover, ToC, sections, figures, headers + page numbers, sensible
  page breaks — visually identical to the web report.
- Hermetic + optional: suite green with/without chromium (skips like the existing browser tests).

---

## 4. Data-model & contract deltas (summary)

- `MetaReport.sections[].figures: [Figure]` (Phase 2). Outline/citations unchanged.
- New `assets` table + `data/assets/` + `/assets/{id}` (Phase 2).
- `record_meta_section` accepts `figures`; `brief_meta_section` frame exposes `available_figures`
  (Phase 2). `export_meta_report` gains `format="pdf"` (Phase 3).
- Authoring contract addition (skills/MCP): the host MAY add callout directives + a `figures` manifest;
  text + figure *selection* are host-authored, figures are *captured/rendered* by the harness.

## 5. Invariants preserved

- **Host authors all text** — directives + captions are authored; the renderer/PDF only typesets and
  the harness only *captures* screenshots/charts (no text generation).
- **Web is read-only** — assets are produced by explicit MCP/CLI actions, not by viewing.
- **No hardcoded vocabulary** — callout kinds + figure kinds are a small fixed *presentation* set, not
  methodology/artifact vocabulary; chart kinds map to existing components.
- **One rendering path** — web + PDF share the Phase-1 HTML/CSS (D3).

## 6. Non-goals (for now)

- A WYSIWYG/block editor or JSON block model (D1).
- A non-browser typesetting engine (D3).
- Live/interactive embeds in the PDF (screenshots are static; the web report may keep the live iframe).
- Multi-format export beyond md + pdf (e.g. docx/pptx) — possible later off the same content.

## 7. Phasing & order

`Phase 1` (design system) → `Phase 2` (figures) → `Phase 3` (PDF). Each is shippable and visibly better
on its own; Phase 1 de-risks 2 and 3 by establishing the HTML/CSS the PDF reuses. Recommended start:
**Phase 1 on the existing demo meta-report** to lock the quality bar, then iterate.
