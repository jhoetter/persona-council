"""Persona calendar grid builders (spec/roadmap.md R2; moved from _routes_pages)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from ._ctx import services, date, timedelta, t, h, fragment


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
