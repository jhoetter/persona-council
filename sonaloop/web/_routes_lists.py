"""Index/list-page builders, split out of _routes_pages (spec/component-ssr-architecture.md C5 — keep
route modules small). Each renders rows through the shared _list_page() shell. Markup via h()."""
from __future__ import annotations

from .. import services
from ..storage import Store
from ._i18n import t
from ._components import _icon, _avatar, _label, _star, _list_page, _artifact_present, _layout, _md, _md_inline, _lang
from ._html import h, raw, fragment, register_css


# ============================ Documentation ============================ #
# A reference page (sidebar entry) describing every artefact the workspace produces — what it is and
# what it can do. Content is bilingual (de/en) here rather than via i18n keys (long prose; keeps the
# t() table lean) and authored in Markdown so the page also exercises the _md renderer.
DOCS_INTRO = {
    "de": "Dieser Workspace bildet **Design-Research** als verknüpften Graphen ab. Jedes Artefakt ist ein "
          "Knoten mit eigener Rolle — vom rohen Signal bis zur entscheidungsreifen Spec. Alle Inhalte "
          "werden vom Host via MCP **authored** (keine In-Process-LLM-Generierung).",
    "en": "This workspace models **design research** as a linked graph. Each artefact is a node with a "
          "distinct role — from a raw signal to a decision-ready spec. All content is host-**authored** "
          "via MCP (no in-process LLM generation).",
}
# The lifecycle / flow — how the artefacts above fit together end to end. Authored prose (de/en),
# rendered as numbered phases above the per-artefact catalog so a reader gets the model before the parts.
# Step shape: ((title_de, body_de), (title_en, body_en)).
HOWITWORKS = [
    (("Personas — das geerdete Fundament",
      "Synthetische Kundenprofile werden host-authored angelegt (`brief_persona` → `record_persona`) "
      "und Tag für Tag simuliert (`brief_day` → `record_day`) zu einem **Memory-Graph**, den sie "
      "`recall`-en und per Zeitreise abfragen können."),
     ("Personas — the grounded foundation",
      "Synthetic customer profiles are created host-authored (`brief_persona` → `record_persona`) and "
      "simulated day by day (`brief_day` → `record_day`) into a **memory graph** they can `recall` and "
      "time-travel.")),
    (("Projekt + Plan-Engine",
      "Ein **Research-Projekt** (Double-Diamond) wird von der **Plan-Engine** getrieben: "
      "`next_action`/`brief_next` schlägt den nächsten *Analyze → Act → Verify*-Schritt vor; der Host "
      "autort ihn und hält Evidenz fest (`record_frame` / `link_evidence` / `record_judgment` → "
      "`complete_task`, mit `assess_project` für den Fortschritt)."),
     ("Project + plan engine",
      "A **research project** (Double-Diamond) is driven by the **plan engine**: `next_action`/"
      "`brief_next` proposes the next *analyze → act → verify* step; the host authors it and records "
      "evidence (`record_frame` / `link_evidence` / `record_judgment` → `complete_task`, with "
      "`assess_project` for progress).")),
    (("Evidenz — Councils, Prototypen, Notizen",
      "Die Evidenz ist memory-geerdet: **Councils** (Persona-Debatten), **Prototypen** (Personas testen "
      "sie in Sessions) und **Notizen/Sections** — jeweils auf die Erinnerung der Personas zurückführbar."),
     ("Evidence — councils, prototypes, notes",
      "The evidence is memory-grounded: **councils** (persona debates), **prototypes** (personas test "
      "them in sessions), and **notes/sections** — each traceable back to a persona's memory.")),
    (("Synthese / Report — die Antwort",
      "Die Evidenz konvergiert zu einer **Synthese**: als *Convergence* (Kernprobleme + Empfehlungen, "
      "Aufwand·Nutzen-2×2) oder als *Projekt-Report* (erzählerisch, präsentationsreif) — beide "
      "PDF-exportierbar."),
     ("Synthesis / report — the answer",
      "The evidence converges into a **synthesis**: as *convergence* (key problems + recommendations, "
      "effort·impact 2×2) or a *project report* (narrative, presentation-grade) — both PDF-exportable.")),
]
HOWITWORKS_CONTRACT = {
    "de": "Jeder generative Schritt folgt **einem Vertrag**: `brief_*` (Kontext sammeln) → der Host "
          "autort JSON → `record_*` / `put_*` (validieren + persistieren). Keine Server-seitige Text-LLM-Generierung.",
    "en": "Every generative step follows **one contract**: `brief_*` (gather context) → the host authors "
          "JSON → `record_*` / `put_*` (validate + persist). No server-side text-LLM generation.",
}
# Each entry documents ONE artefact in depth, with three authored facets so the page answers the same
# questions for every node: WAS es ist (desc), WELCHE Datenpunkte es hält (data), WORIN der große Vorteil
# liegt (advantage). NAME + COLOR still come from data — t(name_key) when a chrome label exists, else
# present(kind)["label"]; colour is always present(kind)["color"] — so no methodology/artifact label is
# hardcoded here (the zero-hardcoded-values gate). Only the descriptive prose is authored, in Markdown.
# Entry shape: {kind, icon, name (i18n key or None), desc, data (bullets), adv} — each prose field a
# (de, en) tuple, each `data` a ([de…], [en…]) pair.
DOCS = [
    {"art": "project", "icon": "projects", "name": "projects",
     "desc": ("Der Forschungs-**Container**: ein Double-Diamond-Graph *einer* Studie "
              "(Discover → Define → Develop → Deliver). Alles, was zu einer Frage gehört, hängt hier.",
              "The research **container**: a Double-Diamond graph of *one* study "
              "(Discover → Define → Develop → Deliver). Everything belonging to a question lives here."),
     "data": (["Methodologie + Phasen-Fortschritt (Discover→Deliver)",
               "Offene Fragen & die *Build-Order*-Narrative",
               "Verknüpfte Councils, Synthesen/Reports, Notizen, Prototypen, Sections",
               "Ein Graph-Snapshot (Knoten + Kanten) für die Outline"],
              ["Methodology + phase progress (Discover→Deliver)",
               "Open questions & the *build-order* narrative",
               "Linked councils, syntheses/reports, notes, prototypes, sections",
               "A graph snapshot (nodes + edges) driving the outline"]),
     "adv": ("Eine Studie an *einem* Ort: du siehst jederzeit, was erledigt und was offen ist — und "
             "wie jedes Artefakt zum Ergebnis beiträgt, statt verstreuter Dokumente.",
             "One study in *one* place: you always see what's done and what's open — and how every "
             "artefact feeds the outcome, instead of scattered documents.")},
    {"art": "persona", "icon": "personas", "name": "personas",
     "desc": ("Ein synthetisches Kundenprofil (**SOUL** + Erinnerung) — der „Proband“. Kein statisches "
              "Profil: die Persona *erinnert sich* an alles, woran sie teilgenommen hat.",
              "A synthetic customer profile (**SOUL** + memory) — the research subject. Not a static "
              "profile: the persona *remembers* everything it has taken part in."),
     "data": (["SOUL: Identität, Rolle, Firmen-Kontext, Werte & Eigenheiten",
               "Episodische **Memories** aus Councils & Prototyp-Sessions",
               "Offene Loops/Threads und Revisionen (die Persona entwickelt sich)",
               "Generierter Avatar"],
              ["SOUL: identity, role, company context, values & quirks",
               "Episodic **memories** from councils & prototype sessions",
               "Open loops/threads and revisions (the persona evolves)",
               "A generated avatar"]),
     "adv": ("**Personas mit Memories**: Antworten kommen aus angesammelter, gelebter Erfahrung — die "
             "Reaktionen verändern sich, je mehr die Persona erlebt, statt jedes Mal dasselbe zu sagen.",
             "**Personas with memories**: answers come from accumulated, lived experience — reactions "
             "shift the more the persona has been through, instead of repeating the same line.")},
    {"art": "council", "icon": "councils", "name": "councils",
     "desc": ("Eine memory-geerdete **Persona-Debatte**. Drei Modi: _Discovery_ (offene Fragen), "
              "_Evaluation_ (Reaktion auf ein Konzept), _Decision_ (Abstimmung).",
              "A memory-grounded **persona debate**. Three modes: _Discovery_ (open questions), "
              "_Evaluation_ (reacting to a concept), _Decision_ (a vote)."),
     "data": (["Teilnehmende Personas + Modus + die gestellte Frage",
               "Turn-für-Turn-Statements mit *Stance* (−2…+2) und Memory-Belegen",
               "Eine Executive Summary + eine verdichtete Erkenntnis (Finding)"],
              ["Participating personas + mode + the question posed",
               "Turn-by-turn statements with *stance* (−2…+2) and memory refs",
               "An executive summary + one distilled finding"]),
     "adv": ("Echte, *nachvollziehbare* Reaktionen statt Meinungen: jedes Statement lässt sich auf die "
             "Erinnerung einer Persona zurückführen.",
             "Real, *traceable* reactions instead of opinions: every statement can be traced back to a "
             "persona's memory.")},
    {"art": "synthesis", "icon": "syntheses", "name": "syntheses",
     "desc": ("Der **Report-Knoten** — *eine* Entität für zwei Tiefen: eine **Convergence**-Synthese "
              "faltet Councils zu Kernproblemen + Empfehlungen (Aufwand·Nutzen-2×2); ein **Projekt**-"
              "Report ist die erzählerische, präsentationsreife Sicht über die ganze Studie.",
              "The **report node** — *one* entity at two depths: a **convergence** synthesis folds "
              "councils into key problems + recommendations (effort·impact 2×2); a **project** report "
              "is the narrative, presentation-grade view across the whole study."),
     "data": (["`scope`-Tag: `convergence` (strukturiert) oder `project` (Report)",
               "Findings: Kernprobleme & Empfehlungen mit Aufwand·Nutzen-Score",
               "Voices (Persona-Stimmen) + Quell-Councils + Graph-Snapshot",
               "Report: Markdown-Sections, Lead, Figuren (Prototyp-Shots, Avatare, 2×2-Charts, Assets)"],
              ["A `scope` tag: `convergence` (structured) or `project` (report)",
               "Findings: key problems & recommendations scored by effort·impact",
               "Voices (persona quotes) + source councils + graph snapshot",
               "Report: markdown sections, lead, figures (prototype shots, avatars, 2×2 charts, assets)"]),
     "adv": ("**Ein** Renderer, *ein* Export: beide Tiefen sind report-grade und als **PDF** abrufbar. "
             "Synthesen verketten sich zu einem wachsenden Studien-Bogen statt loser Einzelreports.",
             "**One** renderer, *one* export: both depths are report-grade and **PDF**-exportable. "
             "Syntheses chain into one growing study arc instead of loose one-off reports.")},
    {"art": "prototype", "icon": "prototype", "name": "prototypes_h",
     "desc": ("Ein **lauffähiges Artefakt** (von grob bis hochauflösend), das Personas tatsächlich testen.",
              "A **runnable artefact** (low to high fidelity) that personas actually test."),
     "data": (["Fidelity/Version + der lauffähige Build",
               "Sessions: Persona-Reaktionen auf konkrete States (mit Belegen)",
               "Verknüpfung zur Notiz/Idee, aus der er gebaut wurde"],
              ["Fidelity/version + the runnable build",
               "Sessions: persona reactions to concrete states (with refs)",
               "A link back to the note/idea it was built from"]),
     "adv": ("Geerdete Reaktionen auf etwas *Echtes* — und die Fidelity-Iteration im Develop-Diamanten "
             "wird über die Sessions sichtbar.",
             "Grounded reactions to something *real* — and the fidelity iteration in the Develop diamond "
             "becomes visible across sessions.")},
    {"art": "note", "icon": "panel", "name": None,
     "desc": ("Die **leichtgewichtige Node** im Projekt-Graph — von der rohen Beobachtung bis zur "
              "ausgearbeiteten Lösungs-Idee. Wird sie gebaut, verlinkt sie auf ihren Prototyp.",
              "The **lightweight node** in the project graph — from a raw observation to a worked-out "
              "solution idea. Once built, it links to its prototype."),
     "data": (["Titel/Text + Kind (Beobachtung … Lösungs-Idee)",
               "Evidence-Links in den Graphen",
               "Optionaler Verweis auf einen gebauten Prototyp"],
              ["Title/text + kind (observation … solution idea)",
               "Evidence links into the graph",
               "An optional pointer to a built prototype"]),
     "adv": ("Methodologie-frei und jederzeit erfassbar — die niedrigste Hürde, ein Signal festzuhalten, "
             "das später ein Council prüft oder ein Prototyp wird.",
             "Methodology-free and capturable anytime — the lowest-friction way to keep a signal that a "
             "council later evaluates or a prototype turns into.")},
    {"art": "section", "icon": "squareGrid", "name": "section",
     "desc": ("Eine **methodologie-unabhängige Gruppierung** von Graph-Knoten (ein Frame/Cluster).",
              "A **methodology-independent grouping** of graph nodes (a frame/cluster)."),
     "data": (["Mitglieder (beliebige Graph-Knoten) + Kind + Reihenfolge"],
              ["Members (any graph nodes) + kind + ordering"]),
     "adv": ("Struktur über den Graphen, ohne sich auf eine feste Methode festzulegen — gruppiere, wie "
             "die Erkenntnisse es verlangen.",
             "Structure over the graph without committing to a fixed method — group however the findings "
             "demand.")},
]


def _docs_page() -> str:
    from .. import presentation as _pres
    store = Store()
    de = _lang() == "de"
    lbl_data = "Datenpunkte" if de else "Data points"
    lbl_adv = "Großer Vorteil" if de else "Big advantage"
    cards = []
    for d in DOCS:
        pres = _pres.present(d["art"])
        name = (t(d["name"]) if d["name"]
                else (pres["label"] if not pres["label"].islower() else pres["label"].capitalize()))
        i = 0 if de else 1
        desc, adv = d["desc"][i], d["adv"][i]
        data = d["data"][i]
        cards.append(h("div", {"class_": "doccard"},
            h("div", {"class_": "doc-h"},
              h("span", {"class_": "rico", "style": f"color:{pres['color']}"}, raw(_icon(d["icon"]))),
              h("span", {"class_": "doc-name"}, name)),
            h("div", {"class_": "es-prose sm doc-desc"}, raw(_md(desc))),
            h("div", {"class_": "doc-sec"}, h("div", {"class_": "doc-lbl"}, lbl_data),
              h("ul", {"class_": "doc-caps"}, fragment(*(h("li", {}, raw(_md_inline(c))) for c in data)))),
            h("div", {"class_": "doc-sec"}, h("div", {"class_": "doc-lbl"}, lbl_adv),
              h("div", {"class_": "es-prose sm doc-adv"}, raw(_md(adv))))))
    prim_rows = []
    for nm, dde, den in PRIMITIVES:
        prim_rows.append(h("div", {"class_": "psolve"},
            h("strong", {}, nm), " — ", raw(_md_inline(dde if de else den))))
    primitives = h("div", {"class_": "block", "style": "margin-top:38px"},
        h("h2", {"class_": "bh"}, ("Datenmodell — fünf Primitive" if de else "Data model — five primitives")),
        h("div", {"class_": "es-prose sm", "style": "margin-bottom:10px"},
          raw(_md(("Unter der Haube sind alle Artefakte aus **denselben fünf JSON-Primitiven** "
                   "zusammengesetzt — so wird jedes „gleiche Ding“ überall gleich dargestellt "
                   "(Details: `spec/unified-artifact-schema.md`).") if de else
                  ("Under the hood every artefact is composed of **the same five JSON primitives** — so the "
                   "\"same thing\" is rendered the same way everywhere (details: `spec/unified-artifact-schema.md`).")))),
        fragment(*prim_rows))
    how_steps = []
    for n, step in enumerate(HOWITWORKS, 1):
        title, bodytxt = step[0 if de else 1]
        how_steps.append(h("div", {"class_": "hiw-step"},
            h("div", {"class_": "hiw-num"}, str(n)),
            h("div", {"class_": "hiw-main"},
              h("div", {"class_": "hiw-title"}, title),
              h("div", {"class_": "es-prose sm hiw-body"}, raw(_md(bodytxt))))))
    howitworks = h("div", {"class_": "block", "style": "margin-top:30px"},
        h("h2", {"class_": "bh"}, ("So funktioniert's" if de else "How it works")),
        h("div", {"class_": "hiw"}, fragment(*how_steps)),
        h("div", {"class_": "es-prose sm hiw-contract"}, raw(_md(HOWITWORKS_CONTRACT["de" if de else "en"]))))
    body = h("section", {},
             h("div", {"class_": "hero"}, h("h1", {}, raw(_icon("overview")), t("documentation")),
               h("div", {"class_": "es-prose sm", "style": "margin-top:6px"}, raw(_md(DOCS_INTRO["de" if de else "en"])))),
             howitworks,
             h("h2", {"class_": "bh", "style": "margin-top:38px"}, ("Artefakte" if de else "Artefacts")),
             h("div", {"class_": "docgrid", "style": "margin-top:14px"}, fragment(*cards)), primitives)
    return _layout(t("documentation"), body, store, crumbs=[(t("documentation"), None)], active="docs")


# The unified data primitives (spec/unified-artifact-schema.md) — surfaced here so the data model is visible.
PRIMITIVES = [
    ("Statement", "Eine Persona-Aussage: Text, Haltung, Bezug, Belege. Vereint Council-Turns, Synthese-Voices und Prototyp-Reaktionen.",
     "A persona's utterance: text, stance, target, refs. Unifies council turns, synthesis voices and prototype reactions."),
    ("Finding", "Ein authored Analyse-Item (Kernproblem, Empfehlung, offene Frage …): Markdown-Text, optionaler Score, Belege.",
     "An authored analysis item (key problem, recommendation, open question …): markdown text, optional score, refs."),
    ("Prompt", "Das Gestellte: Frage, Proposal, Ziel oder Fokus — eine Form für alles, was untersucht wird.",
     "The thing posed: a question, proposal, goal or focus — one shape for everything being investigated."),
    ("Ref", "Ein Beleg-Zeiger (Memory, Council, Prototyp-State, Zitat). Vereint memory_refs, evidence, observed_state_refs, `[C#]`.",
     "A grounding pointer (memory, council, prototype-state, quote). Unifies memory_refs, evidence, observed_state_refs, `[C#]`."),
    ("Stance", "Eine einzige Positivitäts-Skala (−2 oppose … +2 support). Vereint stance, sentiment und votes zu EINER Darstellung.",
     "One positivity scale (−2 oppose … +2 support). Unifies stance, sentiment and votes into ONE representation."),
]


def _row(href: str, ric, title, right=None, *, color: str | None = None, sub=None) -> str:
    """A list row: leading icon/avatar (`ric`), title (+ optional muted `sub`), right-aligned meta."""
    lead = ric if color is None else h("span", {"class_": "rico", "style": f"color:{color}"}, raw(_icon(ric)))
    return h("a", {"class_": "row", "href": href}, lead,
             h("span", {"class_": "title"}, title,
               h("span", {"class_": "muted small"}, f" · {sub}") if sub else None),
             h("span", {"class_": "right"}, right))


def _projects_page() -> str:
    """The Projects list — the app's home (project-centric IA)."""
    store = Store()
    rows = []
    for p in services.list_research_projects(store=store):
        counts = fragment(                                     # the project's real contents (non-zero only)
            h("span", {}, f'{p["councils"]} {t("councils")}') if p.get("councils") else None,
            h("span", {}, f'{p["studies"]} {t("syntheses")}') if p["studies"] else None,
            h("span", {}, f'{p["prototypes"]} {t("prototypes_h")}') if p.get("prototypes") else None,
            h("span", {}, f'{p["notes"]} {t("notes")}') if p.get("notes") else None)
        meta = fragment(counts, raw(_star("project", p["id"], p["title"], f'/projects/{p["id"]}')))
        rows.append(_row(f'/projects/{p["id"]}', "projects", p["title"], meta, color="var(--accent)"))
    return _list_page(store, title=t("projects"), lead=t("projects_lead"), rows=rows,
                      empty_icon="projects", empty_msg=t("no_projects"), active="projects")


def _persona_row(p: dict, store: Store) -> str:
    pid = p["id"]
    try:
        proj = services.list_active_projects(pid, store=store)
    except Exception:
        proj = []
    loops = len(store.list_threads(pid, "open"))
    meta = fragment(
        _label(t("n_projects", n=len(proj)), "var(--accent)") if proj else None,
        _label(t("n_open", n=loops), "var(--amber)") if loops else None)
    right = fragment(h("span", {"class_": "muted small"}, p["company_context"]["industry"]), meta,
                     raw(_star("persona", pid, p["display_name"], f"/personas/{pid}")))
    return _row(f'/personas/{pid}', _avatar(p, 22), p["display_name"], right, sub=p["role"]["title"])


def register_lists(app) -> None:
    """Library/index routes that aren't project-scoped: the global Prototypes and Concepts lists."""
    from fastapi.responses import HTMLResponse

    @app.get("/documentation", response_class=HTMLResponse)   # not /docs (FastAPI reserves that for Swagger)
    def docs_page() -> str:
        return _docs_page()

    @app.get("/prototypes", response_class=HTMLResponse)
    def prototypes_list() -> str:
        store = Store()
        rows = []
        for p in store.list_prototypes():
            ap = _artifact_present(p)
            proj = store.get_research_project(p["project_id"]) if p.get("project_id") else None
            nsess = len(store.list_prototype_sessions(prototype_id=p["id"]))
            right = fragment(
                h("span", {"class_": "muted small"}, proj["title"]) if proj else None,
                h("span", {}, f'{t("sessions")} {nsess}') if nsess else None,
                h("span", {"class_": "muted small"}, p["version"]) if p.get("version") else None,
                raw(_star("prototype", p["id"], p["name"], f'/prototypes/{p["slug"]}')))
            rows.append(_row(f'/prototypes/{p["slug"]}', "prototype", p["name"], right,
                             color=ap["color"], sub=ap["disc"] or ap["label"]))
        return _list_page(store, title=t("prototypes_h"), lead=t("prototypes_lead"), rows=rows,
                          empty_icon="prototype", empty_msg=t("no_prototypes"), active="prototype")

    @app.get("/notes", response_class=HTMLResponse)
    def notes_list() -> str:
        store = Store()
        rows = []
        for proj in store.list_research_projects():
            for n in services.list_notes(proj["id"], store=store):   # ONE note entity (concepts merged in)
                right = fragment(h("span", {"class_": "muted small"}, proj["title"]),
                                 raw(_star("note", n["id"], n.get("title", ""), f'/notes/{n["id"]}')))
                title = n.get("title") or (n.get("text", "")[:60] or "—")
                rows.append(_row(f'/notes/{n["id"]}', "panel", title, right, color="#f29900"))
        return _list_page(store, title=t("notes"), lead=t("notes_lead"), rows=rows,
                          empty_icon="panel", empty_msg=t("no_notes"), active="note")

    @app.get("/meta-reports")                       # unified: reports are project-scope syntheses
    def meta_reports_list():
        from fastapi.responses import RedirectResponse
        return RedirectResponse("/syntheses")

# Co-located CSS (spec/roadmap.md R3): linear list rows.
register_css(r"""
/* ---- linear list rows (G3) ---- */
.group{margin:18px 0 2px;display:flex;align-items:center;gap:8px;font-size:var(--t-sm);color:var(--muted);font-weight:600}
.group .cnt{color:var(--muted);font-weight:500}
.rows{border:0;border-top:1px solid var(--line-2);background:transparent}
.row{display:flex;align-items:center;gap:11px;padding:9px 10px;border-bottom:1px solid var(--line-2);min-height:40px;border-radius:7px;transition:background 110ms}
.row:last-child{border-bottom:0}.row:hover{background:var(--hover)}
.row>svg.ic,.row>.ic{color:var(--faint);flex-shrink:0;width:16px;height:16px}.row:hover>svg.ic{color:var(--muted)}
.rico{display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;width:24px;height:24px;border-radius:6px;background:var(--panel-2)}
.rico svg{width:15px;height:15px}
.h1cnt{font-size:var(--t-body);font-weight:500;color:var(--faint);margin-left:7px;vertical-align:middle}
.list-empty{display:flex;flex-direction:column;align-items:center;gap:8px;padding:48px 0;color:var(--muted);text-align:center}.list-empty svg{width:26px;height:26px;color:var(--faint)}
.row .title{font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
.row .sub{color:var(--muted);font-size:var(--t-sm);flex-shrink:0}
.row .right{display:flex;align-items:center;gap:11px;flex-shrink:0;color:var(--faint);font-size:var(--t-sm)}
.votebar{display:inline-flex;height:6px;width:88px;border-radius:3px;overflow:hidden;border:1px solid var(--line)}
.votebar i{display:block;height:100%}
/* ---- Documentation reference page ---- */
.docgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px;margin-top:22px}
.doccard{border:1px solid var(--line);border-radius:var(--radius-md,10px);padding:16px 18px;background:var(--panel);transition:border-color 120ms,box-shadow 120ms}
.doccard:hover{border-color:var(--line-strong,var(--muted));box-shadow:0 1px 3px rgba(0,0,0,.04)}
.doc-h{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.doc-h .rico{width:30px;height:30px}.doc-h .rico svg{width:18px;height:18px}
.doc-name{font-size:var(--t-md);font-weight:650;letter-spacing:-.01em}
.doc-desc{color:var(--ink)}.doc-desc p{margin:0;max-width:none}
.doc-sec{margin-top:13px;padding-top:11px;border-top:1px solid var(--line-2)}
.doc-lbl{font-size:var(--t-xs,11px);font-weight:650;letter-spacing:.04em;text-transform:uppercase;color:var(--faint);margin-bottom:6px}
.doc-caps{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:5px}
.doc-caps li{position:relative;padding-left:16px;font-size:var(--t-sm);color:var(--muted);line-height:1.5}
.doc-caps li::before{content:"";position:absolute;left:2px;top:8px;width:4px;height:4px;border-radius:50%;background:var(--accent)}
.doc-adv{color:var(--ink)}.doc-adv p{margin:0;max-width:none}
/* ---- How it works (lifecycle steps) ---- */
.hiw{display:flex;flex-direction:column;gap:2px;margin-top:14px}
.hiw-step{display:flex;gap:14px;padding:12px 0;border-bottom:1px solid var(--line-2)}
.hiw-step:last-child{border-bottom:0}
.hiw-num{flex-shrink:0;width:26px;height:26px;border-radius:50%;background:var(--panel-2);color:var(--accent);font-weight:650;font-size:var(--t-sm);display:flex;align-items:center;justify-content:center}
.hiw-main{min-width:0}
.hiw-title{font-weight:600;font-size:var(--t-md);letter-spacing:-.01em;margin-bottom:3px}
.hiw-body{color:var(--muted)}.hiw-body p{margin:0;max-width:none}
.hiw-contract{margin-top:14px;padding:12px 14px;border:1px solid var(--line-2);border-radius:var(--radius-md,10px);background:var(--panel-2);color:var(--ink)}
.hiw-contract p{margin:0;max-width:none}
""")
