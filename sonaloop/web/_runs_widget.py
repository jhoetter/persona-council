"""Live "agents running" chrome widget (ticket agents-running-panel).

Self-contained (CSS + markup + JS, the _palette.py pattern), rendered by _layout into
the topbar of every page: a status dot + active-run count, with a small flyout listing
the active runs (project, last activity) and a link to the full /runs page. The dot
turns amber when any project is stalled — the silent failure mode must be loud.

Live updates ride the EXISTING SSE stream: _live.py re-dispatches every /api/events
frame as a `sl:live-event` DOM event; this widget debounces those into a refetch of
/api/runs and re-renders itself. Graceful static fallback: without EventSource the
server-rendered state simply stands (the SSR markup is always complete).

This module also owns collect_run_states() — the one read the /runs page, the widget
and /api/runs all share (deliberately NOT importing any page module, so _components
can import this without a cycle)."""
from __future__ import annotations

import json
from typing import Any

from .._icons import icon as _picon     # direct import avoids a cycle (_components imports this module)
from ..storage import Store
from ._i18n import t
from ._html import h, raw


def collect_run_states(store: Store | None = None) -> dict[str, list[dict[str, Any]]]:
    """Every project's run state (services.project_run_state), grouped by state.
    Projects without a plan (state None) are skipped — there is no driver to show."""
    from .. import services
    store = store or Store()
    out: dict[str, list[dict[str, Any]]] = {"active": [], "stalled": [], "finished": []}
    for p in store.list_research_projects():
        try:
            rs = services.project_run_state(p["id"], store=store)
        except Exception:
            rs = None
        if not rs or rs.get("state") not in out:
            continue
        out[rs["state"]].append({
            "project_id": p["id"], "title": p["title"], "url": f'/projects/{p["id"]}',
            "last_activity": rs.get("last_activity", ""),
            "next_ready": rs.get("next_ready") or [], "note": rs.get("note", "")})
    return out


RUNS_WIDGET_CSS = r"""
.runsw{position:relative;display:inline-flex}
.runsw-btn{display:inline-flex;align-items:center;gap:7px}
.runsw-dot{flex:none;width:7px;height:7px;border-radius:50%;background:var(--faint)}
.runsw.has-active .runsw-dot{background:var(--green,#34a853);animation:livepulse 1.6s ease-out infinite}
.runsw.has-stalled .runsw-dot{background:var(--amber);animation:none}
.runsw-count{font-size:var(--t-sm);color:var(--muted);min-width:10px;text-align:left}
.runsw.has-active .runsw-count{color:var(--ink)}
.runsw-fly{position:absolute;right:0;top:calc(100% + 8px);width:min(320px,86vw);z-index:160;background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);box-shadow:0 14px 40px rgba(0,0,0,.3);padding:6px}
.runsw-fly[hidden]{display:none}
.runsw-h{font-size:var(--t-xs);color:var(--faint);font-weight:600;letter-spacing:.04em;padding:7px 8px 3px}
.runsw-row{display:flex;align-items:center;gap:9px;padding:7px 8px;border-radius:var(--radius-sm);text-decoration:none;color:var(--ink);font-size:var(--t-body)}
.runsw-row:hover{background:var(--hover)}
.runsw-row .runsw-t{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.runsw-row .runsw-ts{flex:none;color:var(--muted);font-size:var(--t-sm)}
.runsw-empty{color:var(--muted);font-size:var(--t-sm);padding:10px 8px}
.runsw-all{display:block;text-align:center;font-size:var(--t-sm);color:var(--accent);text-decoration:none;border-top:1px solid var(--line-2);margin-top:4px;padding:7px 8px 4px}
"""


def _fly_rows(active: list[dict]) -> str:
    rows = [h("a", {"class_": "runsw-row", "href": r["url"]},
              h("span", {"class_": "runsw-t"}, r["title"]),
              h("span", {"class_": "runsw-ts"}, r["last_activity"][:16].replace("T", " ")))
            for r in active]
    if not rows:
        return h("div", {"class_": "runsw-empty"}, t("runs_none_active"))
    return "".join(rows)


def runs_widget_markup(store: Store) -> str:
    """Per-request widget markup (localised, server-rendered with the current counts —
    the static fallback IS the initial state). JS only mutates it on live events."""
    states = collect_run_states(store)
    n_active, n_stalled = len(states["active"]), len(states["stalled"])
    cls = "runsw" + (" has-active" if n_active else "") + (" has-stalled" if n_stalled else "")
    btn = h("button", {"type": "button", "class_": "sl-iconbtn runsw-btn", "data-runsw-toggle": True,
                       "aria-haspopup": "true", "aria-expanded": "false",
                       "title": t("active_runs"), "aria-label": t("active_runs")},
            h("span", {"class_": "runsw-dot"}),
            h("span", {"class_": "runsw-count", "id": "runsw-count"}, str(n_active)))
    fly = h("div", {"class_": "runsw-fly", "id": "runsw-fly", "hidden": True,
                    "data-empty": t("runs_none_active")},
            h("div", {"class_": "runsw-h"}, t("active_runs")),
            h("div", {"id": "runsw-list"}, raw(_fly_rows(states["active"]))),
            h("a", {"class_": "runsw-all", "href": "/runs"},
              raw(_picon("arrowRight")), " ", t("runs_view_all")))
    return h("div", {"class_": cls, "id": "runsw"}, btn, fly)


RUNS_WIDGET_JS = r"""<script>(function(){
if(window.__slRunsWidget) return; window.__slRunsWidget=1;
function el(id){ return document.getElementById(id); }
function esc(s){ return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
// Delegated toggle: the widget lives inside #main, which SPA navigation replaces.
document.addEventListener('click',function(e){
  var b=e.target.closest&&e.target.closest('[data-runsw-toggle]');
  var fly=el('runsw-fly');
  if(b&&fly){ e.preventDefault(); fly.hidden=!fly.hidden; b.setAttribute('aria-expanded',fly.hidden?'false':'true'); return; }
  if(fly&&!fly.hidden&&!(e.target.closest&&e.target.closest('#runsw'))) fly.hidden=true;
});
document.addEventListener('keydown',function(e){ var fly=el('runsw-fly');
  if(e.key==='Escape'&&fly&&!fly.hidden) fly.hidden=true; });
if(!window.EventSource) return;   // static fallback: the server-rendered state stands
function render(d){
  var w=el('runsw'), list=el('runsw-list'), cnt=el('runsw-count'); if(!w||!list||!cnt) return;
  var act=d.active||[], st=d.stalled||[];
  cnt.textContent=String(act.length);
  w.classList.toggle('has-active',act.length>0);
  w.classList.toggle('has-stalled',st.length>0);
  var html='';
  act.forEach(function(r){ html+='<a class="runsw-row" href="'+esc(r.url)+'">'
    +'<span class="runsw-t">'+esc(r.title)+'</span>'
    +'<span class="runsw-ts">'+esc((r.last_activity||'').slice(0,16).replace('T',' '))+'</span></a>'; });
  if(!html){ var fly=el('runsw-fly'); html='<div class="runsw-empty">'+esc(fly?fly.getAttribute('data-empty'):'')+'</div>'; }
  list.innerHTML=html;
}
var t=null;
document.addEventListener('sl:live-event',function(){
  clearTimeout(t); t=setTimeout(function(){
    fetch('/api/runs').then(function(r){return r.json();}).then(render).catch(function(){});
  },400);
});
})();</script>"""
