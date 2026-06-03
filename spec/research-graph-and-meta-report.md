# Research Graph & Meta-Report — Specification

> **Status:** Vision spec / design proposal (not yet built). Authored 2026-06-03.
> **Scope:** Generalize Persona Council from *single study arcs* into a **persistent,
> themed research graph per project**, navigable and extendable entirely via MCP, with
> a **second-order Meta-Report** that synthesizes the whole graph into one document.
> **Leitsatz (unchanged):** nothing hardcoded; MCP exposes capabilities; the host agent
> authors all text (`brief_* → author → record_*`); every claim traceable to a council;
> personas non-directional (no nudging toward a product thesis without evidence).

---

## 0. TL;DR

Today a **Study** (called an *analysis* in the code) is one arc: a statement/goal →
a chain of **Councils** → one **Synthesis** report, and the synthesis already proposes
the *next* council question. In practice research never stops at one arc: a study about
*pain points* spawns a study about *UX*, which spawns one about *pricing*, which spawns
two more. The real shape is a **graph of studies**, themed and ordered, that grows over
time around a **Project**.

This spec defines that graph as a first-class structure:

- a **Project** container that owns a themed graph of Studies and references a **shared,
  reusable Persona library**;
- explicit **edges** between Studies (`spawned_from`, `refines`, `contrasts`, …) and
  LLM-assigned **theme tags**;
- an MCP surface to **build, navigate, and reason over the whole graph**;
- a **Meta-Report**: a synthesis-of-syntheses that reads the graph topology *and its
  build order*, derives an outline, and authors the report section by section — every
  section traceable down to councils.

The differentiator vs. instant "virtual panel" tools (e.g. experial.ai) is exactly this:
**depth, longitudinality, and provenance** — a research *body of knowledge* that
compounds, not one-shot dashboard answers.

---

## 1. Vision & Motivation

### 1.1 Why a graph
A single synthesis answers one question. But each answer **reframes** the problem and
surfaces new questions. The `Synthesis.next_council_question` field already encodes one
such edge — but only *within* one arc. The moment a synthesis spawns a *different* study
(not just another council on the same question), we are building a graph and have no
structure to hold it. Symptoms today: many syntheses, manual looping, "ideas for two
more and two more", no way to see how they relate or to report on the whole.

### 1.2 The worked example (the canonical demo)
One seed question fans out into a coherent research tree — this is the example to design
against:

```
[Project: "Tool X for role Y"]
        │  seed: "What are your biggest pains?"
        ▼
   Study A — Pain discovery ───────────────┐ (theme: pains)
        │ spawned_from                       │ spawned_from
        ▼                                    ▼
   Study B — "How must the UX be?"      Study C — "What would you pay / how priced?"
        │ (theme: ux)                        │ (theme: pricing)
        ├─ spawned_from                      └─ spawned_from
        ▼                                    ▼
   Study D — "Onboarding bar"           Study E — "Per-seat vs per-project"
        ⋮                                    ⋮
                 ▼  (all of the above)
        [Meta-Report: the whole project, derived from the graph]
```

Each node is a real Study (council chain → synthesis). The edges capture *that pricing
and UX were derived from the pain study*. The Meta-Report later reconstructs this and
turns it into a structured document.

### 1.3 Market reference (keep in mind, do **not** copy)
experial.ai ("Virtual Panels") validates that *continuous synthetic research* is a real
category, and its **use cases are a useful catalogue** (see §10). But its model is
**query → panel → instant dashboard**: broad, fast, shallow, one-shot; by its own pages
it "lacks detail on report formats, data synthesis methodologies, or how findings are
structured." That gap is our thesis. We are not building a faster panel; we are building
a **compounding, traceable research graph + meta-report** on top of memory-grounded,
debating personas. Borrow their *use-case breadth* as inspiration, not their product shape.

### 1.4 What "done" looks like
- A user can open a **Project**, run a seed Study, and from its result let the host agent
  propose and run follow-up Studies — each placed in the graph with edges + theme tags.
- At any time the agent can **see the whole graph** (nodes, edges, tags, order, open
  questions, dissent) via MCP and decide what is worth pursuing next.
- One command produces a **Meta-Report**: an outline derived from the graph, then authored
  section by section, each claim traceable to a Study → Council → persona voice.

---

## 2. Concepts & Vocabulary (with collision warnings)

Three levels of granularity plus a container and a meta layer:

| Term | What it is | Backing entity (today) |
|---|---|---|
| **Council** | one debate among personas (turns, votes, exec_summary) | `CouncilSession` (exists) |
| **Study** (a.k.a. *analysis*) | one arc: statement/goal → chain of Councils → one Synthesis report | `Synthesis` (exists) |
| **Project** | NEW: a themed **graph of Studies** + a referenced persona set; the unit of continuous research | new `Project` entity |
| **Theme tag** | NEW: LLM-assigned label on a Study (`pains`, `ux`, `pricing`, …) | new |
| **Edge** | NEW: typed relation between Studies (`spawned_from`, …) | new |
| **Meta-Report** | NEW: second-order synthesis over a Project's whole graph | new `MetaReport` entity |

**Naming collisions to respect (important):**
- **Do NOT rename "Synthesis" to "Simulation".** `simulate_day` / `simulate_range` /
  `simulate-cohort` already mean the persona's *lived-day simulation*. Overloading
  "simulation" would muddy the methodology. Keep: Council < Study(=Synthesis) < Project.
- **The word "project" is already taken at the memory layer:** `get_project` /
  `list_active_projects` refer to a **persona's own work project** (a memory entity, e.g.
  a building project a persona is working on). The NEW research container is a *different*
  thing. To avoid ambiguity, the new container's MCP tools are namespaced explicitly
  (`open_project_graph`, `get_project_graph`, `list_research_projects`, …) and this spec
  always says **"research Project"** vs **"persona-project"** when context is unclear. (A
  future cleanup may rename the memory tool to `get_persona_project`; tracked as open.)

---

## 3. Data Model

New entities, layered on top of the existing ones (no breaking changes to `Persona`,
`CouncilSession`, `Synthesis`).

### 3.1 `Project` (research container)
```
Project:
  id: str
  slug: str
  title: str
  goal: str                      # the overarching research goal
  description: str
  persona_ids: list[str]         # the personas in scope (references the shared library)
  study_ids: list[str]           # Synthesis ids that are nodes in this graph
  edges: list[Edge]              # see 3.2 (or stored separately, see 3.5)
  themes: list[str]              # the theme vocabulary that emerged (LLM-grown, not fixed)
  status: str                    # active | parked | done
  created_at, updated_at: str
```

### 3.2 `Edge` (typed relation between Studies)
```
Edge:
  from_study_id: str
  to_study_id: str
  type: str        # spawned_from | refines | contrasts | depends_on | duplicates | answers
  rationale: str   # WHY this edge exists (host-authored, one line)
  created_at: str
```
`type` semantics:
- `spawned_from` — B's question came out of A's synthesis (the common case; today's
  `next_council_question` becomes an explicit cross-study edge).
- `refines` — B narrows/sharpens the same question as A.
- `contrasts` — B deliberately tests the opposite / a tension against A.
- `depends_on` — B only makes sense given A's conclusion (ordering constraint).
- `duplicates` — B substantially repeats A (dedup signal; should be merged or dropped).
- `answers` — B closes an `open_question` raised by A.

### 3.3 Study extensions (on `Synthesis`)
Add, without breaking existing fields:
```
project_id: str | None         # which research Project this Study belongs to
theme_tags: list[str]          # LLM-assigned themes (pains | ux | pricing | segmentation | ...)
open_questions: list[OpenQuestion]   # promote offene_fragen to first-class, linkable nodes
dissent: list[Json]            # explicitly tracked minority/negative/non-target findings
```
`Synthesis.offene_fragen` already exists as free strings; `open_questions` upgrades the
*important* ones into addressable objects so an edge (`answers`) can point at them.

```
OpenQuestion:
  id: str
  text: str
  status: str          # open | being_studied | answered | dropped
  answered_by_study_id: str | None
```

### 3.4 `MetaReport` (the Gesamtreport)
```
MetaReport:
  id: str
  project_id: str
  title: str
  outline: list[Section]         # derived from graph topology + build order
  sections: list[SectionContent] # authored section by section, each grounded
  graph_snapshot: Json           # node/edge/tag/order state at generation time (provenance)
  build_order_narrative: str     # how the graph was constructed over time
  created_at: str

Section:           { id, heading, theme_tags, source_study_ids, intent }
SectionContent:    { section_id, markdown, citations: [{study_id, council_id, quote}] }
```

### 3.5 Storage notes
- New SQLite tables: `projects`, `study_edges`, `open_questions`, `meta_reports`. Studies
  (`syntheses`) gain `project_id`, `theme_tags`, `dissent` columns (nullable → backward
  compatible). Bump `MEMORY_SCHEMA_VERSION` with a migration (existing pattern).
- The graph (`study_ids` + `edges`) is derivable/queryable; store edges in their own table
  for indexability, mirror a denormalized view on `Project` for cheap reads.
- Everything stays under `data/` and is **gitignored/local-only** (research content is the
  user's private data; the engine is what ships). `export_snapshot`/`import_snapshot`
  extend to round-trip projects/edges/meta-reports.

---

## 4. Graph Semantics

- **Nodes** are Studies (a Study = one Synthesis = one council chain). Councils are
  *inside* a node; the graph is at the Study level.
- **A node also exposes its open-questions and dissent** as attach points, so the graph
  carries not just conclusions but the live frontier and the disagreements.
- **Edges are directed and typed** (§3.2). The graph is a DAG in the common case but may
  contain `contrasts`/`refines` cycles between sibling studies — allowed; the Meta-Report
  handles them by clustering, not by assuming a tree.
- **Build order is preserved** (every node/edge has `created_at`). Order matters: it tells
  the Meta-Report *how understanding evolved* (trajectory) even though the final outline is
  organized by *theme* (logic), not chronology.
- **Theme tags are LLM-assigned, never hardcoded.** The theme vocabulary (`themes` on the
  Project) grows as studies are added; the host agent proposes tags from the study content
  and is shown the existing vocabulary to encourage reuse over proliferation.

---

## 5. Persona Library & Reuse

- Personas live in a **single shared library** (today's persona store), not inside a
  project. A research Project **references** a subset via `persona_ids`. This is the
  user's "reusable, not project-isolated" requirement.
- A persona's **memory persists across councils and across projects** (already true:
  councils are persona-stateless, but persona memory/recall/threads persist). So the same
  persona can participate in many projects and carry its lived context everywhere.
- **Encapsulation is at the Project level, not the persona level:** the *research artefacts*
  (studies, edges, reports) are scoped to a project; the *personas* are global assets.
- Open design choice (see §12): whether a persona's experiences from *participating in
  councils* should feed back into its memory (council participation as a lived event), or
  whether councils stay strictly read-only on memory. Default for now: **read-only**
  (a council reads memory, does not write it) to avoid contaminating personas with our own
  product framing — protects anti-steering.

---

## 6. MCP Tool Surface

Follows existing conventions: `list_*` overview · `get_*` detail · `record_*`/`put_*`
write · `brief_*` gather-for-host-authoring · envelope `{ok, data,
next_recommended_tool, _meta}` · `next_recommended_tool` encodes the research DAG
(seed study → tag → spawn follow-up → … → meta-report).

### 6.1 Project / graph management
- `create_project(title, goal, persona_ids?, description?)` → Project
- `list_research_projects(filters?)` → compact list
- `get_project(project_id)` → project header + counts (**note:** distinct from the memory
  `get_project`; if the collision is too risky in practice, expose as
  `get_research_project`)
- `get_project_graph(project_id, view?)` → nodes (studies w/ tags, status, sentiment
  rollup), edges (typed), themes, build order, open_questions, dissent. The core
  navigation call — returns enough for the host to reason about *what to do next*.
- `add_study_to_project(project_id, study_id)` / `set_study_themes(study_id, tags[])`
- `link_studies(from_study_id, to_study_id, type, rationale)` → Edge
- `record_open_questions(study_id, questions[])` / `resolve_open_question(question_id, answered_by_study_id)`

### 6.2 Running studies inside the graph (reuses existing council/synthesis tools)
No new council mechanics — a Study is still: run councils (`run_council` /
`record_council`) → `brief_synthesis` → `record_synthesis`. New thin wrapper to keep the
graph coherent:
- `brief_followup_study(project_id, from_study_id?)` → gathers the parent study's synthesis
  + the project graph + theme vocabulary, and returns context for the host to author the
  **next self-contained council question** (personas are council-stateless — the question
  must stand alone) plus a proposed theme tag and edge type.
- `record_study(project_id, synthesis_id, from_study_id?, edge_type?, theme_tags?)` →
  attaches an already-recorded Synthesis as a node, with its edge + tags, in one call.

### 6.3 Prioritization & frontier (the anti-explosion surface — see §8)
- `get_research_frontier(project_id)` → the open_questions + spawnable follow-ups across
  the graph, each scored on **effort/value** (reuse the `aufwand`/`nutzen` axes already in
  `handlungsempfehlungen`) and flagged for **duplication** against existing nodes. This is
  what stops the "and two more and two more" runaway: the host sees a *ranked* frontier,
  not an infinite fan-out.
- `brief_frontier_review(project_id)` / `record_frontier_review(...)` — host-authored pass
  that marks branches as `worth_pursuing | redundant | exhausted | out_of_scope`.

### 6.4 Meta-Report (§7)
- `brief_meta_report(project_id)` → the whole graph (topology + build order + every study's
  exec_summary, themes, open_questions, dissent) + instructions to derive an outline.
- `record_meta_outline(project_id, outline[])` → persist the derived structure.
- `brief_meta_section(project_id, section_id)` → the source studies/councils for one section
  + instructions to author it with citations.
- `record_meta_section(project_id, section_id, markdown, citations[])`
- `export_meta_report(project_id, format=md|json)` → the assembled document.

(The two-step outline-then-sections mirrors the existing `brief_*`/`record_*` split and
keeps each authoring step small enough to be grounded and verifiable.)

---

## 7. The Meta-Report Protocol (Gesamtreport)

A **synthesis of syntheses** — the second-order loop:

```
brief_meta_report(project_id)              # gather whole graph + build order
  → host authors an OUTLINE from the graph:
      • cluster studies by theme  → chapters
      • order chapters by dependency/logic (not chronology)
      • a "How this understanding was built" section from build order (trajectory)
      • a "Tensions & non-targets" section from accumulated dissent
      • an "Open frontier" section from unresolved open_questions
record_meta_outline(project_id, outline)
for each section:                          # author one section at a time
  brief_meta_section(project_id, section_id)   # source studies/councils for THIS section
  → host authors markdown, every claim cited to {study_id, council_id, quote}
  record_meta_section(...)
export_meta_report(project_id)             # assemble + render
```

Design rules:
1. **Outline is derived, not fixed.** The structure comes from the graph's themes and
   dependency edges — different projects produce different outlines. No hardcoded report
   template beyond the three cross-cutting sections (trajectory, tensions/non-targets,
   open frontier).
2. **Understand the build order, organize by logic.** The report explains *how* the
   understanding evolved (because order is real signal) but presents conclusions by *theme*
   (because that is how a reader needs them).
3. **Two-level provenance.** Every Meta-Report claim cites a Study; every Study claim
   already cites a Council/voice. The chain *meta-section → study → council → persona quote*
   must never break. A section with no citations is a bug, not prose.
4. **Honesty preserved.** Dissent and non-targets get their own section — the report must
   not launder a graph that grew around a thesis into false consensus (see §8.2).
5. **Host-authored only.** No server-side text generation; the server gathers and persists.

---

## 8. Methodical Guardrails (designed in from the start)

The graph is powerful and therefore dangerous in three specific ways. These are
first-class requirements, not afterthoughts.

### 8.1 Convergence / anti-explosion
A graph that sprouts endlessly is noise, not insight.
- Every spawnable follow-up carries an **effort/value score** and a **duplication check**
  against existing nodes (`get_research_frontier`, §6.3).
- Studies can be marked **`exhausted`** (a branch that would only repeat).
- A Project carries an optional **budget** (max studies / max councils) and the frontier is
  always *ranked*, so the host pursues the highest-value branch, not the next one that
  happens to appear.
- `duplicates` edges make redundancy explicit and mergeable.

### 8.2 Anti-steering at graph scale
As a graph grows around a product thesis, confirmation drift is the systemic risk.
- **Dissent and non-targets are nodes/attachments, not footnotes** — the graph must make
  its own blind spots visible.
- A periodic **`contrasts` study is encouraged** by the frontier tool: deliberately test
  the opposite of an emerging conclusion (the council `tension` strategy already exists).
- The Meta-Report's mandatory "Tensions & non-targets" section forces the disconfirming
  evidence into the output.
- Personas remain non-directional; council selection stays LLM-authored from candidate
  summaries (no fixed keyword/topic scoring) — unchanged principle, now load-bearing at scale.

### 8.3 Provenance over two levels
Already covered in §7.3 — enforced structurally: citations are required fields, validated
on `record_meta_section`.

---

## 9. Web UI (inspection only — unchanged philosophy)

The web UI stays a **read-only inspection surface**; all creation is CLI/MCP.
- **Project graph view:** nodes (studies, colored by theme, sized by council count or
  sentiment), typed edges, build-order playback (a time slider over `created_at`), open
  frontier and dissent surfaced.
- **Study node → existing synthesis report** (the Notion-style document already built),
  with the Stimmen panel.
- **Meta-Report view:** the assembled document with citations that deep-link down to the
  study → council → voice.

---

## 10. Use-Case Catalogue (illustrative; LLM-driven, never hardcoded)

Kept "in the back of the mind" as the breadth a mature research graph should cover. These
are *example seed studies / themes* a Project might grow — the system never ships a fixed
list; the host derives themes from the actual research. (Catalogue informed by common
synthetic-research use cases, incl. experial's.)

- **Pain discovery** — "what are your biggest problems?" (the usual seed)
- **UX / usability** — "how must the workflow/interface be to fit your day?"
- **Pricing & packaging** — "how would you want to pay; what's it worth?"
- **Positioning & messaging** — "how would you describe this to a peer?"
- **Concept / prototype validation** — reactions to a concrete artefact (the Envelope test
  pattern from prior arcs)
- **Segmentation** — "who is this for / not for?" (non-targets are valid output)
- **Adoption / change** — "what makes you actually switch / champion it?"
- **Visual / asset reaction** — feedback on a rendered design (needs a multimodal council
  input — see open questions)
- **Trust / liability / compliance** — "what must be true for you to sign off?"

The canonical worked example (§1.2) chains *pain discovery → UX → pricing* with explicit
edges — that derivation is the demo that proves the graph model.

---

## 11. Roadmap (the vision, phased)

The end-state should be readable straight from this sequence: **from single arcs → to a
navigable, themed research graph → to an auto-derived meta-report → to an assistant that
runs continuous research on a project and reports on the whole.**

- **R0 — Foundations (today, done):** Council, Study(=Synthesis with arc/voices/
  recommendations), the `synthesize` loop with `next_council_question`. *We already have the
  node and the in-arc edge.*
- **R1 — Project container + persona library reuse:** `Project` entity, `create_project`,
  attach existing studies, shared persona references. Studies gain `project_id`. Migration.
- **R2 — Explicit graph:** `Edge` table + types, `link_studies`, `get_project_graph`,
  promote `offene_fragen` → `open_questions` nodes, `answers` edges. The in-arc
  `next_council_question` is lifted to cross-study edges.
- **R3 — LLM theme tagging + frontier:** `set_study_themes` (LLM-assigned, vocabulary
  grows), `get_research_frontier` with effort/value scoring + duplication detection,
  `brief_followup_study`/`record_study`. *This is where "pain → UX → pricing" becomes a
  first-class, navigable derivation.*
- **R4 — Meta-Report:** the §7 protocol end-to-end (`brief_meta_report` → outline →
  sections → `export_meta_report`), two-level provenance enforced.
- **R5 — Guardrails hardened:** frontier review, `exhausted`/`duplicates` handling, project
  budgets, mandatory dissent/non-target nodes + report section; `contrasts` nudge.
- **R6 — UI & continuous operation:** graph view + build-order playback + meta-report view;
  optional scheduled/continuous research drivers (a project keeps researching its frontier
  on a cadence, host-authored, within budget).

Each phase is shippable and additive; nothing here breaks R0. The product north star: a
user opens a Project, asks one question, and over time the assistant grows a traceable
body of knowledge and can produce a board-ready report from the whole graph on demand —
**depth and provenance, where panel tools give breadth and speed.**

---

## 12. Open Questions

- **Naming:** keep memory `get_project` and add `get_research_project`/`get_project_graph`,
  or rename memory's tool to `get_persona_project`? (Collision is real; decide before R1.)
- **Council participation as memory:** should a persona "remember" having been in a council
  (lived event) or stay read-only (anti-steering safer)? Default read-only; revisit if a
  longitudinal use case needs it.
- **Multimodal councils:** the visual-asset use case (§10) needs councils that take an image
  as input — out of scope here, but the graph should not preclude it.
- **Cross-project knowledge:** may two research Projects share/cite each other's studies, or
  is each project a closed graph? (Personas are shared; studies probably project-local with
  optional explicit cross-links.)
- **Frontier scoring source:** effort/value from the host (judgment) vs. a structural
  heuristic (graph centrality, unanswered-question count). Start host-authored.
- **Meta-Report freshness:** regenerate on demand vs. incremental update as nodes are added.
- **Budget semantics:** hard cap vs. soft warning when a project's study/council budget is hit.

---

## 13. Non-Goals

- Not an instant "ask-a-panel" dashboard (that is experial's shape; ours is depth + graph).
- No hardcoded research templates, theme lists, or report outlines — everything LLM-derived
  from the actual graph.
- No server-side text generation — the host agent authors; the server gathers and persists.
- The web UI does not become a control surface; it stays inspection-only.
- Personas are not steered toward a thesis to make a graph "converge" — convergence comes
  from honest exhaustion + prioritization, never from biased participation.
