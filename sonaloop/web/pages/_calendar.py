"""Persona calendar — week (agenda columns), month (weekday grid), year (activity heatmap).

A persona's calendar visualises LIVED activity (a handful of events/day + a daily mood), not a
scheduling tool — so the views favour density + at-a-glance rhythm over a time-grid. The day view is
retired. Design follows the Linear/Notion-Calendar language: one accent, hairline grids (via a
1px-gap on a line-coloured container), muted out-of-scope days, today as a filled disc / accent ring.
"""
from __future__ import annotations

from datetime import date, timedelta

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from ._ctx import services, t, h, fragment

_EVT = {"meeting": "meeting", "focus": "focus", "admin": "admin", "interruption": "interruption",
        "decision": "meeting", "site_visit": "focus"}


# Day/month names follow the UI language — ONE comma-joined i18n key per table
# (cal_wd_short / cal_mon_short / cal_mon_long), split per request.
def _wd() -> list[str]:
    return t("cal_wd_short").split(",")


def _mon() -> list[str]:
    return t("cal_mon_short").split(",")


def _monf() -> list[str]:
    return t("cal_mon_long").split(",")


_POS = {"zufrieden", "produktiv", "fokussiert", "positiv", "gut"}
_NEG = {"gehetzt", "müde", "muede", "angespannt", "gestresst", "negativ", "erschöpft"}


def _evt_cls(ev: dict) -> str:
    return _EVT.get(ev.get("event_type", "focus"), "focus")


def _mood_cls(mood: str) -> str:
    m = (mood or "").strip().lower()
    return "pos" if m in _POS else "neg" if m in _NEG else "neu" if m else ""


def _today() -> str:
    try:
        return date.today().isoformat()
    except Exception:                      # date.today is unavailable in some harness contexts
        return ""


def _shift(a: date, view: str, delta: int) -> date:
    if view == "week":
        return a + timedelta(days=7 * delta)
    if view == "year":
        return a.replace(year=a.year + delta)
    m = a.month - 1 + delta                                  # month: jump whole months, land on the 1st
    return date(a.year + m // 12, m % 12 + 1, 1)


def _period_title(view: str, period: dict) -> str:
    s = date.fromisoformat(period["period_start"]); e = date.fromisoformat(period["period_end"])
    monf = _monf()
    if view == "year":
        return str(s.year)
    if view == "week":
        if s.month == e.month:
            return f"{s.day}.–{e.day}. {monf[s.month-1]} {s.year}"
        return f"{s.day}. {monf[s.month-1]} – {e.day}. {monf[e.month-1]} {e.year}"
    return f"{monf[s.month-1]} {s.year}"


def _calendar_tabs(persona_id: str, selected_date: str, view: str, period: dict) -> str:
    """Calendar header: ‹ / today / › date navigation + the current-period title + the view switcher."""
    a = date.fromisoformat(period.get("anchor_date", selected_date))
    prev, nxt = _shift(a, view, -1).isoformat(), _shift(a, view, 1).isoformat()
    def go(d: str) -> str:
        return f"/personas/{persona_id}?date={d}&view={view}"
    labels = {"week": t("tab_week"), "month": t("tab_month"), "year": t("tab_year")}
    tabs = [h("a", {"class_": "sl-tab" + (" is-active" if view == tab else ""),
                    "href": f"/personas/{persona_id}?date={selected_date}&view={tab}"}, labels[tab])
            for tab in ["week", "month", "year"]]
    return h("div", {"class_": "sl-cal-nav"},
             h("div", {"class_": "sl-cal-nav-l"},
               h("a", {"class_": "sl-cal-arrow", "href": go(prev), "aria-label": t("pager_prev")}, "‹"),
               h("a", {"class_": "sl-cal-arrow", "href": go(nxt), "aria-label": t("pager_next")}, "›"),
               h("a", {"class_": "sl-cal-today", "href": go(_today())}, t("today")),
               h("span", {"class_": "sl-cal-title"}, _period_title(view, period))),
             h("div", {"class_": "sl-tabs sl-tabs--pill"}, *tabs))


def _event_chip(event: dict) -> str:                          # used in week + month cells
    tm = event.get("timestamp", "")[11:16]
    return h("a", {"class_": f'sl-cev {_evt_cls(event)}', "href": f'/activities/{event.get("id","")}',
                   "title": f'{tm} · {event.get("task","")}'},
             h("span", {"class_": "sl-cev-t"}, tm), event.get("task", ""))


def _week_html(persona_id: str, period: dict, summaries: dict) -> str:
    start = date.fromisoformat(period["period_start"]); days = period["days"]; today = _today()
    cols = []
    for i in range(7):
        d = start + timedelta(days=i); dk = d.isoformat()
        evs = sorted(days.get(dk, []), key=lambda e: e.get("timestamp", ""))
        mood = summaries.get(dk, "")
        head = h("div", {"class_": "sl-cw-h" + (" today" if dk == today else "") + (" we" if i >= 5 else "")},
                 h("div", {"class_": "sl-cw-wd"}, _wd()[i]),
                 h("div", {"class_": "sl-cw-d"}, str(d.day)),
                 h("span", {"class_": f"sl-cw-mood {_mood_cls(mood)}", "title": mood}) if mood else "")
        body = (fragment(*(_event_chip(e) for e in evs)) if evs
                else h("div", {"class_": "sl-cw-empty"}, "—"))
        cols.append(h("div", {"class_": "sl-cw-col" + (" we" if i >= 5 else "")}, head,
                     h("div", {"class_": "sl-cw-body"}, body)))
    return h("div", {"class_": "sl-cal-week"}, *cols)


def _month_html(persona_id: str, period: dict, summaries: dict, anchor: date) -> str:
    first = date.fromisoformat(period["period_start"]); last = date.fromisoformat(period["period_end"])
    days = period["days"]; today = _today()
    grid_start = first - timedelta(days=first.weekday())          # Monday on/before the 1st
    grid_end = last + timedelta(days=(6 - last.weekday()))        # Sunday on/after the last
    wd = _wd()
    cells = [h("div", {"class_": "sl-cm-wd" + (" we" if i >= 5 else "")}, wd[i]) for i in range(7)]
    d = grid_start
    while d <= grid_end:
        dk = d.isoformat(); out = d.month != anchor.month; we = d.weekday() >= 5
        evs = sorted(days.get(dk, []), key=lambda e: e.get("timestamp", ""))
        shown = [_event_chip(e) for e in evs[:3]]
        more = (h("a", {"class_": "sl-cm-more", "href": f"/personas/{persona_id}?date={dk}&view=week"},
                 t("n_more", n=len(evs) - 3)) if len(evs) > 3 else "")
        mood = summaries.get(dk, "")
        num_cls = "sl-cm-num" + (" today" if dk == today else "")
        cells.append(h("div", {"class_": "sl-cm-cell" + (" out" if out else "") + (" we" if we and not out else "")},
                       h("div", {"class_": num_cls}, str(d.day)),
                       fragment(*shown), more,
                       h("span", {"class_": f"sl-cm-mood {_mood_cls(mood)}"}) if (mood and not out) else ""))
        d += timedelta(days=1)
    return h("div", {"class_": "sl-cal-month"}, *cells)


def _year_html(persona_id: str, period: dict, anchor: date) -> str:
    """GitHub-style 53×7 activity heatmap — fill intensity = events that day; today = accent ring."""
    days = period["days"]; year = anchor.year; today = _today()
    jan1 = date(year, 1, 1); dec31 = date(year, 12, 31)
    grid_start = jan1 - timedelta(days=jan1.weekday())           # pad to a Monday so columns align
    n_weeks = ((dec31 - grid_start).days // 7) + 1
    # cells in column-major order (Mon→Sun per week) so grid-auto-flow:column lays them out right
    cells = []
    d = grid_start
    for _ in range(n_weeks * 7):
        if d < jan1 or d > dec31:
            cells.append(h("span", {"class_": "sl-cy-cell empty"}))
        else:
            n = len(days.get(d.isoformat(), []))
            lvl = 0 if n == 0 else 1 if n == 1 else 2 if n == 2 else 3 if n <= 4 else 4
            cls = f"sl-cy-cell l{lvl}" + (" today" if d.isoformat() == today else "")
            cells.append(h("a", {"class_": cls, "href": f"/personas/{persona_id}?date={d.isoformat()}&view=week",
                                 "title": f"{d.day}. {_mon()[d.month-1]} · {t('n_events', n=n)}"}))
        d += timedelta(days=1)
    # month labels: place each at the column where its 1st day falls
    mlabels = []
    for m in range(1, 13):
        col = (date(year, m, 1) - grid_start).days // 7
        mlabels.append(h("span", {"class_": "sl-cy-mon", "style": f"grid-column:{col+1}"}, _mon()[m - 1]))
    wd = _wd()
    wdcol = h("div", {"class_": "sl-cy-wd"}, *[h("span", {}, wd[i] if i in (0, 2, 4, 6) else "") for i in range(7)])
    legend = h("div", {"class_": "sl-cy-legend"}, h("span", {}, t("less")),
               *[h("span", {"class_": f"sl-cy-swatch l{l}"}) for l in range(5)], h("span", {}, t("more")))
    main = h("div", {"class_": "sl-cy-main"},
             h("div", {"class_": "sl-cy-mons", "style": f"grid-template-columns:repeat({n_weeks},11px)"}, *mlabels),
             h("div", {"class_": "sl-cy-grid"}, *cells))
    # legend lives OUTSIDE the horizontally-scrolling grid so it never clips/overlaps the weekday rail
    return fragment(h("div", {"class_": "sl-cal-year"}, wdcol, main), legend)


def _period_calendar_html(persona_id: str, selected_date: str, view: str, period: dict) -> str:
    summaries = {s["date"]: s.get("mood", "") for s in period.get("daily_summaries", [])}
    anchor = date.fromisoformat(period.get("anchor_date", selected_date))
    if view == "week":
        return _week_html(persona_id, period, summaries)
    if view == "year":
        return _year_html(persona_id, period, anchor)
    return _month_html(persona_id, period, summaries, anchor)


# Co-located CSS (spec/roadmap.md R3). One color language across views: activity-type accent, a mood
# tick (pos/neg/neutral), hairline grids via 1px gap on a line-coloured container.
