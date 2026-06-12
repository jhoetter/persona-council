# UX Audit — Phase U rubric (newest on top: Round 4 → Round 3 → Round 2 → P5 → U1 history)

## Round 4 (2026-06-12) — CLOSING AUDIT: every screen re-scored from fresh pixels, W1–W11 verified

> Method: same harsh bar as round 3 (CR anchor: 9 = "würde unverändert bei Linear/Notion
> shippen"). Real showcase DB ("Mittagspause unter Termindruck" + "Component finder") on
> :8799 (live :18787–:18789 untouched, server killed after), every canonical screen PLUS the
> round-4 surfaces — Library tabs with the full-width bar, the threaded council round,
> prototype rows with avatars, the PPTX title-slide preview card (row, files lens, asset
> detail), the docs hub, the sidebar footer, the lightbox over a live prototype iframe, the
> single sentiment encoding — shot fresh at 1440×900 light + dark spot-checks and scored
> from the pixels (shots: `/tmp/ux-audit-r4`, `v-*`/`zz-*` = post-fix verification crops).
> Context: round 3 closed at **9.01 overall / craft 8.3** BEFORE the H-fixes and round 4.
> Scores below are POST-everything, including the three straggler fixes made during this audit.

### Per-screen scores (7 dimensions, CR = craft)

| screen | OR | RP | HD | TX | KB | HN | CR | avg | one-line justification |
|---|---|---|---|---|---|---|---|---|---|
| Projects list | 10 | 9 | 9 | 10 | 9 | 10 | 9 | **9.4** | Cohort avatar group (+1 overflow) on the project row (W11); quiet count chips; nothing floats. |
| Project outline | 10 | 10 | 9 | 9 | 9 | 9 | 8 | **9.1** | W3 verified: Run·Finished + 1 file share ONE chip family beside the Plan/…/★ control row; prototype/survey rows carry avatar groups; the deck row shows its real title slide. CR 8: nine consecutive NOTE eyebrows are still columnar noise. |
| Outline filter (open) | 9 | 10 | 9 | 9 | 9 | 10 | 8 | **9.1** | Facets clean; popover now right-aligns with the Filter button INSIDE the measure (fixed during this audit — was left-anchored, bleeding to the window edge). |
| Files lens (?view=files) | 9 | 9 | 9 | 9 | 8 | 9 | 9 | **8.9** | W6 verified: the PPTX card shows the rasterized first slide (title readable), filename.ext, size · day, ONE download, source chip. Sparse one-card grid stands. |
| Slide-over: decision | 9 | 10 | 9 | 9 | 10 | 9 | 9 | **9.3** | W3 verified in-panel: ★/⤢/× are the same 28px ghost icon-buttons as the page header; quiet props; ADR clamp. |
| Library tabs (Councils/Reports/Prototypes/Sessions/Surveys/Assets) | 9 | 10 | 9 | 9 | 9 | 10 | 9 | **9.3** | W2 verified: search stretches, the bar spans the full measure on every tab; W11 verified: council rows avatar-group +1, prototype rows show their session drivers, session rows the group of one; "1 sessions" → "1 session" fixed during this audit. |
| Library empty tab (Hypotheses) | 9 | 9 | 9 | 9 | 9 | 10 | 9 | **9.1** | Teach card with the MCP verb; no phantom filter bar on an empty tab. |
| Council detail | 9 | 9 | 9 | 9 | 9 | 10 | 8 | **9.0** | W5 verified: answers indent under the question banner, a hairline spine elbows into each card and ENDS curving into the last; W9 verified: no donut anywhere, stance bars ∝ count, diverging persona bars; W4 verified: refs read "11 Jun · 13:25 …" with trim + tooltip (a date-only "2026-06-10:" prefix slipped the formatter — fixed during this audit). CR 8: strip legend, stance bars and rail counts state the same 5 votes three times (J1). |
| Synthesis detail (final) | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | H1 holds (exec opens with non-consumed sentence); Done lifecycle pill (G2); voices' avatar group on the cover; effort·value chart strong. CR 8: sentiment strip card + stance bars card still co-encode one distribution (J1). |
| Synthesis detail (Define) | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Same anatomy, verdict-first; same J1 remainder. |
| Report detail (auto-seeded) | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Done pill + contents card + honest "(noch nicht verfasst)" ems; cover meta follows the content language by documented decision (P5), no avatars because the seeded outline carries no voices (negative rule). |
| Decision detail | 9 | 9 | 9 | 10 | 9 | 9 | 8 | **9.0** | Adopted pill, quiet Based-on/Rejected chip groups; raw ids inside the ADR body are data, not UI. |
| Survey detail | 9 | 10 | 9 | 9 | 9 | 10 | 8 | **9.1** | W11 verified: respondent avatar group (+1) in the header; H4 holds ("5 responses per question" once). CR 8: "DERIVED FROM" role suffix rides only some Based-on chips (data-driven, reads inconsistent). |
| Session detail (usability) + replay | 10 | 9 | 10 | 10 | 9 | 10 | 9 | **9.6** | Step shots + per-step transcript + would-continue chips; still the strongest screen. |
| Lightbox over the prototype iframe | 9 | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | W8 verified: the dialog stacks ABOVE the live iframe (backdrop dims it, zero bleed); close × and "Step 0 · Look" caption present (H6). |
| Session detail (prototype) | 9 | 9 | 9 | 9 | 9 | 10 | 9 | **9.1** | Verdict-first, plain header meta, grounded pill, 12-step replay with shots. |
| Prototype detail | 9 | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | G1 verified fixed: section reads "PROTOTYPE SESSIONS (3)"; header avatar group + "v0.1" (no slug); live embed; honest Grounding 3/3 rail. |
| Note detail (carried, slide-over re-checked) | 9 | 9 | 9 | 9 | 9 | 9 | 9 | **9.0** | Quiet props + prose; unchanged anatomy. |
| Hypothesis detail (carried, seeded golden) | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Unchanged; golden still green. |
| Asset detail (PPTX deliverable) | 9 | 9 | 9 | 9 | 9 | 10 | 7 | **8.9** | W6 verified: full title-slide preview leads the page. CR 7 honest — the W6 preview exposes a redundancy cluster: the raw mimetype string on the meta line AND the file card, the size printed 3×, rail Type/Direction echoing the header pills, and the file card's empty PPTX stage directly UNDER the real preview (J2). |
| Persona detail | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Photo + current state + calendar; long rail values still wrap 3–4 cramped lines. |
| Personas list | 9 | 9 | 9 | 10 | 9 | 9 | 9 | **9.1** | Entity rows, honest counts. |
| Activity + run group | 9 | 9 | 9 | 9 | 9 | 9 | 8 | **8.9** | Run group header + ×2 coalescing verified. CR 8: re-export triplets ("Asset attached · …final-report.pptx" 06:51/06:53/06:54) still render as 3 near-identical rows (J3). |
| /runs (carried, F5 ceiling) | 8 | 8 | 8 | 9 | 8 | 9 | 8 | **8.3** | Minimal by decision. |
| Documentation hub | 10 | 9 | 9 | 10 | 9 | 9 | 9 | **9.3** | W7 verified: sidebar footer entry with active state, eyebrow + tabs + 6 cards + NEXT pointer, clean in dark; footer rows read as nav rows, ? in a kbd chip. |
| ⌘K palette | 10 | 9 | 9 | 9 | 10 | 9 | 9 | **9.3** | Recent w/ icons + project context · Navigate (incl. Documentation, Keyboard shortcuts) · Actions · kbd footer. |
| Slide-over: council (carried) | 10 | 10 | 9 | 9 | 10 | 9 | 9 | **9.4** | Unchanged anatomy, re-checked via outline click. |
| Deck export (carried + H5 re-verified by XML) | 9 | 8 | 8 | 9 | — | 8 | 8 | **8.3** | Valid native votes donut (ONE holeSize, pinned); W6 rasterizer reuses the deck's own first slide. |

**Overall average: 9.04. The craft column alone: 8.5** (14 screens at CR 9, 13 at 8, one at 7).
Round 3's honest gap (structure 9 / craft 8.3) has narrowed but is NOT closed: the H-fixes and
W1–W11 moved real pixels (threading, single encoding, previews, attribution, docs, footer,
lightbox), and the remaining distance to "ships at Linear unchanged" is now concentrated in
THREE patterns — same-data-twice (J1), the asset redundancy cluster (J2), feed coalescing
(J3) — plus two long-standing texture nits (NOTE eyebrow column, persona rail wrap).

### W1–W11 — pixel verdicts (verified against fresh shots, not the implementation notes)

| # | item | pixel evidence | verdict |
|---|---|---|---|
| W1 | spacing sweep | `scripts/ux_spacing.py` re-run during this audit: **TOTAL FLAGS 0** across all 18 screens, exemptions none | **fixed** (gate, re-runnable) |
| W2 | full-width filter bar | every Library tab + the outline: search stretches to the divider, bar spans the measure edge-to-edge | **fixed** |
| W3 | one control vocabulary | page header: Plan (labeled) + … + ★ same-height boxes; Run·Finished + 1 file are one toolbtn chip row; slide-over header … /★/⤢/× identical ghost boxes | **fixed** |
| W4 | quiet refs | "Drew on:" chips: mono "11 Jun · 13:25" prefix, trimmed body, tooltip, open-loop label | **fixed** — straggler found+fixed: a DATE-ONLY "2026-06-10:" prefix passed through raw (formatter required a time); now "10 Jun" |
| W5 | council threading | answer column indents; hairline spine descends from the question, elbows into every card at the avatar line, curves into the last | **fixed** |
| W6 | document title-slide previews | outline file row, files-lens card and asset detail all show the rasterized first slide (title legible); images keep real thumbs | **fixed** — exposed the J2 redundancy cluster on asset detail |
| W7 | docs in sidebar + design pass + footer | Documentation footer entry w/ active state; docs hub eyebrow/tabs/cards/NEXT; footer rows nav-styled, ? as kbd chip | **fixed** |
| W8 | lightbox stacking | lightbox opened OVER the live prototype iframe: backdrop covers it, no bleed; × + caption | **fixed** |
| W9 | single sentiment encoding | zero donuts on council detail + both synthesis kinds; stance bars ∝ count | **fixed** — strip-vs-bars co-encoding remains as J1 (new finding, narrower than W9) |
| W10 | G1/G2/G5 leftovers | "PROTOTYPE SESSIONS (3)" heading; report/synthesis Done lifecycle pill; sidebar active state follows the project-rooted crumb (Library active on /prototypes, Documentation active on /documentation) | **fixed** |
| W11 | persona-attribution rule | avatar groups verified on: project rows, council rows+opener, prototype rows+header, survey rows+header, session rows (group of one), report/synthesis covers; decision/note/asset rows show none | **fixed** — plus the "1 sessions" grammar straggler fixed |

### Fixes made during this audit (all in-contract; gates stayed green, STYLE_BASELINE=35)

| # | finding (screen) | fix |
|---|---|---|
| 1 | "1 sessions" on prototype rows (Library, both outlines) | `sessions_n_one` de+en ("1 Session"/"1 session") — the existing `_one` singular mechanism, two table entries |
| 2 | W4 straggler: refs with a date-only prefix ("2026-06-10: Linus-Huddle kippt …") rendered the raw ISO slab | `_REF_TS` time part made optional; date-only prefixes format via `ui.fmt_day` ("10 Jun"), timed ones keep `fmt_ts` |
| 3 | Filter popover left-anchored to the bar's LAST control — overflowed the measure to the window edge | `.sl-popover--bottom-start` → `--bottom-end` (existing vendored variant): the menu right-aligns with the Filter button |

Verification: `/tmp/ux-audit-r4/zz-vproto.png`, `zz-vrefs.png` + srcchip-ts HTML sweep (raw ISO
survives only in tooltips = the full quote, by design), `zz-vfilter.png`.

### Follow-ups (concrete, honest — the measured craft remainder)

- **J1** One encoding per surface, finishing W9's spirit: the sentiment STRIP card and the
  stance-BARS card co-encode the same distribution on council detail and the synthesis charts
  row (the rail repeats the counts a third time on council). Owner taste call: keep the bars,
  fold the strip into the rail/legend — small renderer change, ~6 goldens shift.
- **J2** — **RESOLVED (2026-06-12)**: filename/size/mimetype now live ONLY on the file card
  (no H1 sub line), the rail dropped its Type/Direction/Size echoes (Project · Files · Created
  remain), provenance dropped its Direction row (the Generated/Received verb states it), and
  the card's extension-badge stage is suppressed when the real preview leads the page —
  the page reads once top to bottom (`pages/assets.py`, `_presence.asset_file_card(stage=)`;
  verified on the showcase deliverable, `/tmp/ux/j2-asset.png`: mimetype 1×, size 1×).
- **J3** — **RESOLVED (2026-06-12)**: within a run, same-key events coalesce across
  interleaved rows (not just adjacent), a repeated asset attach reads as ONE quiet
  "Asset re-exported ×n" row, and flat rows that become neighbors once the run rows fold
  out coalesce too — the showcase triplet is now "Asset re-exported · mittagspause-final-
  report.pptx ×3" + "Report recorded … ×3" (`pages/activity.py`, `evt_asset_reexported` de+en).
- **J4** — **RESOLVED (2026-06-12)**: within a contiguous same-kind run of top-level outline
  rows only the FIRST row shows its kind eyebrow (children/file rows break the run; the fixed
  86px `.ol-ptag` keeps the grid) — the nine-NOTE column reads as one label + a quiet icon
  column (`_graph_outline.mark_kind_runs`).
- **J5** — **RESOLVED (2026-06-12)**: rail prop rows whose plain-text value exceeds the
  inline measure TIER (label line, value at the rail's full 280px) via `.sl-prop--tier`,
  scoped to the page rail only (`.rail:not(.rail--slide)`); short values keep the inline
  Notion anatomy unchanged — persona Role/Industry/Size now read in 1–2 calm lines
  (`web/_detail.py`).
- **J1** stays OPEN — owner taste call on the strip-vs-bars co-encoding (do NOT change the
  encoding without that decision).
- F5 stands for /runs (deliberately minimal); G4 (avatar binaries in snapshots) stands.

### Gate (closing)

`uv run pytest -x -q`: **762 passed, 3 skipped** (unchanged — the three fixes sit under
existing contracts). `scripts/ux_spacing.py`: **0 flags, exemptions none**. `make ux`:
**all 36 goldens match with zero refresh** — the audit fixes touch only showcase-visible
states (singular counts, date-only refs, open popover), none of which the seeded goldens
exercise. Ratchets unchanged: STYLE_BASELINE=35, frozen class whitelist, no new `style=`.

## Round 4 (2026-06-12) — spacing sweep + threading + attribution (ux-contract §10 W1–W5, W9, W11)

### Spacing conformance (W1)

> Method: `scripts/ux_spacing.py` — the DOM-measured sweep. Boots the same seeded app as
> `make ux`, walks every canonical screen (incl. the open slide-over) at 1440×900 and reads
> the COMPUTED paddings/margins/gaps of every structural element (page chrome, topbar,
> headers, tabs, filter bar, list containers, rows, section gaps, card paddings, drawer
> chrome). Every value is classified against the density system (sonaloop-design "Spacing &
> density"): **token** (0/4/8/12/16/20/24/28/32/40/48 px) · **optical** (documented 1–3px
> hairlines/micro-nudges) · **em** (fractional px from the em-sized density-adaptive layer —
> buttons, inputs, entity rows, tabs — deliberately off the px grid) · **center** (resolved
> `margin: auto` of a measure). Anything else FLAGS; the script exits 1 while any flag
> remains, so the sweep is re-runnable as a gate.

**Before → after (flags per screen):** projects 4→0 · project-premium 7→0 ·
project-positioning 7→0 · project-filtered 7→0 · project-slideover 28→0 ·
project-slideover-ssr 28→0 · personas 4→0 · persona 16→0 · councils 5→0 · council 29→0 ·
synthesis 28→0 · decisions 5→0 · hypotheses 5→0 · asset 12→0 · project-files 5→0 ·
activity 4→0 · documentation 5→0 · palette 7→0 — **TOTAL 206 → 0**.

Representative fixes (the off-grid rules, all snapped to tokens): page chrome `26/30→24/32`,
proj-head top `22→24`, outline rows `7px/10px gaps→8px` (+ tree indent `10+n·26 → 8+n·24`),
phase summary `13/6/9 → 12/8/8`, round label `34→32` (now exactly icon-column 8+16+8), doc
grid `30→32`, rail `6→8` + h4 `10/6→8/8`, `.sec 26/18→24/16`, turn cards `13→12` & bare
`11/13→8/12`, q-rounds `22/10→24/12`, q-banner `11/14→12/16` (+ count-chip reserve
`64→48`), study lead `22→24`, finding/rec/segment rows `9/14/11/13→8/12`, filter bar
`10→12`, list `.group 18→16` & `.row 9/10/11→8/12`, docs tabs `22→24`, synthesis blocks
`26→24` & verdict `6/26→8/24`, plan drawer (`.psec/.ptask/.plan-fw` …) and the
open-questions panel — all in `web_assets.py` / the co-located `register_css` blocks; no
inline styles added (STYLE_BASELINE untouched at 35).

**Exemption list: empty.** No per-rule exemptions were needed; the only non-token classes
are the three documented SYSTEM categories above (optical 1–3px, the em density-adaptive
layer, auto-centering) plus the grid-derived outline tree indent (8 + n×24).

**Final conformance table** (distinct measured rule → classification; the per-screen run
lives in `/tmp/ux/w1-spacing-table.txt`, regenerate with
`uv run python scripts/ux_spacing.py`):

| element | property | computed | class |
|---|---|---|---|
| card | margin-bottom | 24px | token |
| card | margin-top | 8px | token |
| card | padding-bottom | 13.65px | em |
| card | padding-bottom | 15.75px | em |
| card | padding-left | 13.65px | em |
| card | padding-left | 15.75px | em |
| card | padding-right | 13.65px | em |
| card | padding-right | 15.75px | em |
| card | padding-top | 13.65px | em |
| card | padding-top | 15.75px | em |
| doc-grid | column-gap | 32px | token |
| doc-grid | row-gap | 32px | token |
| drawer-body | padding-bottom | 20px | token |
| drawer-body | padding-left | 24px | token |
| drawer-body | padding-right | 24px | token |
| drawer-body | padding-top | 20px | token |
| drawer-head | column-gap | 8px | token |
| drawer-head | padding-left | 16px | token |
| drawer-head | padding-right | 8px | token |
| drawer-head | row-gap | 8px | token |
| entity-row | column-gap | 11.05px | em |
| entity-row | padding-bottom | 9.1px | em |
| entity-row | padding-left | 11.7px | em |
| entity-row | padding-right | 11.7px | em |
| entity-row | padding-top | 9.1px | em |
| entity-row | row-gap | 11.05px | em |
| filter-bar | column-gap | 8px | token |
| filter-bar | margin-bottom | 2px | optical |
| filter-bar | margin-top | 12px | token |
| filter-bar | row-gap | 8px | token |
| finding-row | column-gap | 12px | token |
| finding-row | padding-bottom | 8px | token |
| finding-row | padding-top | 8px | token |
| finding-row | row-gap | 12px | token |
| h1 | margin-bottom | 4px | token |
| lead | margin-bottom | 16px | token |
| outline | margin-left | 146px | center |
| outline | margin-right | 146px | center |
| outline | padding-left | 24px | token |
| outline | padding-right | 24px | token |
| outline-row | column-gap | 8px | token |
| outline-row | padding-bottom | 8px | token |
| outline-row | padding-left | 8px | token |
| outline-row | padding-right | 8px | token |
| outline-row | padding-top | 8px | token |
| outline-row | row-gap | 8px | token |
| outlinecard | padding-bottom | 40px | token |
| outlinecard | padding-top | 8px | token |
| page-chrome | padding-bottom | 24px | token |
| page-chrome | padding-left | 32px | token |
| page-chrome | padding-right | 32px | token |
| page-chrome | padding-top | 24px | token |
| page-header | column-gap | 16px | token |
| page-header | row-gap | 16px | token |
| page-header-main | column-gap | 8px | token |
| page-header-main | row-gap | 8px | token |
| proj-chips | column-gap | 8px | token |
| proj-chips | row-gap | 8px | token |
| proj-head | margin-left | 146px | center |
| proj-head | margin-right | 146px | center |
| proj-head | padding-bottom | 12px | token |
| proj-head | padding-left | 24px | token |
| proj-head | padding-right | 24px | token |
| proj-head | padding-top | 24px | token |
| prop | column-gap | 12px | token |
| prop | row-gap | 12px | token |
| props-quiet | column-gap | 12px | token |
| props-quiet | row-gap | 12px | token |
| rail | margin-bottom | 28px | token |
| rail | margin-top | 20px | token |
| rail | padding-bottom | 20px | token |
| rail | padding-top | 8px | token |
| rail-h4 | column-gap | 8px | token |
| rail-h4 | margin-bottom | 8px | token |
| rail-h4 | row-gap | 8px | token |
| rec-row | column-gap | 12px | token |
| rec-row | padding-bottom | 8px | token |
| rec-row | padding-left | 8px | token |
| rec-row | padding-right | 8px | token |
| rec-row | padding-top | 8px | token |
| rec-row | row-gap | 12px | token |
| row-group | column-gap | 8px | token |
| row-group | margin-bottom | 2px | optical |
| row-group | margin-top | 16px | token |
| row-group | row-gap | 8px | token |
| section | margin-top | 24px | token |
| section | padding-top | 16px | token |
| study-lead | margin-bottom | 4px | token |
| study-lead | margin-top | 24px | token |
| tab | column-gap | 8px | token |
| tab | margin-bottom | -1px | optical |
| tab | padding-bottom | 7.176px | em |
| tab | padding-left | 9.568px | em |
| tab | padding-right | 9.568px | em |
| tab | padding-top | 7.176px | em |
| tab | row-gap | 8px | token |
| tabs | column-gap | 4px | token |
| tabs | margin-bottom | 24px | token |
| tabs | margin-top | 2px | optical |
| tabs | row-gap | 4px | token |
| topbar | column-gap | 12px | token |
| topbar | padding-left | 12px | token |
| topbar | padding-right | 12px | token |
| topbar | row-gap | 12px | token |
| turn-answers | column-gap | 12px | token |
| turn-answers | row-gap | 12px | token |
| turn-card | padding-bottom | 12px | token |
| turn-card | padding-bottom | 8px | token |
| turn-card | padding-left | 12px | token |
| turn-card | padding-right | 12px | token |
| turn-card | padding-top | 12px | token |
| turn-card | padding-top | 8px | token |
| turn-q | column-gap | 12px | token |
| turn-q | padding-bottom | 12px | token |
| turn-q | padding-left | 16px | token |
| turn-q | padding-right | 48px | token |
| turn-q | padding-top | 12px | token |
| turn-q | row-gap | 12px | token |
| turn-refs | margin-top | 12px | token |
| turn-round | column-gap | 12px | token |
| turn-round | row-gap | 12px | token |
| turn-rounds | column-gap | 24px | token |
| turn-rounds | row-gap | 24px | token |

### W2 — full-width filter bar

`.sl-filter-bar--grow` (new design-system modifier, vendored): the search slot stretches
(`flex: 1 1 220px`) so search · divider · Filter · chips span the FULL content measure.
Applied to every inspector bar (outline + all Library tabs); verified at 1280/1440/1680 on
both surfaces (`/tmp/ux/w2-bar-*.png`).

### W3 — one control vocabulary (header chrome)

Decision: THREE shapes, one family — all on `--sl-radius-sm` with the shared hover:
1. **Labeled actions** = `.sl-btn` (Plan, dialog buttons) — unchanged.
2. **Icon actions** = `.sl-iconbtn--ghost` (28px box): the favourite ★ (was a bare
   `.starbtn`), the "…" overflow summary (was a BORDERED iconbtn), the slide-over's
   expand ⤢ / close × (were bare `.sl-overlay-close`), the sidebar toggle. Same box,
   same hover, page header AND slide-over header.
3. **Status chips** = `.sl-toolbtn` (the Filter-button contract): the project run chip
   (`▶ Run · state`, was a 99px pill), the topbar "N runs" indicator (same), and the
   "N files" lens chip (was a `.pill`) — state colours ride as modifiers. The project
   header's chip row is one flex `pills` row (8px gap), so Run · files read as one toolbar.

### W4 — quiet refs ("Drew on:")

`render_ref` (web/_render.py) formats the raw memory-ref fallback: a leading
`YYYY-MM-DD HH:MM` timestamp becomes a quiet mono `11 Jun · 08:45` prefix (`ui.fmt_ts`),
an "Open loop:"/"Offener Loop:" marker a localized quiet italic label (`ref_open_loop`,
de+en), and the body word-trims at ~110 chars with a real ellipsis + full text on the
tooltip — same chip anatomy (icon · text) as every other srcchip. `.turn-refs` owns one
rhythm now (12px top, 4/8px wrap gaps, faint lead label `turn-refs__lbl`); the
hypotheses/surveys/syntheses pages route their ref lines through the shared `_refs_line`
instead of composing their own (−1 inline style).

Gate: `uv run pytest -x -q` 744 passed; `make ux UPDATE=1` refreshed all 36 goldens
(spacing shifts deliberate), follow-up `make ux` green.

### W5 — council threading (Q→A as a file tree)

Owner: answers should link to their question "über z.B. leichte Indentation, und dann
runtergehende und leicht angewinkelt laufende Linien (wie bei einem Art File-System)".
Implemented in the ONE statement renderer (`web/_render.py`, so council detail and every
report embed share it): the `.qround-a` answer column indents one 28px token under the
question banner and a pure-CSS connector draws the tree guides — each `.turn` card's
`::before` is the ELBOW (border-left + border-bottom with a 10px `border-bottom-left-radius`
corner, reaching up through the 12px gap, meeting the card exactly at the avatar's center
line, y=25), and each non-last card's `::after` continues the 1px spine down its own height.
The spine therefore descends from the question's underside, elbows into every answer, and
ENDS curving into the last card; one answer degrades to a single elbow. Hairline
`var(--line)` (dark-mode clean); connector geometry is drawing, not rhythm — the spacing
gate stays at 0 flags.

### W9 — one sentiment encoding (decided)

The web's donut re-encoded the SAME vote distribution that the proportional stance strip
already showed beside it. `_overview_html` (web/_synthesis.py) now renders the strip + its
legend as the single encoding — donut, `.dnrow` and `.donut` CSS deleted from the web layer;
council detail and the synthesis charts row inherit it. The DECK keeps its single donut card
(`services/_synthesis_pptx` untouched), and the design-system `pie_chart` stays in the
vendored library/catalogue. Pinned by `test_web_vote_overview_is_one_encoding`.

### W11 — the persona-attribution rule

Owner: "warum hat Artefakt 'prototype' keine Persona-Icons, obwohl da doch Sessions bei
sind?" ONE rule app-wide now, implemented as ONE helper (`web/ui.avatar_group` — the
vendored `.sl-avatar-group` cluster, max 4 avatars + a `.sl-avatar-group__more` "+n"
overflow chip; rows at 18px, detail headers at 22px, byte-identical classes everywhere):
wherever an artifact's DATA carries persona participation, the row AND the detail header
render the group. Wired: council rows/opener (now with honest +n overflow) · report/synthesis
rows + report cover (the voices' personas) · survey rows + detail (persona-sourced
respondents via `services.survey_respondent_personas`) · prototype rows + detail (session
drivers, BOTH kinds, via `services.prototype_participation` — also feeding the outline crew
and the now-combined honest `n_sessions`) · session rows + detail (a group of one) · projects
list rows (the cohort). The outline's local `.ol-crew` avatar overrides retired in favour of
the one contract. NEGATIVE rule (documented in `avatar_group`, pinned by
`tests/test_persona_attribution.py`): decision / hypothesis / note / asset carry no direct
participation → no avatars, ever.

Gate (W5/W9/W11): `uv run pytest -x -q` 751 passed (744 + the 7 new contract/encoding
tests); spacing sweep 0 flags; `make ux UPDATE=1` (24 of 36 goldens shift deliberately:
crew avatars on rows/covers, donut removal, council threading) + follow-up compare green.

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

- **H1 — RESOLVED (2026-06-12).** ONE shared splitter (`web/_synthesis.py::_verdict_split`) now
  feeds BOTH the verdict card (the lead) and the exec-summary section (the rest): exec renders
  from the first NON-consumed sentence — on the final showcase report it now opens "Trifft das
  Fenster auf eine harte Wand…" with zero verbatim overlap (`/tmp/ux/h1-exec.png`); when the
  card consumed everything, the honest fallback is no echo block at all.
- **H2** Donut + proportional strip encode the SAME distribution side by side (council sentiment
  block and the synthesis charts card) — pick one encoding per surface. Small renderer change +
  an owner taste call. **STAYS OPEN — owner call, deliberately not implemented.**
- **H3 — RESOLVED (2026-06-12).** The rail "Type: Decision" row dropped on council detail
  (reverses round 2: with the header mode pill it became an echo) — rail is now Project →
  Personas → stance counts → Created (`/tmp/ux/h3-rail-crop.png`); assets keep Type (real info).
- **H4 — RESOLVED (2026-06-12).** Identical per-question counts collapse into ONE section-level
  hint "5 responses per question" (new `n_responses_each` key de+en); per-row counts render
  ONLY when they differ (`/tmp/ux/h4-survey.png`).
- **H5 — RESOLVED (2026-06-12).** Root cause: `_pptx_charts` APPENDED a second `c:holeSize` to
  the doughnut/gauge plots (python-pptx's template already carries one) — the chart part was
  schema-invalid (CT_DoughnutChart allows ONE), so strict renderers dropped the native chart
  while the shape-drawn legend survived. `_set_hole_size()` now sets the existing element;
  re-export verified by XML/python-pptx introspection (ONE holeSize=62, series [1,1,1,2],
  doughnut graphicFrame on the votes panel; `/tmp/ux/deck-h5.pptx` + verification note) and
  pinned by `test_votes_donut_is_a_valid_native_chart`. The PIL verification rasterizer does
  not draw native charts — the panel reads empty THERE by tool limitation, not in PowerPoint.
- **H6 — RESOLVED (2026-06-12).** The lightbox gained a visible close × and a small caption
  (step number + action, e.g. "Step 0 · Look", fed by `data-caption` on the shot anchors);
  Esc/click-out unchanged (`/tmp/ux/h6-lightbox.png`).
- **G1–G5 stand** from round 2 (G1 prototype session heading; G2 report lifecycle pill;
  G4 avatar binaries in snapshots; G5 sidebar active-state rule), F5 stands for /runs.

### Gate

`uv run pytest -x -q`: **743 passed** (baseline 743, +0 — test updates replaced equals).
`make ux UPDATE=1` + follow-up `make ux`: **all 36 goldens match** (the date-format and label
fixes moved most screens deliberately). Ratchets unchanged: STYLE_BASELINE=35, frozen class
whitelist; no new `style=`, no new classes (one dead CSS rule removed).

### Gate (H follow-ups, 2026-06-12)

`uv run pytest -x -q`: **744 passed** (743 + the new H5 donut-validity pin).
`make ux UPDATE=1` + follow-up `make ux`: **all 36 goldens match** — council (H3 rail) and
synthesis (H1 exec) shifted deliberately; the other refreshed goldens moved only by load-time
relative timestamps. Ratchets unchanged: STYLE_BASELINE=35, frozen class whitelist (the new
lightbox close/caption live as `sl-*` contracts in co-located CSS/JS, not page classes).

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
