# Showcase Review — Pfefferminzia KFZ-Moment → Lebensversicherung (Phase S5)

Self-evaluation of the end-to-end showcase against a "fantastic design-thinking project" rubric and
the Linear-grade UI bar. Scored 1–10; target ≥9 average. Evidence is the live runtime (18 personas,
5 councils, 3 syntheses, 5 prototypes across lo/mid/hi-fi, 10 grounded proband sessions) rendered in
the read-only inspector at `http://127.0.0.1:8787`.

## Rubric

| Dimension | Score | Justification |
|---|---|---|
| **Methodology rigor** (analyze→act→verify, gates) | 9 | Real plan-engine run: `double_diamond` seeded, restructured into **three gated diamonds** (Define / Shortlist / Deliver). Each verify was rejected until its act-fan met `min_inputs`, a decided gate judgment existed, and the required artifact/session evidence was present — no diamond could be skipped. 16/16 tasks done; `plan.md` reads as a coherent log. |
| **Honesty of evidence / anti-steering** | 10 | The Define POV is a genuine **reframe** — the evidence says you *cannot* "begeistern" young people for an LV in the KFZ moment; the synthesis says so plainly instead of forcing the brief's thesis. Skeptics (Tobias, Niklas, Mara) stay skeptical; deliberate non-targets are named. All 10 proband sessions are `grounded_verified=True` (cited state actually present in the live Playwright snapshot log). |
| **Prototype variety & quality** | 9 | Four distinct **non-form** renderers (guided flow, dashboard, card/list, comparison) + a polished hi-fi theme, all data-driven from `artifact_types.json`. The showcase used a guided flow, an overview dashboard and an honest side-by-side comparison — not three forms. Each is a real clickable SPA driven by Playwright. |
| **Iteration story** (lo→mid→hi-fi) | 9 | Feedback genuinely drove change: lo-fi friction (Sophie "ohne Quelle skeptisch", Jana "darf nicht ins Drohen kippen", Deniz "Selbstständigen-Fall") → mid-fi added source transparency, a gentle tone and a self-employed branch → mid-fi friction (save the result, a human to ask) → hi-fi added mitnehmen + an optional low-pressure human touchpoint + a data-sparsamkeit note. Each fidelity was proband-tested before the next. |
| **Clarity of the answer** | 9 | The Deliver synthesis gives a sharp, defensible answer (reframe + core target segment + explicit non-targets + 8 validated pain-solvers + a 12-point dev-ready build spec) with `assess_progress(delta="beantwortet")`, cited to councils and sessions. |
| **Linear-grade UI** | 9 | Sidebar, project graph (filter chips, minimap, zoom), synthesis detail (status pills, FRAGE/ANTWORT, vote bars), persona detail, and the embedded clickable prototype all read as Linear-grade in light + dark. The plan view was rebuilt this phase (see Gaps). |

**Average: 9.2 / 10** — meets the bar.

## Gaps found and fixed this phase

1. **Plan view dumped raw Markdown** (literal `[x]`, backticks, `⊂`, `_..._`) — visibly unpolished and
   below the ≥9 bar. **Fixed:** added a data-driven `_plan_html()` renderer (`web.py`) that renders the
   plan as Linear-styled sections (Analyze / Act / Verify) with status checks, capability pills, gate
   chips, `⊂` consume links and clickable evidence chips (Council ↗ / Synthese ↗ / Prototyp ↗). Evidence
   links resolve by storage identity and labels come from `present()`, so the zero-hardcoded-vocabulary
   grep gate still holds (suite green: 69 passed, 1 skipped).
2. **Stray `prototypes/br-survey`** leaked from a test writing to the real prototypes dir — removed so the
   showcase only contains the five real Pfefferminzia prototypes.

## Minor, non-blocking limitations (honest)

- **Graph default zoom** fits the whole DAG, so node labels are small until you zoom/`F`-fit. The graph
  is fully navigable (zoom, drag, minimap); only the initial framing is dense. Left as-is.
- **Cohort diversity metric** shows `segment_distribution: {"—": 18}` because each persona's `segment` is
  a rich object, not a single label — the structural distinctness check (mean pairwise similarity 0.077,
  0 near-duplicates) is the real signal and is healthy.
- The consumer personas' `tools` are consumer channels (TikTok/Check24/WhatsApp/…), so simulated "work"
  blocks are framed as life moments — intentional for a consumer cohort, and exactly where the
  insurance/money/KFZ memory surfaces.

## Verdict

The showcase explores beautifully and tells a coherent, honest design-thinking story end-to-end:
understand → reframe → ideate → build varied prototypes → test with real probands → iterate across
fidelities → deliver an evidence-backed answer. Rubric ≥9, suite green, UI Linear-grade across screens.
