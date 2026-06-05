from __future__ import annotations

import html
import json
import re
from collections import Counter, defaultdict

from .. import services
from .. import presentation as _pres
from ..storage import Store
from ..web_assets import CSS, HEAD_JS, _RGRAPH_JS, _SYN_STYLE, _SYN_SCRIPT  # noqa: F401  (extracted assets)
from ._i18n import t, _lang


ICONS = {
    "overview": '<svg class="ic" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/></svg>',
    "personas": '<svg class="ic" viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.2"/><path d="M3.5 19a5.5 5.5 0 0 1 11 0"/><path d="M16 5.2a3 3 0 0 1 0 5.6"/><path d="M17.5 19a5.5 5.5 0 0 0-3-4.9"/></svg>',
    "councils": '<svg class="ic" viewBox="0 0 24 24"><path d="M21 11.5a8.5 8.5 0 0 1-12.5 7.5L4 20l1-4.5A8.5 8.5 0 1 1 21 11.5z"/></svg>',
    "syntheses": '<svg class="ic" viewBox="0 0 24 24"><path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/></svg>',
    "projects": '<svg class="ic" viewBox="0 0 24 24"><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="12" cy="18" r="2.5"/><path d="M8 7l8 0M7 8l4 8M17 8l-4 8"/></svg>',
    "memory": '<svg class="ic" viewBox="0 0 24 24"><path d="M12 3a4 4 0 0 0-4 4 3.5 3.5 0 0 0-1 6.8V17a3 3 0 0 0 5 2 3 3 0 0 0 5-2v-3.2A3.5 3.5 0 0 0 16 7a4 4 0 0 0-4-4z"/></svg>',
    "panel": '<svg class="ic" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>',
    "sun": '<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.4 1.4M17.6 17.6L19 19M19 5l-1.4 1.4M6.4 17.6L5 19"/></svg>',
    "back": '<svg class="ic" viewBox="0 0 24 24"><path d="M15 18l-6-6 6-6"/></svg>',
    "analytics": '<svg class="ic" viewBox="0 0 24 24"><path d="M3 21h18"/><rect x="5" y="11" width="3.4" height="7" rx="1"/><rect x="10.3" y="6" width="3.4" height="12" rx="1"/><rect x="15.6" y="13" width="3.4" height="5" rx="1"/></svg>',
    "star": '<svg class="ic star" viewBox="0 0 24 24"><path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 17.9 6.8 20.6l1-5.8L3.5 9.7l5.9-.9z"/></svg>',
    "bulb": '<svg class="ic" viewBox="0 0 24 24"><path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.8 10.6c.5.5.8 1 .8 1.6V16h6v-.8c0-.6.3-1.1.8-1.6A6 6 0 0 0 12 3z"/></svg>',
    "target": '<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/></svg>',
    "compass": '<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M15.6 8.4l-2 5.2-5.2 2 2-5.2z"/></svg>',
    "search": '<svg class="ic" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
}


def _esc(value: object) -> str:
    return html.escape(str(value))


def _icon(name: str) -> str:
    return ICONS.get(name, "")


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
    return '<nav class="breadcrumb" aria-label="Seitenposition">' + "".join(parts) + "</nav>"



APP_JS = """
<script>
(function(){
  var MIN=180,MAX=480,HIDE=32;
  var app=document.getElementById('app'),rz=document.getElementById('rz'),tb=document.getElementById('sbt'),th=document.getElementById('thm');
  try{ if(localStorage.getItem('sidebar-open')==='false') app.classList.add('collapsed');
       var w=localStorage.getItem('sidebar-width'); if(w) app.style.setProperty('--sidebar-w',w+'px'); }catch(e){}
  function toggle(){ app.classList.toggle('collapsed');
    try{localStorage.setItem('sidebar-open',String(!app.classList.contains('collapsed')));}catch(e){} }
  if(tb) tb.addEventListener('click',toggle);
  if(th) th.addEventListener('click',function(){
    var cur=document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
    var nx=cur==='dark'?'light':'dark'; document.documentElement.dataset.theme=nx;
    try{localStorage.setItem('theme',nx);}catch(e){} });
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
    if(!keys.length){ var e=document.createElement('span'); e.className='muted small'; e.style.cssText='padding:5px 9px;display:block'; e.textContent='Mit Stern markieren'; favs.appendChild(e); return; }
    keys.forEach(function(k){ var f=m[k];
      var row=document.createElement('div'); row.className='favrow';
      var a=document.createElement('a'); a.href=f.href||'#'; a.title=f.label||'';
      var ic=document.createElement('span'); ic.className='favic'; ic.innerHTML=ICN[f.type]||''; a.appendChild(ic);
      a.appendChild(document.createTextNode(' '+(f.label||k)));
      var x=document.createElement('button'); x.className='favx'; x.setAttribute('data-unstar',k); x.setAttribute('aria-label','Unstar'); x.title='Unstar'; x.textContent='\\u00d7';
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
    items = [("/projects", "projects", t("projects")), ("/personas", "personas", t("personas"))]
    nav = "".join(
        f'<a href="{href}" class="{"active" if key == active else ""}">{_icon(key)}<span>{label}</span></a>'
        for href, key, label in items
    )
    # Favorites are stored client-side (localStorage); this container is filled by JS.
    favs = (f'<div class="navhead">{t("favorites")}</div>'
            f'<div class="sb-quick" id="favs"><span class="muted small" style="padding:5px 9px;display:block">{t("mark_with_star")}</span></div>')
    return f'<nav class="nav">{nav}</nav>{favs}'


def _star(kind: str, ident: str, label: str, href: str) -> str:
    return (f'<button class="starbtn" data-star="{_esc(kind)}:{_esc(ident)}" data-href="{_esc(href)}" '
            f'data-label="{_esc(label)}" data-type="{_esc(kind)}" title="{_esc(t("favorite"))}" aria-label="{_esc(t("mark_as_favorite"))}">'
            f'{_icon("star")}</button>')


_FAV_ICONS_JSON = json.dumps({"persona": ICONS["personas"], "council": ICONS["councils"], "synthesis": ICONS["syntheses"]})


def _layout(title: str, body: str, store: Store, crumbs: list | None = None,
            active: str = "", actions: str = "") -> str:
    crumbs = crumbs or [(title, None)]
    theme_btn = f'<button class="iconbtn" id="thm" title="{t("theme_toggle")}" aria-label="Theme">' + _icon("sun") + "</button>"
    other = "en" if _lang() == "de" else "de"
    lang_btn = (f'<a class="iconbtn" id="lang" href="?lang={other}" title="{_esc(t("lang_toggle"))}" '
                f'aria-label="Language" style="font-size:11px;font-weight:600;text-decoration:none">{t("lang_short")}</a>')
    app_js = APP_JS.replace("__FAV_ICONS__", _FAV_ICONS_JSON)
    return f"""<!doctype html>
<html lang="{_lang()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} · Persona Council</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
{HEAD_JS}<style>{CSS}</style></head>
<body><div class="app" id="app">
  <aside class="sidebar">
    <div class="brand"><span class="mark"></span><a href="/">Persona&nbsp;Council</a></div>
    <div class="sb-scroll">{_nav(active, store)}</div>
    <div class="sb-foot"><a href="/projects">{t("projects")}</a> · <a href="https://github.com/jhoetter/persona-council">{t("repo")}</a></div>
  </aside>
  <div class="resize" id="rz" role="separator" aria-orientation="vertical" aria-label="Sidebar resize"></div>
  <div class="main">
    <header class="topbar"><button class="iconbtn" id="sbt" title="{t("sidebar")} ([)" aria-label="Sidebar">{_icon("panel")}</button>
      {_crumbs_html(crumbs)}<span class="spacer"></span><span class="tb-actions">{actions}{lang_btn}{theme_btn}</span></header>
    <section>{body}</section>
  </div>
</div>{app_js}</body></html>"""


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

