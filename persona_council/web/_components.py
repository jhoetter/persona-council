from __future__ import annotations

import html
import json
import re
from collections import Counter, defaultdict

from persona_icons import icon as _persona_icon

from .. import services
from .. import presentation as _pres
from ..storage import Store
from ..web_assets import CSS, HEAD_JS, _RGRAPH_JS, _SYN_STYLE  # noqa: F401  (extracted assets)
from ._i18n import t, _lang
from ._palette import PALETTE_CSS, PALETTE_JS, palette_markup


def _esc(value: object) -> str:
    return html.escape(str(value))


def _icon(name: str) -> str:
    # Chrome icons come from the shared persona-icons library (single source of
    # truth in ../persona-icons; geometry authored in icons.data.mjs). Returns
    # "" for unknown names, same as the old inline ICONS lookup.
    return _persona_icon(name)


_AV_COLORS = ["#3d7b5f", "#2f6f9f", "#a66b1f", "#7a5ea6", "#b3493f", "#4a7d7d", "#5a6b8a"]


def _avatar(p: dict, size: int = 36) -> str:
    if (p.get("avatar") or {}).get("path"):
        return f'<img class="av" style="width:{size}px;height:{size}px" src="/{_esc(p["avatar"]["path"])}" alt="">'
    name = p.get("display_name", "?")
    ini = "".join(w[0] for w in name.split()[:2]).upper() or "?"
    c = _AV_COLORS[sum(map(ord, p.get("id", "x"))) % len(_AV_COLORS)]
    fs = max(10, size // 3)
    return f'<span class="av" style="width:{size}px;height:{size}px;background:{c};font-size:{fs}px">{_esc(ini)}</span>'


def _stance_color(s: str) -> str:
    s = (s or "").lower()
    if any(k in s for k in ["positiv", "befürwort", "support", "abgeschloss", "done", "grün", "green", "stark"]):
        return "var(--green)"
    if any(k in s for k in ["skept", "oppose", "nein", "negativ", "rot", "verloren", "abgelehnt", "blocked"]):
        return "var(--red)"
    if any(k in s for k in ["bedingt", "maybe", "neutral", "läuft", "prog", "warn", "teilweise"]):
        return "var(--amber)"
    if any(k in s for k in ["indiff", "abstain", "kaum", "egal"]):
        return "var(--muted)"
    return "var(--accent)"


def _label(text: str, color: str | None = None, variant: str = "soft", dot: bool = True) -> str:
    d = f'<span class="ld" style="background:{color or "var(--muted)"}"></span>' if dot else ""
    return f'<span class="lbl lbl-{variant}">{d}{_esc(text)}</span>'


def _crumbs_html(crumbs: list) -> str:
    parts = []
    for i, (label, href) in enumerate(crumbs):
        last = i == len(crumbs) - 1
        if href and not last:
            parts.append(f'<a class="bc-link" href="{_esc(href)}" title="{_esc(label)}">{_esc(label)}</a>')
        else:
            parts.append(f'<span class="bc-cur" title="{_esc(label)}">{_esc(label)}</span>')
        if not last:
            parts.append('<span class="bc-sep" aria-hidden="true">›</span>')
    return f'<nav class="breadcrumb" aria-label="{_esc(t("breadcrumb_aria"))}">' + "".join(parts) + "</nav>"



APP_JS = """
<script>
(function(){
  var MIN=180,MAX=480,HIDE=32;
  var app=document.getElementById('app'),rz=document.getElementById('rz'),tb=document.getElementById('sbt');
  try{ if(localStorage.getItem('sidebar-open')==='false') app.classList.add('collapsed');
       var w=localStorage.getItem('sidebar-width'); if(w) app.style.setProperty('--sidebar-w',w+'px'); }catch(e){}
  function toggle(){ app.classList.toggle('collapsed');
    try{localStorage.setItem('sidebar-open',String(!app.classList.contains('collapsed')));}catch(e){} }
  if(tb) tb.addEventListener('click',toggle);
  // ---- theme (sun / system / moon) + sidebar user menu ----
  var um=document.getElementById('usermenu'),umb=document.getElementById('umbtn'),ump=document.getElementById('umpop');
  function curTheme(){ try{return localStorage.getItem('theme')||'system';}catch(e){return 'system';} }
  function markTheme(v){ document.querySelectorAll('[data-theme-set]').forEach(function(b){
    b.classList.toggle('on', b.getAttribute('data-theme-set')===v); }); }
  function applyTheme(v){
    if(v==='light'||v==='dark') document.documentElement.dataset.theme=v;
    else delete document.documentElement.dataset.theme;
    try{localStorage.setItem('theme',v);}catch(e){} markTheme(v); }
  document.querySelectorAll('[data-theme-set]').forEach(function(b){
    b.addEventListener('click',function(){ applyTheme(b.getAttribute('data-theme-set')); }); });
  markTheme(curTheme());
  function setMenu(open){ if(!um) return; um.classList.toggle('open',open);
    if(ump) ump.hidden=!open; if(umb) umb.setAttribute('aria-expanded',String(open)); }
  if(umb) umb.addEventListener('click',function(e){ e.stopPropagation();
    setMenu(!um.classList.contains('open')); });
  document.addEventListener('click',function(e){
    if(um && um.classList.contains('open') && !um.contains(e.target)) setMenu(false); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') setMenu(false); });
  var gmode=false,gt;
  document.addEventListener('keydown',function(e){
    var tag=(e.target.tagName||'').toLowerCase(); if(tag==='input'||tag==='textarea'||tag==='select') return;
    if(e.key==='['){ toggle(); return; }
    if(e.key==='g'){ gmode=true; clearTimeout(gt); gt=setTimeout(function(){gmode=false;},800); return; }
    if(gmode){ var m={o:'/projects',p:'/personas',r:'/projects'}; if(m[e.key]) location.href=m[e.key]; gmode=false; }
  });
  if(rz){
    var sx=0,sw=248,resizing=false,last=248;
    rz.addEventListener('pointerdown',function(e){ e.preventDefault(); resizing=true; sx=e.clientX;
      sw=parseInt(getComputedStyle(app).getPropertyValue('--sidebar-w'))||248;
      document.body.style.cursor='col-resize'; document.body.style.userSelect='none'; rz.setPointerCapture(e.pointerId); });
    rz.addEventListener('pointermove',function(e){ if(!resizing) return; var next=sw+(e.clientX-sx);
      if(next<=HIDE){ app.classList.add('collapsed'); try{localStorage.setItem('sidebar-open','false');}catch(e){} }
      else { var c=Math.max(MIN,Math.min(MAX,next)); last=c; app.style.setProperty('--sidebar-w',c+'px');
             app.classList.remove('collapsed'); try{localStorage.setItem('sidebar-open','true');}catch(e){} } });
    rz.addEventListener('pointerup',function(e){ if(!resizing) return; resizing=false;
      document.body.style.cursor=''; document.body.style.userSelect='';
      try{localStorage.setItem('sidebar-width',String(last));}catch(e){} });
  }
  var sc=document.querySelector('section'); var tocLinks=[].slice.call(document.querySelectorAll('.toc a'));
  if(sc && tocLinks.length){
    var map={}; tocLinks.forEach(function(a){ map[a.getAttribute('href').slice(1)]=a; });
    var obs=new IntersectionObserver(function(es){ es.forEach(function(en){ if(en.isIntersecting){
      tocLinks.forEach(function(l){l.classList.remove('active');}); if(map[en.target.id]) map[en.target.id].classList.add('active'); } }); },
      {root:sc,rootMargin:'0px 0px -78% 0px',threshold:0});
    document.querySelectorAll('.doc-main [id]').forEach(function(s){ obs.observe(s); });
  }
  // ---- favorites / stars (client-side, localStorage) ----
  var SK='pc-stars', ICN=__FAV_ICONS__;
  function readStars(){ try{return JSON.parse(localStorage.getItem(SK)||'{}');}catch(e){return {};} }
  function writeStars(m){ try{localStorage.setItem(SK,JSON.stringify(m));}catch(e){} }
  function renderStars(){
    var m=readStars();
    document.querySelectorAll('[data-star]').forEach(function(b){ b.classList.toggle('on', !!m[b.getAttribute('data-star')]); });
    var favs=document.getElementById('favs'); if(!favs) return;
    var keys=Object.keys(m);
    favs.innerHTML='';
    if(!keys.length){ var e=document.createElement('span'); e.className='muted small'; e.style.cssText='padding:5px 9px;display:block'; e.textContent=__FAV_EMPTY__; favs.appendChild(e); return; }
    keys.forEach(function(k){ var f=m[k];
      var row=document.createElement('div'); row.className='favrow';
      var a=document.createElement('a'); a.href=f.href||'#'; a.title=f.label||'';
      var ic=document.createElement('span'); ic.className='favic'; ic.innerHTML=ICN[f.type]||''; a.appendChild(ic);
      a.appendChild(document.createTextNode(' '+(f.label||k)));
      var x=document.createElement('button'); x.className='favx'; x.setAttribute('data-unstar',k); x.setAttribute('aria-label',__UNSTAR__); x.title=__UNSTAR__; x.textContent='\\u00d7';
      row.appendChild(a); row.appendChild(x); favs.appendChild(row); });
  }
  document.addEventListener('click',function(e){
    var ux=e.target.closest && e.target.closest('[data-unstar]');
    if(ux){ e.preventDefault(); e.stopPropagation(); var mm=readStars(); delete mm[ux.getAttribute('data-unstar')]; writeStars(mm); renderStars(); return; }
    var b=e.target.closest && e.target.closest('[data-star]'); if(!b) return;
    e.preventDefault(); e.stopPropagation();
    var m=readStars(), k=b.getAttribute('data-star');
    if(m[k]) delete m[k]; else m[k]={href:b.getAttribute('data-href'),label:b.getAttribute('data-label'),type:b.getAttribute('data-type')};
    writeStars(m); renderStars();
  });
  renderStars();
})();
</script>
"""


def _nav(active: str, store: Store) -> str:
    items = [("/projects", "projects", t("projects")), ("/personas", "personas", t("personas")),
             ("/councils", "councils", t("councils")), ("/syntheses", "syntheses", t("syntheses")),
             ("/prototypes", "prototype", t("prototypes_h"))]
    nav = "".join(
        f'<a href="{href}" class="{"active" if key == active else ""}">{_icon(key)}<span>{label}</span></a>'
        for href, key, label in items
    )
    # Favorites are stored client-side (localStorage); this container is filled by JS.
    favs = (f'<div class="navhead">{t("favorites")}</div>'
            f'<div class="sb-quick" id="favs"><span class="muted small" style="padding:5px 9px;display:block">{t("mark_with_star")}</span></div>')
    return f'<nav class="nav">{nav}</nav>{favs}'


def _user_menu() -> str:
    """Modern user/settings menu pinned to the bottom of the sidebar — a popover with a
    sun/system/moon theme switch and a language switch (replaces the old topbar buttons)."""
    cur = _lang()
    themes = [("light", "sun", t("theme_light")), ("system", "monitor", t("theme_system")),
              ("dark", "moon", t("theme_dark"))]
    theme_opts = "".join(
        f'<button type="button" class="segbtn" data-theme-set="{val}" '
        f'title="{_esc(label)}" aria-label="{_esc(label)}">{_icon(icon)}<span>{_esc(label)}</span></button>'
        for val, icon, label in themes
    )
    langs = [("de", "Deutsch", "DE"), ("en", "English", "EN")]
    lang_opts = "".join(
        f'<a class="segbtn{" on" if code == cur else ""}" href="?lang={code}" '
        f'title="{_esc(full)}" aria-label="{_esc(full)}"><span>{short}</span></a>'
        for code, full, short in langs
    )
    return (
        '<div class="usermenu" id="usermenu">'
        '<div class="um-pop" id="umpop" hidden>'
        f'<div class="um-sec"><div class="um-lbl">{t("theme")}</div><div class="seg seg-theme">{theme_opts}</div></div>'
        f'<div class="um-sec"><div class="um-lbl">{t("language")}</div><div class="seg">{lang_opts}</div></div>'
        '</div>'
        '<button type="button" class="um-trigger" id="umbtn" aria-haspopup="true" aria-expanded="false">'
        f'<span class="um-ava">{_icon("settings")}</span><span class="um-name">{t("settings")}</span>'
        f'<span class="um-caret">{_icon("chevron")}</span></button>'
        '</div>'
    )


def _star(kind: str, ident: str, label: str, href: str) -> str:
    return (f'<button class="starbtn" data-star="{_esc(kind)}:{_esc(ident)}" data-href="{_esc(href)}" '
            f'data-label="{_esc(label)}" data-type="{_esc(kind)}" title="{_esc(t("favorite"))}" aria-label="{_esc(t("mark_as_favorite"))}">'
            f'{_icon("star")}</button>')


_FAV_ICONS_JSON = json.dumps({"persona": _icon("personas"), "council": _icon("councils"), "synthesis": _icon("syntheses")})


def _layout(title: str, body: str, store: Store, crumbs: list | None = None,
            active: str = "", actions: str = "") -> str:
    crumbs = crumbs or [(title, None)]
    # Inject per-request translations into the static JS (client renders need them
    # too — same __PLACEHOLDER__ -> t() pattern used for the voices chart).
    app_js = (APP_JS.replace("__FAV_ICONS__", _FAV_ICONS_JSON)
              .replace("__FAV_EMPTY__", json.dumps(t("mark_with_star")))
              .replace("__UNSTAR__", json.dumps(t("unstar"))))
    return f"""<!doctype html>
<html lang="{_lang()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} · Persona Council</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
{HEAD_JS}<style>{CSS}{PALETTE_CSS}</style></head>
<body><div class="app" id="app">
  <aside class="sidebar">
    <div class="brand"><span class="mark"></span><a href="/">Persona&nbsp;Council</a></div>
    <div class="sb-scroll">{_nav(active, store)}</div>
    {_user_menu()}
  </aside>
  <div class="resize" id="rz" role="separator" aria-orientation="vertical" aria-label="Sidebar resize"></div>
  <div class="main">
    <header class="topbar"><button class="iconbtn" id="sbt" title="{t("sidebar")} ([)" aria-label="Sidebar">{_icon("panel")}</button>
      {_crumbs_html(crumbs)}<span class="spacer"></span><span class="tb-actions">{actions}</span></header>
    <section>{body}</section>
  </div>
</div>{palette_markup()}{PALETTE_JS}{app_js}</body></html>"""


def _study_lead(answer_html: str, answer_label: str, *, question: str = "",
                qlabel: str = "", qid: str = "exec") -> str:
    """Unified Question → Answer/Finding lead — the SAME typographic block on every study page
    (council 'finding', synthesis 'answer'). The qa-q question is shown only when given (synthesis,
    whose hero title is the thesis); council omits it because its hero title IS the question."""
    q = f'<p class="qa-q" data-label="{_esc(qlabel)}">{_esc(question)}</p>' if question else ""
    return (f'<div class="es" id="{_esc(qid)}">{q}'
            f'<div class="eyebrow">{_esc(answer_label)}</div>'
            f'<div class="es-prose">{answer_html}</div></div>')


def _empty_state(title: str, message: str) -> str:
    return f'<div class="page"><div class="card"><h2>{_esc(title)}</h2><p class="muted">{_esc(message)}</p><p><a class="btn" href="/projects">{_icon("back")} {t("projects")}</a></p></div></div>'


_EDGE_COLORS = {"spawned_from": "#6b7cff", "refines": "#34a853", "contrasts": "#ea4335",
                "depends_on": "#a142f4", "duplicates": "#9aa0a6", "answers": "#f29900",
                "informs": "#5e6ad2"}  # the diamond-to-diamond spine (GAP-6)
_THEME_PALETTE = ["#6b7cff", "#34a853", "#f29900", "#a142f4", "#ea4335", "#00897b", "#5f6368", "#d81b60"]


def _theme_color(theme: str, vocab: list[str]) -> str:
    try:
        return _THEME_PALETTE[vocab.index(theme) % len(_THEME_PALETTE)]
    except ValueError:
        return "#9aa0a6"


def _proto_tags(pr: dict) -> set:
    """An artifact's open tags, mirroring methodology._artifact_tags (type tag + discriminators).
    Read from the record's data; no artifact value assumed."""
    tags = {pr.get("type") or _pres.DEFAULT_ARTIFACT_TYPE}
    if pr.get("fidelity"):
        tags.add(pr["fidelity"])
    for tg in (pr.get("tags") or []):
        tags.add(tg)
    return tags


def _artifact_present(pr: dict) -> dict:
    """Resolve an artifact's display fields purely from data: the type tag's presentation hint +
    the first discriminator tag's short label. Generic fallbacks when no hint exists."""
    type_tag = pr.get("type") or _pres.DEFAULT_ARTIFACT_TYPE
    tp = _pres.present(type_tag, pr.get("presentation"))
    disc = ""
    for tg in ([pr.get("fidelity")] + list(pr.get("tags") or [])):
        if tg:
            disc = _pres.present(tg)["short"]
            break
    return {"label": tp["label"], "color": tp["color"], "glyph": tp["glyph"], "icon": tp["icon"], "disc": disc}


def _pills(items: list[str]) -> str:
    return "".join(f'<span class="pill">{_esc(item)}</span>' for item in items)


def _md(text: str) -> str:
    if not text:
        return ""

    def fmt(s: str) -> str:
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", _esc(s))

    def _cells(row: str) -> list[str]:
        r = row.strip()
        if r.startswith("|"): r = r[1:]
        if r.endswith("|"): r = r[:-1]
        return [c.strip() for c in r.split("|")]

    lines = text.split("\n")
    n = len(lines)
    out: list[str] = []
    in_ul = False
    i = 0
    while i < n:
        raw = lines[i]
        line = raw.rstrip(); stripped = line.lstrip()
        # GitHub-style pipe table: header row, then a |---|---| separator row
        if stripped.startswith("|") and i + 1 < n:
            sep = lines[i + 1].strip()
            if sep.startswith("|") and "-" in sep and not set(sep) - set("|:- "):
                if in_ul:
                    out.append("</ul>"); in_ul = False
                header = _cells(stripped)
                j = i + 2
                rows = []
                while j < n and lines[j].strip().startswith("|"):
                    rows.append(_cells(lines[j])); j += 1
                th = "".join(f"<th>{fmt(c)}</th>" for c in header)
                trs = "".join("<tr>" + "".join(f"<td>{fmt(c)}</td>" for c in r) + "</tr>" for r in rows)
                out.append(f'<table class="mdtable"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>')
                i = j; continue
        if not stripped:
            if in_ul:
                out.append("</ul>"); in_ul = False
            i += 1; continue
        if stripped.startswith(("- ", "* ")):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{fmt(stripped[2:])}</li>"); i += 1; continue
        if in_ul:
            out.append("</ul>"); in_ul = False
        if line.startswith("### "):
            out.append(f"<h4>{fmt(line[4:])}</h4>")
        elif line.startswith("## "):
            out.append(f"<h3>{fmt(line[3:])}</h3>")
        elif line.startswith("# "):
            out.append(f"<h3>{fmt(line[2:])}</h3>")
        else:
            out.append(f"<p>{fmt(line)}</p>")
        i += 1
    if in_ul:
        out.append("</ul>")
    return "\n".join(out)


def _srcchips(s: str) -> str:
    return re.sub(r"\[(C\d[^\]]*)\]", r'<span class="srcchip">\1</span>', s)


def _rec_row(text: str) -> str:
    m = re.match(r"\s*\[?PRIO\s*(\d+)\]?\s*[—:\-]\s*(.*)", text, re.S)
    if m:
        n = int(m.group(1)); body = m.group(2)
        badge = f'<span class="prio prio-{min(n, 5)}">PRIO {n}</span>'
    else:
        body = text; badge = '<span class="prio prio-5">•</span>'
    return f'<div class="rec">{badge}<div>{_srcchips(_esc(body))}</div></div>'


def _rec_item(x) -> tuple:
    if isinstance(x, dict):
        return str(x.get("text", "")), x.get("aufwand"), x.get("nutzen")
    return str(x), None, None


def _rec_row_n(i: int, text: str, a, n) -> str:
    ax = f'<span class="axchip">{t("effort_value", a=a, n=n)}</span>' if (a and n) else ""
    return f'<div class="rec" id="rec-{i}"><span class="recnum">{i}</span><div>{_srcchips(_esc(text))}{ax}</div></div>'


_EI_LEV = {"g": ("var(--green)", "ei_high_leverage"), "a": ("var(--accent)", "ei_worthwhile"),
           "m": ("var(--amber)", "ei_neutral"), "r": ("var(--red)", "ei_critical")}
_EI_OFFSETS = {
    1: [(0, 0)], 2: [(-17, 0), (17, 0)], 3: [(0, -18), (-17, 13), (17, 13)],
    4: [(-16, -16), (16, -16), (-16, 16), (16, 16)],
    5: [(0, -20), (-19, -5), (19, -5), (-12, 18), (12, 18)],
    6: [(0, -21), (18, -11), (18, 11), (0, 21), (-18, 11), (-18, -11)],
}


def _effort_impact(recs: list) -> str:
    """recs: [(text, aufwand, nutzen)] (1-based order = label). HTML Aufwand×Nutzen matrix
    with hover popovers — no list needed. Returns '' when nothing is scored."""
    scored = [(i, txt, a, n) for i, (txt, a, n) in enumerate(recs, 1) if a and n]
    if not scored:
        return ""
    W, H = 560, 420
    padL, padR, padT, padB = 50, 24, 22, 46
    def X(a): return padL + (a - 1) / 4 * (W - padL - padR)
    def Y(n): return (H - padB) - (n - 1) / 4 * (H - padT - padB)
    def lev(a, n):
        d = n - a
        return "g" if d >= 2 else "a" if d >= 1 else "r" if d <= -1 else "m"
    mx, my = X(3), Y(3)
    q = 'font-size="11" fill="var(--muted)" opacity="0.85"'
    bg = [
        f'<rect x="{padL}" y="{padT}" width="{mx-padL:.0f}" height="{my-padT:.0f}" fill="var(--green)" opacity="0.06"/>',
        f'<line x1="{mx:.0f}" y1="{padT}" x2="{mx:.0f}" y2="{H-padB}" stroke="var(--line)" stroke-dasharray="3 4"/>',
        f'<line x1="{padL}" y1="{my:.0f}" x2="{W-padR}" y2="{my:.0f}" stroke="var(--line)" stroke-dasharray="3 4"/>',
        f'<line x1="{padL}" y1="{padT}" x2="{padL}" y2="{H-padB}" stroke="var(--line)"/>',
        f'<line x1="{padL}" y1="{H-padB}" x2="{W-padR}" y2="{H-padB}" stroke="var(--line)"/>',
        f'<text x="{padL+8}" y="{padT+15}" {q}>{t("ei_quick_wins")}</text>',
        f'<text x="{W-padR-6}" y="{padT+15}" text-anchor="end" {q}>{t("ei_big_bets")}</text>',
        f'<text x="{padL+8}" y="{H-padB-9}" {q}>{t("ei_fill_ins")}</text>',
        f'<text x="{W-padR-6}" y="{H-padB-9}" text-anchor="end" {q}>{t("ei_time_sinks")}</text>',
        f'<text x="{(padL+W-padR)/2:.0f}" y="{H-9}" text-anchor="middle" font-size="12" fill="var(--ink)">{t("ei_effort_axis")}</text>',
        f'<text transform="translate(15,{(padT+H-padB)/2:.0f}) rotate(-90)" text-anchor="middle" font-size="12" fill="var(--ink)">{t("ei_value_axis")}</text>',
    ]
    svg = f'<svg class="ei-bg" viewBox="0 0 {W} {H}" aria-hidden="true">{"".join(bg)}</svg>'
    groups: dict = {}
    for it in scored:
        groups.setdefault((it[2], it[3]), []).append(it)
    dots = []
    for (a, n), items in groups.items():
        offs = _EI_OFFSETS.get(len(items), [(0, 0)] * len(items))
        cx, cy = X(a), Y(n)
        for off, (i, txt, a2, n2) in zip(offs, items):
            color, levkey = _EI_LEV[lev(a2, n2)]
            levlabel = t(levkey)
            lp = (cx + off[0]) / W * 100
            tp = (cy + off[1]) / H * 100
            cls = "ei-dot"
            if tp <= 24:
                cls += " below"
            if lp >= 70:
                cls += " algn-r"
            elif lp <= 24:
                cls += " algn-l"
            pop = (f'<span class="ei-pop"><span class="ei-pop-h" style="color:{color}">#{i} · {levlabel}</span>'
                   f'<span class="ei-pop-t">{_srcchips(_esc(txt))}</span>'
                   f'<span class="ei-pop-m">{t("effort_value", a=a2, n=n2)}</span></span>')
            dots.append(f'<span class="{cls}" tabindex="0" style="left:{lp:.2f}%;top:{tp:.2f}%;--c:{color}">'
                        f'<span class="ei-num">{i}</span>{pop}</span>')
    leg = ('<div class="ei-leg">'
           f'<span><i style="background:var(--green)"></i>{t("ei_high_leverage")}</span>'
           f'<span><i style="background:var(--accent)"></i>{t("ei_worthwhile")}</span>'
           f'<span><i style="background:var(--amber)"></i>{t("ei_neutral")}</span>'
           f'<span><i style="background:var(--red)"></i>{t("ei_critical")}</span></div>')
    return f'<div class="ei-wrap"><div class="ei-plot">{svg}{"".join(dots)}</div>{leg}</div>'


def _doc(main: str, toc: str = "", rail: str = "") -> str:
    cls = "d3" if (toc and rail) else ("d2" if rail else "d1")
    toc_html = f'<div class="toc">{toc}</div>' if toc else ""
    rail_html = f'<aside class="rail">{rail}</aside>' if rail else ""
    return f'<div class="page"><div class="doc {cls}">{toc_html}<div class="doc-main">{main}</div>{rail_html}</div></div>'

