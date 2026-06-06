"""Persona calendar grid builders (spec/roadmap.md R2; moved from _routes_pages)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from ._ctx import services, date, timedelta, t, h, fragment
from .._html import register_css


def _calendar_html(persona_id: str, day: str, blocks: list[dict]) -> str:
    by_hour: dict[int, list[dict]] = {hr: [] for hr in range(7, 20)}
    for block in blocks:
        hour = int(block["calendar_event"]["start"][11:13])
        by_hour.setdefault(hour, []).append(block)
    cells = []
    for hour in range(7, 20):
        cells.append(h("div", {"class_": "hour"}, f"{hour:02d}:00"))
        slot = []
        for block in by_hour.get(hour, []):
            cal = block["calendar_event"]; activity = block.get("activity") or {}
            kind = activity.get("event_type", "focus")
            slot.append(h("a", {"class_": f'block {kind}', "href": f'/activities/{activity.get("id","")}'},
                          h("strong", {}, f'{cal["start"][11:16]}-{cal["end"][11:16]} · {cal["title"]}'),
                          h("span", {"class_": "meta"}, f'{block.get("collaboration_mode") or ""} · {cal["location_or_tool"]}'),
                          h("br"), block.get("persona_thought") or cal["outcome"]))
        cells.append(h("div", {"class_": "slot"}, slot))
    return h("div", {"class_": "calendar"}, cells)


def _calendar_tabs(persona_id: str, selected_date: str, view: str) -> str:
    labels = {"day": t("tab_day"), "week": t("tab_week"), "month": t("tab_month"), "year": t("tab_year")}
    return h("div", {"class_": "tabs"}, [
        h("a", {"class_": "active" if view == tab else "",
                "href": f"/personas/{persona_id}?date={selected_date}&view={tab}"}, labels[tab])
        for tab in ["day", "week", "month", "year"]])


def _event_chip(event: dict) -> str:
    return h("a", {"class_": f'block {event.get("event_type", "focus")}', "href": f'/activities/{event["id"]}'},
             h("strong", {}, f'{event["timestamp"][11:16]} · {event["task"]}'),
             h("span", {"class_": "meta"}, event.get("tool", "")))


def _period_calendar_html(persona_id: str, selected_date: str, view: str, period: dict) -> str:
    if view == "day":
        return _calendar_html(persona_id, selected_date, services.get_calendar(persona_id, selected_date)["blocks"])
    start = date.fromisoformat(period["period_start"]); end = date.fromisoformat(period["period_end"]); days = period["days"]
    if view == "week":
        cells = []; current = start
        while current <= end:
            dk = current.isoformat(); chips = [_event_chip(e) for e in days.get(dk, [])[:4]]
            cells.append(h("div", {"class_": "daycell"}, h("h4", {}, dk),
                           fragment(*chips) if chips else h("p", {"class_": "muted small"}, "—")))
            current += timedelta(days=1)
        return h("div", {"class_": "calendar-grid week"}, cells)
    if view == "month":
        cells = []; current = start
        while current <= end:
            dk = current.isoformat(); evs = days.get(dk, [])
            cells.append(h("div", {"class_": "daycell monthcell"}, h("h4", {}, current.day),
                           h("div", {"class_": "count"}, t("n_events", n=len(evs))),
                           fragment(*(_event_chip(e) for e in evs[:3]))))
            current += timedelta(days=1)
        return h("div", {"class_": "calendar-grid month"}, cells)
    cells = []
    for m in range(1, 13):
        me = [e for dk, evs in days.items() if date.fromisoformat(dk).month == m for e in evs]
        cells.append(h("div", {"class_": "daycell"}, h("h4", {}, f"{start.year}-{m:02d}"),
                       h("div", {"class_": "count"}, t("n_events", n=len(me))),
                       fragment(*(_event_chip(e) for e in me[:2]))))
    return h("div", {"class_": "calendar-grid year"}, cells)

# Co-located CSS (spec/roadmap.md R3): persona calendar grid.
register_css(r"""
/* ---- calendar (kept, var-ized) ---- */
.calendar{display:grid;grid-template-columns:62px 1fr;border:1px solid var(--line);background:var(--panel);border-radius:8px;overflow:hidden}
.calendar-grid{display:grid;gap:8px}.week{grid-template-columns:repeat(7,minmax(0,1fr))}.month{grid-template-columns:repeat(7,minmax(0,1fr))}.year{grid-template-columns:repeat(4,minmax(0,1fr))}
.daycell{min-height:110px;border:1px solid var(--line);border-radius:8px;background:var(--panel);padding:8px}.monthcell{min-height:140px}
.daycell h4{margin:0 0 6px;font-size:var(--t-body)}.count{font-size:var(--t-sm);color:var(--muted)}
.hour{border-top:1px solid var(--line-2);padding:6px 8px;color:var(--muted);font-size:var(--t-sm);min-height:52px}
.slot{border-top:1px solid var(--line-2);min-height:52px;padding:5px 8px}
.calendar .block,.daycell .block{display:block;background:var(--panel-2);border-radius:7px;padding:7px 9px;margin:0 0 6px}.calendar .block::before,.daycell .block::before{content:'';display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--accent);margin-right:8px;vertical-align:1px}
.daycell .block.focus::before,.calendar .block.focus::before{background:var(--green)}.daycell .block.interruption::before,.calendar .block.interruption::before{background:var(--red)}.daycell .block.admin::before,.calendar .block.admin::before{background:var(--amber)}
.block strong{display:block}.block .meta{color:var(--muted);font-size:var(--t-sm)}
.tabs{display:flex;gap:6px;flex-wrap:wrap;margin:14px 0}
.tabs a{border:1px solid var(--line);border-radius:var(--radius-sm);padding:4px 11px;background:var(--panel);font-size:var(--t-sm)}.tabs a.active{background:var(--ink);color:var(--bg)}
input,select{font:inherit;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:6px;padding:6px 8px}
""")
