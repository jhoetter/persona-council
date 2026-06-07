# Roadmap — architecture cleanup before further feature work

Status: **R1–R3 DONE** (2026-06-06). All three structural items shipped and verified — see the per-item
"✅ Done" notes below. This is the actionable tracker for the three structural items called out
after the component-SSR conversion (C1–C4 done; see `spec/component-ssr-architecture.md` §10). Each item
is independently shippable, ordered by dependency/risk, and verifiable with the existing harness. Detail
for the CSS work lives in `spec/design-system.md`; this file is the *sequence*.

**Shared toolkit (all items):**
- **Golden-diff harness** `/tmp/verify.py` — re-render all ~23 pages via `TestClient`, diff `<body>`
  against `/tmp/g.json` (whitespace/entity-normalized). "byte-identical body" = pixel-identical.
- **Burndown ratchet** `tests/test_web_burndown.py` — must stay green (no new hand-HTML).
- **LOC budget** `tests/test_loc_budget.py` (bar 800) and **full suite** (110 tests) green at every commit.
- Workflow per step: change → `verify` → suite → commit → push. One file/concern per commit.

---

## R1 — Shadowing guard (do FIRST: cheap, protects R2/R3)

> ✅ **Done.** `tests/test_no_render_name_shadowing.py` (AST guard) added; 8 offenders renamed. Both this and the burndown ratchet switched to `rglob` to cover `web/pages/`.

**Why.** Loop/local vars named `h` / `raw` / `fragment` / `t` silently shadow the `h()` builder and the
i18n `t`. This bit us ~4× during C4 (`for h in hits`, `x,y,w,h=…`, `raw=lines[i]`, `for t in …`). An AST
scan today finds **7 live offenders** (benign now, but footguns): `_components.py:364` (`raw`),
`_graph.py:295/497/499/562` (`t`), `_synthesis.py:154/389` (`t`).

**Scope.** (a) a test that fails on any such shadow; (b) rename the 7 existing offenders.

**Approach.**
1. Add `tests/test_no_render_name_shadowing.py`: walk each `sonaloop/web/*.py` AST (skip
   `_html.py`, `_i18n.py`), collect local binding targets (`For.target`, `Assign.targets`,
   `comprehension.target`, function args, `with`/`except` as-names, walrus) whose `Name.id` ∈
   `{h, raw, fragment, esc, Safe, t}`. Fail listing `file:line name`. Absolute rule — these names are
   always the import in web modules.
2. Rename the 7 offenders: geometry `h`→`bh` (already done in `_graph`, re-confirm), `raw`→`line` in
   `_md`, `t`→`task`/`turn`/`thread` in the `_graph`/`_synthesis` loops. Pure local renames.

**Verify.** New test green; golden body byte-identical (renames change nothing rendered); suite green.

**DoD.** `test_no_render_name_shadowing` passes with zero offenders; it's wired into the suite.

**Risk.** Minimal (local renames + a static test).

---

## R2 — Split `_routes_pages.py` (778 LOC) into a `web/pages/` package

> ✅ **Done.** `_routes_pages.py` removed → `web/pages/` (`_ctx`, `_calendar`, `personas`, `councils`, `syntheses`, `projects`, `library`); largest module 195 LOC. Pure move, golden body byte-identical, re-exports preserved.

**Why.** It's at the 800 bar with no headroom; the next page added pushes it over. It's one giant
`register_pages(app)` closure with every route nested inside — hard to navigate and to test in isolation.

**Scope.** Move route handlers into per-entity modules; keep rendered output identical and preserve the
public import surface (`web/__init__.py` re-exports `_calendar_html`, `_calendar_tabs`, `_event_chip`,
`_period_calendar_html`, `_memory_html`, `_projects_page`).

**Target structure.**
```
web/pages/__init__.py     # register_pages(app): calls each module's register(app)
web/pages/_calendar.py    # _calendar_html/_calendar_tabs/_event_chip/_period_calendar_html
web/pages/personas.py     # persona detail, /memory (_memory_html), /activities
web/pages/councils.py     # council list + detail
web/pages/syntheses.py    # synthesis list + detail
web/pages/projects.py     # projects index, project detail, /plan, /meta
web/pages/prototypes.py   # prototype detail   (list stays in _routes_lists)
web/pages/library.py      # sections, notes/concepts, /icons, misc
```
Each route is currently self-contained (creates its own `Store()`, uses module-level imported helpers),
so the only thing the closure provides is `@app.get`. Convert each nested handler to a module-level
function registered via a per-module `register(app)`; `pages/__init__.register_pages` aggregates.
`web/__init__.py` imports the re-exported names from their new homes.

**Approach (incremental, one module per commit).** Stand up `web/pages/` with `_calendar.py` first
(pure helpers, no routes) → verify → then move one entity module at a time, deleting that block from
`_routes_pages.py` as it lands, until `_routes_pages.py` is gone (or a thin shim). Keep `register_pages`
importable from `web` throughout.

**Verify.** Golden body **byte-identical** after every move (route output is unchanged — this is a pure
code move). Suite + the public-surface imports green.

**DoD.** `_routes_pages.py` removed (or ≤ ~40-line shim); every `web/pages/*.py` < 400 LOC; all
re-exports intact; golden byte-identical; LOC budget green with headroom.

**Risk.** Low — output identical, golden-verified. Main care: import wiring + the re-export surface.

---

## R3 — C5: co-locate CSS into components; shrink the monolith

> ✅ **Done.** CSS co-located into component `register_css` fragments; `_SYN_STYLE` deleted; `web_assets.CSS` now 295 lines (base only). Verified by a CSS rule-set differ AND a computed-cascade diff (last-wins per selector+property) that is IDENTICAL across all 23 pages vs pre-R3 — zero flips. Doc-layout grid (`@media`-entangled) + shared `.es-prose` intentionally remain base.

**Why.** Markup is componentized but **styles aren't** — `web_assets.CSS` is still a 759-LOC global blob,
so a component isn't self-contained (markup in its module, CSS elsewhere). This is C5 from the
component-SSR spec and Phase 4 of `spec/design-system.md`.

**Scope.** Move each component's rules from `web_assets.CSS` into a `register_css("""…""")` next to that
component (the mechanism exists; `collect_css()` is already emitted in `_layout`). Delete `_SYN_STYLE`
(fold into `_synthesis`'s `register_css`). Leave **base only** in `web_assets.CSS`: tokens, reset,
`body`, `.muted/.small/.faint`, the app shell (sidebar/topbar/usermenu), and `.es-prose`.

**Order (leaf → engine; verify each move).** chip primitive + `_label`/`_pills`/`_avatar` →
`_crumbs`/`_empty_state`/`_hero`/`_study_lead` → `_doc` grid + `_rail` → detail panels (`_detail`) →
synthesis (`_SYN_STYLE` + blocks/voices/charts) → graph/outline/plan → calendar/memory.

**Cascade caveat (the real risk).** `collect_css()` is emitted *after* `CSS` in `<style>`, so a moved
rule shifts later in source order. Where specificity ties exist, order matters. Mitigate:
1. Move in the leaf→engine order above (low-specificity, self-scoped rules first).
2. Verify per move with a **CSS rule-set diff** (extract all selector→declaration pairs from the rendered
   `<style>`; the *set* must be unchanged — only order moved) in addition to the golden body check.
3. Eyeball cascade-sensitive surfaces (chips, cards, hover/active states) against the running app.

**Verify.** Golden body byte-identical; CSS rule-set identical (set diff); visual spot-check on the
running app per engine.

**DoD.** `web_assets.CSS` ≤ ~300 LOC (base only); `_SYN_STYLE` deleted; every component owns its CSS via
`register_css`; an optional new gate asserts no component-specific selector remains in `web_assets.CSS`.

**Risk.** Medium — the only cascade-sensitive item here. Hence last, smallest moves, per-move verify.

---

## Sequence & after

**Order:** R1 → R2 → R3. R1 guards the renames in R2/R3; R2 is a safe pure-move; R3 is cascade-sensitive
so it goes last on the now-clean, guarded base.

**Then (separate, needs your eye):** the *visual* design-system phases — `spec/design-system.md`
Phase 2 (map raw px → the `--t-*`/`--s-*` scale, rounding in-betweens) and Phase 3 (unify the 7 chip
variants into one primitive). Those are judgment calls flagged `[needs review]` and come after this
structural cleanup, with the running app and Linear references.
