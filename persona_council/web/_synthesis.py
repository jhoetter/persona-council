from __future__ import annotations

from collections import Counter, defaultdict

from .. import services
from ..storage import Store
from ._i18n import t
from ._components import (
    _esc, _icon, _avatar, _label, _stance_color, _md, _srcchips, _prose, _rec_item, _rec_row_n,
    _effort_impact, _star, _study_lead,
)
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
.stacked{display:flex;height:12px;border-radius:6px;overflow:hidden;background:var(--line-2);border:1px solid var(--line)}
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
.brow .btrack{height:9px;border-radius:5px;background:var(--line-2);overflow:hidden}
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

/* ---- voices / Stimmen panel (synthesis cockpit) ---- */
.vtools{display:flex;flex-wrap:wrap;gap:12px 18px;align-items:flex-start;justify-content:space-between;margin:0 0 12px}
.vfilters{display:flex;flex-wrap:wrap;gap:10px 16px}
.fgroup{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.flabel{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600;margin-right:2px}
.vchip{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--line);background:var(--panel);border-radius:var(--radius-sm);padding:3px 10px;font-size:var(--t-sm);color:var(--ink);cursor:pointer}
.vchip:hover{background:var(--hover)}
.vchip.on{background:var(--accent-weak);border-color:transparent;color:var(--accent);font-weight:600}
.vchip i{width:8px;height:8px;border-radius:50%}
.vtools-right{display:flex;gap:8px;align-items:center}
.vsearch{width:180px;font-size:var(--t-sm)}.vsort{font-size:var(--t-sm)}
.vdist{display:grid;grid-template-columns:64px 1fr;gap:8px 10px;align-items:center;margin:0 0 10px;font-size:var(--t-sm);color:var(--muted)}
.vdist .dk{text-align:right}
.vcount{font-size:var(--t-sm);color:var(--muted);margin:0 0 8px}
.vrows{border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;background:var(--panel)}
.vrow{border-bottom:1px solid var(--line-2)}.vrow:last-child{border-bottom:0}
.vrow.hide{display:none}
.vrow-main{display:grid;grid-template-columns:30px 1fr auto;gap:11px;align-items:center;padding:10px 13px;cursor:pointer}
.vrow-main:hover{background:var(--hover)}
.vmeta{min-width:0}
.vline1{display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.vline1 b{font-size:var(--t-body)}
.varg{color:var(--muted);font-size:var(--t-sm);margin-top:2px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.vrow.open .varg{white-space:normal}
.vright{display:flex;align-items:center;gap:9px;flex-shrink:0;color:var(--muted)}
.vchev{transition:transform 150ms;color:var(--muted);font-size:var(--t-xs)}
.vrow.open .vchev{transform:rotate(90deg)}
.segchip{font-size:var(--t-xs);color:var(--muted);border:1px solid var(--line);border-radius:var(--radius-sm);padding:1px 7px;background:var(--panel-2);max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.relbar{display:inline-flex;gap:2px;align-items:center}
.relbar i{width:3px;height:11px;border-radius:1px;background:var(--line)}
.relbar i.on{background:var(--accent)}
.shiftbadge{display:inline-flex;align-items:center;gap:4px;font-size:var(--t-xs);border-radius:var(--radius-sm);padding:1px 8px;background:var(--accent-weak);color:var(--accent);font-weight:600}
.vexp{padding:0 13px 13px 54px;font-size:var(--t-sm)}
.vexp .vshift{background:var(--panel-2);border-radius:8px;padding:8px 11px;margin:0 0 9px}
.vexp .vev{padding:5px 11px;margin:6px 0;color:var(--ink)}
.vexp .vev a{color:var(--muted);font-size:var(--t-xs)}
.vempty{padding:18px;color:var(--muted);font-size:var(--t-sm);text-align:center}
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
.ref-row{display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid var(--line);border-radius:9px;background:var(--panel);text-decoration:none;color:var(--ink)}
.ref-row:hover{border-color:var(--accent)}
.ref-n{font-weight:700;color:var(--accent);font-size:var(--t-sm);flex:none;width:26px}
.ref-t{flex:1;font-size:var(--t-body);line-height:1.35;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ref-bar{flex:none;width:120px}.ref-go{flex:none;color:var(--muted)}
.ccard{border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:var(--panel);display:flex;flex-direction:column;gap:9px}
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
.ei-wrap{margin:6px 0 22px}
.ei-plot{position:relative;width:100%;max-width:600px;aspect-ratio:560/420;margin:0 auto 10px}
.ei-bg{position:absolute;inset:0;width:100%;height:100%}
.ei-dot{position:absolute;transform:translate(-50%,-50%);width:27px;height:27px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:var(--t-sm);font-weight:700;color:var(--c);background:var(--panel);border:1.8px solid var(--c);box-shadow:0 0 0 3px var(--bg);cursor:default;transition:transform .12s}
.ei-dot:hover,.ei-dot:focus{transform:translate(-50%,-50%) scale(1.25);z-index:20;outline:none}
.ei-num{pointer-events:none}
.ei-pop{position:absolute;left:50%;bottom:140%;transform:translateX(-50%);width:264px;max-width:72vw;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:11px 13px;box-shadow:0 12px 34px rgba(0,0,0,.18);opacity:0;visibility:hidden;transition:opacity .12s;z-index:30;pointer-events:none;display:flex;flex-direction:column;gap:6px;text-align:left;font-weight:400}
.ei-dot:hover .ei-pop,.ei-dot:focus .ei-pop{opacity:1;visibility:visible}
.ei-dot.below .ei-pop{bottom:auto;top:140%}
.ei-dot.algn-l .ei-pop{left:-6px;transform:none}
.ei-dot.algn-r .ei-pop{left:auto;right:-6px;transform:none}
.ei-pop-h{font-size:var(--t-xs);font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.ei-pop-t{font-size:var(--t-sm);line-height:1.46;color:var(--ink)}
.ei-pop-m{font-size:var(--t-xs);color:var(--muted)}
.ei-leg{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;font-size:var(--t-sm);color:var(--muted)}
.ei-leg i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle}
.reclist .rec{display:flex;gap:11px;padding:10px 8px;border-bottom:1px solid var(--line-2);scroll-margin-top:72px}
.reclist .rec:last-child{border-bottom:none}
.recnum{flex:0 0 auto;width:22px;height:22px;border-radius:50%;background:var(--accent-weak);color:var(--accent);font-size:var(--t-sm);font-weight:700;display:flex;align-items:center;justify-content:center}
.reclist .rec:target{background:var(--accent-weak);border-radius:8px}
.axchip{display:inline-block;margin-top:6px;font-size:var(--t-xs);color:var(--muted);border:1px solid var(--line);border-radius:var(--radius-sm);padding:1px 7px}
@media(max-width:1180px){.syn-rail{display:none}}
@media(max-width:740px){.cgrid{grid-template-columns:1fr}.syn-head h1{font-size:var(--t-xl)}}
""")

# ----------------------------- chart primitives ----------------------------- #
# Vanilla inline charts (CSS/conic-gradient/SVG) — no build step, dark-mode safe.
_VOTE_ORDER = ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]
_VOTE_COLOR = {"SUPPORT": "var(--green)", "MAYBE": "var(--amber)", "ABSTAIN": "var(--muted)", "OPPOSE": "var(--red)"}


def _vote_label(k: str) -> str:
    return t("vote_" + k.lower())


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


def _stance_bucket(s: str) -> tuple[str, str]:
    """Classify a free-text stance into (label, color) for distribution charts."""
    s = (s or "").lower()
    if any(k in s for k in ["begeist", "positiv", "stark", "support", "befürwort"]):
        return (t("stance_positive"), "var(--green)")
    if any(k in s for k in ["skept", "ableh", "oppose", "negativ", "kaum", "gar nicht"]):
        return (t("stance_skeptical"), "var(--red)")
    if any(k in s for k in ["neutral", "abstain", "enthalt"]):
        return (t("stance_neutral"), "var(--muted)")
    if any(k in s for k in ["bedingt", "maybe", "teilweise", "passt", "tangiert", "hebel"]):
        return (t("stance_conditional"), "var(--amber)")
    return (t("stance_other"), "var(--accent)")


# --------------------- contextual analytics (council / synthesis) --------------------- #
# Charts live ON the council and the synthesis, computed from that scope's sessions.
def _vote_parts(sessions: list[dict]) -> tuple[Counter, list[tuple]]:
    tot: Counter = Counter()
    for s in sessions:
        for v in s.get("votes", []):
            tot[str(v.get("vote", "")).upper()] += 1   # case-robust: 'support' counts as SUPPORT
    return tot, [(tot.get(k, 0), _VOTE_COLOR[k], _vote_label(k)) for k in _VOTE_ORDER]


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
    pv: dict = defaultdict(Counter)
    for s in sessions:
        for v in s.get("votes", []):
            pv[v.get("persona_id")][str(v.get("vote", "")).upper()] += 1   # case-robust
    if not pv:
        return ""
    personas = {p["id"]: p for p in services.list_personas(store=store)}
    data = []
    for pid, cnt in pv.items():
        n = sum(cnt.values()) or 1
        score = (cnt.get("SUPPORT", 0) - cnt.get("OPPOSE", 0) + 0.4 * cnt.get("MAYBE", 0)) / n
        data.append((pid, cnt, score))
    data.sort(key=lambda x: x[2], reverse=True)
    rows = []
    for pid, cnt, score in data:
        p = personas.get(pid)
        name = p["display_name"] if p else pid
        av = _avatar(p, 22) if p else ""
        _, parts = (None, [(cnt.get(k, 0), _VOTE_COLOR[k], _vote_label(k)) for k in _VOTE_ORDER])
        pct = round(score * 100)
        col = _stance_color("positiv" if pct >= 33 else "skept" if pct < 0 else "bedingt")
        rows.append(h("div", {"class_": "prow"},
                      h("a", {"class_": "pn", "href": f'/personas/{pid}'}, av, h("span", {}, name)),
                      _stacked(parts, thin=True),
                      h("span", {"class_": "ps", "style": f"color:{col}"}, f"{pct:+d}")))
    return fragment(*rows)


def _stance_dist_html(sessions: list[dict]) -> str:
    sb: Counter = Counter(); colors: dict = {}
    for s in sessions:
        for turn in s.get("turns", []):
            lbl, col = _stance_bucket(turn.get("stance"))
            sb[lbl] += 1; colors[lbl] = col
    rows = [(lbl, v, colors[lbl]) for lbl, v in sb.most_common()]
    return _hbars(rows) if rows else ""


def _sentiment_section(store: Store, sessions: list[dict], sid: str = "sentiment",
                       title: str | None = None, per_council: bool = False) -> str | None:
    """Reusable sentiment analytics block, embedded ON a council or synthesis."""
    if title is None:
        title = t("sentiment_block")
    sessions = [s for s in sessions if s]
    tot, parts = _vote_parts(sessions)
    nvotes = sum(v for v, _, _ in parts)
    has_turns = any(s.get("turns") for s in sessions)
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


# --------------------------- voices / Stimmen panel --------------------------- #
_SENT_COLOR = {"positiv": "var(--green)", "bedingt": "var(--amber)", "neutral": "var(--muted)",
               "skeptisch": "var(--skep)", "ablehnend": "var(--red)"}
_SENT_ORDER = ["positiv", "bedingt", "neutral", "skeptisch", "ablehnend"]
_REL_ORDER = ["stark", "teilweise", "kaum", "irrelevant"]
_REL_LEVEL = {"stark": 4, "teilweise": 2, "kaum": 1, "irrelevant": 0}


def _sent_color(s: str) -> str:
    return _SENT_COLOR.get(s, "var(--muted)")


def _relbar(rel: str) -> str:
    lvl = _REL_LEVEL.get(rel, 2)
    ticks = [h("i", {"class_": "on" if i < lvl else ""}) for i in range(4)]
    return h("span", {"class_": "relbar", "title": t("relevance_tooltip", rel=rel)}, ticks)


VOICES_JS = """
<script>
(function(){
  var root=document.getElementById('voices'); if(!root) return;
  var rows=[].slice.call(root.querySelectorAll('.vrow'));
  var chips=[].slice.call(root.querySelectorAll('.vchip'));
  var search=root.querySelector('.vsearch'), sortSel=root.querySelector('.vsort');
  var dist=root.querySelector('.vdist'), count=root.querySelector('.vcount'), box=root.querySelector('.vrows');
  var SENT=['positiv','bedingt','neutral','skeptisch','ablehnend'], REL=['stark','teilweise','kaum','irrelevant'];
  var SC={positiv:'var(--green)',bedingt:'var(--amber)',neutral:'var(--muted)',skeptisch:'var(--skep)',ablehnend:'var(--red)'};
  var RC={stark:'var(--accent)',teilweise:'var(--accent)',kaum:'var(--muted)',irrelevant:'var(--line)'};
  function active(f){ return chips.filter(function(c){return c.dataset.facet===f && c.classList.contains('on');}).map(function(c){return c.dataset.val;}); }
  function ok(r){ var fs=['sentiment','relevance','segment'];
    for(var i=0;i<fs.length;i++){ var a=active(fs[i]); if(a.length && a.indexOf(r.dataset[fs[i]])<0) return false; }
    var q=(search.value||'').trim().toLowerCase(); if(q && (r.dataset.text||'').indexOf(q)<0) return false; return true; }
  function bar(keys,colors,counts,tot){ return '<span class="stacked thin">'+keys.map(function(k){var v=counts[k]||0; return v?('<i title="'+k+': '+v+'" style="width:'+(v/tot*100)+'%;background:'+colors[k]+'"></i>'):''; }).join('')+'</span>'; }
  function render(){
    var vis=[]; rows.forEach(function(r){var v=ok(r); r.classList.toggle('hide',!v); if(v)vis.push(r);});
    var cs={},cr={}; vis.forEach(function(r){cs[r.dataset.sentiment]=(cs[r.dataset.sentiment]||0)+1; cr[r.dataset.relevance]=(cr[r.dataset.relevance]||0)+1;});
    var tot=vis.length||1;
    dist.innerHTML='<span class="dk">__SENT_LABEL__</span>'+bar(SENT,SC,cs,tot)+'<span class="dk">__REL_LABEL__</span>'+bar(REL,RC,cr,tot);
    count.textContent='__NOFM__'.replace('{n}',vis.length).replace('{m}',rows.length);
    var key=sortSel.value, so={positiv:0,bedingt:1,neutral:2,skeptisch:3,ablehnend:4}, ro={stark:0,teilweise:1,kaum:2,irrelevant:3};
    vis.sort(function(a,b){
      if(key==='name') return (a.dataset.name||'').localeCompare(b.dataset.name||'');
      if(key==='relevance') return (ro[a.dataset.relevance]-ro[b.dataset.relevance])||(a.dataset.name||'').localeCompare(b.dataset.name||'');
      if(key==='shift') return (b.dataset.shift-a.dataset.shift)||(so[a.dataset.sentiment]-so[b.dataset.sentiment]);
      return (so[a.dataset.sentiment]-so[b.dataset.sentiment])||(a.dataset.name||'').localeCompare(b.dataset.name||''); });
    vis.forEach(function(r){box.appendChild(r);});
  }
  chips.forEach(function(c){ c.addEventListener('click',function(){c.classList.toggle('on'); render();}); });
  search.addEventListener('input',render); sortSel.addEventListener('change',render);
  rows.forEach(function(r){ var m=r.querySelector('.vrow-main'); if(!m) return;
    m.addEventListener('click',function(e){ if(e.target.closest('[data-star]'))return; r.classList.toggle('open'); var ex=r.querySelector('.vexp'); if(ex) ex.hidden=!r.classList.contains('open'); }); });
  render();
})();
</script>
"""


def _voices_panel(store: Store, syn: dict) -> str | None:
    voices = syn.get("voices", [])
    if not voices:
        return None
    personas = {p["id"]: p for p in services.list_personas(store=store)}
    segments = sorted({v.get("segment", "") for v in voices if v.get("segment")})

    def chip(facet: str, val: str, color: str | None = None) -> str:
        dot = h("i", {"style": f"background:{color}"}) if color else ""
        return h("button", {"class_": "vchip", "data-facet": facet, "data-val": val}, val, dot)

    filt = fragment(
        h("div", {"class_": "fgroup"}, h("span", {"class_": "flabel"}, t("sentiment_label")),
          *(chip("sentiment", s, _sent_color(s)) for s in _SENT_ORDER)),
        h("div", {"class_": "fgroup"}, h("span", {"class_": "flabel"}, t("relevance_label")),
          *(chip("relevance", r) for r in _REL_ORDER)),
        (h("div", {"class_": "fgroup"}, h("span", {"class_": "flabel"}, t("segment")),
          *(chip("segment", s) for s in segments)) if segments else None))
    tools = h("div", {"class_": "vtools"}, h("div", {"class_": "vfilters"}, filt),
              h("div", {"class_": "vtools-right"},
                h("input", {"class_": "vsearch", "type": "text", "placeholder": t("search_arg_name")}),
                h("select", {"class_": "vsort"},
                  h("option", {"value": "sentiment"}, t("sort_by_sentiment")),
                  h("option", {"value": "relevance"}, t("sort_relevance")),
                  h("option", {"value": "name"}, t("name_label")),
                  h("option", {"value": "shift"}, t("sort_shift_first")))))

    rows = []
    for v in voices:
        pid = v.get("persona_id", "")
        name = v.get("persona_name") or (personas.get(pid, {}) or {}).get("display_name") or pid
        p = personas.get(pid) or {"id": pid, "display_name": name}
        sent = v.get("sentiment", "neutral"); rel = v.get("relevance", "teilweise"); seg = v.get("segment", "")
        sh = v.get("shift")
        has_shift = bool(sh and (sh.get("trigger") or sh.get("to")))
        shbadge = (h("span", {"class_": "shiftbadge"}, sh.get("from", ""), " → ", sh.get("to", ""))
                   if has_shift else "")
        segchip = h("span", {"class_": "segchip", "title": seg}, seg) if seg else ""
        exp = []
        if has_shift:
            cid = sh.get("council_id", "")
            link = fragment(" ", h("a", {"href": f'/councils/{cid}'}, t("to_council"))) if cid else ""
            exp.append(h("div", {"class_": "vshift"}, h("strong", {}, t("shift_label", a=sh.get("from", ""), b=sh.get("to", ""))),
                         " ", sh.get("trigger", ""), link))
        for e in v.get("evidence", []):
            cid = e.get("council_id", "")
            link = fragment(" ", h("a", {"href": f'/councils/{cid}'}, t("to_council"))) if cid else ""
            exp.append(h("div", {"class_": "vev"}, "„", e.get("quote", ""), "“", link))
        exp_html = h("div", {"class_": "vexp", "hidden": True}, fragment(*exp)) if exp else ""
        text = f'{name} {v.get("key_argument","")} {seg}'.lower()
        rows.append(h("div", {"class_": "vrow", "data-sentiment": sent, "data-relevance": rel, "data-segment": seg,
                              "data-name": name, "data-shift": "1" if has_shift else "0", "data-text": text},
                      h("div", {"class_": "vrow-main"}, h("span", {"class_": "vav"}, _avatar(p, 30)),
                        h("div", {"class_": "vmeta"},
                          h("div", {"class_": "vline1"}, h("b", {}, name), _label(sent, _sent_color(sent)), _relbar(rel), shbadge),
                          h("div", {"class_": "varg"}, v.get("key_argument", ""))),
                        h("div", {"class_": "vright"}, segchip, raw(_star("persona", pid, name, f"/personas/{pid}")),
                          h("span", {"class_": "vchev"}, raw(_icon("caretRight"))))),
                      exp_html))
    js = (VOICES_JS.replace("__SENT_LABEL__", t("sentiment_label"))
          .replace("__REL_LABEL__", t("relevance_label"))
          .replace("__NOFM__", t("voices_n_of_m", n="{n}", m="{m}")))
    return h("div", {"class_": "sec", "id": "stimmen"}, h("h2", {}, t("voices_count", n=len(voices))),
             h("p", {"class_": "ihint"}, t("voices_intro")),
             h("div", {"class_": "voices", "id": "voices"}, tools, h("div", {"class_": "vdist"}),
               h("div", {"class_": "vcount"}), h("div", {"class_": "vrows"}, fragment(*rows)))) + raw(js)


def _persona_voices_html(store: Store, pid: str) -> str:
    out = []
    for syn in store.list_syntheses():
        for v in syn.get("voices", []):
            if v.get("persona_id") != pid:
                continue
            sent = v.get("sentiment", "neutral")
            sh = v.get("shift")
            shb = (h("span", {"class_": "shiftbadge"}, sh.get("from", ""), " → ", sh.get("to", ""))
                   if (sh and (sh.get("trigger") or sh.get("to"))) else "")
            out.append(h("div", {"class_": "vrow"},
                h("div", {"class_": "vrow-main", "style": "cursor:default"}, h("span", {}),
                  h("div", {"class_": "vmeta"},
                    h("div", {"class_": "vline1"},
                      h("a", {"href": f'/syntheses/{syn["id"]}'}, h("b", {}, syn["title"])),
                      _label(sent, _sent_color(sent)), _relbar(v.get("relevance", "teilweise")), shb),
                    h("div", {"class_": "varg", "style": "white-space:normal"}, v.get("key_argument", ""))),
                  h("div", {"class_": "vright"}))))
            break
    if not out:
        return ""
    return h("div", {"class_": "sec", "id": "stimmen"}, h("h2", {}, t("voices_in_analyses")),
             h("div", {"class_": "vrows"}, fragment(*out)))


# --------------------------- synthesis report --------------------------- #


def _synthesis_html(store: Store, syn: dict):
    done = syn.get("status", "done") == "done"
    sec = []  # (id, short_label, html)

    def _block(bid, label, inner):                            # the shared section wrapper
        return h("div", {"class_": "block", "id": bid}, h("h2", {"class_": "bh"}, label), inner)

    def _segrow(head, body):
        return h("div", {"class_": "segrow"}, h("div", {}, h("strong", {}, head), h("br"),
                                                h("span", {"class_": "muted"}, body)))

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
        tally = Counter(str(v.get("vote", "")).upper() for v in (c.get("votes") or []) if isinstance(v, dict))
        parts = [(tally.get(k, 0), _VOTE_COLOR[k], k) for k in _VOTE_ORDER]
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
    rec_items = [_rec_item(x) for x in syn.get("handlungsempfehlungen", [])]
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
                           h("div", {"class_": "es-prose sm"}, raw(_md(syn["positionierung"]))))))
    # Structured convergence blocks (GAP-3): a methodology's key problems / affinity clusters /
    # down-select ranking + shortlist render as first-class answer content when present (data-driven —
    # labels via i18n, content free-text; no methodology value hardcoded).
    if syn.get("key_problems"):
        kp = fragment(*(h("div", {"class_": "psolve"}, raw(_prose(x))) for x in syn["key_problems"]))
        sec.append(("keyproblems", t("key_problems"), _block("keyproblems", t("key_problems"), kp)))
    if syn.get("clusters"):
        cl = fragment(*(_segrow(c.get("label", ""), c.get("insight", "")) for c in syn["clusters"]))
        sec.append(("clusters", t("affinity_clusters"), _block("clusters", t("affinity_clusters"), cl)))
    if syn.get("ranking"):
        rk = fragment(*(_segrow(r.get("prototype_id", ""), r.get("score_rationale", "")) for r in syn["ranking"]))
        sec.append(("ranking", t("ranking"), _block("ranking", t("ranking"), rk)))
    if syn.get("shortlist"):
        sl = fragment(*(h("div", {"class_": "psolve"}, raw(_prose(x))) for x in syn["shortlist"]))
        sec.append(("shortlist", t("shortlist"), _block("shortlist", t("shortlist"), sl)))
    # voices — who thinks what & why (filter/sort/shift/evidence)
    panel = _voices_panel(store, syn)
    if panel:
        sec.append(("stimmen", t("voices"), h("div", {"class_": "block", "id": "stimmen"}, raw(panel))))
    else:
        syn_sessions = [store.get_council_session(cid) for cid in syn.get("council_ids", [])]
        sent = _sentiment_section(store, syn_sessions, title=t("sentiment_over_chain"), per_council=True)
        if sent:
            sec.append(("stimmen", t("voices"), h("div", {"class_": "block", "id": "stimmen"}, raw(sent))))
    # supporting analysis (omit when empty — an empty section reads as a broken box)
    if syn.get("segmente"):
        segs = fragment(*(
            h("div", {"class_": "segrow"},
              h("div", {}, h("strong", {}, s.get("segment", "")), h("br"),
                h("span", {"class_": "muted"}, s.get("why", ""))),
              raw(_label(s.get("stance", ""), _stance_color(s.get("stance", "")))))
            for s in syn["segmente"]))
        sec.append(("segmente", t("segments"), _block("segmente", t("segments"), segs)))
    if syn.get("pain_solvers"):
        ps = fragment(*(h("div", {"class_": "psolve"}, raw(_prose(x))) for x in syn["pain_solvers"]))
        sec.append(("painsolver", "Pain-Solver", _block("painsolver", t("validated_pain_solvers"), ps)))
    if syn.get("offene_fragen"):
        of = fragment(*(h("div", {"class_": "psolve"}, raw(_prose(x))) for x in syn["offene_fragen"]))
        sec.append(("offene", t("open_questions"), _block("offene", t("open_questions_next_study"), of)))
    if belege:                       # cited evidence (councils) — demoted, near the end, collapsible
        sec.append(belege)
    # arc (collapsed) — only when there is a narrative; an empty <details> reads as a broken box
    if (syn.get("arc_narrative") or "").strip():
        sec.append(("bogen", t("course"),
                    h("details", {"class_": "block", "id": "bogen"},
                      h("summary", {"class_": "bh", "style": "cursor:pointer"}, t("arc_course")),
                      h("div", {"class_": "es-prose sm"}, raw(_md(_srcchips(syn["arc_narrative"])))))))

    # ---- slim meta strip (replaces the old Eigenschaften rail) ----
    cs = Counter(v.get("sentiment", "neutral") for v in syn.get("voices", []))
    smeta = " · ".join(f"{cs[k]} {k}" for k in _SENT_ORDER if cs.get(k))
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
