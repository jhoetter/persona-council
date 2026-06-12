"""Hypotheses: the cross-project list page + the shared bet renderers.

A hypothesis LIVES on its project page — an outline row in its phase context (UX P2,
spec/ux-contract.md §3.4 / decision §7.1); the canonical Ref route /hypotheses/{id} (registered
in projects.py) redirects into that row's anchor. This module owns everything bet-shaped that is
shared between the global /hypotheses index and the hypothesis peek (web/pages/peek.py): the
predicted/observed row card and the hit-rate strip (the lifecycle pills live in web/_presence,
shared with the outline chips). The list is READ-ONLY like every page; rows deep-link into their
project's row. /hypotheses and /hypotheses/{id} have distinct path shapes, so the list route
never shadows the redirect regardless of registration order (we still register it after
projects' routes — see pages/__init__)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._html import register_css
from .._presence import HYP_STATUS_COLORS, hypothesis_status_label, hypothesis_status_pill
from .._render import render_ref

# Card CSS shared by hypothesis AND decision rows (.hyp is the generic artifact card; decisions.py
# reuses it — co-located here with its primary owner).
register_css(r"""
.hyp{border:1px solid var(--line-2);border-radius:9px;padding:10px 14px;margin:8px 0;background:var(--panel)}
.hypvals{display:flex;gap:16px;flex-wrap:wrap;margin-top:4px;font-size:var(--t-sm)}
.hyprate{display:flex;gap:10px;align-items:center;margin:6px 0 12px}
.hypstrip{display:flex;height:14px;border-radius:7px;overflow:hidden;background:var(--line-2);flex:1;max-width:340px}
.hypseg{height:100%}
""")


def _hyp_predicted_text(pred: dict) -> str:
    """metric → expectation (value ±tolerance, or the direction word) · confidence."""
    if "expected_value" in pred:
        expected = str(pred.get("expected_value"))
        if pred.get("tolerance"):
            expected += f' ±{pred["tolerance"]:g}'
    else:
        expected = (t("hyp_dir_increase") if pred.get("expected_direction") == "increase"
                    else t("hyp_dir_decrease"))
    out = f'{pred.get("metric", "")} → {expected}'
    conf = pred.get("confidence")
    if conf is not None:
        out += f' · {t("hyp_confidence")} {conf:.0%}'
    return out


def _hypothesis_row(hx: dict, store, *, title_href: str | None = None,
                    project_title: str | None = None) -> str:
    """One bet card. On the project page the card is the anchor target (plain bold title); on the
    cross-project list `title_href` links the title into that anchor and `project_title` names
    where the bet lives."""
    pred = hx.get("prediction") or {}
    res = hx.get("result") or {}
    vals = [h("span", {}, h("span", {"class_": "muted"}, t("hyp_predicted"), ": "),
              _hyp_predicted_text(pred))]
    if res:
        vals.append(h("span", {}, h("span", {"class_": "muted"}, t("hyp_observed"), ": "),
                      str(res.get("observed_value", ""))))
    note = (h("p", {"class_": "muted small", "style": "margin:4px 0 0"}, res["note"])
            if res.get("note") else None)
    src = (h("p", {"class_": "muted small turn-refs", "style": "margin:4px 0 0"},
             t("hyp_observed"), ": ", raw(render_ref(res["source"], store)))
           if res.get("source") else None)
    derived = (h("p", {"class_": "muted small turn-refs", "style": "margin:4px 0 0"},
                 t("rel_based_on"), ": ",
                 fragment(*(raw(render_ref(r, store)) for r in hx["derived_from"])))
               if hx.get("derived_from") else None)
    status = hx.get("status", "open")
    title = h("b", {}, hx.get("text", ""))
    if title_href:
        title = h("a", {"href": title_href}, title)
    proj = (h("span", {"class_": "muted small", "style": "margin-left:8px"}, project_title)
            if project_title else None)
    return h("div", {"class_": "hyp", "id": f'hyp-{hx["id"]}'},
             h("div", {}, raw(hypothesis_status_pill(status)), " ", title, proj),
             h("div", {"class_": "hypvals"}, fragment(*vals)), note, src, derived)


def _hyp_hit_rate_strip(hyps: list) -> str:
    """The hit-rate strip over RESOLVED bets only — open ones haven't been scored by reality yet,
    and dropped ones aren't scored at all. Honest line when nothing is resolved."""
    scored = [x for x in hyps if x.get("status") not in ("open", "dropped")]
    if not scored:
        return h("p", {"class_": "muted small"}, t("hyp_no_resolved"))
    decisive = [x for x in scored if x.get("status") in ("validated", "refuted")]
    hits = sum(1 for x in decisive if x["status"] == "validated")
    segs = []
    for status in ("validated", "refuted", "inconclusive"):
        n = sum(1 for x in scored if x["status"] == status)
        if n:
            segs.append(h("span", {"class_": "hypseg",
                                   "style": (f"width:{n / len(scored) * 100:.1f}%;"
                                             f"background:{HYP_STATUS_COLORS[status]}"),
                                   "title": f"{hypothesis_status_label(status)}: {n}"}))
    rate = (f"{hits}/{len(decisive)} · {hits / len(decisive) * 100:.0f}%" if decisive
            else t("hyp_no_decisive"))
    return h("div", {"class_": "hyprate"},
             h("span", {"class_": "muted small"}, t("hyp_hit_rate"), f": {rate}"),
             h("div", {"class_": "hypstrip"}, fragment(*segs)))


def register_hypotheses(app) -> None:
    @app.get("/hypotheses", response_class=HTMLResponse)
    def hypotheses_list() -> str:
        """Every bet across all projects — the Library's Hypotheses tab (ux-contract §3.5),
        keeping the GLOBAL hit-rate strip: how often do our predictions survive reality?"""
        from .library import library_page
        store = Store()
        hyps = services.list_hypotheses(store=store)
        strip = str(_hyp_hit_rate_strip(hyps)) if hyps else ""
        return library_page("hypotheses", store, pre_extra=strip)
