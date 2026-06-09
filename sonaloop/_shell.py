"""sonaloop._shell — VENDORED COPY of the sonaloop-design app-shell behaviour.

Do not edit by hand. Single source of truth: ../sonaloop-design (py/sonaloop_icons/shell.py +
styles/components.css `.sl-app-shell`). Refresh with `make icons` / scripts/sync_icons.sh.
Vendored so the PyPI package has no local-path dependency.


Hand-authored here (like charts.py) and vendored into the Python-SSR app as sonaloop/_shell.py
(see ../../scripts gen + the app's scripts/sync_icons.sh). The CSS lives in styles/components.css
(.sl-app-shell layer); this is just the vanilla-JS behaviour that drives it, so the inspector and
any tsx consumer share ONE shell contract:

  • collapse / expand the sidebar  (persisted; toggled by [data-sidebar-toggle] or the `[` key)
  • drag-resize the sidebar        (the .sl-resize handle writes --sl-sidebar-w; past a threshold it collapses)
  • the bottom user-menu popover   (.sl-um-trigger toggles .is-open / [hidden]; outside-click + Esc close)

Markup contract (emit these from your layout):
  <div class="sl-app-shell" id="...">
    <aside class="sl-sidebar"> <div class="sl-brand">…</div> <div class="sl-sb-scroll">…nav…</div>
      <div class="sl-usermenu"> <div class="sl-um-pop" hidden>…</div>
        <button class="sl-um-trigger">…</button> </div>
    </aside>
    <div class="sl-resize" role="separator"></div>
    <div class="sl-main"> <header class="sl-topbar">
        <button class="sl-iconbtn" data-sidebar-toggle>…</button> …crumbs/actions… </header> …body… </div>
  </div>

State persists under the `sl-shell:*` localStorage keys (shared default with the React AppShell).
"""

# Wrapped in <script> for drop-in next to the page's other scripts.
SHELL_JS: str = r"""<script>(function(){
var MIN=180,MAX=480,HIDE=32;
var app=document.querySelector('.sl-app-shell'); if(!app) return;
var rz=app.querySelector('.sl-resize');
function persist(k,v){ try{localStorage.setItem(k,v);}catch(e){} }
try{ if(localStorage.getItem('sl-shell:open')==='false') app.classList.add('is-collapsed');
     var w=localStorage.getItem('sl-shell:width'); if(w) app.style.setProperty('--sl-sidebar-w',w+'px'); }catch(e){}
function toggle(){ app.classList.toggle('is-collapsed');
  persist('sl-shell:open', String(!app.classList.contains('is-collapsed'))); }
// delegated so it survives an SPA swap of the toggle button
document.addEventListener('click',function(e){ if(e.target.closest&&e.target.closest('[data-sidebar-toggle]')){ e.preventDefault(); toggle(); } });
document.addEventListener('keydown',function(e){ var t=(e.target.tagName||'').toLowerCase();
  if(t==='input'||t==='textarea'||t==='select') return; if(e.key==='['){ e.preventDefault(); toggle(); } });
// bottom user-menu popover
var um=app.querySelector('.sl-usermenu');
if(um){ var umb=um.querySelector('.sl-um-trigger'), ump=um.querySelector('.sl-um-pop');
  function setMenu(open){ um.classList.toggle('is-open',open); if(ump) ump.hidden=!open; if(umb) umb.setAttribute('aria-expanded',String(open)); }
  if(umb) umb.addEventListener('click',function(e){ e.stopPropagation(); setMenu(!um.classList.contains('is-open')); });
  document.addEventListener('click',function(e){ if(um.classList.contains('is-open') && !um.contains(e.target)) setMenu(false); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') setMenu(false); });
}
// drag-resize
if(rz){ var sx=0,sw=248,resizing=false,last=248;
  rz.addEventListener('pointerdown',function(e){ e.preventDefault(); resizing=true; sx=e.clientX;
    sw=parseInt(getComputedStyle(app).getPropertyValue('--sl-sidebar-w'))||248;
    document.body.style.cursor='col-resize'; document.body.style.userSelect='none'; rz.setPointerCapture(e.pointerId); });
  rz.addEventListener('pointermove',function(e){ if(!resizing) return; var next=sw+(e.clientX-sx);
    if(next<=HIDE){ app.classList.add('is-collapsed'); persist('sl-shell:open','false'); }
    else { var c=Math.max(MIN,Math.min(MAX,next)); last=c; app.style.setProperty('--sl-sidebar-w',c+'px');
           app.classList.remove('is-collapsed'); persist('sl-shell:open','true'); } });
  rz.addEventListener('pointerup',function(e){ if(!resizing) return; resizing=false;
    document.body.style.cursor=''; document.body.style.userSelect=''; persist('sl-shell:width',String(last)); });
}
})();</script>"""
