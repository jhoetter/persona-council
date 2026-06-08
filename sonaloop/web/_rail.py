"""A reusable right-edge section MINIMAP rail (the synthesis TOC, generalised to any detail page).

Self-contained: carries its own scoped CSS + scrollspy JS, so adding it to a page is one call. Only the
HOVERED tick's label shows (no overlap). Items: a list of (anchor_id, label); needs >=2 to render.
"""
from __future__ import annotations

from ._i18n import t
from ._components import _esc  # noqa: F401
from ._html import h, raw

_RAIL_CSS = """<style>
.pgrail{position:fixed;right:18px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:9px;z-index:40;padding:10px 4px;align-items:flex-end}
.pgrail .tick{display:flex;align-items:center;justify-content:flex-end;gap:10px;height:6px;text-decoration:none}
.pgrail .tk-bar{width:18px;height:2px;border-radius:2px;background:var(--ink);opacity:.30;transition:width .14s,opacity .14s,background .14s}
.pgrail .tick:hover .tk-bar{opacity:.75;width:28px}
.pgrail .tick.active .tk-bar{opacity:1;width:28px;background:var(--accent)}
.pgrail .tk-label{font-size:var(--t-sm);color:var(--ink);background:var(--panel);border:1px solid var(--line);border-radius:var(--radius-sm);padding:3px 10px;white-space:nowrap;opacity:0;transform:translateX(8px);transition:opacity .14s,transform .14s;pointer-events:none;box-shadow:0 6px 20px rgba(0,0,0,.12)}
.pgrail .tick:hover .tk-label{opacity:1;transform:none}
.pgrail .tick.active .tk-label{color:var(--accent);border-color:var(--accent)}
@media(max-width:1560px){.pgrail{display:none}}/* show the minimap only once there's margin beside the right aside */
</style>"""

_RAIL_JS = """<script>(function(){
var sc=document.querySelector('.main');
var ticks=[].slice.call(document.querySelectorAll('.pgrail .tick'));
if(!ticks.length)return;
var map={};ticks.forEach(function(a){map[a.getAttribute('href').slice(1)]=a;});
var obs=new IntersectionObserver(function(es){es.forEach(function(en){
var el=map[en.target.id];if(en.isIntersecting&&el){ticks.forEach(function(t){t.classList.remove('active');});el.classList.add('active');}});},
{root:sc||null,rootMargin:'0px 0px -72% 0px',threshold:0});
ticks.forEach(function(a){var el=document.getElementById(a.getAttribute('href').slice(1));if(el)obs.observe(el);});
})();</script>"""


def _page_rail(items: list[tuple[str, str]]) -> str:
    items = [(i, l) for i, l in (items or []) if i and l]
    if len(items) < 2:
        return ""
    ticks = [h("a", {"class_": "tick", "href": f"#{i}"},
               h("span", {"class_": "tk-label"}, l), h("span", {"class_": "tk-bar"}))
             for i, l in items]
    nav = h("nav", {"class_": "pgrail", "aria-label": t("sections")}, ticks)
    return raw(_RAIL_CSS) + nav + raw(_RAIL_JS)
