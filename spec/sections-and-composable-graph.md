# Tracker — Sections (overlay frames) + a Composable Graph of Low-Level Tools

> **Status:** SPEC (build-ready). Authored from a deep codebase analysis + online research
> (canvas frames, research-ops/affinity, graph grouping & composability — sources at the end).
> **One-line goal:** add a **Section** — a methodology-independent, labeled grouping of graph nodes
> ("Initial user research", "Problem exploration", …) — and, around it, lock in the direction that
> the graph is a **canvas of composable low-level primitives** (council · prototype · synthesis ·
> note · edge · **section**) that compose into good approaches, with the methodology/plan engine as
> *one optional orchestrator* rather than the only structure.

---

## 0. Why (the user's ask, restated)

Today the only "grouping" in the graph is **derived from the methodology** (the fan→waist
"diamonds"). The user wants a **free, first-class grouping primitive** — a *section / frame* — that
can be used **independent of any methodology** to put nodes under a named group (e.g. *Initial user
research*, *Problem exploration*, *Solution space*). The broader intent: have **excellent
low-level tools** (councils, prototypes, syntheses, …) that can be **freely composed inside the
graph** to reach good approaches — structure should be *composed*, not *prescribed*.

This is the natural next step after two recent moves that point the same way:
- **Synthesis ⟂ Council decoupling** (2026-06-04): a synthesis is a first-class node that can stand
  alone and merely *cites* evidence. Sections extend the same philosophy to *grouping*.
- The **plan/methodology graph already renders labeled hull-overlays** (`diamonds`) over node sets.
  A Section is the *generalization* of that overlay, made first-class and user-defined.

---

## 1. Current state (analysis — where a Section slots in)

- **Nodes**: the project graph (`services/_research.py::plan_graph` / `get_project_graph`) emits
  heterogeneous nodes — `council:<id>`, `synthesis:<id>`, prototypes (their own ids), frames stay
  internal. Every node has a stable string id (`study_id`). **This id is the only vocabulary a
  Section needs.**
- **Grouping today** is implicit: `web/_graph.py::_methodology_layout` positions nodes by
  longest-path depth over the plan's `consumes` DAG and computes **diamond hull polygons** with
  `_convex_hull` + `_expand_hull`. Those polygons are passed to the canvas as `diamonds` and drawn
  in the `#rgdia` SVG group **behind** nodes. → **The render mechanism for "a labeled region around
  a set of nodes" already exists.**
- **Storage**: `models.ResearchProject` already carries JSON group-ish state (`study_tags`,
  `themes`, methodology binding). Adding `sections: Json` is a non-breaking additive field
  (`storage/_research.py` round-trips the project row; migration = default `[]`).
- **Authoring model**: the web UI is **read-only**; all mutations are **host-authored via MCP/CLI**
  (gather → author → persist, envelope with `next_recommended_tool`). Section *authoring* therefore
  lives in MCP/CLI; the web *renders + navigates* sections. This is not a limitation — see §3, it is
  exactly the membership model the research recommends.
- **Invariants to preserve**: no in-process LLM text-gen; **zero hardcoded methodology/section
  vocabulary** (labels/colors/kinds come from data via `presentation.present()` + suggestions JSON);
  web read-only; structure enforced, dynamics evidence-backed.

---

## 2. Research synthesis (what "good" looks like)

Convergent findings across canvas tools (Miro/FigJam/tldraw/Excalidraw/Obsidian/Node-RED/Unreal),
research-ops (Dovetail/Condens/Atomic-Research, KJ affinity) and graph systems
(Graphviz clusters, BPMN lanes, Cytoscape compound nodes, React Flow groups, ELK):

1. **Explicit membership beats geometric — especially over an auto-laid-out DAG.** "What's inside
   the box" membership (Obsidian/tldraw UX) is fragile the moment the layout re-runs. Store
   `members: [node_id]`; *derive* geometry. (Cytoscape `parent`, React Flow `parentId`.)
2. **Pure overlay — never feed grouping back into the DAG layout.** Graphviz/Mermaid show the
   anti-pattern: putting a node in a cluster silently rewrites the flow layout. Keep sections a
   *read-only overlay* computed **after** layout. Optional "hard lanes" (yFiles PartitionGrid /
   BPMN pools) are a *separate, opt-in* mode, not the default.
3. **Two grouping kinds answer orthogonal questions** and a good tool needs both:
   **process-phase** (methodology-supplied, ordered, ~single-membership: "what stage is this?") vs
   **free theme/affinity** (user-defined, **many-to-many**, emergent: "what is this *about*?").
   Forcing themes into phases kills emergence; only-themes loses procedural rigor.
4. **Sets, not trees → support overlap + cross-cutting.** A node should be able to sit in
   *Discover* (phase) **and** *Trust* + *Onboarding friction* (themes) at once (the BPMN-lane
   insight: an orthogonal partition over the same flow). Shallow **nesting** (sub-theme → theme) is
   useful; deep trees are not.
5. **Insight/synthesis cites evidence by reference, never contains it** (Atomic Research; already
   true here). Sections are *views over shared nodes*, never owners — deleting a section never
   deletes nodes.
6. **Minimal good metadata:** `{title, color, kind, order, collapsed?, note?}`. Color is the
   primary wayfinding device; an explicit **order index** unlocks presentation/outline navigation.
7. **Geometry derived from member bounds + padding** (Cytoscape compound parents have no own
   coords; tldraw groups = union of children). Recomputes for free on re-layout.
8. **Uniform, orthogonal interface** (Unix small-tools / tldraw `ShapeUtil`): a section is just
   another first-class object addressed by node-ids + style + label. The methodology layer must not
   know sections exist, and vice-versa. **Shared symbol = node id only.**

Anti-pattern to avoid: n8n-style "sticky note behind nodes with no real membership" — a frame that
doesn't actually own a set of nodes is universally felt as insufficient.

---

## 3. Design — the `Section` primitive

A **Section** is a first-class, methodology-independent, labeled overlay grouping a set of graph
nodes. It is a *view*, not a container: it references nodes by id and never owns/moves/mutates them.

### 3.1 Data model (additive; lives on the project)
```
Section = {
  id:        "section_<stable>",     # stable id
  title:     str,                    # "Initial user research"
  kind:      str,                    # OPEN tag: "theme" (default) | "phase" | invented — data-driven
  member_ids:[node_id, ...],         # explicit, may overlap other sections (set semantics)
  parent_id: str | null,             # optional shallow nesting (sub-theme → theme)
  order:     int,                    # user-orderable sequence (outline / present order)
  presentation: {label?,short?,color?,glyph?} | null,  # object-level override (else present(kind))
  note:      str,                    # optional markdown rationale
  created_at, updated_at
}
ResearchProject.sections: [Section]   # new JSON field, default []
```
- **Membership is explicit + set-based** (overlap allowed). `kind` is an **open tag** resolved for
  display through `presentation.present()` + `suggestions/section_kinds.json` (no hardcoded vocab —
  same pattern as artifact types / evidence kinds). `"phase"` sections are the methodology bridge
  (§3.4); `"theme"` is the free default; users/host may invent kinds.
- **Geometry is NOT stored** — derived at render time from member node bounds.

### 3.2 Orthogonality contract (the load-bearing rule)
- The **plan/methodology layer** owns *nodes, edges, columns* (the DAG + its layout).
- The **section layer** owns *(member-id set) + label + style + order*.
- **Only shared symbol: the node id.** Sections are computed **after** layout and never alter it.
  You can add/remove/restyle sections without touching the methodology engine, and run any
  methodology without creating a single section. (Unix "integrate at the top layer".)

### 3.3 Rendering (reuse what exists)
- New pure function `section_hulls(graph, pos, node_bounds)` → for each section, gather member node
  rectangles, compute `_expand_hull(_convex_hull(corners), margin)` (the **exact** primitives the
  diamonds use), attach `{id,title,color,order,parent_id}`.
- Pass `sections` alongside `diamonds` into the canvas JSON; draw them in a new `#rgsections` SVG
  group **behind** nodes (and behind/around diamonds by z = nesting depth), each with a label chip
  at the hull's top-left and a translucent fill / outline (fill-vs-outline by `kind`).
- **Web is read-only**: render + a **filter/highlight** (click a section chip → dim non-members,
  like the existing theme-filter chips) + an **outline panel** (sections by `order`, deep-linkable).
  No drag-to-add on the canvas (membership is authored via MCP). Overlapping hulls are fine
  (translucent); nesting draws inner hulls on top.

### 3.4 Methodology bridge (unify the diamonds)
- Today's `diamonds` are *derived phase grouping*. Make the methodology project its steps as
  **derived, read-only `kind:"phase"` sections** (one per fan/waist region) computed from the plan —
  so phase grouping and free theme sections render through **one** mechanism and **coexist**: a node
  can be in the derived *Develop* phase-section **and** a user's *"ehrliche Nicht-Option"* theme.
- Derived phase-sections are not persisted as editable rows (they follow the plan); persisted
  Sections are user/host-authored `theme`s (and any invented kinds). Both are unioned at render.

### 3.5 Composable-primitives north star (the broader ask)
Frame the graph explicitly as a **canvas of composable primitives**, each creatable **independent of
any methodology**:
- **Node primitives**: `council`, `synthesis` (decoupled), `prototype`/`artifact`, `persona-ref`,
  and a new lightweight **`note`** node (a markdown sticky / observation — the atomic unit for
  affinity). 
- **Edge primitives**: typed relations (`refines`, `contrasts`, `cites`, `answers`, …) authored
  freely (`link_studies`) — not only methodology-implied.
- **Section primitive**: this doc.
- **Orchestrators** (optional): the **methodology/plan engine** is *one* way to wire primitives; a
  **freeform** project wires them by hand. Sections + notes + free edges make the freeform path
  first-class. North star: *you can build a great study by composing primitives directly, and reach
  for a methodology only when you want its scaffolding + gates.*

---

## 4. Surface (MCP + CLI — host-authored, data-driven, enveloped)

New tools (mirror existing naming/envelope conventions; all mutations host-authored):
- `create_section(project_id, title, kind="theme", member_ids=[], parent_id=None, note="", presentation=None)` → Section
- `update_section(section_id, patch)` (title/kind/color/order/parent/note)
- `add_to_section(section_id, node_ids[])` / `remove_from_section(section_id, node_ids[])`
- `set_section_members(section_id, node_ids[])` (bulk set — the "promote this cluster" affordance)
- `reorder_sections(project_id, ordered_ids[])`
- `list_sections(project_id)` / `get_section(section_id)` / `delete_section(section_id)`
- Suggestion seed: `suggest_section_kinds()` (data, like `suggest_artifact_types`).
- CLI mirrors: `section-create/-update/-add/-remove/-set/-reorder/-list/-get/-delete`.
- **Validation**: member_ids must resolve to real nodes in the project graph; deleting a section
  never deletes nodes; `kind`/presentation are free tags (grep-gated against hardcoding).

---

## 5. Milestones (build order; each: implement → full `pytest` green → characterization unchanged → commit)

- **SEC1 — Model + storage + migration.** Add `Section` model + `ResearchProject.sections`
  (default `[]`); storage round-trip; idempotent migration. Pure data, no behavior change.
  *Accept:* a project persists/loads sections; old projects load with `sections=[]`.
- **SEC2 — MCP/CLI surface.** All tools in §4 with validation + envelopes + suggestion seed.
  *Accept:* create a section over real node-ids, add/remove/set/reorder/list/delete; member
  validation rejects unknown ids; grep gate: no hardcoded kind/label/color literals in engine/UI.
- **SEC3 — Render overlay.** `section_hulls()` (reusing `_convex_hull`/`_expand_hull`); draw
  `#rgsections` behind nodes; label chips; fill-vs-outline by `kind` via `present()`; filter
  chips + outline panel + deep-link. *Accept:* a section visibly frames its members under a label;
  overlap + shallow nesting render; clicking a chip highlights members; zero layout drift for the
  DAG (characterization route hashes for non-section projects unchanged).
- **SEC4 — Methodology bridge.** Project plan phases as derived `kind:"phase"` sections; unify with
  user theme sections at render (a node may be in both). *Accept:* the Pfefferminzia project shows
  derived phase sections AND any added theme sections together; the existing diamonds remain or are
  re-expressed as phase sections (one mechanism).
- **SEC5 — Affinity workflow + `note` node (composability).** Add a lightweight `note`/observation
  node primitive + `set_section_members` "promote a cluster" flow; document the freeform
  compose-without-methodology path. *Accept:* one can author notes, group them into a named theme
  section, and read it back — no methodology required.
- **SEC6 — Section-scoped views/export.** Filter the graph/report to a section; `export_section`
  (md/json, self-contained like `export_synthesis`); section as outline navigation.
  *Accept:* exporting a section yields a self-contained artifact of its member nodes.
- **SEC7 — Tests + gates + docs.** Unit/characterization tests; grep gates (no hardcoded section
  vocab; data-driven presentation); update `AGENTS.md` + a `methodology-presentation-from-data`
  note. *Accept:* full suite green; gates pass; docs describe the primitive + the composable model.

---

## 6. Key decisions (locked) & open questions

**Locked (from research):** explicit set-membership (not geometric) · pure overlay (never alters the
DAG layout) · derived geometry · two+ open `kind`s (theme/phase/invented) data-driven · overlap +
shallow nesting · reference-not-containment · authoring via MCP, rendering+navigation in the
read-only web · reuse `_convex_hull`/`_expand_hull`.

**Open (decide during SEC3–SEC4):**
- Do persisted phase-sections ever replace derived diamonds, or always derive? (Lean: always
  derive; persist only themes/invented.)
- Hull style for heavy overlap — translucent fills vs outline-only when ≥3 sections overlap a node.
- Optional **hard-lane layout mode** (yFiles PartitionGrid analogue) — defer; only if users want
  sections to *organize* (not just annotate) the layout. Keep as a separate opt-in primitive.
- Should `note` nodes participate in the plan evidence graph, or live purely on the freeform canvas?

---

## 7. Sources (research)
Canvas frames: Miro Frames/Presentation, FigJam Sections, tldraw `TLFrameShape`/groups, Excalidraw
frames, Obsidian Canvas groups, Node-RED groups, Unreal comment Move-Mode. Research-ops/affinity:
NN/g Affinity Diagramming (KJ), Dovetail/Condens/Aurelius + Atomic Research (insight⟂evidence,
many-to-many by reference), Double Diamond, Teresa Torres Opportunity Solution Tree. Graph/compose:
Graphviz clusters, BPMN pools/lanes, Cytoscape compound nodes, React Flow sub-flows, ELK
`hierarchyHandling`, yFiles PartitionGrid swimlanes, Unix small-tools / orthogonality, tldraw
composable primitives. (Full URLs captured in the research briefs that produced this tracker.)
