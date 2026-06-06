# Presentation-from-Data — Zero Hardcoded Methodology Values

> **Status:** IMPLEMENTED — milestones P1–P4 landed; full suite green. Amends `spec/methodology-constellations.md` (the tag-driven
> model) with a strict **presentation contract**: the UI must render a methodology **entirely from
> data authored via MCP** — no methodology- or artifact-specific *value* may live in code.
> **User directive (verbatim intent):** "it is JUST methodology generated via LLMs in the MCP that
> allow us to do this methodology, nothing hardcoded." So `lofi`/`midfi`/`prototype`/labels/colors/
> icons must NOT appear in `web.py`/`prototypes.py`; they are data.
> **Leitsatz (unchanged):** capabilities via MCP; host/subagents author ALL text; no in-process LLM
> text-gen; OpenAI = embeddings + images only; structure enforced, dynamics LLM-judged.

---

## 1. The problem — the engine is tag-agnostic, the UI is not
`spec/methodology-constellations.md` made the *engine* fully tag-driven (proven: an invented
methodology with `survey` artifacts and invented tags runs unchanged). But the **UI and the artifact
subsystem still hardcode specific methodology values.** Audit (exact lines):

| # | Hardcoded value | Where | Why it's wrong |
|---|---|---|---|
| 1 | `{"lofi":"lo-fi","midfi":"mid-fi"}` + `"Artefakt"` | `web.py` `_fid_label` | a per-value label table — a `survey` artifact renders as the fallback word |
| 2 | `tags = {"prototype"}` base | `web.py` `_proto_tags` | every artifact is assumed to be a "prototype" |
| 3 | `"▢"`, `"Prototyp"`, color `#00897b` | `web.py` proto node build | artifact glyph/label/color baked in code |
| 4 | `◆`/`◇` keyed off `mode` string | `web.py` strip | a glyph table keyed to a value name |
| 5 | `TEMPLATES = {"spa-min":"midfi","spa-sketch":"lofi"}`, `fidelity` default `"midfi"`, template→fidelity map | `prototypes.py` | artifact types/fidelities are a closed code vocabulary; only 2 templates allowed |
| 6 | "Artifact" == the `Prototype` entity (`list_prototypes_artifacts`, `graph["prototypes"]`) | `services.py`/`web.py` | there is no generic artifact concept; non-prototype artifacts can't exist cleanly |

(For contrast, what is **already correct**: columns/positions from the `consumes` DAG; diamond
geometry from `fan→waist`; `_theme_color` = a hash of the tag string into a palette; the strip's
capability label = the step's first tag. These are *generic functions of data*, with no per-value
table — they stay.)

---

## 2. The contract — only three legitimate sources of any rendered value
Every label, color, icon, glyph, grouping or shape the UI shows for a methodology MUST come from
exactly one of these — and **nothing else**:

- **(S1) Verbatim data** — the raw string the host authored via MCP: a tag (`explore`, `survey`,
  `lofi`), a step `name`, an `artifact_type`, a `role`. Shown as-is.
- **(S2) Optional `presentation` metadata** — an OPTIONAL block on a tag / artifact-type / step,
  authored via MCP (in the suggestions data or the methodology spec): `{label?, color?, icon?,
  glyph?, short?}`. The UI uses it when present.
- **(S3) A deterministic generic function of the data/structure** — e.g. column = longest-path
  depth over `consumes`; diamond = geometry of a `fan→waist`; color = `hash(tag) → palette`; the
  fan/waist glyph = a pure function of the step's *structural role* (does it fan or converge),
  not of any value string. Contains **no per-value table or per-value branch.**

**Forbidden (the acceptance test greps for these):** any code map or branch keyed to a specific
methodology/artifact *value* — `{"lofi": …}`, `{"prototype"}`, `if role == "spec"`, `glyph =
"◇" if mode == "diverge"` *as a value lookup*, `TEMPLATES = {"spa-min": "midfi"}`, the literal
strings `"lofi"`/`"midfi"`/`"prototype"`/`"Prototyp"` anywhere in `web.py`/`prototypes.py`/the
graph builder.

### 2.1 Resolution order for a displayed value
```
display(x) = x.presentation.<field>            # S2, if the data carries a hint
          ?? generic_fallback(x)               # S3: hash-color / raw-string / structural-glyph
```
A value is **never** looked up in a code table of specific names.

---

## 3. The `presentation` block (authored via MCP, optional everywhere)
Add an OPTIONAL `presentation` object wherever the data already carries a vocabulary, all fields
optional:
```
presentation: {
  label?:  string     # human label (else: the raw tag/name verbatim)
  short?:  string     # compact chip label (else: label)
  color?:  string     # CSS color (else: hash(tag) -> _THEME_PALETTE)
  icon?:   string     # an icon name from the existing _icon() set, or an emoji/glyph (else: none)
  glyph?:  string     # node/shape glyph (else: structural default — fan vs waist)
}
```
It may appear on:
- **capability / role / artifact-type tags** in `suggestions/*.json` (served by `suggest_*`),
- a **step** in a methodology spec (`step.presentation`),
- an **artifact type** in the artifact registry (§4).

Because suggestions + methodology specs are authored via MCP by the host/LLM, **all presentation is
data the host controls** — exactly "JUST methodology generated via LLMs in the MCP." Seeding the
built-ins' hints (e.g. `lofi → {label:"lo-fi", color:"#00897b"}`) lives in `suggestions/`, not code,
so the current look is preserved **without a single value in `web.py`.**

---

## 4. Generalize the artifact subsystem (the core change)
"Prototype" stops being *the* artifact entity and `lofi/midfi` stop being a code vocabulary.

### 4.1 A generic `Artifact`
An artifact is a typed, tagged record (the existing `Prototype` table is renamed/wrapped, or kept
as the storage backing for `type == "prototype"`):
```
Artifact: { id, project_id, step, type: string, tags: string[], name,
            presentation?, run?, entry?, path?, created_at }
```
- `type` is a **free tag** (e.g. `prototype`, `survey`, `journey-map`) — matched by tag-equality in
  the engine's INV-ARTIFACT (already generic).
- `tags` carry discriminators (e.g. `lofi`/`midfi`) — also free.
- `presentation` (optional) gives label/color/icon; absent → generic fallback (label = `type`,
  color = `hash(type)`).
- The graph builder exposes `graph["artifacts"]` (generic); `graph["prototypes"]` becomes an alias
  (back-compat) = artifacts with `type == "prototype"`.

### 4.2 Artifact-type registry (data, MCP-served) replaces `TEMPLATES`
`suggestions/artifact_types.json` (already exists) becomes the source of truth for renderers too:
```
{ "tag": "prototype",
  "renderer": "spa",                  # which builder/template family to use (data, not a code enum branch)
  "discriminators": [
     {"tag":"lofi","template":"spa-sketch","presentation":{"label":"lo-fi"}},
     {"tag":"midfi","template":"spa-min","presentation":{"label":"mid-fi"}}],
  "presentation": {"label":"Prototyp","icon":"projects","color":"#00897b","glyph":"▢"} }
```
`scaffold_artifact(type, tags, …)` looks up the renderer/template from this data; there is no
`TEMPLATES` map and no `fidelity in {"lofi","midfi"}` check in code. A new artifact type = a new data
entry (+ optionally a new renderer template file), never a code edit. (`fidelity` is retired as a
typed field; it is just one of `tags`.)

### 4.3 UI renders an artifact from data
The artifact graph node + viewer read `artifact.presentation` (S2) or fall back (S3):
- label = `presentation.label` ?? `artifact.type`
- chip/discriminator = `presentation.short` of the matching discriminator tag ?? the raw tag
- color = `presentation.color` ?? `hash(artifact.type)`
- glyph/icon = `presentation.glyph/icon` ?? none
No `lofi`/`midfi`/`prototype`/`Prototyp`/`#00897b`/`▢` literal remains in `web.py`.

---

## 5. The shape glyph (◇/◆) — make it structural, not a value lookup
The diamond strip glyph must not be `"◇" if mode == "diverge"` *as a string lookup*. Instead:
- The engine already derives a step's **structural role** (fans vs converges) from `breadth`/
  `consumes`/node-count. Expose a boolean/derived `is_fan` on the step.
- The glyph = a fixed **geometric** rendering of that boolean (hollow for a fan, filled for a
  waist) — a single structural mapping, not a per-tag/per-value table — OR `step.presentation.glyph`
  when the data supplies one. This keeps it generic (S3) and overridable (S2).

---

## 6. Boundary: app chrome vs methodology vocabulary
The app's OWN navigation words ("Filter", "Legend", "Open questions", section headings) stay in the
`t()` i18n tables — that is product chrome, not methodology vocabulary. The rule applies to
**methodology/artifact vocabulary**: anything that names a tag, role, capability, artifact type,
fidelity, step, or their presentation. Those come from data (§2), never `t()` and never a code map.
A noun like the artifact node's "Prototyp" is methodology vocabulary → it moves to data; a noun like
the panel header "Prototypen" (the generic artifacts panel) may stay as chrome **only if** it no
longer implies a single artifact type (rename to the generic "Artefakte"/"Artifacts").

---

## 7. Tags as first-class, filterable (carry over the open item)
Independent of presentation: a step's open tags must be **filterable** like theme tags. The graph
builder attaches each node's step tags to its filter facet, and the filter chip vocabulary is the
**union of tags actually present on nodes** (not the LLM theme list alone). This is pure data
plumbing (no values), and it makes the capability/role tags filterable for every methodology.

---

## 8. Milestones (each with a failure-proof acceptance test)
- **P1 — Presentation contract + fallbacks:** add the optional `presentation` block + a single
  `present(x)` resolver (S2→S3). Seed the built-ins' hints in `suggestions/`. **Accept:** grep proves
  `web.py` contains no `"lofi"`/`"midfi"`/`"prototype"`/`"Prototyp"`/`#00897b`/`▢` literal; the
  built-ins look identical (hints come from data).
- **P2 — Generic Artifact + registry:** generic `Artifact` (+ `graph["artifacts"]`), artifact-type
  registry replaces `TEMPLATES`/`fidelity`-enum; `scaffold_artifact` resolves renderer from data.
  **Accept:** a methodology authored via MCP with an **invented** artifact type (`journey-map`,
  discriminators `draft`/`final`) scaffolds, renders its node with a label/color **from its data**,
  and routes in the graph — with **zero** code changes and no value literal in `prototypes.py`.
- **P3 — Structural glyph + filterable tags:** glyph from structure/`presentation`; step tags
  filterable (union vocabulary). **Accept:** an empty step draws no diamond; the capability/role
  tags appear as filter chips and filter the graph; grep shows no value-keyed glyph table.
- **P4 — Grep gate in CI/tests:** a test that fails if any forbidden literal (§2) reappears in
  `web.py`/`prototypes.py`/the graph builder. **Accept:** the test is green and would fail on a
  regression (verified by a temporary re-introduction).

---

## 9. Amendments
This spec amends `spec/methodology-constellations.md`: the constellation model already makes the
*engine* tag-driven; this adds the **presentation-from-data** contract so the *UI and artifact
subsystem* carry zero methodology/artifact values. After approval, implement P1–P4; the interim
`_fid_label` helper (itself a violation) is removed by P1.

---

## 10. Cross-entity STUDY contract — divergent field names block one-component rendering (GAP, found 2026-06-06)
**Context:** A Linear-consistency pass unified every detail page onto one shell (hero → content →
Properties/Relations aside → minimap) and one *Question → Answer/Finding* typographic block
(`_study_lead` + global `.es/.qa-q/.eyebrow/.es-prose`). Doing so surfaced a **data-contract gap**,
not a style gap.

**Finding.** Council and synthesis are both *studies* (a question + an answer/finding + voices +
cited evidence), yet their MCP-authored records expose the SAME semantic roles under DIFFERENT keys:

| role | council record | synthesis record |
|---|---|---|
| the question | `prompt` | `goal` ‖ `start_input` |
| the answer / finding (rich md) | `exec_summary` (fallback `summary`) | `gesamtbild` |
| answer label | (implicit "Finding") | `answer_exec_summary` |
| voices | `turns` | `voices` / via `council_ids` |

**Consequence.** The UI can only stay consistent by mapping per-type at the call site (council passes
`exec_summary`+"Finding"; synthesis passes `gesamtbild`+`goal`+"Answer"). Today the *values exist on
every record* (verified: all 7 councils have `prompt`+`exec_summary`; both syntheses have
`goal`+`gesamtbild`) — so **no data patch was needed**; the fix was presentation-only (`_study_lead`,
global typography). But the divergent shape is fragile: any new study-like entity must re-map, and a
methodology that omits one of these fields silently renders an empty block.

**Required methodology change (so data always fits the UI).** Normalize a **study head contract** —
either:
- (a) a services resolver `study_head(record) -> {question, answer_md, answer_label, voices}` that the
  UI calls for ANY study entity (council/synthesis/future), mapping the per-type keys in ONE place; or
- (b) have `record_council` / `record_synthesis` (and their MCP brief prompts) populate normalized
  keys (`question`, `answer`, `answer_label`) alongside the methodology-specific ones.
Prefer (a) — it keeps the authored records methodology-rich while giving the UI a single contract;
the brief prompts then only need to guarantee the source fields are non-empty.

**Status:** presentation unified (done); contract resolver = TODO (no data migration required when
done, since the source values already exist).
