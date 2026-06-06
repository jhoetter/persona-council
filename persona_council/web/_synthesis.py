from __future__ import annotations

from collections import Counter, defaultdict

from .. import services
from ..storage import Store
from ._i18n import t
from ._components import (
    _esc, _icon, _avatar, _label, _stance_color, _md, _srcchips, _rec_item, _rec_row_n,
    _effort_impact, _star, _study_lead, _SYN_STYLE,
)
from ._vm import study_head
from ._html import h, raw, fragment


# ----------------------------- chart primitives ----------------------------- #
# Vanilla inline charts (CSS/conic-gradient/SVG) — no build step, dark-mode safe.
_VOTE_ORDER = ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]
_VOTE_COLOR = {"SUPPORT": "var(--green)", "MAYBE": "var(--amber)", "ABSTAIN": "var(--muted)", "OPPOSE": "var(--red)"}


def _vote_label(k: str) -> str:
    return t("vote_" + k.lower())


def _stacked(parts: list[tuple], thin: bool = False) -> str:
    """parts: [(value, color, label)]. Renders a single horizontal stacked bar."""
    total = sum(v for v, _, _ in parts) or 1
    segs = "".join(f'<i style="width:{v / total * 100:.3f}%;background:{c}" title="{_esc(lbl)}: {v}"></i>'
                   for v, c, lbl in parts if v)
    return f'<div class="stacked{" thin" if thin else ""}">{segs}</div>'


def _legend(parts: list[tuple]) -> str:
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{c}"></i>{_esc(lbl)} {v}</span>' for v, c, lbl in parts) + "</div>"


def _donut(parts: list[tuple], size: int = 118) -> str:
    total = sum(v for v, _, _ in parts) or 1
    stops, acc = [], 0.0
    for v, c, _ in parts:
        if not v:
            continue
        start = acc / total * 100; acc += v; end = acc / total * 100
        stops.append(f"{c} {start:.3f}% {end:.3f}%")
    grad = "conic-gradient(" + ",".join(stops or ["var(--line-2) 0 100%"]) + ")"
    return f'<div class="donut" style="--g:{grad};width:{size}px;height:{size}px"></div>'


def _hbars(rows: list[tuple], maxv: int | None = None) -> str:
    """rows: [(label, value, color)]. Horizontal bar chart."""
    mx = maxv or max((v for _, v, _ in rows), default=0) or 1
    return "".join(
        f'<div class="brow"><span class="blab" title="{_esc(lbl)}">{_esc(lbl)}</span>'
        f'<span class="btrack"><i style="width:{v / mx * 100:.2f}%;background:{c}"></i></span>'
        f'<span class="bval">{v}</span></div>' for lbl, v, c in rows)


def _area(points: list[tuple], w: int = 560, h: int = 140) -> str:
    """points: [(label, value)]. Area + line chart (SVG, viewBox-scaled)."""
    if not points:
        return f'<p class="muted small">{t("no_data")}</p>'
    n = len(points); mx = max(v for _, v in points) or 1
    pad = 6
    def x(i): return pad + (i * (w - 2 * pad) / (n - 1 if n > 1 else 1))
    def y(v): return h - pad - (v / mx * (h - 2 * pad))
    pts = [(x(i), y(v)) for i, (_, v) in enumerate(points)]
    line = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    fill = f"M{pts[0][0]:.1f},{h - pad} L" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts) + f" L{pts[-1][0]:.1f},{h - pad} Z"
    dots = "".join(f'<circle class="dot" cx="{px:.1f}" cy="{py:.1f}" r="2"></circle>' for px, py in pts)
    first, last = points[0][0], points[-1][0]
    return (f'<div class="area"><svg viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
            f'<path class="fl" d="{fill}"></path><path class="ln" d="{line}"></path>{dots}</svg></div>'
            f'<div class="axis"><span>{_esc(first)}</span><span>{_esc(last)}</span></div>')


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
    return (f'<div class="dnrow">{_donut(parts)}<div style="flex:1">'
            f'{_stacked(parts)}{_legend(parts)}</div></div>')


def _per_council_html(sessions: list[dict]) -> str:
    rows = []
    for s in sorted(sessions, key=lambda x: x.get("created_at", "")):
        _, parts = _vote_parts([s])
        n = len(s.get("persona_ids", []))
        rows.append(
            f'<a class="crow" href="/councils/{_esc(s["id"])}"><span class="ct" title="{_esc(s["prompt"])}">{_esc(s["prompt"])}</span>'
            f'{_stacked(parts, thin=True)}<span class="cn">{n} P · {_esc(s.get("created_at", "")[:10])}</span></a>'
        )
    return "".join(rows)


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
        rows.append(
            f'<div class="prow"><a class="pn" href="/personas/{_esc(pid)}">{av}<span>{_esc(name)}</span></a>'
            f'{_stacked(parts, thin=True)}<span class="ps" style="color:{col}">{pct:+d}</span></div>'
        )
    return "".join(rows)


def _stance_dist_html(sessions: list[dict]) -> str:
    sb: Counter = Counter(); colors: dict = {}
    for s in sessions:
        for t in s.get("turns", []):
            lbl, col = _stance_bucket(t.get("stance"))
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
    blocks = [f'<p class="ihint">{t("sentiment_intro", scope=scope)}</p>']
    if nvotes:
        blocks.append(_overview_html(parts))
    if per_council and len(sessions) > 1:
        pc = _per_council_html(sessions)
        if pc:
            blocks.append(f'<p class="ihint" style="margin-top:18px">{t("per_council")}</p>' + pc)
    pbs = _personas_by_sentiment_html(store, sessions)
    if pbs:
        blocks.append(f'<p class="ihint" style="margin-top:18px">{t("personas_by_sentiment")}</p>' + pbs)
    sd = _stance_dist_html(sessions)
    if sd:
        blocks.append(f'<p class="ihint" style="margin-top:18px">{t("stance_of_contributions")}</p>' + sd)
    return f'<div class="sec" id="{_esc(sid)}"><h2>{_esc(title)}</h2>' + "".join(blocks) + "</div>"


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
    ticks = "".join(f'<i class="{"on" if i < lvl else ""}"></i>' for i in range(4))
    return f'<span class="relbar" title="{_esc(t("relevance_tooltip", rel=rel))}">{ticks}</span>'


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
        dot = f'<i style="background:{color}"></i>' if color else ""
        return f'<button class="vchip" data-facet="{facet}" data-val="{_esc(val)}">{_esc(val)}{dot}</button>'

    filt = (f'<div class="fgroup"><span class="flabel">{t("sentiment_label")}</span>'
            + "".join(chip("sentiment", s, _sent_color(s)) for s in _SENT_ORDER) + "</div>"
            + f'<div class="fgroup"><span class="flabel">{t("relevance_label")}</span>'
            + "".join(chip("relevance", r) for r in _REL_ORDER) + "</div>")
    if segments:
        filt += (f'<div class="fgroup"><span class="flabel">{t("segment")}</span>'
                 + "".join(chip("segment", s) for s in segments) + "</div>")
    ph_search = _esc(t("search_arg_name"))
    tools = (f'<div class="vtools"><div class="vfilters">{filt}</div>'
             f'<div class="vtools-right"><input class="vsearch" type="text" placeholder="{ph_search}">'
             f'<select class="vsort"><option value="sentiment">{t("sort_by_sentiment")}</option>'
             f'<option value="relevance">{t("sort_relevance")}</option><option value="name">{t("name_label")}</option>'
             f'<option value="shift">{t("sort_shift_first")}</option></select></div></div>')

    rows = []
    for v in voices:
        pid = v.get("persona_id", "")
        name = v.get("persona_name") or (personas.get(pid, {}) or {}).get("display_name") or pid
        p = personas.get(pid) or {"id": pid, "display_name": name}
        sent = v.get("sentiment", "neutral"); rel = v.get("relevance", "teilweise"); seg = v.get("segment", "")
        sh = v.get("shift")
        has_shift = bool(sh and (sh.get("trigger") or sh.get("to")))
        shbadge = (f'<span class="shiftbadge">{_esc(sh.get("from",""))} → {_esc(sh.get("to",""))}</span>'
                   if has_shift else "")
        segchip = f'<span class="segchip" title="{_esc(seg)}">{_esc(seg)}</span>' if seg else ""
        exp = []
        if has_shift:
            cid = sh.get("council_id", "")
            link = f' <a href="/councils/{_esc(cid)}">{t("to_council")}</a>' if cid else ""
            shift_lbl = _esc(t("shift_label", a=sh.get("from", ""), b=sh.get("to", "")))
            exp.append(f'<div class="vshift"><strong>{shift_lbl}</strong> {_esc(sh.get("trigger",""))}{link}</div>')
        for e in v.get("evidence", []):
            cid = e.get("council_id", "")
            link = f' <a href="/councils/{_esc(cid)}">{t("to_council")}</a>' if cid else ""
            exp.append(f'<div class="vev">„{_esc(e.get("quote",""))}“{link}</div>')
        exp_html = f'<div class="vexp" hidden>{"".join(exp)}</div>' if exp else ""
        text = f'{name} {v.get("key_argument","")} {seg}'.lower()
        rows.append(
            f'<div class="vrow" data-sentiment="{_esc(sent)}" data-relevance="{_esc(rel)}" data-segment="{_esc(seg)}" '
            f'data-name="{_esc(name)}" data-shift="{1 if has_shift else 0}" data-text="{_esc(text)}">'
            f'<div class="vrow-main"><span class="vav">{_avatar(p, 30)}</span>'
            f'<div class="vmeta"><div class="vline1"><b>{_esc(name)}</b>{_label(sent, _sent_color(sent))}{_relbar(rel)}{shbadge}</div>'
            f'<div class="varg">{_esc(v.get("key_argument",""))}</div></div>'
            f'<div class="vright">{segchip}{_star("persona", pid, name, f"/personas/{pid}")}<span class="vchev">{_icon("caretRight")}</span></div>'
            f'</div>{exp_html}</div>'
        )
    js = (VOICES_JS.replace("__SENT_LABEL__", t("sentiment_label"))
          .replace("__REL_LABEL__", t("relevance_label"))
          .replace("__NOFM__", t("voices_n_of_m", n="{n}", m="{m}")))
    return (f'<div class="sec" id="stimmen"><h2>{t("voices_count", n=len(voices))}</h2>'
            f'<p class="ihint">{t("voices_intro")}</p>'
            f'<div class="voices" id="voices">{tools}<div class="vdist"></div><div class="vcount"></div>'
            f'<div class="vrows">{"".join(rows)}</div></div></div>') + js


def _persona_voices_html(store: Store, pid: str) -> str:
    out = []
    for syn in store.list_syntheses():
        for v in syn.get("voices", []):
            if v.get("persona_id") != pid:
                continue
            sent = v.get("sentiment", "neutral")
            sh = v.get("shift")
            shb = (f'<span class="shiftbadge">{_esc(sh.get("from",""))} → {_esc(sh.get("to",""))}</span>'
                   if (sh and (sh.get("trigger") or sh.get("to"))) else "")
            out.append(
                '<div class="vrow"><div class="vrow-main" style="cursor:default"><span></span>'
                f'<div class="vmeta"><div class="vline1"><a href="/syntheses/{_esc(syn["id"])}"><b>{_esc(syn["title"])}</b></a>'
                f'{_label(sent, _sent_color(sent))}{_relbar(v.get("relevance","teilweise"))}{shb}</div>'
                f'<div class="varg" style="white-space:normal">{_esc(v.get("key_argument",""))}</div></div>'
                '<div class="vright"></div></div></div>'
            )
            break
    if not out:
        return ""
    return f'<div class="sec" id="stimmen"><h2>{t("voices_in_analyses")}</h2><div class="vrows">{"".join(out)}</div></div>'


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
        ref_rows.append(
            f'<a class="ref-row" href="/councils/{_esc(cid)}"><span class="ref-n">C{i}</span>'
            f'<span class="ref-t">{_esc(prompt[:96])}</span>'
            f'<span class="ref-bar">{_stacked(parts, thin=True)}</span><span class="ref-go">{_icon("arrowRight")}</span></a>')
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
            rows = "".join(_rec_row_n(i, t, a, n) for i, (t, a, n) in enumerate(rec_items, 1))
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
        kp = fragment(*(h("div", {"class_": "psolve"}, raw(_srcchips(_esc(x)))) for x in syn["key_problems"]))
        sec.append(("keyproblems", t("key_problems"), _block("keyproblems", t("key_problems"), kp)))
    if syn.get("clusters"):
        cl = fragment(*(_segrow(c.get("label", ""), c.get("insight", "")) for c in syn["clusters"]))
        sec.append(("clusters", t("affinity_clusters"), _block("clusters", t("affinity_clusters"), cl)))
    if syn.get("ranking"):
        rk = fragment(*(_segrow(r.get("prototype_id", ""), r.get("score_rationale", "")) for r in syn["ranking"]))
        sec.append(("ranking", t("ranking"), _block("ranking", t("ranking"), rk)))
    if syn.get("shortlist"):
        sl = fragment(*(h("div", {"class_": "psolve"}, x) for x in syn["shortlist"]))
        sec.append(("shortlist", t("shortlist"), _block("shortlist", t("shortlist"), sl)))
    # voices — who thinks what & why (filter/sort/shift/evidence)
    panel = _voices_panel(store, syn)
    if panel:
        sec.append(("stimmen", t("voices"), f'<div class="block" id="stimmen">{panel}</div>'))
    else:
        syn_sessions = [store.get_council_session(cid) for cid in syn.get("council_ids", [])]
        sent = _sentiment_section(store, syn_sessions, title=t("sentiment_over_chain"), per_council=True)
        if sent:
            sec.append(("stimmen", t("voices"), f'<div class="block" id="stimmen">{sent}</div>'))
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
        ps = fragment(*(h("div", {"class_": "psolve"}, raw(_srcchips(_esc(x)))) for x in syn["pain_solvers"]))
        sec.append(("painsolver", "Pain-Solver", _block("painsolver", t("validated_pain_solvers"), ps)))
    if syn.get("offene_fragen"):
        of = fragment(*(h("div", {"class_": "psolve"}, x) for x in syn["offene_fragen"]))
        sec.append(("offene", t("open_questions"), _block("offene", t("open_questions_next_study"), of)))
    if belege:                       # cited evidence (councils) — demoted, near the end, collapsible
        sec.append(belege)
    # arc (collapsed) — only when there is a narrative; an empty <details> reads as a broken box
    if (syn.get("arc_narrative") or "").strip():
        sec.append(("bogen", t("course"),
                    f'<details class="block" id="bogen"><summary class="bh" style="cursor:pointer">{t("arc_course")}</summary><div class="es-prose sm">{_md(_srcchips(syn["arc_narrative"]))}</div></details>'))

    # ---- slim meta strip (replaces the old Eigenschaften rail) ----
    cs = Counter(v.get("sentiment", "neutral") for v in syn.get("voices", []))
    smeta = " · ".join(f"{cs[k]} {k}" for k in _SENT_ORDER if cs.get(k))
    mchips = [_label(t("completed") if done else t("running"), "var(--green)" if done else "var(--amber)")]
    mchips.append(f'<span class="mchip">{len(syn.get("council_ids", []))} {t("councils")}</span>')
    if syn.get("iterations"):
        mchips.append(f'<span class="mchip">{syn["iterations"]} {t("iterations")}</span>')
    if smeta:
        mchips.append(f'<span class="mchip">{t("voices_meta", s=_esc(smeta))}</span>')
    mchips.append(f'<span class="mchip">{_esc(syn["created_at"][:10])}</span>')
    head = (f'<header class="syn-head"><h1>{_esc(syn["title"])}</h1>'
            f'<div class="syn-meta">{"".join(mchips)}</div></header>')

    main = head + "".join(h for _, _, h in sec)
    # Unified detail shell: the caller wraps this content in _doc (content column + Properties/Relations
    # aside) and renders the section minimap via _page_rail(toc) — same as every other detail page.
    toc = [(sid, lbl) for sid, lbl, _ in sec]
    return _SYN_STYLE + f'<div class="syn-main">{main}</div>', toc
