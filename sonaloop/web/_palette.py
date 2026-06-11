"""Cmd+K command palette: global jump across every entity + nav commands.

Self-contained (CSS + markup + JS), injected once by _layout so it works on every
page. Kept out of web_assets.py to respect the per-file LOC bar. Results come from
/api/search and are grouped by type, Linear/Raycast-style (leading type dot, muted
section headers, a footer hint bar).

WHAT the palette can reach is not declared here: the coverage registry
(web/_palette_registry.py) enumerates the searchable entity types (labels, icons,
colors, ordering — all generated from it below) and derives the static jump commands
from the nav registry, so core AND extension nav items appear automatically. The
canary test (tests/test_palette_coverage.py) fails when the app grows a surface the
registry doesn't reach."""
from __future__ import annotations

import json

from .._icons import icon as _picon       # direct import avoids a cycle (_components imports _palette)
from ._i18n import t
from ._html import h, raw
from ._palette_registry import SEARCH_SOURCES, nav_commands, search_rows  # noqa: F401 (search_rows re-exported for the API)


PALETTE_CSS = r"""
.cmdk[hidden]{display:none}
.cmdk{position:fixed;inset:0;z-index:200;display:flex;align-items:flex-start;justify-content:center}
.cmdk-bd{position:absolute;inset:0;background:rgba(0,0,0,.5)}
.cmdk-panel{position:relative;margin-top:12vh;width:min(600px,92vw);max-height:74vh;display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);box-shadow:0 24px 70px rgba(0,0,0,.45);overflow:hidden}
.cmdk-in{width:100%;border:0;border-radius:0;border-bottom:1px solid var(--line);background:transparent;color:var(--ink);font-size:var(--t-md);padding:14px 16px;font-family:inherit}
.cmdk-in:focus,.cmdk-in:focus-visible{outline:none;box-shadow:none}
.cmdk-in::placeholder{color:var(--faint)}
.cmdk-list{flex:1;overflow:auto;padding:6px}
.cmdk-empty{color:var(--muted);font-size:var(--t-body);padding:26px;text-align:center}
.cmdk-sec{font-size:var(--t-xs);color:var(--faint);font-weight:600;letter-spacing:.04em;padding:10px 10px 4px}
.cmdk-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:var(--radius);text-decoration:none;color:var(--ink);cursor:pointer}
.cmdk-item.sel{background:var(--hover)}
.cmdk-ic{flex:none;width:16px;height:16px;display:inline-flex;align-items:center;justify-content:center;color:var(--muted)}
.cmdk-ic svg{width:16px;height:16px}
.cmdk-ic[data-t=go]{color:var(--muted)}
.cmdk-t{flex:1;min-width:0;font-size:var(--t-body);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cmdk-sub{flex:none;max-width:40%;color:var(--muted);font-size:var(--t-sm);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cmdk-foot{display:flex;gap:18px;padding:8px 16px;border-top:1px solid var(--line);background:var(--panel-2);color:var(--muted);font-size:var(--t-sm)}
.cmdk-foot kbd{font-family:var(--mono);background:var(--panel);border:1px solid var(--line);border-radius:var(--radius-sm);padding:0 5px;margin-right:6px;color:var(--ink);font-size:var(--t-xs)}
""" + "".join(f".cmdk-ic[data-t={tp}]{{color:{src.color}}}"     # per-type dot colors FROM the registry
              for tp, src in SEARCH_SOURCES.items())


def palette_markup() -> str:
    """Per-request overlay markup (localised). Static nav commands, group labels, icons
    and the grouping order are all seeded as JSON FROM the coverage registry."""
    cfg = json.dumps({
        "cmds": nav_commands(),
        "labels": {"go": t("cmdk_jump"), **{tp: src.label() for tp, src in SEARCH_SOURCES.items()}},
        "icons": {"go": _picon("arrowRight"), **{tp: _picon(src.icon) for tp, src in SEARCH_SOURCES.items()}},
        "order": ["go", *SEARCH_SOURCES],
    })
    foot = h("div", {"class_": "cmdk-foot"},
             h("span", {}, h("kbd", {}, "↑↓"), t("cmdk_nav")),
             h("span", {}, h("kbd", {}, "↵"), t("cmdk_open")),
             h("span", {}, h("kbd", {}, "esc"), t("cmdk_close")))
    overlay = h("div", {"class_": "cmdk", "id": "cmdk", "hidden": True},
                h("div", {"class_": "cmdk-bd", "data-cmdk-close": True}),
                h("div", {"class_": "cmdk-panel", "role": "dialog", "aria-modal": "true"},
                  h("input", {"id": "cmdk-in", "class_": "cmdk-in", "type": "text", "autocomplete": "off",
                              "spellcheck": "false", "placeholder": t("cmdk_placeholder")}),
                  h("div", {"class_": "cmdk-list", "id": "cmdk-list", "data-empty": t("cmdk_empty")}),
                  foot))
    return overlay + h("script", {"id": "cmdk-cfg", "type": "application/json"}, raw(cfg))


PALETTE_JS = r"""<script>(function(){
var ov=document.getElementById('cmdk'); if(!ov) return;
var inp=document.getElementById('cmdk-in'), list=document.getElementById('cmdk-list');
var CFG={cmds:[],labels:{},order:['go']}; try{ CFG=JSON.parse(document.getElementById('cmdk-cfg').textContent)||CFG; }catch(e){}
var ORDER=CFG.order||['go'];
var items=[], sel=0, timer=null;
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
function open(){ ov.hidden=false; inp.value=''; render(CFG.cmds); inp.focus(); }
function close(){ ov.hidden=true; }
function render(rows){
  if(!rows||!rows.length){ items=[]; sel=0; list.innerHTML='<div class="cmdk-empty">'+esc(list.getAttribute('data-empty'))+'</div>'; return; }
  var groups={}; rows.forEach(function(r){ (groups[r.type]=groups[r.type]||[]).push(r); });
  var ordered=[], html='';
  ORDER.forEach(function(tp){ var g=groups[tp]; if(!g) return;
    html+='<div class="cmdk-sec">'+esc(CFG.labels[tp]||tp)+'</div>';
    g.forEach(function(r){ var i=ordered.length; ordered.push(r);
      html+='<a class="cmdk-item'+(i===0?' sel':'')+'" href="'+esc(r.url)+'" data-i="'+i+'">'
        +'<span class="cmdk-ic" data-t="'+esc(r.type)+'">'+(CFG.icons[r.type]||'')+'</span>'
        +'<span class="cmdk-t">'+esc(r.title)+'</span>'
        +(r.subtitle?'<span class="cmdk-sub">'+esc(r.subtitle)+'</span>':'')+'</a>'; }); });
  items=ordered; sel=0; list.scrollTop=0; list.innerHTML=html;
}
function move(d){ var els=list.querySelectorAll('.cmdk-item'); if(!els.length) return;
  if(els[sel]) els[sel].classList.remove('sel'); sel=(sel+d+els.length)%els.length;
  els[sel].classList.add('sel'); els[sel].scrollIntoView({block:'nearest'}); }
function search(q){ q=(q||'').trim();
  if(!q){ render(CFG.cmds); return; }
  var hits=CFG.cmds.filter(function(c){ return c.title.toLowerCase().indexOf(q.toLowerCase())>=0; });
  fetch('/api/search?q='+encodeURIComponent(q)).then(function(r){return r.json();}).then(function(rows){
    if(ov.hidden) return; render(hits.concat(rows||[])); }).catch(function(){ render(hits); });
}
inp.addEventListener('input',function(){ clearTimeout(timer); var q=inp.value; timer=setTimeout(function(){ search(q); },120); });
inp.addEventListener('keydown',function(e){
  if(e.key==='ArrowDown'){ e.preventDefault(); move(1); }
  else if(e.key==='ArrowUp'){ e.preventDefault(); move(-1); }
  else if(e.key==='Enter'){ e.preventDefault(); var a=list.querySelector('.cmdk-item[data-i="'+sel+'"]'); if(a) a.click(); }
  else if(e.key==='Escape'){ e.preventDefault(); close(); } });
list.addEventListener('click',function(e){ if(e.target.closest&&e.target.closest('.cmdk-item')) close(); });
list.addEventListener('mousemove',function(e){ var a=e.target.closest&&e.target.closest('.cmdk-item'); if(!a) return;
  var i=+a.getAttribute('data-i'); if(i!==sel){ var els=list.querySelectorAll('.cmdk-item'); if(els[sel]) els[sel].classList.remove('sel'); sel=i; a.classList.add('sel'); } });
ov.addEventListener('click',function(e){ if(e.target.hasAttribute('data-cmdk-close')) close(); });
// the sidebar search trigger (under the logo) opens the palette; delegated so it survives SPA swaps
document.addEventListener('click',function(e){ if(e.target.closest&&e.target.closest('[data-cmdk-open]')){ e.preventDefault(); open(); } });
// the '#settings' jump command opens the sidebar's settings popover (no /settings route)
document.addEventListener('click',function(e){
  var a=e.target.closest&&e.target.closest('a[href="#settings"]'); if(!a) return;
  e.preventDefault(); var tg=document.querySelector('.sl-um-trigger'); if(tg) tg.click(); });
window.addEventListener('keydown',function(e){
  if((e.metaKey||e.ctrlKey)&&(e.key==='k'||e.key==='K')){ e.preventDefault(); if(ov.hidden) open(); else close(); }
  else if(e.key==='Escape'&&!ov.hidden){ close(); } });
})();</script>"""
