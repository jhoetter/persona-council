"""Peek partials — /peek/{kind}/{id} (spec/ux-contract.md §3.3, decision §7.3).

Clicking any row opens its kind's ESSENCE in the shared right drawer (DRAWER_JS fetches this
fragment); Enter / middle-click / no-JS follow the row's plain href to the detail route, so
peeks are navigation sugar, never the only address. v1 covers ALL kinds: a generic default
(header row via ui.primitive_row · clamped body · ref chips · "Open ↗") plus cheap kind extras
only where the renderer already exists — the decision/hypothesis cards (pages/decisions,
pages/hypotheses), the survey stance strip (pages/surveys), the session verdict + verified
badge, the asset preview/download. READ-ONLY; returns a bare fragment (one root <div class=
"page">), not a full layout — the drawer extracts it, a direct hit still renders standalone."""
from __future__ import annotations

from fastapi.responses import HTMLResponse

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .. import ui
from .._presence import open_question_status_pill
from .._render import render_ref
from ... import artifacts as _A
from .decisions import _decision_row
from .hypotheses import _hypothesis_row
from .surveys import _stance_strip


def _frame(*parts, open_href: str | None = None) -> str:
    """The shared peek scaffold: the kind's parts + the explicit 'Open ↗' deep link."""
    open_link = (h("div", {"class_": "sec"},
                   h("a", {"class_": "sl-btn", "href": open_href},
                     t("peek_open"), " ", raw(_icon("external")))) if open_href else None)
    return h("div", {"class_": "page"}, *[p for p in parts if p], open_link)


def _refs(label: str, refs: list, store) -> str:
    if not refs:
        return ""
    return h("p", {"class_": "muted small turn-refs"}, label, ": ",
             fragment(*(raw(render_ref(r, store)) for r in refs)))


def _value_strip(stance_counts: dict, store=None) -> str:
    """A council's stance lean as the survey-style distribution strip — value counts mapped onto
    the canonical scale terms (artifacts.stance_meta), nothing stance-y hardcoded."""
    by_term = {}
    for term in _A.stance_terms():
        n = int(stance_counts.get(term["value"]) or stance_counts.get(str(term["value"])) or 0)
        if n:
            by_term[term["term"]] = n
    total = sum(by_term.values())
    return _stance_strip(by_term, total) if total else ""


def _council_peek(oid: str, store) -> str | None:
    c = store.get_council_session(oid)
    if not c:
        return None
    stance_counts: dict = {}
    for s in c.get("statements") or []:
        v = (s.get("stance") or {}).get("value")
        if v is not None:
            stance_counts[int(v)] = stance_counts.get(int(v), 0) + 1
    return _frame(ui.primitive_row("council", {**c, "mode": services.council_mode(c)}, store),
                  h("div", {"class_": "sec"}, ui.clamp(c.get("summary") or c.get("exec_summary") or "")),
                  raw(_value_strip(stance_counts)),
                  open_href=f"/councils/{oid}")


def _synthesis_peek(oid: str, store, kind: str) -> str | None:
    syn = store.get_synthesis(oid)
    if not syn:
        return None
    sentiment = _A.synthesis_sentiment_counts(syn, store)
    total = sum(sentiment.values())
    return _frame(ui.primitive_row(kind, syn, store),
                  h("div", {"class_": "sec"}, ui.clamp(syn.get("gesamtbild", ""))),
                  raw(_stance_strip(sentiment, total)) if total else None,
                  open_href=f"/syntheses/{oid}")


def _survey_peek(oid: str, store) -> str | None:
    try:
        s = services.get_survey(oid, store=store)
    except KeyError:
        return None
    results = services.survey_results(s["id"], store=store)
    by_q = {r["question_id"]: r for r in results["questions"]}
    q_rows = [h("p", {"class_": "small"}, h("span", {"class_": "muted"}, f'{q.get("id", "")} '),
                q.get("text", ""), " ", h("span", {"class_": "pill"}, q.get("kind", "")))
              for q in s.get("questions") or []]
    # The stance distribution over the REAL responses (stance-mapped questions aggregated).
    agg: dict[str, int] = {}
    for q in s.get("questions") or []:
        actual = ((by_q.get(q["id"]) or {}).get("comparison") or {}).get("actual") or {}
        for term, n in (actual.get("counts") or {}).items():
            agg[term] = agg.get(term, 0) + n
    total = sum(agg.values())
    return _frame(ui.primitive_row("survey", s, store),
                  h("div", {"class_": "sec"}, ui.clamp(s.get("intro", ""))) if s.get("intro") else None,
                  raw(_stance_strip(agg, total)) if total else None,
                  h("div", {"class_": "sec"}, *q_rows),
                  _refs(t("rel_based_on"), s.get("derived_from") or [], store),
                  open_href=f'/surveys/{s["id"]}')


def _session_peek(oid: str, store) -> str | None:
    sess = services.get_usability_session(oid, store=store)
    if not sess:
        return None
    out = sess.get("outcome") or {}
    first_friction = next((st for st in sess.get("steps") or []
                           if (st.get("friction") or {}).get("level") not in (None, "", "none")), None)
    friction = (h("p", {"class_": "muted small"},
                  raw(_icon("flag")), " ", (first_friction.get("friction") or {}).get("note", "")
                  or (first_friction.get("action") or {}).get("detail", ""))
                if first_friction else None)
    return _frame(ui.primitive_row("session", sess, store),
                  h("div", {"class_": "sec"}, ui.clamp(out.get("summary", ""))),
                  friction,
                  open_href=f"/sessions/{oid}")


def _asset_peek(oid: str, store) -> str | None:
    rec = next((a for p in store.list_research_projects()
                for a in (p.get("assets") or []) if a.get("id") == oid), None)
    if not rec:
        return None
    preview = (h("p", {}, h("img", {"src": rec["url"], "alt": rec.get("title", ""), "loading": "lazy"}))
               if rec.get("kind") in ("image", "screenshot") and rec.get("url") else None)
    is_out = rec.get("direction") == "out"
    action = h("a", {"class_": "sl-btn", "href": rec.get("url", "#"),
                     **({"download": rec.get("filename", "")} if is_out
                        else {"target": "_blank", "rel": "noopener"})},
               raw(_icon("download" if is_out else "external")), " ",
               t("asset_dir_out") if is_out else t("open"))
    size_kb = f'{max(1, int(rec.get("bytes") or 0) // 1024)} KB'    # a unit, not a UI string
    meta = h("p", {"class_": "muted small"},
             f'{rec.get("filename", "")} · {size_kb}'
             + (f' · {rec.get("notes")}' if rec.get("notes") else ""))
    return _frame(ui.primitive_row("asset", rec, store), preview, meta,
                  h("div", {"class_": "sec"}, action))


def _open_question_peek(oid: str, store) -> str | None:
    rec = next((o for p in store.list_research_projects()
                for o in store.list_open_questions(p["id"]) if o.get("id") == oid), None)
    if not rec:
        return None
    return _frame(h("p", {}, raw(open_question_status_pill(rec.get("status", "open"))), " ",
                    rec.get("text", "")))


def peek_body(kind: str, oid: str, store) -> str | None:
    """The drawer fragment for one primitive — None when the record is gone (honest 404)."""
    if kind == "council":
        return _council_peek(oid, store)
    if kind in ("synthesis", "report"):
        return _synthesis_peek(oid, store, kind)
    if kind == "decision":
        try:
            d = services.get_decision(oid, store=store)
        except KeyError:
            return None
        by_id = {x["id"]: x for x in store.list_decisions(d.get("project_id"))}
        return _frame(raw(_decision_row(d, store, by_id)), open_href=f"/decisions/{oid}")
    if kind == "hypothesis":
        try:
            hx = services.get_hypothesis(oid, store=store)
        except KeyError:
            return None
        return _frame(raw(_hypothesis_row(hx, store)), open_href=f"/hypotheses/{oid}")
    if kind == "survey":
        return _survey_peek(oid, store)
    if kind == "session":
        return _session_peek(oid, store)
    if kind == "asset":
        return _asset_peek(oid, store)
    if kind == "open_question":
        return _open_question_peek(oid, store)
    if kind == "note":
        try:
            n = services.get_note(oid, store=store)["note"]
        except KeyError:
            return None
        return _frame(ui.primitive_row("note", n, store),
                      h("div", {"class_": "sec"}, ui.clamp(n.get("text", ""))),
                      open_href=f"/notes/{oid}")
    if kind == "prototype":
        p = store.get_prototype(oid)
        if not p:
            return None
        return _frame(ui.primitive_row("prototype", p, store),
                      h("div", {"class_": "sec"}, ui.clamp(p.get("description", ""))) if p.get("description") else None,
                      open_href=f'/prototypes/{p["slug"]}')
    return None


def register_peek(app) -> None:
    @app.get("/peek/{kind}/{oid}", response_class=HTMLResponse)
    def peek_partial(kind: str, oid: str):
        store = Store()
        body = peek_body(kind, oid, store)
        if body is None:
            return HTMLResponse(str(h("div", {"class_": "page"},
                                      h("p", {"class_": "muted"}, t("not_found")))), status_code=404)
        return HTMLResponse(str(body))
