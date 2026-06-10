"""Survey pages: list + detail (the outbound instrument's inspector surface).

READ-ONLY like every page: authoring/export/import happen through MCP/CLI. The detail page shows
the instrument (questions, status, derived-from chips via render_ref) and — once real responses are
imported — the per-question aggregates plus the predicted-vs-actual strip for stance_mapped
questions, drawn with the canonical stance colors (artifacts.stance_meta — no stance word or color
is hardcoded here)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._html import register_css
from .._render import render_ref
from ... import artifacts as _A


register_css(r"""
.svq{border:1px solid var(--line-2);border-radius:9px;padding:12px 14px;margin:0 0 10px;background:var(--panel)}
.svq .qhead{display:flex;gap:8px;align-items:baseline}
.svq .qnum{color:var(--muted);font-size:var(--t-sm)}
.svopts{margin:6px 0 0;display:flex;flex-wrap:wrap;gap:6px}
.svbar{position:relative;height:18px;border-radius:5px;background:var(--line-2);overflow:hidden;flex:1}
.svbar i{position:absolute;inset:0 auto 0 0;background:var(--accent);opacity:.35}
.svrow{display:grid;grid-template-columns:minmax(120px,1fr) 3fr 44px;gap:10px;align-items:center;margin:4px 0;font-size:var(--t-sm)}
.pvlbl{color:var(--muted);font-size:var(--t-sm);min-width:130px}
.pvbar{display:flex;height:14px;border-radius:7px;overflow:hidden;background:var(--line-2);flex:1}
.pvseg{height:100%}
.pvline{display:flex;gap:10px;align-items:center;margin:5px 0}
""")


def _status_pill(status: str) -> str:
    """Survey lifecycle pill (a lifecycle, not a vocabulary — the stance strip below stays fully
    data-driven via stance_meta). Resolved per request so the labels follow the active UI language."""
    pills = {"draft": (t("survey_status_draft"), "var(--muted)"),
             "open": (t("survey_status_open"), "var(--green)"),
             "closed": (t("survey_status_closed"), "var(--violet)")}
    label, color = pills.get(status, pills["draft"])
    return _label(label, color)


def _stance_strip(counts: dict, total: int) -> str:
    """One distribution strip — segments ordered/colored by the canonical scale (stance_terms +
    stance_meta), labels resolved through t(label_key). Nothing stance-y is hardcoded."""
    segs = []
    for term in _A.stance_terms():
        n = counts.get(term["term"], 0)
        if not n:
            continue
        meta = _A.stance_meta(term["value"])
        segs.append(h("span", {"class_": "pvseg",
                               "style": f'width:{n / total * 100:.1f}%;background:{meta["color"]}',
                               "title": f'{t(meta["label_key"])}: {n}'}))
    return h("div", {"class_": "pvbar"}, fragment(*segs))


def _predicted_vs_actual(comparison: dict, store) -> str:
    pred, act = comparison.get("predicted") or {}, comparison.get("actual") or {}
    rows = []
    for label, dist in ((t("survey_predicted"), pred), (t("survey_actual"), act)):
        n = dist.get("n", 0)
        bar = _stance_strip(dist.get("counts") or {}, n) if n else h("div", {"class_": "pvbar"})
        rows.append(h("div", {"class_": "pvline"},
                      h("span", {"class_": "pvlbl"}, f"{label} ({n})"), raw(bar)))
    chips = fragment(*(raw(render_ref(r, store)) for r in (pred.get("refs") or [])))
    refs_line = (h("p", {"class_": "muted small turn-refs"}, t("rel_based_on"), ": ", chips)
                 if pred.get("refs") else None)
    return h("div", {"style": "margin-top:8px"}, fragment(*rows), refs_line)


def _question_html(q: dict, result: dict | None, store) -> str:
    kind_pill = h("span", {"class_": "pill"}, q.get("kind", ""))
    mapped = (h("span", {"class_": "pill"}, t("survey_stance_mapped"))
              if q.get("stance_mapped") else None)
    head = h("div", {"class_": "qhead"}, h("span", {"class_": "qnum"}, q.get("id", "")),
             h("b", {}, q.get("text", "")), kind_pill, mapped)
    body = []
    res = result or {}
    answered = res.get("answered", 0)
    if answered and q.get("kind") == "text":
        body += [h("p", {"class_": "muted small", "style": "margin:6px 0 0"}, f"„{a}“")
                 for a in (res.get("answers") or [])[:8]]
    elif answered:
        counts = res.get("counts") or {}
        for opt in q.get("options") or []:
            n = counts.get(opt, 0)
            pct = (n / answered * 100) if answered else 0
            body.append(h("div", {"class_": "svrow"}, h("span", {}, opt),
                          h("div", {"class_": "svbar"}, h("i", {"style": f"width:{pct:.1f}%"})),
                          h("span", {"class_": "muted small", "style": "text-align:right"}, str(n))))
    elif q.get("options"):
        body.append(h("div", {"class_": "svopts"},
                      fragment(*(h("span", {"class_": "pill"}, o) for o in q["options"]))))
    if answered and q.get("stance_mapped") and res.get("comparison"):
        body.append(raw(_predicted_vs_actual(res["comparison"], store)))
    return h("div", {"class_": "svq"}, head, fragment(*body))


def register_surveys(app) -> None:
    @app.get("/surveys", response_class=HTMLResponse)
    def surveys() -> str:
        store = Store()
        rows = []
        for s in services.list_surveys(store=store):
            rows.append(h("a", {"class_": "row", "href": f'/surveys/{s["id"]}'},
                          h("span", {"class_": "rico", "style": "color:var(--accent)"},
                            raw(_icon("plan"))),
                          h("span", {"class_": "title"}, s["title"]),
                          h("span", {"class_": "right"}, raw(_status_pill(s.get("status", "draft"))),
                            h("span", {}, t("n_questions", n=len(s.get("questions") or []))),
                            h("span", {}, t("n_responses", n=s.get("response_count", 0))),
                            h("span", {}, s["created_at"][:10]))))
        return _list_page(store, title=t("surveys_h"), lead=t("surveys_lead"), rows=rows,
                          empty_icon="plan", empty_msg=t("no_surveys"), active="projects")

    @app.get("/surveys/{survey_id}", response_class=HTMLResponse)
    def survey_detail(survey_id: str) -> str:
        store = Store()
        try:
            s = services.get_survey(survey_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("surveys_h"), t("runtime_maybe_cleared"),
                                                        icon="plan"), store, active="projects")
        results = services.survey_results(s["id"], store=store)
        by_q = {r["question_id"]: r for r in results["questions"]}
        proj = store.get_research_project(s.get("project_id")) if s.get("project_id") else None
        crumbs = [(t("projects"), "/projects")]
        if proj:
            crumbs.append((proj["title"], f'/projects/{proj["id"]}'))
        crumbs.append((s["title"], None))
        derived = s.get("derived_from") or []
        derived_html = (h("p", {"class_": "muted small turn-refs", "style": "margin:4px 0 14px"},
                          t("rel_based_on"), ": ",
                          fragment(*(raw(render_ref(r, store)) for r in derived)))
                        if derived else None)
        intro_html = (h("p", {"class_": "sub", "style": "margin:0 0 10px"}, s.get("intro", ""))
                      if s.get("intro") else None)
        questions_html = h("div", {"class_": "sec", "id": "sec-questions"},
                           h("h2", {}, t("n_questions", n=len(s["questions"]))),
                           fragment(*(_question_html(q, by_q.get(q["id"]), store)
                                      for q in s["questions"])))
        n_resp = results["responses"]
        results_head = h("div", {"class_": "sec", "id": "sec-responses", "style": "margin-top:8px"},
                         h("h2", {}, t("n_responses", n=n_resp)),
                         (h("p", {"class_": "muted small"}, t("no_survey_responses"))
                          if not n_resp else None))
        body = fragment(intro_html, derived_html, results_head, questions_html)
        proj_link = (h("a", {"href": f'/projects/{proj["id"]}'}, proj["title"]) if proj else "—")
        return detail_page(
            store, title=s["title"], active="projects", crumbs=crumbs,
            icon="plan", sub=fragment(t("surveys_h"), " ", raw(_status_pill(s.get("status", "draft")))),
            body=body,
            prop_rows=[("dot", t("type_h"), t("surveys_h")),
                       ("personas", t("n_responses", n=n_resp), str(results["respondents"])),
                       ("projects", t("project"), proj_link),
                       ("clock", t("created"), s.get("created_at", "")[:10])],
            rail_sections=[("sec-responses", t("n_responses", n=n_resp)),
                           ("sec-questions", t("n_questions", n=len(s["questions"])))],
            star=("survey", s["id"], s["title"], f'/surveys/{s["id"]}'))
