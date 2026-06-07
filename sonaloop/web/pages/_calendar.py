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
from .._html import register_css

_EVT = {"meeting": "meeting", "focus": "focus", "admin": "admin", "interruption": "interruption",
        "decision": "meeting", "site_visit": "focus"}
_WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
_MON = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"]
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


def _calendar_tabs(persona_id: str, selected_date: str, view: str) -> str:
    labels = {"week": t("tab_week"), "month": t("tab_month"), "year": t("tab_year")}
    return h("div", {"class_": "cal-tabs"}, [
        h("a", {"class_": "active" if view == tab else "",
                "href": f"/personas/{persona_id}?date={selected_date}&view={tab}"}, labels[tab])
        for tab in ["week", "month", "year"]])


def _event_chip(event: dict) -> str:                          # used in week + month cells
    tm = event.get("timestamp", "")[11:16]
    return h("a", {"class_": f'cev {_evt_cls(event)}', "href": f'/activities/{event.get("id","")}',
                   "title": f'{tm} · {event.get("task","")}'},
             h("span", {"class_": "cev-t"}, tm), event.get("task", ""))


def _week_html(persona_id: str, period: dict, summaries: dict) -> str:
    start = date.fromisoformat(period["period_start"]); days = period["days"]; today = _today()
    cols = []
    for i in range(7):
        d = start + timedelta(days=i); dk = d.isoformat()
        evs = sorted(days.get(dk, []), key=lambda e: e.get("timestamp", ""))
        mood = summaries.get(dk, "")
        head = h("div", {"class_": "cw-h" + (" today" if dk == today else "") + (" we" if i >= 5 else "")},
                 h("div", {"class_": "cw-wd"}, _WD[i]),
                 h("div", {"class_": "cw-d"}, str(d.day)),
                 h("span", {"class_": f"cw-mood {_mood_cls(mood)}", "title": mood}) if mood else "")
        body = (fragment(*(_event_chip(e) for e in evs)) if evs
                else h("div", {"class_": "cw-empty"}, "—"))
        cols.append(h("div", {"class_": "cw-col" + (" we" if i >= 5 else "")}, head,
                     h("div", {"class_": "cw-body"}, body)))
    return h("div", {"class_": "cal-week"}, *cols)


def _month_html(persona_id: str, period: dict, summaries: dict, anchor: date) -> str:
    first = date.fromisoformat(period["period_start"]); last = date.fromisoformat(period["period_end"])
    days = period["days"]; today = _today()
    grid_start = first - timedelta(days=first.weekday())          # Monday on/before the 1st
    grid_end = last + timedelta(days=(6 - last.weekday()))        # Sunday on/after the last
    cells = [h("div", {"class_": "cm-wd" + (" we" if i >= 5 else "")}, _WD[i]) for i in range(7)]
    d = grid_start
    while d <= grid_end:
        dk = d.isoformat(); out = d.month != anchor.month; we = d.weekday() >= 5
        evs = sorted(days.get(dk, []), key=lambda e: e.get("timestamp", ""))
        shown = [_event_chip(e) for e in evs[:3]]
        more = (h("a", {"class_": "cm-more", "href": f"/personas/{persona_id}?date={dk}&view=week"},
                 t("n_more", n=len(evs) - 3)) if len(evs) > 3 else "")
        mood = summaries.get(dk, "")
        num_cls = "cm-num" + (" today" if dk == today else "")
        cells.append(h("div", {"class_": "cm-cell" + (" out" if out else "") + (" we" if we and not out else "")},
                       h("div", {"class_": num_cls}, str(d.day)),
                       fragment(*shown), more,
                       h("span", {"class_": f"cm-mood {_mood_cls(mood)}"}) if (mood and not out) else ""))
        d += timedelta(days=1)
    return h("div", {"class_": "cal-month"}, *cells)


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
            cells.append(h("span", {"class_": "cy-cell empty"}))
        else:
            n = len(days.get(d.isoformat(), []))
            lvl = 0 if n == 0 else 1 if n == 1 else 2 if n == 2 else 3 if n <= 4 else 4
            cls = f"cy-cell l{lvl}" + (" today" if d.isoformat() == today else "")
            cells.append(h("a", {"class_": cls, "href": f"/personas/{persona_id}?date={d.isoformat()}&view=week",
                                 "title": f"{d.day}. {_MON[d.month-1]} · {t('n_events', n=n)}"}))
        d += timedelta(days=1)
    # month labels: place each at the column where its 1st day falls
    mlabels = []
    for m in range(1, 13):
        col = (date(year, m, 1) - grid_start).days // 7
        mlabels.append(h("span", {"class_": "cy-mon", "style": f"grid-column:{col+1}"}, _MON[m - 1]))
    wdcol = h("div", {"class_": "cy-wd"}, *[h("span", {}, _WD[i] if i in (0, 2, 4, 6) else "") for i in range(7)])
    legend = h("div", {"class_": "cy-legend"}, t("less"),
               *[h("span", {"class_": f"cy-cell l{l}"}) for l in range(5)], t("more"))
    main = h("div", {"class_": "cy-main"},
             h("div", {"class_": "cy-mons", "style": f"grid-template-columns:repeat({n_weeks},11px)"}, *mlabels),
             h("div", {"class_": "cy-grid"}, *cells), legend)
    return h("div", {"class_": "cal-year"}, wdcol, main)


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
register_css(r"""
.cal-tabs{display:inline-flex;gap:2px;background:var(--panel-2);border:1px solid var(--line);border-radius:8px;padding:2px;margin:14px 0}
.cal-tabs a{border-radius:6px;padding:4px 13px;font-size:var(--t-sm);color:var(--muted);font-weight:500}
.cal-tabs a:hover{color:var(--ink)}
.cal-tabs a.active{background:var(--panel);color:var(--ink);box-shadow:0 1px 2px rgba(0,0,0,.06)}
/* event chip (week + month) — soft fill, leading type-coloured rule */
.cev{display:flex;align-items:baseline;gap:6px;border-left:2.5px solid var(--accent);background:var(--panel-2);border-radius:4px;padding:2px 7px;font-size:var(--t-xs);color:var(--ink);line-height:1.45;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cev .cev-t{color:var(--muted);font-variant-numeric:tabular-nums;flex:none}
.cev.focus{border-left-color:var(--green)}.cev.admin{border-left-color:var(--amber)}.cev.interruption{border-left-color:var(--red)}.cev.meeting{border-left-color:var(--accent)}
.cev:hover{background:var(--hover)}
/* ---- WEEK: 7 agenda columns ---- */
.cal-week{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.cw-col{background:var(--panel);min-height:300px}.cw-col.we{background:var(--panel-2)}
.cw-h{padding:8px 6px 9px;text-align:center;border-bottom:1px solid var(--line);position:relative}
.cw-wd{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600}
.cw-d{font-size:var(--t-md);font-weight:550;margin-top:3px;color:var(--ink)}
.cw-h.today .cw-d{background:var(--accent);color:#fff;width:24px;height:24px;line-height:24px;border-radius:50%;margin:3px auto 0}
.cw-mood{position:absolute;top:9px;right:9px;width:7px;height:7px;border-radius:50%;background:var(--muted)}
.cw-mood.pos{background:var(--green)}.cw-mood.neg{background:var(--amber)}.cw-mood.neu{background:var(--line-2)}
.cw-body{padding:8px;display:flex;flex-direction:column;gap:5px}
.cw-empty{color:var(--faint);font-size:var(--t-sm);text-align:center;padding-top:10px}
/* ---- MONTH: weekday grid ---- */
.cal-month{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.cm-wd{background:var(--panel);padding:7px 8px;font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600}
.cm-wd.we{color:var(--faint)}
.cm-cell{background:var(--panel);min-height:108px;padding:6px 7px 9px;position:relative;display:flex;flex-direction:column;gap:3px}
.cm-cell.out{background:var(--bg)}.cm-cell.we{background:var(--panel-2)}
.cm-num{font-size:var(--t-sm);font-weight:500;color:var(--ink);align-self:flex-start}
.cm-cell.out .cm-num{color:var(--faint)}
.cm-num.today{background:var(--accent);color:#fff;min-width:21px;height:21px;line-height:21px;text-align:center;border-radius:50%}
.cm-more{font-size:var(--t-xs);color:var(--muted)}.cm-more:hover{color:var(--accent)}
.cm-mood{position:absolute;left:0;right:0;bottom:0;height:2px;background:var(--line-2)}
.cm-mood.pos{background:var(--green)}.cm-mood.neg{background:var(--amber)}.cm-mood.neu{background:var(--line-2)}
/* ---- YEAR: activity heatmap ---- */
.cal-year{display:flex;gap:9px;align-items:flex-start;overflow-x:auto;padding:6px 2px 2px}
.cy-wd{display:grid;grid-template-rows:repeat(7,11px);gap:3px;padding-top:18px}
.cy-wd span{font-size:9px;line-height:11px;height:11px;color:var(--muted)}
.cy-main{min-width:0}
.cy-mons{display:grid;gap:3px;height:14px;margin-bottom:4px}
.cy-mon{font-size:var(--t-xs);color:var(--muted);font-weight:500;white-space:nowrap}
.cy-grid{display:grid;grid-template-rows:repeat(7,11px);grid-auto-flow:column;grid-auto-columns:11px;gap:3px}
.cy-cell{width:11px;height:11px;border-radius:3px;background:var(--cal-h0);display:block}
a.cy-cell:hover{outline:1.5px solid var(--accent);outline-offset:1px}
.cy-cell.empty{background:transparent}
.cy-cell.l0{background:var(--cal-h0)}.cy-cell.l1{background:var(--cal-h1)}.cy-cell.l2{background:var(--cal-h2)}.cy-cell.l3{background:var(--cal-h3)}.cy-cell.l4{background:var(--cal-h4)}
.cy-cell.today{box-shadow:0 0 0 1.5px var(--accent)}
.cy-legend{display:flex;align-items:center;gap:4px;margin-top:12px;font-size:var(--t-xs);color:var(--muted)}
.cy-legend .cy-cell{margin:0 1px}
:root{--cal-h0:#eceef1;--cal-h1:#bfe3cf;--cal-h2:#86cda6;--cal-h3:#46ad77;--cal-h4:#1f7d4d}
""")
