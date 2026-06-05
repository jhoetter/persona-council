"""Cmd+K command palette: global jump across every entity + nav commands.

Self-contained (CSS + markup + JS), injected once by _layout so it works on every
page. Kept out of web_assets.py to respect the per-file LOC bar. The result list is
rendered client-side from /api/search; static nav commands are seeded in the markup."""
from __future__ import annotations

import json

from ._i18n import t


PALETTE_CSS = r"""
.cmdk[hidden]{display:none}
.cmdk{position:fixed;inset:0;z-index:200;display:flex;align-items:flex-start;justify-content:center}
.cmdk-bd{position:absolute;inset:0;background:rgba(0,0,0,.45)}
.cmdk-panel{position:relative;margin-top:13vh;width:min(640px,92vw);background:var(--panel);border:1px solid var(--line);border-radius:14px;box-shadow:0 24px 60px rgba(0,0,0,.4);overflow:hidden}
.cmdk-in{width:100%;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--ink);font-size:16px;padding:16px 18px;outline:none;font-family:inherit}
.cmdk-list{max-height:min(56vh,440px);overflow:auto;padding:6px}
.cmdk-empty{color:var(--muted);font-size:13px;padding:18px;text-align:center}
.cmdk-item{display:flex;align-items:center;gap:11px;padding:9px 12px;border-radius:9px;text-decoration:none;color:var(--ink);cursor:pointer}
.cmdk-item.sel{background:var(--accent-weak)}
.cmdk-type{flex:none;font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);border:1px solid var(--line);border-radius:6px;padding:2px 7px;min-width:66px;text-align:center}
.cmdk-t{flex:1;min-width:0;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cmdk-sub{flex:none;max-width:38%;color:var(--muted);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
"""


def palette_markup() -> str:
    """Per-request overlay markup (localised). Static nav commands are seeded as JSON."""
    cmds = json.dumps([
        {"title": t("projects"), "url": "/projects", "type": "go"},
        {"title": t("personas"), "url": "/personas", "type": "go"},
    ])
    return (
        '<div class="cmdk" id="cmdk" hidden>'
        '<div class="cmdk-bd" data-cmdk-close></div>'
        '<div class="cmdk-panel" role="dialog" aria-modal="true">'
        f'<input id="cmdk-in" class="cmdk-in" type="text" autocomplete="off" spellcheck="false" placeholder="{t("cmdk_placeholder")}">'
        f'<div class="cmdk-list" id="cmdk-list" data-empty="{t("cmdk_empty")}"></div>'
        '</div></div>'
        f'<script id="cmdk-cmds" type="application/json">{cmds}</script>'
    )


PALETTE_JS = r"""<script>(function(){
var ov=document.getElementById('cmdk'); if(!ov) return;
var inp=document.getElementById('cmdk-in'), list=document.getElementById('cmdk-list');
var cmds=[]; try{ cmds=JSON.parse(document.getElementById('cmdk-cmds').textContent)||[]; }catch(e){}
var items=[], sel=0, timer=null;
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
function open(){ ov.hidden=false; inp.value=''; render(cmds); inp.focus(); }
function close(){ ov.hidden=true; }
function render(rows){ items=rows||[]; sel=0;
  if(!items.length){ list.innerHTML='<div class="cmdk-empty">'+esc(list.getAttribute('data-empty'))+'</div>'; return; }
  list.innerHTML=items.map(function(r,i){
    return '<a class="cmdk-item'+(i===0?' sel':'')+'" href="'+esc(r.url)+'" data-i="'+i+'">'
      +'<span class="cmdk-type">'+esc(r.type)+'</span>'
      +'<span class="cmdk-t">'+esc(r.title)+'</span>'
      +(r.subtitle?'<span class="cmdk-sub">'+esc(r.subtitle)+'</span>':'')+'</a>'; }).join('');
}
function move(d){ var els=list.querySelectorAll('.cmdk-item'); if(!els.length) return;
  if(els[sel]) els[sel].classList.remove('sel'); sel=(sel+d+els.length)%els.length;
  els[sel].classList.add('sel'); els[sel].scrollIntoView({block:'nearest'}); }
function search(q){ q=(q||'').trim();
  if(!q){ render(cmds); return; }
  var hits=cmds.filter(function(c){ return c.title.toLowerCase().indexOf(q.toLowerCase())>=0; });
  fetch('/api/search?q='+encodeURIComponent(q)).then(function(r){return r.json();}).then(function(rows){
    if(ov.hidden) return; render(hits.concat(rows||[])); }).catch(function(){ render(hits); });
}
inp.addEventListener('input',function(){ clearTimeout(timer); var q=inp.value; timer=setTimeout(function(){ search(q); },120); });
inp.addEventListener('keydown',function(e){
  if(e.key==='ArrowDown'){ e.preventDefault(); move(1); }
  else if(e.key==='ArrowUp'){ e.preventDefault(); move(-1); }
  else if(e.key==='Enter'){ e.preventDefault(); if(items[sel]) location.href=items[sel].url; }
  else if(e.key==='Escape'){ e.preventDefault(); close(); } });
list.addEventListener('mousemove',function(e){ var a=e.target.closest&&e.target.closest('.cmdk-item'); if(!a) return;
  var i=+a.getAttribute('data-i'); if(i!==sel){ var els=list.querySelectorAll('.cmdk-item'); if(els[sel]) els[sel].classList.remove('sel'); sel=i; a.classList.add('sel'); } });
ov.addEventListener('click',function(e){ if(e.target.hasAttribute('data-cmdk-close')) close(); });
window.addEventListener('keydown',function(e){
  if((e.metaKey||e.ctrlKey)&&(e.key==='k'||e.key==='K')){ e.preventDefault(); if(ov.hidden) open(); else close(); }
  else if(e.key==='Escape'&&!ov.hidden){ close(); } });
})();</script>"""
