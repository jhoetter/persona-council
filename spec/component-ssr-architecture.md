# Component-based SSR Architecture — make the Python/SSR layer read like React

> **Status:** SPEC (build-ready, 2026-06-06). Authored after repeated UI-refactoring friction
> (LOC-budget fights, styles trapped in the wrong file, 150× manual `_esc`, per-page divergence).
> **Goal:** keep server-rendered HTML in pure Python — but structure it like a component framework
> (auto-escaping element tree, co-located CSS, typed view-models, thin routes). **No new runtime
> behavior**; routes stay read-only; the existing invariants (no in-process LLM text, zero hardcoded
> methodology vocab, grep gates) hold. Migration is **incremental and page-by-page**, each step gated
> by the full `pytest` suite + visual diff.

---

## 1. The problem (measured, 2026-06-06)
The `web/` layer already grew a real **component layer** (~29 functions returning HTML: `_layout`,
`_doc`, `_list_page`, `_properties_html`, `_relations_html`, `_session_card`, `_study_lead`, `_nav`,
`_page_rail`, `_icon`, `_pills`, `_star`, `_artifact_present`, …). But pages don't *compose* them —
they build large inline strings beside them. Concretely:

| Symptom | Measure | Root cause |
|---|---|---|
| Inline HTML blobs in routes | **162** `f'<…>'` in `_routes_pages.py` | pages aren't components |
| Manual escaping everywhere | **151×** `_esc(...)` (`_routes_pages`+`_synthesis`) | strings, not an escaping tree |
| Styles decoupled from markup | `CSS` is one ~700-line string; `.es-prose` was trapped in `_SYN_STYLE` (note page rendered unstyled) | no CSS co-location |
| LOC-budget fights | `_routes_pages.py` pinned at 799/800; constant one-lining | few big files, not many small components |
| Field-shape divergence | council `prompt`/`exec_summary` vs synthesis `goal`/`gesamtbild` | components take raw dicts, no typed props |
| Can't transform UI | string concatenation only | no element tree |

**Consequence:** every refactor hits a ceiling — you can only string-append, you must hand-escape, a
component's CSS lives in a different file, and the file-size cap punishes extraction. That ceiling is
exactly what we keep hitting.

## 2. Principles (the target shape)
1. **HTML is a tree, not a string.** A tiny element builder `h()` produces an auto-escaped node;
   text is escaped by default, trusted HTML is explicitly `raw()`. No component ever calls `_esc` by
   hand again.
2. **A component is `data → element`.** Pure function, typed input (a view-model, not a raw record),
   returns `Safe` HTML. Co-located with its CSS.
3. **CSS lives next to its component.** Each component module exports a `CSS` fragment; `_layout`
   assembles `BASE_CSS + Σ component fragments`. (We already do this for `_palette`/`_rail`.)
4. **Routes are thin.** `route = fetch → view-model → page_component(vm) → str`. No `<` in a route.
5. **One view-model per concept.** A resolver maps each record type to a typed VM (generalizes the
   `study_head()` idea from `methodology-presentation-from-data.md` §10) — so council and synthesis
   feed the SAME components.
6. **Many small files beat few big ones.** The ~800-LOC cap becomes natural (per-component modules),
   not a thing we fight. Re-tune the guard to reward small component files (see §7).

## 3. Design

### 3.1 The element builder (`web/_html.py`, new — zero deps)
```python
class Safe(str):                       # a string already safe to emit (won't be re-escaped)
    __slots__ = ()

def esc(x) -> Safe:                    # escape arbitrary text → Safe
    return x if isinstance(x, Safe) else Safe(html.escape("" if x is None else str(x)))

def raw(s) -> Safe:                    # mark trusted HTML (markdown render, icon svg) as Safe
    return Safe("" if s is None else str(s))

VOID = {"br","hr","img","input","meta","link","source"}

def h(tag, attrs=None, *children) -> Safe:
    """Element node. attrs: dict (None/False skip; True → bare attr; 'class_'→'class').
    children: str (escaped), Safe (kept), Iterable, or None (skipped)."""
    ...                                 # ~30 lines: render attrs + flatten/escape children
```
- **Auto-escaping**: any non-`Safe` child or attr value is escaped. This deletes the 151 `_esc`
  call-sites and the whole class of "forgot to escape" bugs.
- **Composition**: `h("div", {"class":"row"}, h("span", …), title)` nests; returns `Safe`.
- **Escape hatch**: `raw(_md(text))`, `raw(_icon(name))` for already-HTML fragments.
- Keep the existing `_esc` as a thin alias to `esc` during migration (no churn at call sites yet).

### 3.2 Component contract
- Signature: `def component(vm, ...) -> Safe`. Input is a **view-model** (dataclass / TypedDict),
  not a raw store record.
- Output is always `Safe` (built via `h()`), so composing components never double-escapes.
- Co-located CSS: the module defines `CSS: str` (a `<style>`-less fragment); registered once.

### 3.3 CSS registry (co-location)
- `web/_styles.py` (or extend `web_assets`): `register_css(fragment)` + `collect_css()`.
- Component modules call `register_css(CSS)` at import; `_layout` emits `<style>{collect_css()}</style>`.
- Migrate rules **out of** the monolithic `CSS`/`_SYN_STYLE` into the owning component, incrementally.
  End state: `CSS` holds only base/tokens; components own their rules. (Fixes the "trapped style" bug
  class and frees the big files.)

### 3.4 View-models (typed props)
- Per concept, a small dataclass + resolver in `services` (or `web/_vm.py` if purely presentational):
  - `StudyVM{question, answer_md, answer_label, voices, evidence, created, mode}` ← council OR synthesis
  - `ArtifactVM` (already effectively `_artifact_present`), `PersonaVM`, `ListRowVM`, …
- Components depend on the VM, never on `record["prompt"]` vs `record["goal"]`.

### 3.5 Page = component
- `web/pages/council.py: def council_page(vm) -> Safe` composing `hero()`, `study_lead()`,
  `voices()`, `properties_aside()`, `page_rail()`.
- Route shrinks to: `vm = council_vm(session, …); return _layout(title, council_page(vm), …)`.

## 4. Migration phases (each: implement → full `pytest` green → visual diff → commit+push)

- **C1 — Foundation (`_html.py`): `Safe`/`esc`/`raw`/`h` + unit tests** (escaping, nesting, void
  tags, attr rules, `class_`, None/booleans, iterables). `_esc` aliases `esc`. **No page changes.**
  *Accept:* `h()` round-trips known cases; XSS payload in a text child is escaped; `raw()` passes
  through; suite green.
- **C2 — CSS co-location mechanism**: `register_css`/`collect_css`; `_layout` uses it; migrate ONE
  component's CSS (e.g. `.es/.eyebrow/.qa-q/.es-prose` → a `study_lead` module) as proof. *Accept:*
  identical rendered CSS (text diff of the `<style>` content is a pure move); suite green.
- **C3 — POC: convert the council page** to `h()` + co-located CSS + `StudyVM` + `council_page()`.
  *Accept:* council page renders functionally identically (review visual screenshot + HTML diff —
  not byte-identical, since markup may improve); `_esc` count in the council route → 0; suite green.
  **This is the go/no-go gate for the whole effort.**
- **C4 — Roll out, one page per commit**: synthesis → persona → prototype → list pages → project →
  note/concept/section. Each via VM + page-component, each behind the suite + a screenshot.
- **C5 — Collapse the monoliths**: shrink `CSS`/`_SYN_STYLE` to base tokens; delete superseded
  f-string helpers; split `_routes_pages.py` into `pages/` modules; re-tune the LOC guard (§7).

## 5. Safety net
- `tests/test_web_smoke.py` + `exports/cohort/_charz.py` (route HTML hashes). For **mechanical**
  moves (C2) require byte-identical; for **improving** conversions (C3+) review the HTML diff +
  a Playwright screenshot, then re-bless the hash. Never commit with the suite red.

## 6. Library vs home-grown
**Decision: home-grown `_html.py`** (~40 LOC, zero deps, grep-gate-able, matches the repo's
minimal/controlled ethos). `htpy`/FastHTML are viable off-the-shelf alternatives (auto-escape, typed
elements) — revisit only if the home-grown builder proves limiting. Recorded so the choice is explicit.

## 7. Invariants / grep gates (added as the migration lands)
- **No hand-escaping in migrated modules**: `_esc(`/`html.escape(` count trends to 0 in `pages/`.
- **No raw HTML literals in routes**: a converted route contains no `<` literal.
- **No component CSS in the monoliths**: a component's rules live in its module, not in `CSS`.
- **LOC guard re-tuned**: keep the per-file bar but expect many small `pages/`/component files; the
  bar should no longer require cramming (revisit the 800 number if it forces it).
- All standing invariants unchanged (read-only UI; no in-process LLM text; zero hardcoded vocab).

## 8. Risks & mitigations
- **Hybrid double-escaping** (a plain-`str` component fed into `h()` gets escaped): migrate **leaf
  components first** (return `Safe`), wrap known-HTML in `raw()`, and keep `_esc==esc` so old code is
  unaffected. C1 ships before any page conversion.
- **Verbosity of `h()` for big trees**: acceptable; readability + safety win. Helper sub-components
  keep trees shallow.
- **Perf**: building a small object tree per request is negligible vs. f-strings; SSR already does
  string work.
- **Scope creep**: strictly one page per commit; C3 is the explicit go/no-go before C4.

## 9. Out of scope (for now)
Client-side interactivity beyond today's tiny vanilla JS; a virtual DOM/hydration; streaming. This is
SSR structure only.
