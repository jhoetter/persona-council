# Design system — toward an ideal, Linear-grade, component-owned UI

Status: **audit + plan** (2026-06-06). Follow-on to `spec/component-ssr-architecture.md` (C1–C4 done:
every page now renders through the `h()` builder). This spec defines the *design* layer that those
components should share, and the phased plan to get there. Visual changes that change pixels are flagged
**[needs review]** — they should be eyeballed against the running app before landing.

## 1. Where we are (audit)

**Good, keep:** the token foundation is already Linear-oriented — `--accent:#5e6ad2` (Linear's indigo),
a complete light/dark palette via `:root` + `[data-theme]`, `--radius`/`--radius-sm`, `--ease`,
`--shadow-sm`/`--shadow-lg`, Inter with `letter-spacing:-0.003em`. The IA, the doc grid (`_doc` d1/d2/d3),
the sticky Properties/Relations rail, and the section minimap are all coherent.

**The gaps (measured):**
- **Type-scale sprawl — the #1 issue.** 18 distinct `font-size` values are in use
  (10, 10.5, 11, 11.5, 12, 12.5, 13, 13.5, 14, 14.5, 15, 16, 17, 18, 21, 24, 26 px). Headings alone span
  7 sizes. A Linear-grade system uses ~7 steps. → define a **type scale** and map every use to it.
- **No spacing scale.** Padding/margins are raw px (4/6/8/9/10/11/12/14/16/18/22…). → an **8px-based
  spacing scale** (with 2/4/6 for tight inline) tokenized as `--s-1…--s-8`.
- **CSS not yet component-owned.** Most rules still live in the `web_assets.CSS` monolith (756 LOC)
  rather than next to the `h()` component that uses them (`register_css`). This is **C5** from the
  component-SSR spec. Co-location is what makes a component *self-contained* (markup + style together).
- **Minor inconsistencies to normalize:** card padding varies (`11px 13px` vs `14px` vs `16px`);
  muted-label treatment (`.muted small` vs `.ihint` vs `.eyebrow`) overlaps; pill/chip variants
  (`.pill`, `.lbl`, `.rgchip`, `.mchip`, `.segchip`, `.axchip`, `.gate`) have drifted in
  padding/radius/size and should resolve to one chip primitive with modifiers.

## 2. The ideal — tokens first

**Type scale** (CSS vars; one ramp, semantic aliases):
```
--t-display:24px/1.25 650   (page H1 / hero title)
--t-h2:15px/1.35 600        (section H2 / .bh)
--t-h3:13px/1.4 600         (card H3)
--t-body:13px/1.5 400       (default)
--t-sm:12px/1.45 400        (.small, meta)
--t-xs:11px/1.4 500         (chips, eyebrows, nav-head)
--t-mono-num: tabular-nums for counts
```
Collapse 18 → 7. The handful of in-between sizes (13.5/14.5/12.5) round to the nearest step
**[needs review]** — most are ±0.5px and visually indistinguishable.

**Spacing scale:** `--s-1:4 --s-2:8 --s-3:12 --s-4:16 --s-5:20 --s-6:24 --s-8:32` (+ inline 2/6 kept as
literals only inside chips). Card padding standardizes to `--s-3 var(--s-4)` (12/16).

**One chip primitive:** `.chip` (radius 999, `--t-xs`, `2px 8px`) + modifiers `.chip-soft/-outline/-dot`.
`.pill/.lbl/.rgchip/.mchip/.segchip/.axchip/.gate` become modifiers or aliases of it.

## 3. Component ownership (C5, now unblocked)

Now that every view is an `h()` component, move each component's rules out of `web_assets.CSS` into a
`register_css("""…""")` next to it (the mechanism already exists and is emitted via `collect_css()`):
- leaf: `_hero`, `_study_lead` (done), `_avatar/_label/_pills`, `_crumbs`, `_empty_state`, the chip
  primitive, `_doc` grid, `_rail`, palette (done).
- engines: synthesis blocks (`_SYN_STYLE` → `register_css`, then delete `_SYN_STYLE`), voices panel,
  sentiment charts, graph/outline, plan, calendar, memory.
What remains in `web_assets.CSS` after the sweep = **base only**: tokens, reset, `body`, `.muted/.small`,
the app shell (sidebar/topbar), and `.es-prose`. Target: monolith ≪ 300 LOC.

**Cascade caveat:** `collect_css()` is emitted AFTER `CSS` in `<style>`, so a moved rule changes order.
Move in dependency order and verify byte/visually per move (golden-diff for structure, eyeball for
cascade). This is why C5 belongs here, with the design pass, not as blind churn.

## 4. Consistency rules (the "same everywhere" contract)

- Every detail page = `_hero` + content column (max 900) + Properties/Relations rail (280) + minimap.
  (Already true post-C4 — keep it as an invariant, don't special-case.)
- Section heading = `<h2 class="bh">` at `--t-h2`; card heading = `<h3>` at `--t-h3`. No ad-hoc sizes.
- Muted helper text = one class (`.ihint`), eyebrows = one class (`.eyebrow`); retire the overlaps.
- Counts use tabular-nums; dates render `YYYY-MM-DD`; empty sections render an `_empty_state`, never a
  bare empty box (already enforced in several engines — make it universal).

## 5. Plan (phased; each phase verifiable)

1. **Tokens (additive, zero pixels):** add `--t-*` and `--s-*` to `:root`. No rule changes yet → golden
   byte-identical. Lands safely now.
2. **Map to scale [needs review]:** replace raw font-sizes/paddings with the tokens, rounding the
   in-betweens. Per-file, eyeball each against the running app (the rounding is the only visual delta).
3. **Chip primitive [needs review]:** unify the chip variants; verify each surface.
4. **C5 co-location (structural):** move CSS into `register_css` per component, dependency-ordered,
   verifying per move; shrink `web_assets.CSS` to base; delete `_SYN_STYLE`.
5. **Consistency sweep:** apply §4 rules where any page still deviates.

Phase 1 is safe to land immediately; 2–3 need the user's eye (rounding/unification are judgment calls);
4 is mechanical-but-cascade-sensitive; 5 is cleanup. Tools: the running app (`make dev-forwarded`), the
golden-diff harness (`/tmp/verify.py`) for structure, and Mobbin (Linear references) for the polish bar.
