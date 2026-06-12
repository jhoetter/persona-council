# UX Audit — Phase U rubric (newest on top: Round 3 → Round 2 → P5 → U1 history)

## Round 3 (2026-06-12) — closing CRAFT audit of the §9 findings (recalibrated bar)

> Method: real showcase DB on :8799 (live :18787 untouched, server killed after), every canonical
> screen PLUS the round-3 surfaces (filter open + applied, `?q=` search, council charts block,
> session replay with step shots, lightbox, ⌘K empty + typed, files grid, edit dialog, overflow in
> the slide-over, activity run group, deck slides 3–5 from `/tmp/ux/deck-after-*.png`) shot fresh
> at 1440×900 light + dark spot-checks and scored from the pixels. Rubric v3 = the six prior
> dimensions + **CR Craft** (information design, density judgment, redundancy, microcopy, visual
> rhythm; anchors: 9 = "würde unverändert bei Linear/Notion shippen", 7 = solid but a designer
> would tweak, 5 = functional but visibly unrefined — judged against Linear/Notion, NOT against
> our previous state). Context: the owner rejected round 2's 9.18 ("noch weit von einem 9/10
> entfernt") because the rubric measured structure, not craft. Scores are POST-fix.
> Shots: `/tmp/ux-audit-r3` (`v-*`/`f-*` = post-fix verification).

### Per-screen scores (final, after fixes)

| screen | OR | RP | HD | TX | KB | HN | CR | avg | one-line justification |
|---|---|---|---|---|---|---|---|---|---|
| Projects list | 10 | 9 | 9 | 10 | 9 | 10 | 9 | **9.4** | Minimal and clean; the duplicate floating "Take the tour" link under the list removed (one entry: sidebar footer). |
| Project outline | 10 | 10 | 9 | 9 | 9 | 9 | 8 | **9.1** | Rows ≤2 chips + date; "PROTOTYP" data label fixed to "Prototype". CR 8: nine consecutive NOTE eyebrows are columnar noise; theme dots are color-only. |
| Outline filter (open + applied) | 9 | 10 | 9 | 9 | 9 | 10 | 8 | **9.1** | V1: Filter inside the measure; facets Type/Phase/Theme/Persona/Status ("Thema" → "Theme" fixed); chips + honest regrouped counts. CR 8: facet option labels wrap to 3 lines in the popover. |
| Outline search (?q=) | 9 | 10 | 9 | 9 | 9 | 9 | 8 | **9.0** | V1: search input part of the FilterBar; results stay phase-grouped. CR 8: no result-count/clear affordance beyond the input itself. |
| Files lens (?view=files, V9) | 9 | 9 | 9 | 9 | 8 | 9 | 8 | **8.7** | File card: type chip, filename+ext prominent, size · day, one download, source chip, day separators. CR 8: empty thumb panel for non-image types, sparse one-card grid. |
| Slide-over: council | 10 | 10 | 9 | 9 | 10 | 9 | 9 | **9.4** | V5: quiet label/value property rows, no boxed card; full detail in the panel; URL semantics correct. |
| Slide-over: decision | 9 | 10 | 9 | 9 | 10 | 9 | 8 | **9.1** | Same anatomy; based-on/rejected chips no longer repeat the group label ("· based on" suffix dropped). |
| Slide-over: session | 9 | 10 | 9 | 9 | 9 | 9 | 8 | **9.0** | Outcome banner + frictions + props in-panel; header meta is plain text, not pill soup (V5). |
| Slide-over: asset | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Preview/file card + provenance; pills equal the rail. |
| Overflow "…" + edit dialog (V10) | 9 | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | One visible "…" on detail headers AND in the slide-over header → Edit (native dialog, same fields/route) + Delete (typed confirm). Kinds without edit/delete routes render no overflow — by design (U9). |
| ⌘K empty (V6) | 10 | 9 | 9 | 9 | 10 | 9 | 9 | **9.3** | Recent (entity icons + owning project) · Navigate · Library sub-targets with caret · Actions · kbd footer. |
| ⌘K typed results (V6) | 9 | 10 | 9 | 9 | 10 | 9 | 9 | **9.3** | Grouped by kind, project context line, right-aligned dates — now "11 Jun", the row format (was ISO). |
| Council detail + charts (V3) | 9 | 9 | 9 | 9 | 9 | 10 | 8 | **9.0** | Diverging persona bars (+2.0 … −1.0) encode value; stance bars ∝ count; zero categories gone; meta line no longer repeats the mode pill. CR 8: donut + strip still encode one distribution twice (H2); rail "Type: Decision" echoes the pill (H3). |
| Report detail (auto-seeded) | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Cover meta now "6 Abschnitte · 5 Studien · 11 Jun 2026" (no raw ISO); unwritten sections stay honest ems. |
| Synthesis detail (Define) | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Verdict-first, charts row, clamped prose; same cover anatomy. |
| Synthesis detail (final) | 9 | 9 | 9 | 9 | 9 | 9 | 7 | **8.7** | CR 7 honest: the verdict card text duplicates the exec-summary opening VERBATIM on one screen (H1); "SENTIMENT"/"Sentiment" double heading fixed (card now "Sentiment across the council chain"); effort·value chart is strong. |
| Decision detail | 9 | 9 | 9 | 10 | 9 | 9 | 8 | **9.0** | ADR clamp + based-on/rejected chips de-duped; raw ids inside the ADR body are data, not UI. |
| Survey detail | 9 | 10 | 9 | 9 | 9 | 10 | 8 | **9.1** | Question rows w/ kind icons + value-encoded distribution strips; respondent rows now say "8 answers · 11 Jun" — "responses" no longer means two things on one screen. CR 8: every question row repeats "5 responses" (H4). |
| Session detail (usability) + replay shots (V4) | 10 | 9 | 10 | 10 | 9 | 10 | 9 | **9.6** | Step screenshots back (src fixed pre-audit), per-step transcript + quotes + "would continue" chips; strongest screen. |
| Lightbox open (V4) | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Click → full-size step shot. CR 8: no visible close/caption affordance — Esc/outside-click only (H6). |
| Session detail (prototype) + predicted (V3) | 9 | 9 | 9 | 9 | 9 | 10 | 9 | **9.1** | Header meta plain ("Fabian Drees · Prototype session · 12 Jun"); PREDICTED BEHAVIOR rows: labeled % + mini-bar + ref chip — no bare "0.6" chips anywhere. |
| Prototype detail | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | REAL bug found+fixed: reached by id (⌘K/refs), the iframe/star/delete built from the URL param → 404 embed; now canonical slug. Meta line drops the slug ("v0.1", V12). CR 8: "Prototypes · Sessions (3)" heading still reads odd (G1 stands). |
| Note detail | 9 | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Quiet props (Project · Created), prose body — Notion-plain. |
| Hypothesis detail (seeded golden) | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Same anatomy; hit-rate strip value-encoded and honest. |
| Asset detail (in + out) | 9 | 9 | 9 | 9 | 9 | 10 | 8 | **9.0** | Provenance rows now "12 Jun · 06:10" incl. the supersede chain (was raw ISO). |
| Persona detail | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Current-state → calendar → voices; CR 8: long rail values (Role/Size) wrap to 4–5 cramped lines. |
| Personas list | 9 | 9 | 9 | 10 | 9 | 9 | 9 | **9.1** | Same entity rows, honest counts. |
| Library tabs (Councils/Sessions/Assets) | 9 | 10 | 9 | 9 | 9 | 10 | 9 | **9.3** | One row vocabulary + FilterBar per tab; sessions rows two-line (persona + walked subject) with grounded pill. |
| Library empty tab (Hypotheses) | 9 | 9 | 9 | 9 | 9 | 10 | 9 | **9.1** | Teaches the MCP verb ("Record a falsifiable bet (record_hypothesis)."). |
| Activity + run group (V8) | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Lead explains the feed; per-run group header ("Run · {project} · 8 events · Finished") + ×n coalescing; timestamps now "12 Jun · 06:10". CR 8: re-export triplets inside a run still render as 3 near-identical rows. |
| /runs (off-nav telemetry) | 8 | 8 | 8 | 9 | 8 | 9 | 8 | **8.3** | "A run is one autonomous research engagement…" explainer leads; stays minimal by decision (F5 ceiling). |
| Documentation hub | 10 | 9 | 9 | 10 | 9 | 9 | 9 | **9.3** | Tabs + cards + next-pointer; instant orientation. |
| Deck export, slides 3–5 (V11) | 9 | 8 | 8 | 9 | — | 8 | 7 | **8.2** | Verdict slide (quote bar) + exec-summary cards + sentiment slide replace the text wall; CR 7: the "Votes" card renders its legend with NO donut (empty 300px, H5), slide 3's lower half is bare. |

**Average: 9.01. The Craft column alone averages 8.3 — no screen below 8, but the recalibrated
bar ("9 = ships at Linear unchanged") is NOT met on craft yet.** Stated plainly: the structure
is at 9, the craft is at 8.3. The H-follow-ups below are the measured remainder; the round-2
9.18 overstated this and is superseded.

### The owner's 12 findings — pixel verification (finding → evidence → verdict)

| # | owner finding | pixel evidence (shot) | verdict |
|---|---|---|---|
| V1 | Filter outside measure, themes chip row overflows, no search | Search input + Filter button share the scaffold bar INSIDE the measure; themes are a facet with dot colors + counts; `?q=Fenster` filters phase-grouped (`project-filter-open/-theme`, `project-search`) | **fixed** — facet label said "Thema" in the en UI; → "Theme" during this audit |
| V2 | Outline rows overloaded/redundant | Council rows: icon · eyebrow · title · dot · avatars · phase tag · date; notes: eyebrow + title + dot + date; no "15 statements"-style counts, no default-kind pills (`project`) | **fixed** — row eyebrow said "PROTOTYP" (de data label); → "Prototype" during this audit |
| V3 | Bars all full width, persona boxes, "Oppose 0", bare "0.6" chips | Diverging zero-centered persona bars (+2.0/+1.0/+0.0/−1.0), stance bars ∝ count, legend has no zero entries, predicted behaviors render "70 % ▮▮" labeled mini-bars (`_c900`, `session-predicted`) | **fixed** — donut+strip dual-encoding remains (H2) |
| V4 | Step screenshots gone; prototypes must show them | Usability replay: 13 steps each with screenshot + URL caption; prototype sessions carry 12-step shot strips; lightbox opens full-size (`_su-bot`, `session-lightbox`) | **fixed** — adjacent bug found+fixed: prototype-by-id iframe 404 |
| V5 | Boxed cramped props; session header pill soup | PROPERTIES = quiet label/value rows, frameless, on every kind incl. slide-overs; session meta is plain text "Fabian Drees · Prototype session · 12 Jun" (`session-prototype`, `slideover-*`) | **fixed** — rails still printed raw ISO dates; → "11 Jun 2026" during this audit |
| V6 | ⌘K a bare 17-link jump list | Recent (icons + project context) · Navigate · Library sub-targets (caret) · Actions; typed: results grouped by kind with context + dates (`cmdk-empty`, `v-cmdk`) | **fixed** — result dates were ISO; → "11 Jun" during this audit |
| V7 | Tour floats as toast; footer rows off; "• 0" chip | Footer rows (Feedback / Take the tour / ? for shortcuts) styled as nav rows; no zero runs chip in the topbar | **fixed** — a SECOND floating "Take the tour" link still rendered under the projects list; removed during this audit (C10) |
| V8 | Runs vs Activity unclear | Both lead with one-sentence explainers; Activity folds per-run groups with event count + state pill; "Run finished ×2" coalescing (`v-activity`, `runs`) | **fixed** — within-run re-export triplets still show as 3 rows (noted) |
| V9 | Files lens not file-like | File cards: type chip (PPTX), filename.ext bold, size · day, Deliverable pill, ONE download icon, source chip, day separators (`project-files`) | **fixed** |
| V10 | Edit should be dialogs; delete undiscoverable | "…" on detail headers and in the slide-over header → Edit opens a native dialog (same fields/route), Delete a (typed) confirm (`detail-overflow-open`, `edit-dialog-open`, `slideover-overflow-open`) | **fixed** — recorded artifacts without edit/delete routes deliberately render no overflow |
| V11 | Deck reads "wie auf dem Terminal" | Slides 3–5: verdict slide w/ quote bar, exec summary as 3 cards, sentiment slide w/ value-encoded stance bars (`/tmp/ux/deck-after-03..05.png`) | **partial** — the Votes card shows a legend with NO donut (H5); verified in detail separately |
| V12 | Terminal-flavored microcopy de+en | Council voices lead de-shouted (no CAPS/colon-syntax, de+en); prototype meta drops the slug; en data hints (artifact_types/section_kinds.json); "8 answers" vs "5 responses"; zero raw-ISO dates on screens | **mostly fixed** — teaching empty states keep the MCP verb in parens (deliberate, C8) |

### Fixes made during this audit (all in-contract; ratchets unchanged, STYLE_BASELINE=35)

| # | finding (screen) | fix |
|---|---|---|
| 1 | Prototype reached by id (⌘K, ref chips): iframe src/star/delete built from the URL param → embed 404s `{"detail":"Not Found"}` | canonical `slug = p.get("slug") or slug` after fetch (`web/pages/library.py`) |
| 2 | Prototype meta line printed the slug/id ("v0.1 · prototype_21e8…") | meta = version only — the slug is an address, not information (V12) |
| 3 | "Thema" facet + "PROTOTYP" eyebrows + "Umfrage"/"Vergleich"/… — German shipped data hints in the en UI | `suggestions/artifact_types.json` + `section_kinds.json` labels normalized to English (the round-2 evidence_kinds.json precedent) |
| 4 | Raw ISO dates all over: rails "Created 2026-06-11", ⌘K results, activity "2026-06-12 06:10", asset provenance, runs, report covers, survey rows | ONE date language: `ui.fmt_day` ("11 Jun", rows) / `ui.fmt_date` ("11 Jun 2026", rails) / `ui.fmt_ts` ("12 Jun · 06:10", feeds/provenance) wired through all 20+ call sites |
| 5 | Survey respondent rows said "8 responses" while the section is "5 RESPONSES" — one word, two meanings | new `n_answers` key de+en ("8 answers" / "8 Antworten") |
| 6 | Decision chips repeated the group label ("Based on: ⟬…· BASED ON⟭") | `render_ref(show_role=False)` under labeled groups |
| 7 | Council meta line led with the mode the eyebrow pill already states ("Decision · 5 voices · …", + rail Type = 3×) | kicker keys trimmed to "{n} voices · …" de+en |
| 8 | Synthesis charts row: "SENTIMENT" section heading + card titled "Sentiment" | first card retitled "Sentiment across the council chain" (existing key) |
| 9 | Council voices lead shouted ("react from their LIVED EXPERIENCE: confirms (for), …") | plain sentences de+en, no CAPS / colon-syntax (V12) |
| 10 | Duplicate "Take the tour": sidebar footer (V7) AND a floating centered link under the projects list | in-list link + dead CSS removed — one concept, one place (C10) |

Tests updated to the new contracts: `test_presentation_from_data` (label "Prototype"),
`test_palette_coverage` (compact palette date), `test_web_tour` (single tour entry).

### Follow-ups (the honest craft remainder — concrete, with effort)

- **H1** Synthesis verdict card can duplicate the exec-summary opening VERBATIM on one screen
  (final showcase report) — derive a non-overlapping lead (skip the sentences the verdict
  consumed) or suppress the card when no distinct key_problem exists. Renderer change in
  `web/_synthesis.py::_verdict_card`; ~0.5d.
- **H2** Donut + proportional strip encode the SAME distribution side by side (council sentiment
  block and the synthesis charts card) — pick one encoding per surface. Small renderer change +
  an owner taste call.
- **H3** Council rail "Type: Decision" repeats the header mode pill (round 2 kept it as "real
  info"; with the pill it is now an echo) — drop the rail row or rename to "Mode". One-liner +
  golden refresh; needs the owner's call because round 2 decided the opposite.
- **H4** Survey question rows each repeat "5 responses" when every question shares the count —
  show per-question counts only when they differ. Small (`web/pages/surveys.py`).
- **H5** Deck sentiment slide: the "Votes" card renders the legend with NO donut (empty ~300px
  panel, `deck-after-05.png`) — chart missing or invisible in the PPTX renderer
  (`_pptx_charts`). Needs a deck-side fix + re-render; ~0.5d.
- **H6** Session lightbox has no visible close "×" or step caption (Esc/outside-click only) —
  add both in `LIGHTBOX_JS`/CSS. Small.
- **G1–G5 stand** from round 2 (G1 prototype session heading; G2 report lifecycle pill;
  G4 avatar binaries in snapshots; G5 sidebar active-state rule), F5 stands for /runs.

### Gate

`uv run pytest -x -q`: **743 passed** (baseline 743, +0 — test updates replaced equals).
`make ux UPDATE=1` + follow-up `make ux`: **all 36 goldens match** (the date-format and label
fixes moved most screens deliberately). Ratchets unchanged: STYLE_BASELINE=35, frozen class
whitelist; no new `style=`, no new classes (one dead CSS rule removed).

---

## Round 2 (2026-06-12) — closing audit of U6–U10 (ux-contract §8)

> Method: same as P5 — real showcase DB ("Mittagspause unter Termindruck" + "Component finder"),
> server on :8799 (the live :18787 untouched), every canonical screen PLUS the §8 surfaces
> screenshotted at 1440×900 (light) and scored from the rendered pixels. The hypothesis detail
> (showcase has none) was shot against the seeded `premium-pricing-study` example. Dimensions as
> in P5: **OR** orientation/concept economy · **RP** row+peek consistency · **HD** hierarchy &
> density · **TX** text discipline · **KB** keyboard · **HN** empty/count honesty. Bar:
> **average ≥9, no screen <8.** Scores are POST-fix (the fixes table below lists what moved).
> Shots: `/tmp/ux-audit-r2` (pre-fix) · `/tmp/ux-audit-r2-fixed` (post-fix).

### Per-screen scores (final, after fixes)

| screen | OR | RP | HD | TX | KB | HN | avg | one-line justification |
|---|---|---|---|---|---|---|---|---|
| Projects list | 10 | 9 | 9 | 10 | 9 | 10 | **9.5** | One row vocabulary; per-kind counts now pluralize ("1 Prototype"); ⌘K + tour entry. |
| Project outline (default) | 10 | 10 | 9 | 9 | 9 | 9 | **9.3** | The outline IS the page; header chip says "1 file"; note rows now carry the en "NOTE" eyebrow, not "NOTIZ". |
| Project outline + filters | 9 | 10 | 9 | 9 | 9 | 10 | **9.3** | FilterBar (U10): "Type is Council, Decision ×" + clear; phase groups re-count the filtered set honestly. |
| Project ?view=files | 9 | 10 | 9 | 9 | 9 | 9 | **9.2** | Chronological provenance timeline, day separators, direction pills (Evidence/Deliverable), inline download. |
| Slide-over: council | 10 | 10 | 9 | 9 | 10 | 9 | **9.5** | Full detail page in the panel (U6): eyebrow+pill, clamped title, properties card (now Project-first), relations; URL is canonical. |
| Slide-over: decision | 9 | 10 | 9 | 9 | 10 | 9 | **9.3** | Same anatomy; ADR body + based-on/rejected chips all present in the narrow layout. |
| Slide-over: session | 9 | 10 | 9 | 9 | 9 | 9 | **9.2** | Outcome banner, friction points, properties card — sessions first-class in the peek too. |
| Slide-over: asset | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Preview + file card + provenance in-panel; pills equal the rail values. |
| Expand / back cycle | 10 | 9 | 9 | 9 | 10 | 9 | **9.3** | Expand = real navigation (URL already correct); Esc restores the list URL and highlights the visited row. |
| Library · Councils | 9 | 10 | 9 | 9 | 9 | 10 | **9.3** | 9 tabs, count 3 = DB truth; same rows as everywhere; FilterBar present. |
| Library · Sessions | 9 | 10 | 9 | 9 | 9 | 9 | **9.2** | Both session kinds in one tab (9 = 1 walk + 8 reactions); reaction rows no longer claim "0 steps". |
| Library · Assets | 9 | 10 | 9 | 9 | 9 | 9 | **9.2** | In/out as Evidence/Deliverable pills, size + date + download — the same rows as the files lens. |
| Library · empty tab (Hypotheses) | 9 | 9 | 9 | 9 | 9 | 10 | **9.2** | F1 closed: "Record a falsifiable bet (record_hypothesis)." — the empty state teaches the MCP verb. |
| Council detail | 9 | 9 | 9 | 9 | 9 | 10 | **9.2** | Verdict-first; rail now opens with Project (was the one kind missing it), then mode/voices/stances, Created last. |
| Report detail (auto-seeded) | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Cover → contents → numbered sections; rail Project → sources → Created (the "Type: Report" echo removed). |
| Synthesis detail (Define) | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Verdict card, sentiment + stance strips, relations rail; same cover anatomy as the report. |
| Decision detail | 9 | 9 | 9 | 10 | 9 | 9 | **9.2** | Projects-rooted crumb; rail Project link lands on the deciding row (the "View in project" one-off retired). |
| Survey detail | 9 | 10 | 9 | 9 | 9 | 10 | **9.3** | Question rows w/ kind icons + distribution bars; rail Project → Respondents → Created. |
| Session detail (usability) | 10 | 9 | 10 | 10 | 9 | 10 | **9.7** | Outcome banner → frictions → dual-timeline replay; meta line no longer repeats the title; strongest screen. |
| Session detail (prototype) | 9 | 9 | 9 | 9 | 9 | 10 | **9.2** | New in U7: verdict → liked → frictions → predicted behaviors on the SAME scaffold; "Prototype" rail label singular. |
| Prototype detail | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Live iframe + session rows deep-linking to /sessions/{id}; rail Project-first with grounded tally + Created. |
| Note detail | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Data-vocabulary eyebrow (now "NOTE"), prose body, minimal honest rail (Project → Created). |
| Hypothesis detail | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Predicted/observed structure + DERIVED/OBSERVED chips; Validated pill; same anatomy as every other kind. |
| Asset detail (in + out) | 9 | 9 | 9 | 9 | 9 | 10 | **9.2** | Image preview / file card + PROVENANCE (now the same small-caps section idiom); honest direction story. |
| Persona detail | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Current-state → calendar → voices ladder; rail Role/Industry/Size/Memory. |
| Overflow-delete (open) | 9 | 9 | 9 | 10 | 9 | 9 | **9.2** | U9: one quiet "…" → one danger item → modal confirm; the dialog no longer says "cannot be undone" twice. |
| Activity | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Consecutive duplicates coalesce ("Run finished ×2", F4); every row links to its record. |
| /runs (off-nav telemetry) | 8 | 8 | 8 | 9 | 8 | 9 | **8.3** | Deliberately minimal (ux-contract §7.4, follow-up F5) — the accepted ceiling for telemetry. |
| Documentation hub | 10 | 9 | 9 | 10 | 9 | 9 | **9.3** | Tabs + card grid + prev/next; bilingual; orientation instant. |

**Average: 9.18 — no screen below 8.** Bar met (P5: 9.15).

### Consistency sweep (the owner's "Sicherheit, dass Layouts stringent sind")

All detail screenshots compared side by side. The header anatomy (kind eyebrow + status pills →
icon + title → optional meta line) was already identical across all 11 kinds. The deviations
found were in the rail and the breadcrumb, all fixed in this audit:

- **Rail order is now `Project → kind-specifics → Created` on every kind.** Before: council had
  NO project row; report/survey led with "Type"; both session kinds and the prototype buried the
  project mid-rail; the note led with Created.
- **Breadcrumbs are project-rooted everywhere** (`Projects › {project} › {title}` — the council's
  documented pattern). Before: decision, hypothesis, both session kinds and asset rooted at their
  kind list instead.
- **One-off affordances removed:** the decision/hypothesis "View in project" meta-line link (no
  other kind had one) folded into the rail's Project link, which lands on the exact row anchor.

### Fixes made during the audit (all in-contract; ratchets unchanged, STYLE_BASELINE=38)

| # | finding (screen) | fix |
|---|---|---|
| 1 | Rail anatomy drifted per kind (see sweep above) | council/report/survey/sessions/note/prototype rails normalized to Project → specifics → Created (`web/pages/*`); prototype rail gained Created |
| 2 | "Type: Report" / "Type: Survey" rail rows echo the eyebrow | rows removed (council keeps Type=mode, asset keeps Type=Document — real info) |
| 3 | Kind-rooted breadcrumbs on decision/hypothesis/sessions/asset | project-rooted crumbs (kind root only for orphan records) |
| 4 | "View in project" meta link on decision+hypothesis only | retired; the rail Project link carries the `#dec-`/`#hyp-` row anchor; i18n key removed |
| 5 | Session detail meta line repeated the title (subject/prototype name) | subject dropped from the meta line — the rail carries the link (both session kinds) |
| 6 | Outline/note eyebrows said "NOTIZ"/"Artefakt" amid the en UI | shipped data hints normalized (`suggestions/evidence_kinds.json`: Note, Artifact — the file's other labels were already English) |
| 7 | "1 Prototypes" (projects list), "1 files" (project header chip, asset rail) | singular count labels: `*_one` i18n keys + the `one_file` key, de+en |
| 8 | Delete dialog: "Really delete? This cannot be undone." + hint "This cannot be undone." | `delete_confirm_q` trimmed to the question — the hint states the consequence once |
| 9 | Reaction-only prototype sessions showed a "0 steps" chip (reads as a broken recording) | steps chip only when a replay exists (`ui.primitive_row`) |
| 10 | Asset detail "Provenance" heading rendered heavier than the page's other section heads | the same `.sec`/h2 small-caps idiom as sec-file/sec-excerpt |

### Follow-ups recorded (not blocking the bar)

- **G1** Prototype detail's reaction-session heading reads "Prototypes · Sessions (2)" — give the
  two session sections distinct, plain names ("Replays" / "Prototype sessions"); needs a plural
  for `session_kind_prototype`.
- **G2** Reports/syntheses carry their lifecycle ("done") in the meta line, not as an eyebrow
  pill — the one kind without a status pill; consider a quiet lifecycle pill for full parity.
- **G3** Activity coalescing (F4) merges only *consecutive* duplicates; a re-export still shows
  alternating "Asset attached / Report recorded" triplets — consider per-run grouping.
- **G4** (carries F2) Persona avatar binaries still aren't part of `data/export` snapshots; the
  UI degrades to initials, the data story remains open.
- **G5** Sidebar active state differs per kind (council details highlight Projects, the other
  kinds Library) while breadcrumbs are now uniformly project-rooted — unify the rule.
- **F5 stands**: /runs stays minimal by decision (§7.4); 8.3 is its accepted ceiling.

### Gate

`make ux` now covers 32 goldens (16 screens × light+dark — incl. the slide-over interaction,
the filtered outline, the files lens and the asset detail); goldens refreshed after the fixes
above and green. Full `pytest -q`: 688 passed. Ratchets unchanged: STYLE_BASELINE=38, frozen
class whitelist.

---

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
