from __future__ import annotations

from collections import Counter, defaultdict

from .. import services
from ..storage import Store
from ._i18n import t
from ._components import (
    _esc, _icon, _avatar, _label, _md, _srcchips, _prose, _rec_row_n,
    _effort_impact, _star, _study_lead,
)
from ._render import render_findings, render_statement
from .. import artifacts as _A
from ._vm import study_head
from ._html import h, raw, fragment, register_css


# Co-located CSS (spec/roadmap.md R3): analytics charts + voices/Stimmen cockpit.
register_css(r"""
/* ---- analytics (Linear-style insight cards) ---- */
.insights{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.insight{border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);padding:16px}
.insight.wide{grid-column:1 / -1}
.insight h3{margin:0 0 2px;font-size:var(--t-body)}
.insight .ihint{color:var(--muted);font-size:var(--t-sm);margin:0 0 14px}
.kpi{display:flex;align-items:baseline;gap:6px;margin:2px 0 10px}
.kpi b{font-size:var(--t-xl);font-weight:720;letter-spacing:-.01em}.kpi span{color:var(--muted);font-size:var(--t-sm)}
.stacked{display:flex;height:12px;border-radius:var(--radius-sm);overflow:hidden;background:var(--line-2);border:1px solid var(--line)}
.stacked i{display:block;height:100%}
.stacked.thin{height:8px}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin:11px 0 0;font-size:var(--t-sm);color:var(--muted)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.legend i{width:9px;height:9px;border-radius:2px;display:inline-block}
.dnrow{display:flex;align-items:center;gap:18px}
.donut{width:118px;height:118px;border-radius:50%;background:var(--g);flex-shrink:0;
  -webkit-mask:radial-gradient(closest-side,transparent 60%,#000 61%);mask:radial-gradient(closest-side,transparent 60%,#000 61%)}
.brow{display:grid;grid-template-columns:118px 1fr 30px;gap:10px;align-items:center;padding:5px 0;font-size:var(--t-sm)}
.brow .blab{color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.brow .btrack{height:9px;border-radius:var(--radius-sm);background:var(--line-2);overflow:hidden}
.brow .btrack i{display:block;height:100%}
.brow .bval{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.crow{display:grid;grid-template-columns:1fr 150px 64px;gap:12px;align-items:center;padding:9px 0;border-bottom:1px solid var(--line-2)}
.crow:last-child{border-bottom:0}.crow .ct{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--t-sm)}
.crow .cn{text-align:right;color:var(--muted);font-size:var(--t-sm)}
.prow{display:grid;grid-template-columns:150px 1fr 38px;gap:11px;align-items:center;padding:6px 0}
.prow .pn{display:flex;align-items:center;gap:8px;overflow:hidden}.prow .pn span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:var(--t-sm)}
.prow .ps{text-align:right;font-size:var(--t-sm);font-variant-numeric:tabular-nums}
.area svg{display:block;width:100%;height:140px}
.area .ln{fill:none;stroke:var(--accent);stroke-width:2}
.area .fl{fill:var(--accent);opacity:.10}
.area .dot{fill:var(--accent)}
.axis{display:flex;justify-content:space-between;color:var(--muted);font-size:var(--t-xs);margin-top:4px}
@media (max-width:760px){.insights{grid-template-columns:1fr}}

""")

# Co-located CSS (spec/roadmap.md R3): the synthesis report styles (was _SYN_STYLE in body).
register_css(r"""

.syn-head h1{font-size:var(--t-xl);line-height:1.2;letter-spacing:-.02em;font-weight:650;margin:0 0 8px;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}
.syn-head h1 svg{width:21px;height:21px;color:var(--accent);margin-right:8px;vertical-align:-2px}
.syn-goal{color:var(--muted);font-size:var(--t-md);line-height:1.5;max-width:72ch;margin:0 0 14px}
.syn-meta{display:flex;flex-wrap:wrap;gap:7px;align-items:center}
.mchip{font-size:var(--t-sm);color:var(--muted);border:1px solid var(--line);background:var(--panel-2);border-radius:var(--radius-sm);padding:3px 10px}
.block{margin:40px 0 0;padding-top:26px;border-top:1px solid var(--line)}
.block>.bh{font-size:var(--t-sm);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;margin:0 0 16px;display:flex;align-items:center;gap:8px}
.block>.bh .cnt{color:var(--accent);background:var(--accent-weak);border-radius:var(--radius-sm);padding:1px 9px;font-size:var(--t-xs)}details.block>summary.bh{cursor:pointer;margin-bottom:0}details.block[open]>summary.bh{margin-bottom:16px}
.syn-main section{padding:0;overflow:visible}
.syn-main .block{margin-top:40px;padding-top:26px}
.cgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.ref-list{display:flex;flex-direction:column;gap:6px}
.ref-row{display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);text-decoration:none;color:var(--ink)}
.ref-row:hover{border-color:var(--accent)}
.ref-n{font-weight:700;color:var(--accent);font-size:var(--t-sm);flex:none;width:26px}
.ref-t{flex:1;font-size:var(--t-body);line-height:1.35;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ref-bar{flex:none;width:120px}.ref-go{flex:none;color:var(--muted)}
.ccard{border:1px solid var(--line);border-radius:var(--radius-lg);padding:14px 16px;background:var(--panel);display:flex;flex-direction:column;gap:9px}
.cc-top{display:flex;align-items:center;gap:10px}
.cc-n{font-weight:740;color:var(--accent);font-size:var(--t-sm);letter-spacing:.03em}
.cc-bar{flex:1}
.cc-title{font-size:var(--t-md);line-height:1.3;margin:0;font-weight:660}
.cc-title a{color:var(--ink)}.cc-title a:hover{color:var(--accent)}
.cc-take{color:var(--muted);font-size:var(--t-body);line-height:1.5;margin:0}
.cc-chips{display:flex;gap:6px;flex-wrap:wrap}
.cc-more>summary{cursor:pointer;color:var(--muted);font-size:var(--t-sm);list-style:none}
.cc-more>summary::-webkit-details-marker{display:none}
.cc-more>summary::before{content:"\25B8 Exec-Summary";color:var(--muted)}
.cc-more[open]>summary::before{content:"\25BE Exec-Summary"}
.cc-es{font-size:var(--t-sm);line-height:1.55;margin-top:8px;border-top:1px dashed var(--line);padding-top:8px}
.cc-es h3{font-size:var(--t-sm);text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:10px 0 4px}
.cc-es p{margin:0 0 7px}.cc-es ul{margin:0 0 7px;padding-left:18px}
.cc-jump{font-weight:600;color:var(--accent);font-size:var(--t-body)}
.syn-main [id]{scroll-margin-top:26px}
/* effort·impact chart is a design-system component now (.sl-quad/.sl-legend, vendored from
   sonaloop-design via _components_css.py) — no local chart CSS here. */
.reclist .rec{display:flex;gap:11px;padding:10px 8px;border-bottom:1px solid var(--line-2);scroll-margin-top:72px}
.reclist .rec:last-child{border-bottom:none}
.recnum{flex:0 0 auto;width:22px;height:22px;border-radius:50%;background:var(--accent-weak);color:var(--accent);font-size:var(--t-sm);font-weight:700;display:flex;align-items:center;justify-content:center}
.reclist .rec:target{background:var(--accent-weak);border-radius:var(--radius)}
.axchip{display:inline-block;margin-top:6px;font-size:var(--t-xs);color:var(--muted);border:1px solid var(--line);border-radius:var(--radius-sm);padding:1px 7px}
@media(max-width:1180px){.syn-rail{display:none}}
@media(max-width:740px){.cgrid{grid-template-columns:1fr}.syn-head h1{font-size:var(--t-xl)}}
""")

# ----------------------------- chart primitives ----------------------------- #
# Vanilla inline charts (CSS/conic-gradient/SVG) — no build step, dark-mode safe.


def _stacked(parts: list[tuple], thin: bool = False) -> str:
    """parts: [(value, color, label)]. Renders a single horizontal stacked bar."""
    total = sum(v for v, _, _ in parts) or 1
    segs = [h("i", {"style": f"width:{v / total * 100:.3f}%;background:{c}", "title": f"{lbl}: {v}"})
            for v, c, lbl in parts if v]
    return h("div", {"class_": f'stacked{" thin" if thin else ""}'}, segs)


def _legend(parts: list[tuple]) -> str:
    return h("div", {"class_": "legend"},
             [h("span", {}, h("i", {"style": f"background:{c}"}), f"{lbl} {v}") for v, c, lbl in parts])


def _donut(parts: list[tuple], size: int = 118) -> str:
    total = sum(v for v, _, _ in parts) or 1
    stops, acc = [], 0.0
    for v, c, _ in parts:
        if not v:
            continue
        start = acc / total * 100; acc += v; end = acc / total * 100
        stops.append(f"{c} {start:.3f}% {end:.3f}%")
    grad = "conic-gradient(" + ",".join(stops or ["var(--line-2) 0 100%"]) + ")"
    return h("div", {"class_": "donut", "style": f"--g:{grad};width:{size}px;height:{size}px"})


def _hbars(rows: list[tuple], maxv: int | None = None) -> str:
    """rows: [(label, value, color)]. Horizontal bar chart."""
    mx = maxv or max((v for _, v, _ in rows), default=0) or 1
    return fragment(*(
        h("div", {"class_": "brow"},
          h("span", {"class_": "blab", "title": lbl}, lbl),
          h("span", {"class_": "btrack"}, h("i", {"style": f"width:{v / mx * 100:.2f}%;background:{c}"})),
          h("span", {"class_": "bval"}, str(v)))
        for lbl, v, c in rows))


def _area(points: list[tuple], w: int = 560, ht: int = 140) -> str:
    """points: [(label, value)]. Area + line chart (SVG, viewBox-scaled)."""
    if not points:
        return h("p", {"class_": "muted small"}, t("no_data"))
    n = len(points); mx = max(v for _, v in points) or 1
    pad = 6
    def x(i): return pad + (i * (w - 2 * pad) / (n - 1 if n > 1 else 1))
    def y(v): return ht - pad - (v / mx * (ht - 2 * pad))
    pts = [(x(i), y(v)) for i, (_, v) in enumerate(points)]
    line = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    fill = f"M{pts[0][0]:.1f},{ht - pad} L" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + f" L{pts[-1][0]:.1f},{ht - pad} Z"
    dots = [h("circle", {"class_": "dot", "cx": f"{px:.1f}", "cy": f"{py:.1f}", "r": "2"}) for px, py in pts]
    first, last = points[0][0], points[-1][0]
    return fragment(
        h("div", {"class_": "area"}, h("svg", {"viewBox": f"0 0 {w} {ht}", "preserveAspectRatio": "none"},
          h("path", {"class_": "fl", "d": fill}), h("path", {"class_": "ln", "d": line}), fragment(*dots))),
        h("div", {"class_": "axis"}, h("span", {}, first), h("span", {}, last)))


# --------------------- contextual analytics (council / synthesis) --------------------- #
# Charts live ON the council and the synthesis, computed from that scope's sessions.
# Votes ARE stances (suggestions/stance_scale.json — the ONE positivity vocabulary): chart order
# (+2 → −2), colors and labels all come from the scale; no hardcoded vote vocabulary here.
def _vote_chart_parts(cnt: Counter) -> list[tuple]:
    """Counter keyed by stance VALUE → [(count, color, label)] in scale order — every term representable."""
    return [(cnt.get(r["value"], 0), r["color"], t(r["label_key"])) for r in _A.stance_terms()]


def _vote_parts(sessions: list[dict]) -> tuple[Counter, list[tuple]]:
    """Bucket votes by canonical stance VALUE (legacy tokens resolve via the scale's aliases; an
    unresolvable token lands in its value bucket via label_raw — never dropped from the charts)."""
    tot: Counter = Counter()
    for s in sessions:
        for v in s.get("votes", []):
            st = _A.vote_stance(v)
            if st is not None:
                tot[st["value"]] += 1
    return tot, _vote_chart_parts(tot)


def _overview_html(parts: list[tuple]) -> str:
    return h("div", {"class_": "dnrow"}, _donut(parts),
             h("div", {"style": "flex:1"}, _stacked(parts), _legend(parts)))


def _per_council_html(sessions: list[dict]) -> str:
    rows = []
    for s in sorted(sessions, key=lambda x: x.get("created_at", "")):
        _, parts = _vote_parts([s])
        n = len(s.get("persona_ids", []))
        rows.append(h("a", {"class_": "crow", "href": f'/councils/{s["id"]}'},
                      h("span", {"class_": "ct", "title": s["prompt"]}, s["prompt"]),
                      _stacked(parts, thin=True),
                      h("span", {"class_": "cn"}, f'{n} P · {s.get("created_at", "")[:10]}')))
    return fragment(*rows)


def _personas_by_sentiment_html(store: Store, sessions: list[dict]) -> str:
    pv: dict = defaultdict(list)                     # persona → resolved stance VALUES
    for s in sessions:
        for v in s.get("votes", []):
            st = _A.vote_stance(v)
            if st is not None:
                pv[v.get("persona_id")].append(st["value"])
    if not pv:
        return ""
    personas = {p["id"]: p for p in services.list_personas(store=store)}
    # score = the MEAN of the stance values (−2..+2) — no token-specific coefficients
    data = sorted(((pid, Counter(vals), sum(vals) / len(vals)) for pid, vals in pv.items()),
                  key=lambda x: x[2], reverse=True)
    rows = []
    for pid, cnt, score in data:
        p = personas.get(pid)
        name = p["display_name"] if p else pid
        av = _avatar(p, 22) if p else ""
        # the score's color = the NEAREST scale value's color (value-bucketed, no keyword matching)
        col = min(_A.stance_terms(), key=lambda r: abs(r["value"] - score))["color"]
        rows.append(h("div", {"class_": "prow"},
                      h("a", {"class_": "pn", "href": f'/personas/{pid}'}, av, h("span", {}, name)),
                      _stacked(_vote_chart_parts(cnt), thin=True),
                      h("span", {"class_": "ps", "style": f"color:{col}"}, f"{score:+.1f}")))
    return fragment(*rows)


def _stance_dist_html(sessions: list[dict]) -> str:
    # Bucketed by the canonical stance VALUE (the five scale buckets via artifacts.stance_meta) —
    # stored label strings (legacy free labels, label_raw tokens) never classify a contribution.
    sb: Counter = Counter()
    for s in sessions:
        for st in _A.council_statements(s):
            stv = st.get("stance")
            if not stv:
                continue
            sb[int(stv.get("value") or 0)] += 1
    rows = [(t(_A.stance_meta(v)["label_key"]), n, _A.stance_meta(v)["color"]) for v, n in sb.most_common()]
    return _hbars(rows) if rows else ""


def _sentiment_section(store: Store, sessions: list[dict], sid: str = "sentiment",
                       title: str | None = None, per_council: bool = False) -> str | None:
    """Reusable sentiment analytics block, embedded ON a council or synthesis."""
    if title is None:
        title = t("sentiment_block")
    sessions = [s for s in sessions if s]
    tot, parts = _vote_parts(sessions)
    nvotes = sum(v for v, _, _ in parts)
    has_turns = any(_A.council_statements(s) for s in sessions)
    if not nvotes and not has_turns:
        return None
    scope = t("sentiment_scope_chain") if per_council else t("sentiment_scope_session")
    blocks = [h("p", {"class_": "ihint"}, t("sentiment_intro", scope=scope))]
    if nvotes:
        blocks.append(_overview_html(parts))
    if per_council and len(sessions) > 1:
        pc = _per_council_html(sessions)
        if pc:
            blocks.append(fragment(h("p", {"class_": "ihint", "style": "margin-top:18px"}, t("per_council")), pc))
    pbs = _personas_by_sentiment_html(store, sessions)
    if pbs:
        blocks.append(fragment(h("p", {"class_": "ihint", "style": "margin-top:18px"}, t("personas_by_sentiment")), pbs))
    sd = _stance_dist_html(sessions)
    if sd:
        blocks.append(fragment(h("p", {"class_": "ihint", "style": "margin-top:18px"}, t("stance_of_contributions")), sd))
    return h("div", {"class_": "sec", "id": sid}, h("h2", {}, title), fragment(*blocks))


def _persona_voices_html(store: Store, pid: str) -> str:
    """This persona's ACTUAL council statements — the ONE place their words live (no synthesis re-host;
    spec/artifact-cross-references.md). Each card carries a cross-ref deep-link back to the council."""
    cards = []
    for c in store.list_council_sessions():
        for st in (c.get("statements") or []):
            if st.get("persona_id") != pid:
                continue
            # On the persona's OWN page the identity is implied — drop the repeated avatar/name/context
            # and lead each card with the VARYING info instead: which council it was said in.
            src = h("a", {"class_": "turn-src", "href": f'/councils/{c["id"]}'},
                    raw(_icon("councils")), " ", (c.get("prompt", "") or "—")[:72])
            cards.append(render_statement(st, store, head_extra=src, show_persona=False))
    if not cards:
        return ""
    return h("div", {"class_": "sec", "id": "stimmen"}, h("h2", {}, t("voices_in_analyses")),
             h("div", {"style": "display:flex;flex-direction:column;gap:10px"}, fragment(*cards)))


# --------------------------- synthesis report --------------------------- #


def _synthesis_html(store: Store, syn: dict, *, embed: bool = False):
    # embed=True omits the bespoke syn-head so the content can sit inside the unified report shell
    # (rp-cover + report typography) — spec/unified-synthesis-report.md §3 (one renderer).
    done = syn.get("status", "done") == "done"
    sec = []  # (id, short_label, html)

    def _block(bid, label, inner):                            # the shared section wrapper
        return h("div", {"class_": "block", "id": bid}, h("h2", {"class_": "bh"}, label), inner)

    # 1) Executive Summary — the unified Question → Answer lead (shared with the council 'finding'),
    # fed by the shared study view-model so council/synthesis never branch on field names.
    if syn.get("gesamtbild"):
        vm = study_head(syn, is_synthesis=True)
        sec.append(("exec", t("summary"), _study_lead(
            _md(vm["answer_md"]), vm["answer_label"], question=vm["question"], qlabel=t("question"))))
    # 2) Cited evidence — councils are DECOUPLED: this synthesis is a standalone answer that may
    # CITE councils (or none). Render them as a compact reference list, NOT as the synthesis body.
    belege = None
    ref_rows = []
    for i, cid in enumerate(syn.get("council_ids", []), 1):
        c = store.get_council_session(cid)
        if not c:
            continue
        _, parts = _vote_parts([c])                 # value-bucketed via the scale (votes ARE stances)
        prompt = c.get("prompt") or cid
        ref_rows.append(h("a", {"class_": "ref-row", "href": f"/councils/{cid}"},
                          h("span", {"class_": "ref-n"}, f"C{i}"),
                          h("span", {"class_": "ref-t"}, prompt[:96]),
                          h("span", {"class_": "ref-bar"}, _stacked(parts, thin=True)),
                          h("span", {"class_": "ref-go"}, raw(_icon("arrowRight")))))
    if ref_rows:
        belege = ("belege", t("councils"),
                  h("details", {"class_": "block", "id": "belege"},
                    h("summary", {"class_": "bh", "style": "cursor:pointer"},
                      t("councils_overview"), " ", h("span", {"class_": "cnt"}, str(len(ref_rows)))),
                    h("p", {"class_": "muted small", "style": "margin:6px 0 10px"}, t("evidence_decoupled_note")),
                    h("div", {"class_": "ref-list"}, raw("".join(ref_rows)))))
    # Finding LIST sections (key_problems/pain_solvers/open_questions/shortlist) now render through the
    # ONE finding renderer — id + label from finding_kinds.json, prose via _prose (spec/unified-…).
    _findings = _A.synthesis_findings(syn)

    def _fsec(kind, label, toc=None):        # id from data (finding_kinds.json); label = static i18n
        items = [f for f in _findings if f.get("kind") == kind]
        if not items:
            return None
        sid = _A.finding_kind(kind)["id"]
        return (sid, toc or label, _block(sid, label, render_findings(items, store=store)))

    rec_items = _A.synthesis_recommendations(syn)         # [(text, effort, value)] from recommendation findings
    if rec_items:
        chart = _effort_impact(rec_items)
        if chart:
            body = raw(chart)  # hover popovers replace the list
        else:
            rows = "".join(_rec_row_n(i, txt, a, n) for i, (txt, a, n) in enumerate(rec_items, 1))
            body = h("div", {"class_": "reclist"}, raw(rows))
        sec.append(("empfehlungen", t("recommendations"), _block("empfehlungen", t("recommendations"), body)))
    if syn.get("positionierung"):
        sec.append(("positionierung", t("positioning"),
                    _block("positionierung", t("positioning"),
                           h("div", {"class_": "sl-prose sm"}, raw(_md(syn["positionierung"]))))))
    # Structured convergence blocks (GAP-3): a methodology's key problems / affinity clusters /
    # down-select ranking + shortlist render as first-class answer content when present (data-driven —
    # labels via i18n, content free-text; no methodology value hardcoded).
    if (s := _fsec("key_problem", t("key_problems"))):
        sec.append(s)
    if (s := _fsec("cluster", t("affinity_clusters"))):
        sec.append(s)
    if (s := _fsec("ranking", t("ranking"))):
        sec.append(s)
    if (s := _fsec("shortlist", t("shortlist"))):
        sec.append(s)
    # A synthesis does NOT re-host council voices (spec/artifact-cross-references.md): the personas'
    # actual words live ONCE, in the councils, and the findings above cross-reference the specific
    # statements they derive from. Here we show only the AGGREGATE — the sentiment across the council
    # chain — which is genuine cross-council analysis, not a copied transcript.
    syn_sessions = [store.get_council_session(cid) for cid in syn.get("council_ids", [])]
    sent = _sentiment_section(store, syn_sessions, title=t("sentiment_over_chain"), per_council=True)
    if sent:
        sec.append(("stimmen", t("sentiment_block"), h("div", {"class_": "block", "id": "stimmen"}, raw(sent))))
    # supporting analysis (omit when empty — an empty section reads as a broken box)
    if (s := _fsec("segment", t("segments"))):
        sec.append(s)
    if (s := _fsec("pain_solver", t("validated_pain_solvers"))):
        sec.append(s)
    if (s := _fsec("open_question", t("open_questions_next_study"), toc=t("open_questions"))):
        sec.append(s)
    if belege:                       # cited evidence (councils) — demoted, near the end, collapsible
        sec.append(belege)
    # arc (collapsed) — only when there is a narrative; an empty <details> reads as a broken box
    if (syn.get("arc_narrative") or "").strip():
        sec.append(("bogen", t("course"),
                    h("details", {"class_": "block", "id": "bogen"},
                      h("summary", {"class_": "bh", "style": "cursor:pointer"}, t("arc_course")),
                      h("div", {"class_": "sl-prose sm"}, raw(_md(_srcchips(syn["arc_narrative"])))))))

    # ---- slim meta strip (replaces the old Eigenschaften rail) — omitted when embedded in the report shell
    head = ""
    if not embed:
        cs = _A.synthesis_sentiment_counts(syn, store)        # aggregated over the REAL council voices
        smeta = " · ".join(f"{cs[k]} {k}" for k in ("positiv", "bedingt", "neutral", "skeptisch", "ablehnend") if cs.get(k))
        mchips = [_label(t("completed") if done else t("running"), "var(--green)" if done else "var(--amber)")]
        mchips.append(h("span", {"class_": "mchip"}, f'{len(syn.get("council_ids", []))} {t("councils")}'))
        if syn.get("iterations"):
            mchips.append(h("span", {"class_": "mchip"}, f'{syn["iterations"]} {t("iterations")}'))
        if smeta:
            mchips.append(h("span", {"class_": "mchip"}, raw(t("voices_meta", s=_esc(smeta)))))
        mchips.append(h("span", {"class_": "mchip"}, syn["created_at"][:10]))
        head = h("header", {"class_": "syn-head"},
                 h("h1", {"title": syn["title"]}, raw(_icon("syntheses")), syn["title"]),
                 h("div", {"class_": "syn-meta"}, fragment(*mchips)))

    main = head + raw("".join(str(html) for _, _, html in sec))   # section htmls are all trusted (h() Safe or built strings)
    # Unified detail shell: the caller wraps this content in _doc (content column + Properties/Relations
    # aside) and renders the section minimap via _page_rail(toc) — same as every other detail page.
    toc = [(sid, lbl) for sid, lbl, _ in sec]
    return h("div", {"class_": "syn-main"}, raw(main)), toc
