"""Linear-grade faceted FilterBar (UX U10 + V1, spec/ux-contract.md §8.5/§9 V1) — the SSR
mirror of the design-system <FilterBar> (sonaloop-design/src/components.tsx, proven in the
tracker).

Anatomy (the vendored `.sl-filter-*` + `.sl-popover`/`.sl-menu-item` contracts): a leading
quiet SEARCH slot (`.sl-filter-search` — borderless until focus, hairline-separated; V1:
"filter + suche immer"), a "Filter" toolbar button that opens a two-level facet menu — pick
a facet, then its values as selectable rows with live counts — and every non-empty facet
becomes a removable chip ("Kind is Council, Decision ×") with a trailing Clear action. All
of it ONE wrapping row.

State lives in the URL, never in JS: the search slot is a real GET form (`?q=` — Enter
submits, the current facet params ride along as hidden inputs), and every value row and
chip "×" is a REAL link to the toggled URL (`?kind=council,decision&phase=…` — comma = OR
within a facet, params AND across facets), so a filtered view round-trips, is shareable,
and works without JS down to the link level. The only script is progressive enhancement:
it toggles the menu popover and switches its panels (plus Esc / outside-click dismiss);
without it the popover stays closed but active chips still clear and shared URLs still
render filtered.

The host page owns the MODEL (which facets exist, their options/counts/selection — counted
over the UNFILTERED in-scope rows, exactly like the tracker feeds the React FilterBar) and
applies filter + search server-side; this module owns the chrome.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, quote

from ._components import _icon
from ._html import Safe, h, raw, fragment, register_css
from ._i18n import t


def parse_multi(value: str | None) -> list[str]:
    """One query param -> the facet's selected values (comma = OR), blanks dropped."""
    return [v for v in (value or "").split(",") if v.strip()]


def filter_url(base: str, selected: dict[str, list[str]]) -> str:
    """The canonical filtered URL: `base` (which may already carry fixed params like
    `?tab=assets`) + one comma-joined param per non-empty facet. Deterministic ordering
    (the facet dict's insertion order), so a state always renders the same address."""
    parts = [f"{key}={quote(','.join(vals), safe=',')}" for key, vals in selected.items() if vals]
    if not parts:
        return base
    return base + ("&" if "?" in base else "?") + "&".join(parts)


def _toggled(selected: dict[str, list[str]], key: str, value: str) -> dict[str, list[str]]:
    vals = list(selected.get(key) or [])
    vals = [v for v in vals if v != value] if value in vals else vals + [value]
    out = dict(selected)
    out[key] = vals
    return out


def _without(selected: dict[str, list[str]], key: str) -> dict[str, list[str]]:
    return {k: v for k, v in selected.items() if k != key}


def _option_rows(base: str, facet: dict, selected: dict[str, list[str]]) -> Safe:
    """One facet's value panel: selectable rows (check column · [dot ·] label · live count),
    each a real link to the toggled URL — the `.sl-menu-item` selectable anatomy. An option's
    optional `dot` (a CSS color, e.g. a theme's section color) leads its label."""
    options = facet.get("options") or []
    if not options:
        return h("div", {"class_": "sl-filter-empty"}, t("filter_no_options"))
    sel = selected.get(facet["key"]) or []
    rows = []
    for o in options:
        on = o["value"] in sel
        dot = (h("span", {"class_": "sl-dot", "style": f'background:{o["dot"]}'})
               if o.get("dot") else None)
        rows.append(h("a", {"class_": "sl-menu-item", "aria-pressed": "true" if on else "false",
                            "href": filter_url(base, _toggled(selected, facet["key"], o["value"]))},
                      h("span", {"class_": "sl-menu-item__check"}, raw(_icon("check")) if on else None),
                      h("span", {"class_": "sl-menu-item__label"}, dot, o["label"]),
                      h("span", {"class_": "sl-menu-item__count"}, str(o.get("count", "")))))
    return fragment(*rows)


def _search_form(base: str, search: dict, selected: dict[str, list[str]]) -> Safe:
    """The leading search slot (V1): a real GET form over the vendored `.sl-filter-search`
    contract. The active facet params (and `base`'s own fixed params, e.g. ?tab=) ride along
    as hidden inputs so Enter composes search WITH the filters instead of resetting them."""
    path, _, query = base.partition("?")
    hidden = [h("input", {"type": "hidden", "name": k, "value": v})
              for k, v in parse_qsl(query) if k != "q"]
    hidden += [h("input", {"type": "hidden", "name": k, "value": ",".join(vals)})
               for k, vals in selected.items() if vals]
    ph = search.get("placeholder") or t("search")
    return h("form", {"class_": "sl-filter-search", "method": "get", "action": path or "",
                      "role": "search"},
             raw(_icon("search")),
             h("input", {"class_": "sl-filter-search__input", "type": "search", "name": "q",
                         "value": search.get("value") or None, "placeholder": ph,
                         "aria-label": ph}),
             fragment(*hidden))


def filter_bar(base: str, facets: list[dict], selected: dict[str, list[str]],
               search: dict | None = None) -> Safe:
    """The bar. `facets`: [{key, label, icon, options: [{value, label, count, dot?}]}, …] —
    the page's honest model (only values that actually occur; counts over the unfiltered set).
    `selected`: {facet key -> [values]} parsed from the URL. `search`: {value, placeholder}
    renders the leading `.sl-filter-search` slot (V1 — search is PART of the filter contract);
    `base` must already carry an active `?q=` so the facet links round-trip it. Returns ""
    when there is nothing to filter (no facet has options), nothing is selected and no
    search slot was asked for."""
    facets = [f for f in facets if f.get("options")]
    active = [f for f in facets if selected.get(f["key"])]
    if not facets and not any(selected.values()) and search is None:
        return raw("")
    label_of = {f["key"]: {o["value"]: o["label"] for o in (f.get("options") or [])} for f in facets}

    # the two-level menu: the facet list panel (data-flt-panel="") + one value panel per facet
    panels = [h("div", {"data-flt-panel": ""},
                fragment(*(h("button", {"class_": "sl-menu-item", "type": "button",
                                        "data-flt-open": f["key"]},
                            raw(_icon(f.get("icon", "filter"))),
                            h("span", {"class_": "sl-menu-item__label"}, f["label"]))
                           for f in facets)))]
    for f in facets:
        panels.append(h("div", {"data-flt-panel": f["key"], "hidden": True},
                        h("button", {"class_": "sl-filter-back", "type": "button",
                                     "data-flt-open": ""}, "← ", f["label"]),
                        _option_rows(base, f, selected)))
    trigger = h("span", {"class_": "sl-popover-wrap"},
                h("button", {"class_": "sl-toolbtn", "type": "button", "data-flt-toggle": True,
                             "aria-haspopup": "true", "aria-expanded": "false"},
                  raw(_icon("filter")), t("filter_h")),
                h("div", {"class_": "sl-popover sl-popover--bottom-start", "hidden": True},
                  fragment(*panels)))

    chips = []
    for f in active:
        vals = selected[f["key"]]
        summary = ", ".join(str(label_of.get(f["key"], {}).get(v, v)) for v in vals)
        chips.append(h("span", {"class_": "sl-filter-chip"},
                       h("button", {"class_": "sl-filter-chip__body", "type": "button",
                                    "data-flt-chip": f["key"]},
                         h("span", {"class_": "sl-filter-chip__key"}, f["label"]),
                         h("span", {"class_": "sl-filter-chip__op"}, t("filter_is")),
                         h("span", {"class_": "sl-filter-chip__val"}, summary)),
                       h("a", {"class_": "sl-filter-chip__x",
                               "href": filter_url(base, _without(selected, f["key"])),
                               "aria-label": f'{t("clear_filter")} · {f["label"]}'},
                         raw(_icon("close")))))
    clear = (h("a", {"class_": "sl-filter-clear", "href": base}, t("clear_filter"))
             if any(selected.values()) else None)
    search_html = _search_form(base, search, selected) if search is not None else None
    return fragment(h("div", {"class_": "sl-filter-bar", "data-filterbar": True},
                      search_html, trigger, fragment(*chips), clear), raw(_FB_JS))


def empty_filter_state(clear_href: str) -> Safe:
    """The teaching empty result (C8/F1): filters matched nothing — say so and offer the way
    out. Shared by the outline and the Library so the moment reads identically everywhere."""
    return h("div", {"class_": "sl-empty"},
             h("div", {"class_": "sl-empty__icon"}, raw(_icon("filter"))),
             h("h2", {"class_": "sl-empty__title"}, t("filter_no_matches_h")),
             h("p", {"class_": "sl-empty__body"}, t("filter_no_matches")),
             h("a", {"class_": "sl-btn", "href": clear_href}, t("clear_filter")))


# Progressive enhancement only (state lives in the URL): toggle the popover, switch the
# two-level panels, open a chip's value panel, Esc/outside-click dismiss. Idempotent —
# one delegated listener regardless of how many bars a page renders.
_FB_JS = """
<script>(function(){if(window.__slfb)return;window.__slfb=1;
function panel(pop,key){pop.querySelectorAll('[data-flt-panel]').forEach(function(p){
  p.hidden=p.getAttribute('data-flt-panel')!==key;});}
function close(){document.querySelectorAll('[data-filterbar] .sl-popover').forEach(function(p){p.hidden=true;});
  document.querySelectorAll('[data-flt-toggle]').forEach(function(b){b.setAttribute('aria-expanded','false');});}
document.addEventListener('click',function(e){
  var t=e.target.closest&&e.target.closest('[data-flt-toggle],[data-flt-open],[data-flt-chip]');
  if(!t){if(!(e.target.closest&&e.target.closest('[data-filterbar] .sl-popover')))close();return;}
  var bar=t.closest('[data-filterbar]');if(!bar)return;
  var pop=bar.querySelector('.sl-popover');if(!pop)return;
  if(t.hasAttribute('data-flt-toggle')){var open=pop.hidden;close();pop.hidden=!open;
    t.setAttribute('aria-expanded',String(open));if(open)panel(pop,'');}
  else if(t.hasAttribute('data-flt-open')){panel(pop,t.getAttribute('data-flt-open'));}
  else{close();pop.hidden=false;panel(pop,t.getAttribute('data-flt-chip'));}
});
document.addEventListener('keydown',function(e){if(e.key==='Escape')close();});
})();</script>
"""

# Bar spacing + menu sizing on top of the vendored chrome (.sl-filter-*, .sl-popover): the
# value panels can be long (personas), so the popover scrolls; the bar sits quietly between
# the page head and the rows it filters.
register_css(
    ".sl-filter-bar{margin:10px 0 2px}"
    ".sl-filter-bar .sl-popover{min-width:230px;max-height:340px;overflow:auto}"
    ".sl-filter-bar .sl-menu-item__label .sl-dot{flex:none}")
