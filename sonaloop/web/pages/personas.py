"""Persona pages: list, detail, memory, activity (spec/roadmap.md R2)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from ._calendar import _calendar_tabs, _period_calendar_html
from .._render import render_findings
from ... import artifacts as _artifacts


def _memory_html(store: Store, persona_id: str, as_of: str | None, q: str | None) -> str:
    p = store.get_persona(persona_id)
    if not p:
        return _empty_state(t("profile_not_found"), t("runtime_maybe_cleared"))
    pid = p["id"]
    outdated_label = _label(t("outdated"), "var(--muted)", "outline", False)
    since_label = t("since")
    none_html = h("p", {"class_": "muted"}, t("none"))
    proj_cards = []
    for proj in services.list_active_projects(pid, store=store):
        tl = services.get_project(pid, proj["entity_id"], store=store)["facts"]
        rows = [h("p", {"class_": "muted" if not f["valid"] else ""},
                  f["t_valid"][:10], " · ", h("strong", {}, f.get("status") or "—"), " · ", f["fact"],
                  (fragment(" ", outdated_label) if not f["valid"] else None)) for f in tl[-8:]]
        proj_cards.append(h("div", {"class_": "card"},
                            h("h3", {}, proj["name"], " · ", h("span", {"class_": "muted"}, proj.get("status") or "?")),
                            fragment(*rows)))
    loops = [h("p", {}, "• ", th["text"], " ",
               h("span", {"class_": "muted small"}, f'{since_label} {(th.get("opened_on") or "")[:10]}'))
             for th in store.list_threads(pid, "open")[:20]]
    digests = [h("div", {"class_": "card"},
                 h("h3", {}, d["scope"], " · ", f'{d["period_start"][:10]}–{d["period_end"][:10]}'),
                 h("p", {}, d.get("text", ""))) for d in store.list_digests(pid)[-6:]]
    struct = services.evaluate_simulation(pid, store=store, persist=False)
    crit = services.latest_critic_report(pid, store=store)
    struct_rows = fragment(*(_label(f'{c["name"]}: {c["status"]}', _stance_color(c["status"])) for c in struct["checks"]))
    crit_rows = (fragment(*(_label(f"{k}: {v}/5", "var(--green)" if v >= 4 else "var(--amber)") for k, v in crit["dimensions"].items()))
                 if crit else h("span", {"class_": "muted"}, t("no_critic_run")))
    tt = ""
    if as_of:
        st = services.get_state_at(pid, as_of, store=store)
        ent_rows = [h("p", {}, h("strong", {}, e["name"]), " ", h("span", {"class_": "muted"}, f'({e["kind"]})'),
                      " → ", e.get("status_at") or "—") for e in st["entities"] if e.get("status_at")]
        tt = h("div", {"class_": "card"}, h("h3", {}, t("state_at", date=as_of)),
               fragment(*ent_rows) if ent_rows else h("p", {"class_": "muted"}, t("nothing_valid")),
               h("p", {"class_": "muted small"}, t("open_threads_count", n=len(st.get("open_threads", [])))))
    rc = ""
    if q:
        hits = services.recall_memory(pid, q, store=store, k=8)["hits"]
        hit_rows = [h("p", {"class_": "quote"}, f'[{hit["obj_type"]}] {hit.get("when") or ""} · score {hit["score"]}',
                      h("br"), hit["text"]) for hit in hits]
        rc = h("div", {"class_": "card"}, h("h3", {}, t("recall")),
               fragment(*hit_rows) if hit_rows else h("p", {"class_": "muted"}, t("nothing")))
    mem_title = t("memory_title", name=p["display_name"])
    date_in = h("input", {"type": "date", "name": "as_of", "value": as_of or ""})
    q_in = h("input", {"type": "text", "name": "q", "value": q or "", "placeholder": t("recall_placeholder"), "style": "width:58%"})
    main = fragment(
        _hero(mem_title, sub=t("memory_sub"), icon="memory"),
        h("div", {"class_": "card"}, h("h3", {}, t("quality")),
          h("p", {}, h("strong", {}, f'{t("structure")}:'), " ", struct["verdict"], " · ", struct_rows),
          h("p", {}, h("strong", {}, f'{t("critic")}:'), " ", crit_rows)),
        h("div", {"class_": "grid two"},
          h("form", {"method": "get", "class_": "card"}, h("h3", {}, t("time_travel")), date_in, " ",
            h("button", {"class_": "btn"}, t("show_state"))),
          h("form", {"method": "get", "class_": "card"}, h("h3", {}, t("recall")), q_in, " ",
            h("button", {"class_": "btn"}, t("search")))),
        tt, rc,
        h("div", {"class_": "sec"}, h("h2", {}, t("active_projects")),
          h("div", {"class_": "grid two"}, fragment(*proj_cards) if proj_cards else none_html)),
        h("div", {"class_": "sec"}, h("h2", {}, t("open_threads")),
          h("div", {"class_": "card"}, fragment(*loops) if loops else none_html)),
        h("div", {"class_": "sec"}, h("h2", {}, t("digests")), fragment(*digests) if digests else none_html))
    return _doc(main)



def register_personas(app) -> None:
    @app.get("/personas", response_class=HTMLResponse)
    def personas_list() -> str:
        store = Store()
        rows = [_persona_row(p, store) for p in services.list_personas(store=store)]
        return _list_page(store, title=t("personas"), lead=t("personas_lead"), rows=rows,
                          empty_icon="personas", empty_msg=t("no_personas"), active="personas")

    @app.get("/personas/{persona_id}", response_class=HTMLResponse)
    def persona_detail(persona_id: str, date_value: str | None = Query(default=None, alias="date"), view: str = Query(default="day")) -> str:
        store = Store()
        try:
            data = services.get_persona(persona_id, store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("profile_not_found"), t("persona_runtime_cleared")), store, active="personas")
        p = data["persona"]
        state = services.get_current_state(p["id"], store=store)
        selected_date = date_value or (data["daily_summaries"][-1]["date"] if data["daily_summaries"] else date.today().isoformat())
        view = view if view in {"day", "week", "month", "year"} else "day"
        period = services.get_calendar_period(p["id"], selected_date, view, store)
        avatar = (h("img", {"class_": "avatar", "src": f'/{p["avatar"]["path"]}', "alt": ""})
                  if p.get("avatar") else h("div", {}, _avatar(p, 120)))
        date_links = fragment(*(
            h("a", {"class_": "pill", "href": f'/personas/{p["id"]}?date={s["date"]}&view={view}'}, s["date"])
            for s in data["daily_summaries"][-10:]))
        daycount = Counter()
        for e in store.list_experience_events(p["id"]):
            ts = e.get("timestamp") or ""
            if len(ts) >= 10:
                daycount[ts[:10]] += 1
        act_pts = [(d[5:], daycount[d]) for d in sorted(daycount)]
        activity = (h("div", {"class_": "sec", "id": "aktivitaet"}, h("h2", {}, t("activity_over_time")),
                      h("p", {"class_": "ihint"}, t("activities_per_day", n=sum(daycount.values()))), _area(act_pts))
                    if act_pts else "")
        voices = _persona_voices_html(store, p["id"])
        rel_rows = fragment(*(h("p", {}, h("strong", {}, r["name"]), " ",
                              h("span", {"class_": "muted"}, f'— {r["type"]}: {r["friction"]}')) for r in p["relationships"]))
        main = fragment(
            _hero(p["display_name"], sub=f'{p["role"]["title"]} · {p["company_context"]["industry"]}'),
            h("div", {"class_": "identity"}, h("div", {}, avatar), h("div", {},
              h("div", {"class_": "card"}, h("h3", {}, t("current_state")),
                h("p", {}, h("strong", {}, state["current_activity"])), h("p", {"class_": "muted"}, state["collaboration_mode"]),
                h("p", {"class_": "thought"}, state["current_thought"])))),
            raw(voices), activity,
            h("div", {"class_": "sec", "id": "ziele"}, h("h2", {}, t("goals")), raw(_pills(p["goals"]))),
            h("div", {"class_": "sec", "id": "pains"}, h("h2", {}, t("pain_points")),
              # structured observations (issue + opportunity + severity/evidence) → the SAME finding row
              # as the synthesis; the plain profile list stays compact pills.
              (raw(render_findings([_artifacts.pain_point_finding(x) for x in data["pain_points"]]))
               if data["pain_points"] else raw(_pills(p["pain_points"])))),
            h("div", {"class_": "sec", "id": "tools"}, h("h2", {}, t("tools")), raw(_pills(p["tools"]))),
            h("div", {"class_": "sec", "id": "bez"}, h("h2", {}, t("relationships")), rel_rows),
            h("div", {"class_": "sec", "id": "cal"}, h("h2", {}, t("calendar")),
              h("p", {"class_": "muted"}, date_links or t("no_days_yet")),
              raw(_calendar_tabs(p["id"], selected_date, view)),
              raw(_period_calendar_html(p["id"], selected_date, view, period))))
        props = _properties_html([
            ("personas", t("role"), p["role"]["title"]),
            ("projects", t("industry"), p["company_context"]["industry"]),
            ("dot", t("size"), p["company_context"].get("size", "")),
            ("memory", t("memory"), h("a", {"class_": "bc-link", "href": f'/personas/{p["id"]}/memory'}, raw(_icon("memory")), " ", t("open"))),
        ], aside=True)
        prail = [("aktivitaet", t("activity_over_time"))] if activity else []
        prail += [("ziele", t("goals")), ("pains", t("pain_points")), ("tools", t("tools")),
                  ("bez", t("relationships")), ("cal", t("calendar")), ("sec-properties", t("properties"))]
        return _layout(p["display_name"], _doc(main, rail=props) + _page_rail(prail), store,
                       crumbs=[(t("personas"), "/personas"), (p["display_name"], None)], active="personas",
                       actions=_star("persona", p["id"], p["display_name"], f'/personas/{p["id"]}'))

    @app.get("/personas/{persona_id}/memory", response_class=HTMLResponse)
    def persona_memory(persona_id: str, as_of: str | None = Query(default=None), q: str | None = Query(default=None)) -> str:
        store = Store()
        pm = store.get_persona(persona_id)
        cr = [(t("personas"), "/personas"), (pm["display_name"] if pm else persona_id, f"/personas/{persona_id}"), (t("memory"), None)]
        return _layout(t("memory"), _memory_html(store, persona_id, as_of, q), store, crumbs=cr, active="personas")

    @app.get("/activities/{activity_id}", response_class=HTMLResponse)
    def activity_detail(activity_id: str) -> str:
        store = Store()
        try:
            data = services.get_activity(activity_id, store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("activity_not_found"), t("runtime_maybe_cleared")), store, active="personas")
        p = data["persona"]; a = data["activity"]
        alone_label = t("alone")
        conv = [h("div", {"class_": "quote"}, h("strong", {}, c.get("speaker", "")), h("br"), c.get("text", ""))
                for c in a.get("conversation", [])]
        main = fragment(
            _hero(a["task"], sub=f'{a["timestamp"]} · {a["event_type"]} · {a.get("collaboration_mode","unknown")}'),
            h("div", {"class_": "grid two"},
              h("div", {"class_": "card"}, h("h3", {}, t("what_happened")), h("p", {}, a.get("what_happened", a["summary"]))),
              h("div", {"class_": "card"}, h("h3", {}, t("thought")), h("p", {"class_": "thought"}, a.get("persona_thought", "—")))),
            h("div", {"class_": "sec"}, h("h2", {}, t("conversation")),
              fragment(*conv) if conv else h("p", {"class_": "muted"}, t("none_f"))),
            h("div", {"class_": "grid"},
              h("div", {"class_": "card"}, h("h3", {}, t("actions")), raw(_pills(a.get("actions_done", [])) or "—")),
              h("div", {"class_": "card"}, h("h3", {}, t("artifacts")), raw(_pills(a.get("artifacts_touched", [])) or "—")),
              h("div", {"class_": "card"}, h("h3", {}, t("open_loops")), raw(_pills(a.get("open_loops", [])) or "—"))))
        props = _properties_html([
            ("personas", t("persona"), h("a", {"class_": "bc-link", "href": f'/personas/{p["id"]}'}, p["display_name"])),
            ("square", t("tool"), a["tool"]),
            ("dot", t("mood"), a["impact"]["mood"]),
            ("personas", t("participants"), _pills(a.get("participants", []) or [alone_label])),
            ("check", t("decision"), a.get("decision") or ""),
        ], aside=True)
        return _layout(a["task"], _doc(main, rail=props), store,
                       crumbs=[(t("personas"), "/personas"), (p["display_name"], f'/personas/{p["id"]}'), (a["task"][:46], None)], active="personas")
