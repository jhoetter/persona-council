from __future__ import annotations

import html
import json
import re
from collections import Counter, defaultdict

from persona_icons import icon as _persona_icon, HIFI_ANIM_CSS as _ICON_ANIM_CSS

from .. import services
from .. import presentation as _pres
from ..storage import Store
from ..web_assets import CSS, HEAD_JS, _RGRAPH_JS  # noqa: F401  (extracted assets)
from ._i18n import t, _lang
from ._html import h, raw, fragment, register_css, collect_css  # noqa: F401  (component-SSR foundation)
from ._palette import PALETTE_CSS, PALETTE_JS, palette_markup


def _esc(value: object) -> str:
    return html.escape(str(value))


def _display_title(text: str, n: int = 90) -> str:
    """A short, header-safe title from possibly-long prose. Some records overload their 'title' with a
    long question-prompt; a title should be a scannable label, so the H1 shows this short form while the
    full text lives in the body (and a real editable title field will supersede it later). Returns the
    first sentence when it fits, else a word-boundary truncation — both with an ellipsis when shortened."""
    s = " ".join((text or "").split())
    if len(s) <= n:
        return s
    first = re.split(r"(?<=[.?!])\s", s, 1)[0]
    if 0 < len(first) <= n:
        return first + ("…" if len(first) < len(s) else "")
    return s[:n].rsplit(" ", 1)[0].rstrip(" ,;:—-") + "…"


def _icon(name: str, animate: bool = False) -> str:
    # Chrome icons come from the shared persona-icons library (single source of
    # truth in ../persona-icons; geometry authored in icons.data.mjs). Returns
    # "" for unknown names, same as the old inline ICONS lookup. animate=True adds
    # .pi-animate (opt-in hover micro-interaction; needs _ICON_ANIM_CSS, registered below).
    return _persona_icon(name, animate=animate)


# Icon hover micro-interactions (persona-icons HIFI_ANIM_CSS — covers regular .pi-animate icons too).
register_css(_ICON_ANIM_CSS)


_AV_COLORS = ["#3d7b5f", "#2f6f9f", "#a66b1f", "#7a5ea6", "#b3493f", "#4a7d7d", "#5a6b8a"]


def _avatar(p: dict, size: int = 36) -> str:
    if (p.get("avatar") or {}).get("path"):
        return h("img", {"class_": "av", "style": f"width:{size}px;height:{size}px",
                         "src": f'/{p["avatar"]["path"]}', "alt": ""})
    name = p.get("display_name", "?")
    ini = "".join(w[0] for w in name.split()[:2]).upper() or "?"
    c = _AV_COLORS[sum(map(ord, p.get("id", "x"))) % len(_AV_COLORS)]
    fs = max(10, size // 3)
    return h("span", {"class_": "av", "style": f"width:{size}px;height:{size}px;background:{c};font-size:{fs}px"}, ini)


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
    d = h("span", {"class_": "ld", "style": f"background:{color or 'var(--muted)'}"}) if dot else None
    return h("span", {"class_": f"lbl lbl-{variant}"}, d, text)


def _crumbs_html(crumbs: list) -> str:
    parts = []
    for i, (label, href) in enumerate(crumbs):
        last = i == len(crumbs) - 1
        if href and not last:
            parts.append(h("a", {"class_": "bc-link", "href": href, "title": label}, label))
        else:
            parts.append(h("span", {"class_": "bc-cur", "title": label}, label))
        if not last:
            parts.append(h("span", {"class_": "bc-sep", "aria-hidden": "true"}, "›"))
    return h("nav", {"class_": "breadcrumb", "aria-label": t("breadcrumb_aria")}, parts)



APP_JS = """
<script>
(function(){
  var MIN=180,MAX=480,HIDE=32;
  var app=document.getElementById('app'),rz=document.getElementById('rz');
  try{ if(localStorage.getItem('sidebar-open')==='false') app.classList.add('collapsed');
       var w=localStorage.getItem('sidebar-width'); if(w) app.style.setProperty('--sidebar-w',w+'px'); }catch(e){}
  function toggle(){ app.classList.toggle('collapsed');
    try{localStorage.setItem('sidebar-open',String(!app.classList.contains('collapsed')));}catch(e){} }
  // delegated so it keeps working after an SPA swap of #main (where #sbt lives)
  document.addEventListener('click',function(e){ if(e.target.closest&&e.target.closest('#sbt')){ e.preventDefault(); toggle(); } });
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
    var favsec=document.getElementById('favsec');
    var keys=Object.keys(m);
    favs.innerHTML='';
    if(!keys.length){ if(favsec) favsec.hidden=true; return; }   // hide the whole section when nothing is starred
    if(favsec) favsec.hidden=false;
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
  // After an SPA content swap (sidebar persists), re-apply star states to the new page's buttons.
  document.addEventListener('spa:load', renderStars);
  // Long hero titles/subs clamp to 3 lines; mark the truncated ones clickable to expand inline.
  function initClamp(){ document.querySelectorAll('.hero h1,.syn-head h1,.hero .sub').forEach(function(el){
    if(!el.classList.contains('expanded')) el.classList.toggle('is-clamped', el.scrollHeight-el.clientHeight>2); }); }
  document.addEventListener('click',function(e){ var t=e.target.closest&&e.target.closest('.is-clamped'); if(t) t.classList.toggle('expanded'); });
  initClamp(); document.addEventListener('spa:load',initClamp);
})();
</script>
"""


# SPA-style navigation (spec/design-system.md): the sidebar/topbar shell is rendered once; internal
# link clicks fetch the target and swap ONLY #main, so the sidebar (and its favorites) never re-render
# or flicker. Pure progressive enhancement — falls back to a full load on any error or non-HTML response.
SPA_JS = """
<script>
(function(){
  var main=document.getElementById('main');
  if(!main || !window.history || !window.history.pushState || !window.fetch) return;
  function runScripts(root){            // importNode'd <script>s don't execute — recreate them so they do
    root.querySelectorAll('script').forEach(function(old){
      var s=document.createElement('script');
      for(var i=0;i<old.attributes.length;i++){ s.setAttribute(old.attributes[i].name, old.attributes[i].value); }
      s.textContent=old.textContent; old.parentNode.replaceChild(s, old);
    });
  }
  function syncActive(doc){             // mirror the fetched page's sidebar active-state onto the live nav
    var on={}; doc.querySelectorAll('.sidebar .nav a.active').forEach(function(a){ on[a.getAttribute('href')]=1; });
    document.querySelectorAll('.sidebar .nav a').forEach(function(a){ a.classList.toggle('active', !!on[a.getAttribute('href')]); });
  }
  function swap(html, url, push){
    var doc=new DOMParser().parseFromString(html, 'text/html');
    var nm=doc.getElementById('main');
    if(!nm){ location.href=url; return; }                 // unexpected shape -> full load
    var imp=document.importNode(nm, true);
    main.replaceWith(imp); main=imp;
    if(doc.title) document.title=doc.title;
    syncActive(doc);
    runScripts(main);
    if(push) history.pushState({spa:1}, '', url);
    window.scrollTo(0,0);
    document.dispatchEvent(new CustomEvent('spa:load'));   // let app_js re-apply star states etc.
  }
  function navigate(url, push){
    document.body.classList.add('spa-loading');
    fetch(url, {headers:{'X-Requested-With':'spa'}, credentials:'same-origin'}).then(function(r){
      var ct=r.headers.get('content-type')||'';
      if(!r.ok || ct.indexOf('text/html')<0){ location.href=url; return; }
      return r.text().then(function(t){ swap(t, url, push); });
    }).catch(function(){ location.href=url; })
      .then(function(){ document.body.classList.remove('spa-loading'); });
  }
  document.addEventListener('click', function(e){
    if(e.defaultPrevented||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey) return;
    var a=e.target.closest && e.target.closest('a'); if(!a) return;
    if(a.hasAttribute('data-drawer')) return;                                // handled by the drawer
    var href=a.getAttribute('href');
    if(!href || href.charAt(0)!=='/' || href.indexOf('//')===0) return;     // internal absolute paths only
    if(a.target==='_blank' || a.hasAttribute('download') || a.getAttribute('rel')==='external') return;
    if(href.indexOf('/data/')===0 || href.indexOf('/proto-files/')===0) return;  // static assets -> real nav
    e.preventDefault();
    if(href===location.pathname+location.search){ return; }
    navigate(href, true);
  });
  window.addEventListener('popstate', function(){ navigate(location.pathname+location.search, false); });
})();
</script>
"""


# Reusable right slide-over drawer. Any element with data-drawer="<url>" opens that page's content in a
# peek panel (fetched + script-reexec via the same approach as SPA nav), without leaving the current page.
# The trigger keeps its href as a graceful fallback (deep-linkable full page when JS is off).
DRAWER_CSS = register_css(
    ".drawer-wrap{position:fixed;inset:0;z-index:120;pointer-events:none}"
    ".drawer-wrap.open{pointer-events:auto}"
    ".drawer-bd{position:absolute;inset:0;background:rgba(10,12,16,.32);opacity:0;transition:opacity .2s var(--ease)}"
    ".drawer-wrap.open .drawer-bd{opacity:1}"
    ".drawer-panel{position:absolute;top:0;right:0;height:100%;width:min(620px,94vw);background:var(--panel);"
    "border-left:1px solid var(--line);box-shadow:var(--shadow-lg);transform:translateX(100%);"
    "transition:transform .24s var(--ease);overflow-y:auto;display:flex;flex-direction:column}"
    ".drawer-wrap.open .drawer-panel{transform:none}"
    ".drawer-head{height:var(--row-h);flex-shrink:0;display:flex;align-items:center;gap:8px;padding:0 16px;"
    "border-bottom:1px solid var(--line);position:sticky;top:0;background:var(--panel);z-index:1}"
    ".drawer-title{font-weight:600;font-size:var(--t-md);flex:1;min-width:0}"
    ".drawer-x{border:0;background:none;cursor:pointer;color:var(--muted);border-radius:var(--radius-sm);"
    "padding:4px;line-height:0;display:inline-flex}.drawer-x:hover{background:var(--hover);color:var(--ink)}"
    ".drawer-body{padding:18px 22px;min-height:0}.drawer-body .page{padding:0;max-width:none}")

DRAWER_MARKUP = (
    '<div class="drawer-wrap" id="drawer">'
    '<div class="drawer-bd" data-drawer-close></div>'
    '<aside class="drawer-panel" role="dialog" aria-modal="true" aria-labelledby="drawer-title">'
    '<header class="drawer-head"><span class="drawer-title" id="drawer-title"></span>'
    '<button class="drawer-x" type="button" data-drawer-close aria-label="Close">✕</button></header>'
    '<div class="drawer-body"></div></aside></div>')

DRAWER_JS = """
<script>
(function(){
  var wrap=document.getElementById('drawer'); if(!wrap || !window.fetch) return;
  var body=wrap.querySelector('.drawer-body'), titleEl=wrap.querySelector('.drawer-title'), lastFocus=null;
  function close(){ wrap.classList.remove('open'); if(lastFocus&&lastFocus.focus) lastFocus.focus(); }
  function runScripts(root){
    root.querySelectorAll('script').forEach(function(old){ var s=document.createElement('script');
      for(var i=0;i<old.attributes.length;i++){ s.setAttribute(old.attributes[i].name, old.attributes[i].value); }
      s.textContent=old.textContent; old.parentNode.replaceChild(s, old); });
  }
  function open(url, title, trigger){
    lastFocus=trigger||document.activeElement;
    titleEl.textContent=title||'';
    body.innerHTML='<p class="muted small">\\u2026</p>';
    wrap.classList.add('open');
    fetch(url, {headers:{'X-Requested-With':'drawer'}, credentials:'same-origin'}).then(function(r){
      if(!r.ok) throw 0; return r.text();
    }).then(function(html){
      var doc=new DOMParser().parseFromString(html, 'text/html');
      var sec=doc.querySelector('#main section') || doc.getElementById('main');
      body.innerHTML='';
      if(sec){ var imp=document.importNode(sec, true); body.appendChild(imp); runScripts(body); }
      var sp=wrap.querySelector('.drawer-panel'); if(sp) sp.scrollTop=0;
      document.dispatchEvent(new CustomEvent('spa:load'));   // re-apply star states inside the drawer
    }).catch(function(){ location.href=url; });               // any failure -> just open the real page
  }
  document.addEventListener('click', function(e){
    var t=e.target.closest && e.target.closest('[data-drawer]');
    if(t){ e.preventDefault(); e.stopPropagation(); open(t.getAttribute('data-drawer'), t.getAttribute('data-drawer-title')||(t.textContent||'').trim(), t); return; }
    if(e.target.closest && e.target.closest('[data-drawer-close]')){ e.preventDefault(); close(); }
  });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape' && wrap.classList.contains('open')) close(); });
})();
</script>
"""


def _nav(active: str, store: Store) -> str:
    # Workspace = the inputs/containers; Research = the methodology-agnostic primitives any
    # methodology produces (council/concept/prototype/synthesis). (href, active-key, icon, label).
    work = [("/projects", "projects", "projects", t("projects")),
            ("/personas", "personas", "personas", t("personas"))]
    research = [("/councils", "councils", "councils", t("councils")),
                ("/concepts", "concept", "bulb", t("concepts")),
                ("/prototypes", "prototype", "prototype", t("prototypes_h")),
                ("/syntheses", "syntheses", "syntheses", t("syntheses"))]
    # .pi-hover makes the row the animation trigger — the icon plays its micro-interaction on row hover.
    render = lambda items: fragment(*(
        h("a", {"href": href, "class_": "pi-hover active" if k == active else "pi-hover"},
          raw(_icon(ic, animate=True)), h("span", {}, lbl))
        for href, k, ic, lbl in items))
    # Favorites are stored client-side (localStorage); the section is filled AND shown/hidden by JS
    # (renderStars) — it only appears once something is starred, so an empty sidebar stays clean.
    favs = h("div", {"id": "favsec", "hidden": True},
             h("div", {"class_": "navhead"}, t("favorites")),
             h("div", {"class_": "sb-quick", "id": "favs"}))
    return fragment(h("nav", {"class_": "nav"}, render(work)),
                    h("div", {"class_": "navhead"}, t("library_h")),
                    h("nav", {"class_": "nav"}, render(research)), favs,
                    h("nav", {"class_": "nav nav-foot"},
                      render([("/documentation", "docs", "overview", t("documentation"))])))


def _user_menu() -> str:
    """Modern user/settings menu pinned to the bottom of the sidebar — a popover with a
    sun/system/moon theme switch and a language switch (replaces the old topbar buttons)."""
    cur = _lang()
    themes = [("light", "sun", t("theme_light")), ("system", "monitor", t("theme_system")),
              ("dark", "moon", t("theme_dark"))]
    theme_opts = [h("button", {"type": "button", "class_": "segbtn", "data-theme-set": val,
                                "title": label, "aria-label": label}, raw(_icon(icon)), h("span", {}, label))
                  for val, icon, label in themes]
    langs = [("de", "Deutsch", "DE"), ("en", "English", "EN")]
    lang_opts = [h("a", {"class_": f'segbtn{" on" if code == cur else ""}', "href": f"?lang={code}",
                         "title": full, "aria-label": full}, h("span", {}, short))
                 for code, full, short in langs]
    return h("div", {"class_": "usermenu", "id": "usermenu"},
             h("div", {"class_": "um-pop", "id": "umpop", "hidden": True},
               h("div", {"class_": "um-sec"}, h("div", {"class_": "um-lbl"}, t("theme")),
                 h("div", {"class_": "seg seg-theme"}, theme_opts)),
               h("div", {"class_": "um-sec"}, h("div", {"class_": "um-lbl"}, t("language")),
                 h("div", {"class_": "seg"}, lang_opts))),
             h("button", {"type": "button", "class_": "um-trigger pi-hover", "id": "umbtn",
                          "aria-haspopup": "true", "aria-expanded": "false"},
               h("span", {"class_": "um-ava"}, raw(_icon("settings", animate=True))),
               h("span", {"class_": "um-name"}, t("settings")),
               h("span", {"class_": "um-caret"}, raw(_icon("chevron")))))


def _star(kind: str, ident: str, label: str, href: str) -> str:
    return h("button", {"class_": "starbtn", "data-star": f"{kind}:{ident}", "data-href": href,
                        "data-label": label, "data-type": kind, "title": t("favorite"),
                        "aria-label": t("mark_as_favorite")}, raw(_icon("star")))


_FAV_ICONS_JSON = json.dumps({
    "persona": _icon("personas"), "council": _icon("councils"), "synthesis": _icon("syntheses"),
    "project": _icon("projects"), "prototype": _icon("prototype"), "concept": _icon("bulb"),
    "note": _icon("square"), "section": _icon("squareGrid"),
})


def _layout(title: str, body: str, store: Store, crumbs: list | None = None,
            active: str = "", actions: str = "") -> str:
    crumbs = crumbs or [(title, None)]
    # Inject per-request translations into the static JS (client renders need them
    # too — same __PLACEHOLDER__ -> t() pattern used for the voices chart).
    app_js = (APP_JS.replace("__FAV_ICONS__", _FAV_ICONS_JSON)
              .replace("__UNSTAR__", json.dumps(t("unstar"))))
    return f"""<!doctype html>
<html lang="{_lang()}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)} · Persona Council</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
{HEAD_JS}<style>{CSS}{PALETTE_CSS}{collect_css()}</style></head>
<body><div class="app" id="app">
  <aside class="sidebar">
    <div class="brand"><span class="mark"></span><a href="/">Persona&nbsp;Council</a></div>
    <div class="sb-scroll">{_nav(active, store)}</div>
    {_user_menu()}
  </aside>
  <div class="resize" id="rz" role="separator" aria-orientation="vertical" aria-label="Sidebar resize"></div>
  <div class="main" id="main">
    <header class="topbar"><button class="iconbtn" id="sbt" title="{t("sidebar")} ([)" aria-label="Sidebar">{_icon("panel")}</button>
      {_crumbs_html(crumbs)}<span class="spacer"></span><span class="tb-actions">{actions}</span></header>
    <section>{body}</section>
  </div>
</div>{DRAWER_MARKUP}{palette_markup()}{PALETTE_JS}{app_js}{SPA_JS}{DRAWER_JS}</body></html>"""


# First component on the new builder (spec C3): markup via h() (auto-escaped), CSS co-located here.
_STUDY_LEAD_CSS = register_css(
    ".es{margin:22px 0 4px}"
    ".eyebrow{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.09em;color:var(--accent);font-weight:700;margin:0 0 12px}"
    ".qa-q{font-size:var(--t-lg);line-height:1.42;font-weight:600;color:var(--ink);margin:2px 0 18px}"
    ".qa-q::before{content:attr(data-label);display:block;font-size:var(--t-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin-bottom:5px}")


# Long titles/subs (e.g. a council's full question-prompt) are clamped to a few lines + ellipsis — the
# header stays scannable (Linear-style) and the full text is available on hover (title=) and in the body.
_HERO_CSS = register_css(
    ".hero h1{font-size:var(--t-xl);line-height:1.2;letter-spacing:-.02em;margin:0 0 6px;font-weight:650;"
    "display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}"
    ".hero h1 svg{width:21px;height:21px;color:var(--accent);margin-right:8px;vertical-align:-2px}"
    ".hero .sub{color:var(--muted);font-size:var(--t-body);margin:0 0 4px;max-width:74ch;"
    "display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}"
    ".is-clamped{cursor:pointer}"                                  # only set by JS when actually truncated
    "h1.expanded,.sub.expanded{-webkit-line-clamp:unset;display:block;overflow:visible}")


def _hero(title, *, sub=None, icon: str | None = None, hid: str | None = None, top=None) -> str:
    """The page hero used by every detail page: optional `top` slot (a pill, trusted HTML), a title
    (text → escaped, or Safe HTML kept) with an optional leading `icon`, and an optional `sub`
    (text → escaped, or Safe HTML like a chip line). Title/sub are line-clamped (see _HERO_CSS); plain
    text gets a full-text title= tooltip."""
    h1_attrs = {"title": title} if type(title) is str else {}      # full text on hover (clamped display)
    sub_attrs = {"class_": "sub"}
    if type(sub) is str:
        sub_attrs["title"] = sub
    return h("div", {"class_": "hero", "id": hid},
             raw(top) if top else None,
             h("h1", h1_attrs, raw(_icon(icon)) if icon else None, title),
             h("p", sub_attrs, sub) if sub else None)


def _study_lead(answer_html: str, answer_label: str, *, question: str = "",
                qlabel: str = "", qid: str = "exec") -> str:
    """Unified Question → Answer/Finding lead — the SAME typographic block on every study page
    (council 'finding', synthesis 'answer'). The qa-q question is shown only when given (synthesis,
    whose hero title is the thesis); council omits it because its hero title IS the question."""
    return h("div", {"class_": "es", "id": qid},
             h("p", {"class_": "qa-q", "data_label": qlabel}, question) if question else None,
             h("div", {"class_": "eyebrow"}, answer_label),
             h("div", {"class_": "es-prose"}, raw(answer_html)))


def _list_page(store: Store, *, title: str, lead: str, rows: list,
               empty_icon: str, empty_msg: str, active: str) -> str:
    """One index-page shell — title + count + lead + rows (or an empty state). Every list page
    (projects, personas, councils, syntheses, prototypes, concepts) renders identically through this."""
    rows_html = raw("".join(str(r) for r in rows)) if rows else h("div", {"class_": "list-empty"}, raw(_icon(empty_icon)), h("span", {}, empty_msg))
    cnt = h("span", {"class_": "h1cnt"}, str(len(rows))) if rows else ""
    body = h("div", {"class_": "page"}, h("h1", {"class_": "h1"}, title, cnt),
             h("p", {"class_": "lead"}, lead), h("div", {"class_": "rows"}, rows_html))
    return _layout(title, body, store, crumbs=[(title, None)], active=active)


def _empty_state(title: str, message: str) -> str:
    return h("div", {"class_": "page"}, h("div", {"class_": "card"},
             h("h2", {}, title), h("p", {"class_": "muted"}, message),
             h("p", {}, h("a", {"class_": "btn", "href": "/projects"}, raw(_icon("back")), " ", t("projects")))))


# Edge-type → color is DATA (suggestions/edge_types.json via presentation.edge_colors); no edge color
# hardcoded here (Layer 2). The spine type (GAP-6) "informs" lives in that file like the rest.
_EDGE_COLORS = _pres.edge_colors()
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
    return fragment(*(h("span", {"class_": "pill"}, item) for item in items))


def _md_inline(s: str) -> str:
    """Inline Markdown → HTML (auto-escaped): `code`, [text](/url), **bold**, ~~strike~~, _italic_,
    *italic*. Code spans and links are processed first and protected so their content isn't re-formatted."""
    s = _esc(s)
    holds: list[str] = []
    def _hold(html: str) -> str:
        holds.append(html); return f"\x00{len(holds) - 1}\x00"
    s = re.sub(r"`([^`]+)`", lambda m: _hold("<code>" + m.group(1) + "</code>"), s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+|/[^)\s]*)\)",
               lambda m: _hold(f'<a href="{m.group(2)}">{m.group(1)}</a>'), s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"~~(.+?)~~", r"<del>\1</del>", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)([^*]+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)      # *italic*
    s = re.sub(r"(?<![\w_])_(?!\s)([^_]+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", s)        # _italic_ (not word-internal)
    for k, hh in enumerate(holds):
        s = s.replace(f"\x00{k}\x00", hh)
    return s


def _md(text: str) -> str:
    """Minimal-but-real GitHub-flavored Markdown → HTML (no deps). Covers the host-authored subset
    (spec/markdown-authoring-harness.md): #/##/### headings, **bold**/_italic_/`code`/[links]/~~del~~,
    `-`/`*` and `1.` lists, `>` blockquotes, `---` rules, ``` fenced code, pipe tables, paragraphs."""
    if not text:
        return ""

    def _cells(row: str) -> list[str]:
        return [c.strip() for c in row.strip().strip("|").split("|")]

    lines = text.split("\n")
    n = len(lines); out: list[str] = []; stack: list[str] = []; i = 0

    def _close():                                  # close any open list(s)
        while stack:
            out.append(f"</{stack.pop()}>")

    while i < n:
        line = lines[i].rstrip(); stripped = line.lstrip()
        if stripped.startswith("```"):             # fenced code block
            _close(); j = i + 1; buf = []
            while j < n and not lines[j].lstrip().startswith("```"):
                buf.append(_esc(lines[j])); j += 1
            out.append("<pre><code>" + "\n".join(buf) + "</code></pre>"); i = j + 1; continue
        if stripped.startswith("|") and i + 1 < n:  # pipe table (header + |---| separator)
            sep = lines[i + 1].strip()
            if sep.startswith("|") and "-" in sep and not set(sep) - set("|:- "):
                _close(); header = _cells(stripped); j = i + 2; rows = []
                while j < n and lines[j].strip().startswith("|"):
                    rows.append(_cells(lines[j])); j += 1
                th = "".join(f"<th>{_md_inline(c)}</th>" for c in header)
                trs = "".join("<tr>" + "".join(f"<td>{_md_inline(c)}</td>" for c in r) + "</tr>" for r in rows)
                out.append(f'<table class="mdtable"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>')
                i = j; continue
        if not stripped:
            _close(); i += 1; continue
        if re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", stripped):     # horizontal rule
            _close(); out.append("<hr>"); i += 1; continue
        if stripped.startswith(">"):                 # blockquote (consume consecutive > lines)
            _close(); buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(lines[i].lstrip()[1:].lstrip()); i += 1
            out.append("<blockquote>" + _md_inline(" ".join(buf)) + "</blockquote>"); continue
        m = re.match(r"\d+\.\s+(.*)", stripped)      # ordered list
        if m:
            if not (stack and stack[-1] == "ol"):
                _close(); out.append("<ol>"); stack.append("ol")
            out.append(f"<li>{_md_inline(m.group(1))}</li>"); i += 1; continue
        if stripped[:2] in ("- ", "* ") or stripped.startswith("• "):   # unordered list
            if not (stack and stack[-1] == "ul"):
                _close(); out.append("<ul>"); stack.append("ul")
            out.append(f"<li>{_md_inline(stripped[2:].lstrip())}</li>"); i += 1; continue
        _close()
        if stripped.startswith("#### "): out.append(f"<h4>{_md_inline(stripped[5:])}</h4>")
        elif stripped.startswith("### "): out.append(f"<h4>{_md_inline(stripped[4:])}</h4>")
        elif stripped.startswith("## "): out.append(f"<h3>{_md_inline(stripped[3:])}</h3>")
        elif stripped.startswith("# "): out.append(f"<h3>{_md_inline(stripped[2:])}</h3>")
        else: out.append(f"<p>{_md_inline(line)}</p>")
        i += 1
    _close()
    return "\n".join(out)


def _srcchips(s: str) -> str:
    return re.sub(r"\[(C\d[^\]]*)\]", r'<span class="srcchip">\1</span>', s)


def _prose(s: object) -> str:
    """The ONE renderer for inline authored prose (list items, verdicts, arguments, recommendations):
    inline Markdown (**bold**/_italic_/`code`/links) PLUS [C#] citation chips. Use this everywhere a
    single line/paragraph of host-authored text is shown, so Markdown renders consistently and no
    surface shows literal `**`. Multi-paragraph blocks still use _md()."""
    return _srcchips(_md_inline(str(s)))


def _rec_row(text: str) -> str:
    m = re.match(r"\s*\[?PRIO\s*(\d+)\]?\s*[—:\-]\s*(.*)", text, re.S)
    if m:
        n = int(m.group(1)); body = m.group(2)
        badge = h("span", {"class_": f"prio prio-{min(n, 5)}"}, f"PRIO {n}")
    else:
        body = text; badge = h("span", {"class_": "prio prio-5"}, "•")
    return h("div", {"class_": "rec"}, badge, h("div", {}, raw(_srcchips(_esc(body)))))


def _rec_item(x) -> tuple:
    if isinstance(x, dict):
        return str(x.get("text", "")), x.get("aufwand"), x.get("nutzen")
    return str(x), None, None


def _rec_row_n(i: int, text: str, a, n) -> str:
    ax = h("span", {"class_": "axchip"}, t("effort_value", a=a, n=n)) if (a and n) else ""
    return h("div", {"class_": "rec", "id": f"rec-{i}"}, h("span", {"class_": "recnum"}, str(i)),
             h("div", {}, raw(_prose(text)), ax))


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
            pop = h("span", {"class_": "ei-pop"},
                    h("span", {"class_": "ei-pop-h", "style": f"color:{color}"}, f"#{i} · {levlabel}"),
                    h("span", {"class_": "ei-pop-t"}, raw(_srcchips(_esc(txt)))),
                    h("span", {"class_": "ei-pop-m"}, t("effort_value", a=a2, n=n2)))
            dots.append(h("span", {"class_": cls, "tabindex": "0", "style": f"left:{lp:.2f}%;top:{tp:.2f}%;--c:{color}"},
                          h("span", {"class_": "ei-num"}, str(i)), pop))
    leg = h("div", {"class_": "ei-leg"},
            h("span", {}, h("i", {"style": "background:var(--green)"}), t("ei_high_leverage")),
            h("span", {}, h("i", {"style": "background:var(--accent)"}), t("ei_worthwhile")),
            h("span", {}, h("i", {"style": "background:var(--amber)"}), t("ei_neutral")),
            h("span", {}, h("i", {"style": "background:var(--red)"}), t("ei_critical")))
    return h("div", {"class_": "ei-wrap"}, h("div", {"class_": "ei-plot"}, raw(svg), fragment(*dots)), leg)


def _doc(main: str, toc: str = "", rail: str = "") -> str:
    cls = "d3" if (toc and rail) else ("d2" if rail else "d1")
    toc_html = h("div", {"class_": "toc"}, raw(toc)) if toc else ""
    rail_html = h("aside", {"class_": "rail"}, raw(rail)) if rail else ""
    return h("div", {"class_": "page"}, h("div", {"class_": f"doc {cls}"}, toc_html,
             h("div", {"class_": "doc-main"}, raw(main)), rail_html))

# Co-located CSS (spec/roadmap.md R3): labels/avatars, stat strip, stars/favorites.
register_css(r"""
/* ---- labels / avatars (G5) ---- */
.lbl{display:inline-flex;align-items:center;gap:6px;font-size:var(--t-sm);border-radius:6px;padding:2px 8px;white-space:nowrap}
.lbl-soft{background:var(--panel-2);border:1px solid var(--line);color:var(--ink)}
.lbl-outline{border:1px solid var(--line);color:var(--muted)}
.lbl .ld{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.av{border-radius:50%;object-fit:cover;flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;font-size:var(--t-xs);font-weight:600;color:#fff;border:1px solid var(--line)}
.avs{display:inline-flex}.avs .av{margin-left:-6px;box-shadow:0 0 0 2px var(--panel)}.avs .av:first-child{margin-left:0}
/* ---- stat strip + persona cards (G2) ---- */
.stats{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 22px}
.stat{display:flex;align-items:baseline;gap:7px;border:1px solid var(--line);border-radius:8px;background:var(--panel);padding:8px 12px}
.stat b{font-size:var(--t-lg);font-weight:700}.stat span{color:var(--muted);font-size:var(--t-sm)}
/* ---- stars / favorites ---- */
.starbtn{border:0;background:none;cursor:pointer;color:var(--muted);padding:2px;line-height:0;border-radius:6px;display:inline-flex}
.starbtn:hover{color:#e3a008;background:var(--hover)}
.starbtn .star{fill:none}
.starbtn.on{color:#e3a008}.starbtn.on .star{fill:#e3a008;stroke:#e3a008}
#favs a{display:flex;align-items:center;gap:6px;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.favrow{display:flex;align-items:center;gap:2px}
.favx{border:0;background:none;color:var(--muted);cursor:pointer;font-size:var(--t-prose);line-height:1;padding:1px 7px;border-radius:6px;opacity:0;transition:opacity 120ms}
.favrow:hover .favx{opacity:1}.favx:hover{color:#e3a008;background:var(--hover)}
""")

# Co-located CSS (spec/roadmap.md R3): turn cards / detail-page chrome.
register_css(r"""
/* ---- turn cards / detail ---- */
.turn{border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);padding:13px}
.turn .hd{display:flex;align-items:center;gap:8px;margin:0 0 7px;flex-wrap:wrap}.turn .hd b{font-size:var(--t-body)}
.turn.mod{background:var(--panel-2)}
.turn-who{display:inline-flex;align-items:center;gap:7px;color:var(--ink);text-decoration:none}
.turn-who:hover b{color:var(--accent)}
.turn-ctx{flex-basis:100%;margin:2px 0 0;font-style:italic}
/* a persona's multiple answers stack in one card, separated by a hairline */
.turn-ans+.turn-ans{margin-top:11px;padding-top:11px;border-top:1px solid var(--line-2)}
.turn-ans>p{margin:0}
/* moderated transcript: one round per moderator question (the question, then the answers) */
.qrounds{display:flex;flex-direction:column;gap:22px}
.qround{display:flex;flex-direction:column;gap:10px}
.qround-q{display:flex;align-items:flex-start;gap:10px;padding:11px 14px;background:var(--accent-weak);border:1px solid var(--line);border-radius:var(--radius)}
.qround-q>svg{color:var(--accent);flex-shrink:0;width:18px;height:18px;margin-top:1px}
.qround-q p{margin:2px 0 0;font-weight:600;font-size:var(--t-md);line-height:1.35}
.qround-n{font-size:var(--t-xs);font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--accent)}
.qround-a{display:flex;flex-direction:column;gap:10px}
.turn-input{margin:2px 0 8px;border:1px dashed var(--line);border-radius:8px;padding:6px 10px;background:var(--bg)}
.turn-input summary{cursor:pointer}
/* prototype-session fields, inside the shared .turn statement card — labelled like the es-prose eyebrows */
.sfield{margin:10px 0 0}.sfield:first-child{margin-top:2px}.sfield .eyebrow{margin:0 0 3px}.sfield .es-prose{margin:0}.sfield .es-prose p{margin:0}
.detail{max-width:980px}.thought{font-size:var(--t-md);padding:9px 12px;background:var(--panel-2);border-radius:8px}
.quote{padding:8px 12px;background:var(--panel-2);margin:6px 0;border-radius:8px}
.identity{display:grid;grid-template-columns:160px 1fr;gap:20px;align-items:start}
.identity .avatar{width:160px;height:200px;object-fit:cover;border-radius:8px;border:1px solid var(--line)}
""")
