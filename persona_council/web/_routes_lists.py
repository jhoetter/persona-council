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
# Entry = (kind, icon, name_i18n_key_or_None, desc_de, desc_en, caps_de, caps_en).
# NAME + COLOR come from data: t(name_key) when a chrome label exists, else present(kind)["label"];
# colour is always present(kind)["color"] — so no methodology/artifact label is hardcoded here
# (the zero-hardcoded-values gate). Only the descriptive prose is authored, in Markdown.
DOCS = [
    ("project", "projects", "projects",
     "Der Forschungs-**Container**: ein Double-Diamond-Graph einer Studie (Discover → Define → Develop → Deliver).",
     "The research **container**: a Double-Diamond graph of one study (Discover → Define → Develop → Deliver).",
     ["Bündelt Councils, Synthesen, Notizen & Prototypen", "Trackt Phasen, offene Fragen und einen Meta-Report"],
     ["Bundles councils, syntheses, notes & prototypes", "Tracks phases, open questions and a meta-report"]),
    ("persona", "personas", "personas",
     "Ein synthetisches Kundenprofil (**SOUL** + Erinnerung) — der „Proband“.",
     "A synthetic customer profile (**SOUL** + memory) — the research subject.",
     ["Antwortet _in character_ in Councils", "Reagiert auf Prototypen aus gelebter Erfahrung"],
     ["Answers _in character_ in councils", "Reacts to prototypes from lived experience"]),
    ("council", "councils", "councils",
     "Eine memory-geerdete **Persona-Debatte**. Drei Modi: _Discovery_ (offene Fragen), _Evaluation_ "
     "(Reaktion auf ein Konzept), _Decision_ (Abstimmung).",
     "A memory-grounded **persona debate**. Three modes: _Discovery_ (open questions), _Evaluation_ "
     "(reacting to a concept), _Decision_ (a vote).",
     ["Sammelt echte Reaktionen statt Meinungen", "Liefert eine Executive Summary + Erkenntnis"],
     ["Gathers real reactions, not opinions", "Produces an executive summary + finding"]),
    ("synthesis", "syntheses", "syntheses",
     "Der **Report-Knoten**: faltet Councils zu einem Gesamtbild, Kernproblemen und Empfehlungen zusammen.",
     "The **report node**: folds councils into a big picture, key problems and recommendations.",
     ["Empfehlungen mit Aufwand·Nutzen", "Verkettet zu einem wachsenden Studien-Bogen"],
     ["Recommendations scored by effort·impact", "Chains into one growing study arc"]),
    ("concept", "bulb", "concepts",
     "Eine **Lösungs-Idee** aus der Ideation — bereit, von einem Council geprüft oder als Artefakt gebaut zu werden.",
     "A **solution idea** from ideation — ready to be evaluated by a council or built as an artefact.",
     ["Brücke von Insight zu Artefakt"], ["The bridge from insight to artefact"]),
    ("prototype", "prototype", "prototypes_h",
     "Ein **lauffähiges Artefakt** (von grob bis hochauflösend), das Personas testen.",
     "A **runnable artefact** (low to high fidelity) that personas test.",
     ["Sessions erfassen geerdete Reaktionen", "Zeigt die Fidelity-Iteration im Develop-Diamanten"],
     ["Sessions capture grounded reactions", "Shows the fidelity iteration in the Develop diamond"]),
    ("note", "panel", None,
     "Ein **leichtgewichtiges Signal** im Projekt-Graph — eine rohe Beobachtung.",
     "A **lightweight signal** in the project graph — a raw observation.",
     ["Methodologie-frei, jederzeit erfassbar"], ["Methodology-free, capture anytime"]),
    ("section", "squareGrid", "section",
     "Eine **methodologie-unabhängige Gruppierung** von Graph-Knoten (ein Frame/Cluster).",
     "A **methodology-independent grouping** of graph nodes (a frame/cluster).",
     ["Strukturiert den Graphen ohne feste Methode"], ["Structures the graph without a fixed method"]),
    ("meta", "overview", "meta_report",
     "Ein **studienübergreifender** Projekt-Report, der den ganzen Graphen verdichtet.",
     "A **cross-study** project report that distills the whole graph.",
     ["Die Vogelperspektive über alle Synthesen"], ["The bird's-eye view across all syntheses"]),
]


def _docs_page() -> str:
    from .. import presentation as _pres
    store = Store()
    de = _lang() == "de"
    cards = []
    for kind, icon, name_key, dde, den, cde, cen in DOCS:
        pres = _pres.present(kind)
        name = t(name_key) if name_key else (pres["label"] if not pres["label"].islower() else pres["label"].capitalize())
        desc, caps = (dde, cde) if de else (den, cen)
        cards.append(h("div", {"class_": "doccard"},
            h("div", {"class_": "doc-h"},
              h("span", {"class_": "rico", "style": f"color:{pres['color']}"}, raw(_icon(icon))),
              h("span", {"class_": "doc-name"}, name)),
            h("div", {"class_": "es-prose sm doc-desc"}, raw(_md(desc))),
            h("ul", {"class_": "doc-caps"}, fragment(*(h("li", {}, raw(_md_inline(c))) for c in caps)))))
    body = h("section", {},
             h("div", {"class_": "hero"}, h("h1", {}, raw(_icon("overview")), t("documentation")),
               h("div", {"class_": "es-prose sm", "style": "margin-top:6px"}, raw(_md(DOCS_INTRO["de" if de else "en"])))),
             h("div", {"class_": "docgrid"}, fragment(*cards)))
    return _layout(t("documentation"), body, store, crumbs=[(t("documentation"), None)], active="docs")


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
            h("span", {}, f'{p["concepts"]} {t("concepts")}') if p.get("concepts") else None)
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

    @app.get("/concepts", response_class=HTMLResponse)
    def concepts_list() -> str:
        store = Store()
        rows = []
        for proj in store.list_research_projects():
            for n in services.list_notes(proj["id"], store=store):
                if (n.get("kind") or "note") != "concept":
                    continue
                right = fragment(h("span", {"class_": "muted small"}, proj["title"]),
                                 raw(_star("concept", n["id"], n.get("title", ""), f'/concepts/{n["id"]}')))
                rows.append(_row(f'/concepts/{n["id"]}', "bulb", n.get("title", ""), right, color="#ea4335"))
        return _list_page(store, title=t("concepts"), lead=t("concepts_lead"), rows=rows,
                          empty_icon="bulb", empty_msg=t("no_concepts"), active="concept")

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
.doc-caps{list-style:none;margin:12px 0 0;padding:10px 0 0;border-top:1px solid var(--line-2);display:flex;flex-direction:column;gap:6px}
.doc-caps li{position:relative;padding-left:18px;font-size:var(--t-sm);color:var(--muted);line-height:1.5}
.doc-caps li::before{content:"";position:absolute;left:3px;top:8px;width:5px;height:5px;border-radius:50%;background:var(--accent)}
.nav-foot{margin-top:auto;padding-top:8px}
""")
