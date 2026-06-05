from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from .. import services
from ..storage import Store
from ._i18n import t, _lang
from ._components import (
    _esc, _icon, _avatar, _label, _pills, _md, _layout, _empty_state, _doc,
    _star, _stance_color, _EDGE_COLORS, _theme_color, _artifact_present,
)
from ._synthesis import (
    _area, _vote_label, _sentiment_section, _synthesis_html, _persona_voices_html,
)
from ._graph import _graph_interactive, _plan_html


def _projects_page() -> str:
    """The Projects list — the app's home (project-centric IA)."""
    store = Store()
    rows = []
    for p in services.list_research_projects(store=store):
        rows.append(f'<a class="row" href="/projects/{_esc(p["id"])}">{_icon("projects")}'
                    f'<span class="title">{_esc(p["title"])}</span>'
                    f'<span class="right"><span>{p["studies"]} {t("syntheses")}</span>'
                    f'<span>{p["edges"]} {t("build_order_h")}</span>'
                    f'<span>{len(p.get("themes", []))} {t("themes_h")}</span></span></a>')
    rows_html = "".join(rows) or f'<div class="row muted">{t("no_projects")}</div>'
    body = f'<div class="page"><h1 class="h1">{t("projects")}</h1><p class="lead">{t("projects_lead")}</p><div class="rows">{rows_html}</div></div>'
    return _layout(t("projects"), body, store, crumbs=[(t("projects"), None)], active="projects")


# ----------------------------- calendar helpers ----------------------------- #
def _calendar_html(persona_id: str, day: str, blocks: list[dict]) -> str:
    by_hour: dict[int, list[dict]] = {h: [] for h in range(7, 20)}
    for block in blocks:
        hour = int(block["calendar_event"]["start"][11:13])
        by_hour.setdefault(hour, []).append(block)
    rows = []
    for hour in range(7, 20):
        rows.append(f'<div class="hour">{hour:02d}:00</div><div class="slot">')
        for block in by_hour.get(hour, []):
            cal = block["calendar_event"]; activity = block.get("activity") or {}
            kind = activity.get("event_type", "focus")
            rows.append(
                f'<a class="block {kind}" href="/activities/{_esc(activity.get("id",""))}">'
                f'<strong>{_esc(cal["start"][11:16])}-{_esc(cal["end"][11:16])} · {_esc(cal["title"])}</strong>'
                f'<span class="meta">{_esc(block.get("collaboration_mode") or "")} · {_esc(cal["location_or_tool"])}</span><br>'
                f'{_esc(block.get("persona_thought") or cal["outcome"])}</a>')
        rows.append("</div>")
    return f'<div class="calendar">{"".join(rows)}</div>'


def _calendar_tabs(persona_id: str, selected_date: str, view: str) -> str:
    labels = {"day": t("tab_day"), "week": t("tab_week"), "month": t("tab_month"), "year": t("tab_year")}
    return '<div class="tabs">' + "".join(
        f'<a class="{"active" if view == tab else ""}" href="/personas/{_esc(persona_id)}?date={_esc(selected_date)}&view={tab}">{labels[tab]}</a>'
        for tab in ["day", "week", "month", "year"]) + "</div>"


def _event_chip(event: dict) -> str:
    return (f'<a class="block {event.get("event_type","focus")}" href="/activities/{_esc(event["id"])}">'
            f'<strong>{_esc(event["timestamp"][11:16])} · {_esc(event["task"])}</strong>'
            f'<span class="meta">{_esc(event.get("tool",""))}</span></a>')


def _period_calendar_html(persona_id: str, selected_date: str, view: str, period: dict) -> str:
    if view == "day":
        return _calendar_html(persona_id, selected_date, services.get_calendar(persona_id, selected_date)["blocks"])
    start = date.fromisoformat(period["period_start"]); end = date.fromisoformat(period["period_end"]); days = period["days"]
    if view == "week":
        cells = []; current = start
        while current <= end:
            dk = current.isoformat(); chips = "".join(_event_chip(e) for e in days.get(dk, [])[:4])
            cells.append(f'<div class="daycell"><h4>{_esc(dk)}</h4>{chips or "<p class=\"muted small\">—</p>"}</div>'); current += timedelta(days=1)
        return f'<div class="calendar-grid week">{"".join(cells)}</div>'
    if view == "month":
        cells = []; current = start
        while current <= end:
            dk = current.isoformat(); evs = days.get(dk, []); chips = "".join(_event_chip(e) for e in evs[:3])
            cells.append(f'<div class="daycell monthcell"><h4>{current.day}</h4><div class="count">{t("n_events", n=len(evs))}</div>{chips}</div>'); current += timedelta(days=1)
        return f'<div class="calendar-grid month">{"".join(cells)}</div>'
    cells = []
    for m in range(1, 13):
        me = [e for dk, evs in days.items() if date.fromisoformat(dk).month == m for e in evs]
        cells.append(f'<div class="daycell"><h4>{start.year}-{m:02d}</h4><div class="count">{t("n_events", n=len(me))}</div>{"".join(_event_chip(e) for e in me[:2])}</div>')
    return f'<div class="calendar-grid year">{"".join(cells)}</div>'


def _memory_html(store: Store, persona_id: str, as_of: str | None, q: str | None) -> str:
    p = store.get_persona(persona_id)
    if not p:
        return _empty_state(t("profile_not_found"), t("runtime_maybe_cleared"))
    pid = p["id"]
    outdated_label = _label(t("outdated"), "var(--muted)", "outline", False)
    since_label = t("since")
    none_html = f'<p class="muted">{t("none")}</p>'
    proj_cards = []
    for proj in services.list_active_projects(pid, store=store):
        tl = services.get_project(pid, proj["entity_id"], store=store)["facts"]
        rows = "".join(
            f'<p class="{"muted" if not f["valid"] else ""}">{_esc(f["t_valid"][:10])} · <strong>{_esc(f.get("status") or "—")}</strong> · {_esc(f["fact"])}'
            f'{" " + outdated_label if not f["valid"] else ""}</p>' for f in tl[-8:])
        proj_cards.append(f'<div class="card"><h3>{_esc(proj["name"])} · <span class="muted">{_esc(proj.get("status") or "?")}</span></h3>{rows}</div>')
    loops = "".join(f'<p>• {_esc(t["text"])} <span class="muted small">{since_label} {_esc((t.get("opened_on") or "")[:10])}</span></p>' for t in store.list_threads(pid, "open")[:20])
    digests = "".join(f'<div class="card"><h3>{_esc(d["scope"])} · {_esc(d["period_start"][:10])}–{_esc(d["period_end"][:10])}</h3><p>{_esc(d.get("text",""))}</p></div>' for d in store.list_digests(pid)[-6:])
    struct = services.evaluate_simulation(pid, store=store, persist=False)
    crit = services.latest_critic_report(pid, store=store)
    struct_rows = "".join(_label(f'{c["name"]}: {c["status"]}', _stance_color(c["status"])) for c in struct["checks"])
    crit_rows = ("".join(_label(f"{k}: {v}/5", "var(--green)" if v >= 4 else "var(--amber)") for k, v in crit["dimensions"].items()) if crit else f'<span class="muted">{t("no_critic_run")}</span>')
    tt = ""
    if as_of:
        st = services.get_state_at(pid, as_of, store=store)
        ent_rows = "".join(f'<p><strong>{_esc(e["name"])}</strong> <span class="muted">({_esc(e["kind"])})</span> → {_esc(e.get("status_at") or "—")}</p>' for e in st["entities"] if e.get("status_at"))
        nothing_valid_html = f'<p class="muted">{t("nothing_valid")}</p>'
        tt = (f'<div class="card"><h3>{t("state_at", date=_esc(as_of))}</h3>{ent_rows or nothing_valid_html}'
              f'<p class="muted small">{t("open_threads_count", n=len(st.get("open_threads", [])))}</p></div>')
    rc = ""
    if q:
        hits = services.recall_memory(pid, q, store=store, k=8)["hits"]
        nothing_html = f'<p class="muted">{t("nothing")}</p>'
        rc = f'<div class="card"><h3>{t("recall")}</h3>' + ("".join(f'<p class="quote">[{_esc(h["obj_type"])}] {_esc(h.get("when") or "")} · score {_esc(h["score"])}<br>{_esc(h["text"])}</p>' for h in hits) or nothing_html) + "</div>"
    mem_title = t("memory_title", name=_esc(p["display_name"]))
    recall_ph = _esc(t("recall_placeholder"))
    main = f"""
    <div class="hero"><h1 style="display:flex;align-items:center;gap:9px">{_icon("memory")} {mem_title}</h1><p class="sub">{t("memory_sub")}</p></div>
    <div class="card"><h3>{t("quality")}</h3><p><strong>{t("structure")}:</strong> {_esc(struct["verdict"])} · {struct_rows}</p><p><strong>{t("critic")}:</strong> {crit_rows}</p></div>
    <div class="grid two">
      <form method="get" class="card"><h3>{t("time_travel")}</h3><input type="date" name="as_of" value="{_esc(as_of or '')}"> <button class="btn">{t("show_state")}</button></form>
      <form method="get" class="card"><h3>{t("recall")}</h3><input type="text" name="q" value="{_esc(q or '')}" placeholder="{recall_ph}" style="width:58%"> <button class="btn">{t("search")}</button></form>
    </div>{tt}{rc}
    <div class="sec"><h2>{t("active_projects")}</h2><div class="grid two">{''.join(proj_cards) or none_html}</div></div>
    <div class="sec"><h2>{t("open_threads")}</h2><div class="card">{loops or none_html}</div></div>
    <div class="sec"><h2>{t("digests")}</h2>{digests or none_html}</div>
    """
    return _doc(main)


def register_pages(app) -> None:
    from fastapi import Query
    from fastapi.responses import HTMLResponse

    # ---------- helpers that need the store ----------
    def _persona_card(p: dict, store: Store) -> str:
        pid = p["id"]
        try:
            proj = services.list_active_projects(pid, store=store)
        except Exception:
            proj = []
        loops = len(store.list_threads(pid, "open"))
        st = services.get_current_state(pid, store=store)
        cur = st.get("current_activity") if st.get("current_activity") != "not simulated yet" else t("not_simulated_yet")
        meta = []
        if proj:
            meta.append(_label(t("n_projects", n=len(proj)), "var(--accent)"))
        if loops:
            meta.append(_label(t("n_open", n=loops), "var(--amber)"))
        return (
            f'<a class="pcard" href="/personas/{_esc(pid)}">'
            f'{_star("persona", pid, p["display_name"], f"/personas/{pid}")}'
            f'<div class="top">{_avatar(p, 40)}<div style="min-width:0"><div class="nm">{_esc(p["display_name"])}</div>'
            f'<div class="ro">{_esc(p["role"]["title"])} · {_esc(p["company_context"]["industry"])}</div></div></div>'
            f'<div class="st">{_esc(cur)}</div><div class="meta">{"".join(meta)}</div></a>'
        )

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        # Home is the Projects list (project-centric IA; Overview removed).
        return _projects_page()

    @app.get("/personas", response_class=HTMLResponse)
    def personas_list() -> str:
        store = Store()
        personas = services.list_personas(store=store)
        cards = "".join(_persona_card(p, store) for p in personas) or f'<p class="muted">{t("no_personas")}</p>'
        body = f'<div class="page"><h1 class="h1">{t("personas")}</h1><p class="lead">{t("personas_lead", n=len(personas))}</p><div class="pgrid">{cards}</div></div>'
        return _layout(t("personas"), body, store, crumbs=[(t("personas"), None)], active="personas")

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
        avatar = f'<img class="avatar" src="/{_esc(p["avatar"]["path"])}" alt="">' if p.get("avatar") else f'<div>{_avatar(p, 120)}</div>'
        date_links = "".join(
            f'<a class="pill" href="/personas/{_esc(p["id"])}?date={_esc(s["date"])}&view={_esc(view)}">{_esc(s["date"])}</a>'
            for s in data["daily_summaries"][-10:])
        daycount = Counter()
        for e in store.list_experience_events(p["id"]):
            ts = e.get("timestamp") or ""
            if len(ts) >= 10:
                daycount[ts[:10]] += 1
        act_pts = [(d[5:], daycount[d]) for d in sorted(daycount)]
        activity = (f'<div class="sec" id="aktivitaet"><h2>{t("activity_over_time")}</h2>'
                    f'<p class="ihint">{t("activities_per_day", n=sum(daycount.values()))}</p>{_area(act_pts)}</div>'
                    if act_pts else "")
        voices = _persona_voices_html(store, p["id"])
        main = f"""
        <div class="hero"><h1>{_esc(p["display_name"])}</h1><p class="sub">{_esc(p["role"]["title"])} · {_esc(p["company_context"]["industry"])}</p></div>
        <div class="identity"><div>{avatar}</div><div>
          <div class="card"><h3>{t("current_state")}</h3><p><strong>{_esc(state["current_activity"])}</strong></p><p class="muted">{_esc(state["collaboration_mode"])}</p><p class="thought">{_esc(state["current_thought"])}</p></div>
        </div></div>
        {voices}
        {activity}
        <div class="sec" id="ziele"><h2>{t("goals")}</h2>{_pills(p["goals"])}</div>
        <div class="sec" id="pains"><h2>{t("pain_points")}</h2>{_pills([x["issue"] for x in data["pain_points"]] or p["pain_points"])}</div>
        <div class="sec" id="bez"><h2>{t("relationships")}</h2>{''.join(f'<p><strong>{_esc(r["name"])}</strong> <span class="muted">— {_esc(r["type"])}: {_esc(r["friction"])}</span></p>' for r in p["relationships"])}</div>
        <div class="sec" id="cal"><h2>{t("calendar")}</h2><p class="muted">{date_links or t("no_days_yet")}</p>
        {_calendar_tabs(p["id"], selected_date, view)}{_period_calendar_html(p["id"], selected_date, view, period)}</div>
        """
        rail = (f'<h4>{t("properties")}</h4>'
                f'<div class="prop"><span class="k">{t("role")}</span><span class="v">{_esc(p["role"]["title"])}</span></div>'
                f'<div class="prop"><span class="k">{t("industry")}</span><span class="v">{_esc(p["company_context"]["industry"])}</span></div>'
                f'<div class="prop"><span class="k">{t("size")}</span><span class="v">{_esc(p["company_context"].get("size",""))}</span></div>'
                f'<div class="prop"><span class="k">{t("tools")}</span><span class="v">{_pills(p["tools"])}</span></div>'
                f'<div class="prop"><span class="k">{t("memory")}</span><span class="v"><a class="bc-link" href="/personas/{_esc(p["id"])}/memory">{_icon("memory")} {t("open")}</a></span></div>')
        return _layout(p["display_name"], _doc(main, rail=rail), store,
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
        main = f"""
        <div class="hero"><h1>{_esc(a["task"])}</h1><p class="sub">{_esc(a["timestamp"])} · {_esc(a["event_type"])} · {_esc(a.get("collaboration_mode","unknown"))}</p></div>
        <div class="grid two">
          <div class="card"><h3>{t("what_happened")}</h3><p>{_esc(a.get("what_happened", a["summary"]))}</p></div>
          <div class="card"><h3>{t("thought")}</h3><p class="thought">{_esc(a.get("persona_thought","—"))}</p></div></div>
        <div class="sec"><h2>{t("conversation")}</h2>{''.join(f'<div class="quote"><strong>{_esc(c.get("speaker",""))}</strong><br>{_esc(c.get("text",""))}</div>' for c in a.get("conversation", [])) or f'<p class="muted">{t("none_f")}</p>'}</div>
        <div class="grid"><div class="card"><h3>{t("actions")}</h3>{_pills(a.get("actions_done", [])) or '—'}</div>
          <div class="card"><h3>{t("artifacts")}</h3>{_pills(a.get("artifacts_touched", [])) or '—'}</div>
          <div class="card"><h3>{t("open_loops")}</h3>{_pills(a.get("open_loops", [])) or '—'}</div></div>
        """
        rail = (f'<h4>{t("properties")}</h4>'
                f'<div class="prop"><span class="k">{t("persona")}</span><span class="v"><a class="bc-link" href="/personas/{_esc(p["id"])}">{_esc(p["display_name"])}</a></span></div>'
                f'<div class="prop"><span class="k">{t("tool")}</span><span class="v">{_esc(a["tool"])}</span></div>'
                f'<div class="prop"><span class="k">{t("mood")}</span><span class="v">{_esc(a["impact"]["mood"])}</span></div>'
                f'<div class="prop"><span class="k">{t("participants")}</span><span class="v">{_pills(a.get("participants", []) or [alone_label])}</span></div>'
                f'<div class="prop"><span class="k">{t("decision")}</span><span class="v muted">{_esc(a.get("decision") or "—")}</span></div>')
        return _layout(a["task"], _doc(main, rail=rail), store,
                       crumbs=[(t("personas"), "/personas"), (p["display_name"], f'/personas/{p["id"]}'), (a["task"][:46], None)], active="personas")

    @app.get("/councils", response_class=HTMLResponse)
    def councils() -> str:
        store = Store()
        rows = []
        for c in services.list_councils(store=store):
            v = c["votes"]; tot = max(1, sum(v.values()))
            bar = (f'<span class="votebar" title="SUPPORT {v["SUPPORT"]} · MAYBE {v["MAYBE"]} · OPPOSE {v["OPPOSE"]}">'
                   f'<i style="width:{v["SUPPORT"]/tot*100}%;background:var(--green)"></i>'
                   f'<i style="width:{v["MAYBE"]/tot*100}%;background:var(--amber)"></i>'
                   f'<i style="width:{(v["OPPOSE"]+v["ABSTAIN"])/tot*100}%;background:var(--muted)"></i></span>')
            rows.append(f'<a class="row" href="/councils/{_esc(c["id"])}">{_icon("councils")}'
                        f'<span class="title">{_esc(c["prompt"])}</span>'
                        f'<span class="right">{bar}<span>{c["personas"]} {t("personas")}</span><span>{_esc(c["created_at"][:10])}</span>'
                        f'{_star("council", c["id"], c["prompt"][:60], f"/councils/{c['id']}")}</span></a>')
        rows_html = "".join(rows) or f'<div class="row muted">{t("no_councils")}</div>'
        body = f'<div class="page"><h1 class="h1">{t("councils")}</h1><p class="lead">{t("councils_lead")}</p><div class="rows">{rows_html}</div></div>'
        return _layout(t("councils"), body, store, crumbs=[(t("projects"), "/projects"), (t("councils"), None)], active="projects")

    @app.get("/councils/{session_id}", response_class=HTMLResponse)
    def council_detail(session_id: str) -> str:
        store = Store()
        session = store.get_council_session(session_id)
        if not session:
            return _layout(t("not_found"), _empty_state(t("council_not_found"), t("runtime_maybe_cleared")), store, active="councils")
        voices_detail_h = t("voices_in_detail", n=len(session["turns"]))
        proposal_short_h = t("proposal_short_summary")
        proposal_h = t("proposal"); summary_h = t("summary")
        sentiment_title = t("sentiment_this_council")
        vote_h = t("vote"); personas_h = t("personas"); created_h = t("created")
        councils_crumb = t("councils"); council_title = t("councils")
        # Each voice shows WHO the persona is + the life-context that shaped them (the per-persona
        # "input") and any recorded input snapshot, so you can see what each was given → what they said.
        pmap = {pid: store.get_persona(pid) for pid in session.get("persona_ids", [])}
        turns = []
        for tn in session["turns"]:
            body = tn.get("content") or tn.get("text") or tn.get("message") or ""   # tolerate turn-body field variants
            mod = " mod" if (tn.get("speaker") == "Moderator" or tn.get("stance") in ("moderation", "moderator") or tn.get("type") == "moderator") else ""
            stance = _label(tn["stance"], _stance_color(tn.get("stance", ""))) if tn.get("stance") else ""
            p = pmap.get(tn.get("persona_id"))
            if p:
                seg = p.get("segment") or {}
                desc = " · ".join(x for x in [seg.get("lebensphase"), seg.get("einstellung")] if x)[:130] \
                    or (p.get("source_description") or "")[:130]
                head = (f'<a href="/personas/{_esc(p["id"])}" class="turn-who">{_avatar(p, 26)}'
                        f'<b>{_esc(p.get("display_name") or tn.get("speaker", ""))}</b></a> {stance}'
                        f'<div class="muted small turn-ctx">{_esc(desc)}</div>')
            else:
                head = f'<b>{_esc(tn.get("speaker", ""))}</b> {stance}'
            given = tn.get("input") or tn.get("context_given") or ""
            given_html = (f'<details class="turn-input"><summary class="muted small">{t("council_input_given")}</summary>'
                          f'<p class="muted small" style="white-space:pre-wrap">{_esc(given)}</p></details>') if given else ""
            concerns = "".join(f'<p class="muted small">• {_esc(q)}</p>' for q in (tn.get("questions_or_pushback") or [])[:4])
            mrefs = (tn.get("memory_refs") or tn.get("memory_used") or [])[:3]
            mem = (f'<p class="muted small">{_icon("memory")} {t("council_drew_on")}: ' + ", ".join(_esc(m) for m in mrefs) + '</p>') if mrefs else ""
            turns.append(f'<div class="turn{mod}"><div class="hd">{head}</div>{given_html}<p>{_esc(body)}</p>{concerns}{mem}</div>')
        turns_html = (f'<p class="muted small" style="margin:-4px 0 12px">{t("council_voices_help")}</p>'
                      '<div style="display:grid;gap:12px">' + "".join(turns) + "</div>")
        exec_html = _md(session.get("exec_summary", "")) or f'<p>{_esc(session["summary"])}</p>'
        n_voices = len(session.get("persona_ids", []))
        # A council has THREE honest shapes (derived, no stored type): DISCOVERY (open questions →
        # answers, no vote — listening), EVALUATION (react to a concept), DECISION (a motion put to a
        # vote). Lead the page with the right framing so "what is the question?" is always answered.
        mode = services.council_mode(session)
        voices_label = t("council_voices_answers") if mode == "discovery" else voices_detail_h
        if mode == "discovery":
            qs = session.get("questions") or ([session.get("prompt")] if session.get("prompt") else [])
            qlist = "".join(f'<li>{_esc(q)}</li>' for q in qs) or f'<li class="muted">—</li>'
            lead_block = (f'<div class="callout motion"><span class="emj">{_icon("compass")}</span>'
                          f'<div><strong>{t("council_questions_h")}</strong>'
                          f'<ul style="margin:.4em 0 .2em 20px;font-size:1.02em">{qlist}</ul>'
                          f'<p class="muted small">{t("council_questions_help", n=n_voices)}</p></div></div>')
            sentiment = ""                                    # a listening session has no vote/sentiment chart
        else:
            motion = (session.get("proposal") or "").strip()
            label = t("council_eval_h") if mode == "evaluation" else t("council_motion")
            help_ = t("council_eval_help", n=n_voices) if mode == "evaluation" else t("council_motion_help", n=n_voices)
            lead_block = (f'<div class="callout motion"><span class="emj">{_icon("compass")}</span>'
                          f'<div><strong>{label}</strong>'
                          f'<p style="font-size:1.1em;margin:.35em 0">&bdquo;{_esc(motion)}&ldquo;</p>'
                          f'<p class="muted small">{help_}</p></div></div>') if motion else ""
            sentiment = _sentiment_section(store, [session], title=sentiment_title) or ""
        main = (f'<div class="hero"><h1>{_esc(session["prompt"])}</h1>'
                f'<p class="sub">{t("council_kicker_" + mode, n=n_voices)} · {_esc(session["selection_reason"])}</p></div>'
                f'{lead_block}'
                f'<div class="callout"><span class="emj">{_icon("bulb")}</span>'
                f'<div><strong>{t("council_finding")}</strong>{exec_html}</div></div>'
                f'{sentiment}'
                f'<div class="sec" id="stimmen"><h2>{voices_label}</h2>{turns_html}</div>'
                f'<details class="sec"><summary>{summary_h}</summary><div class="card"><strong>{summary_h}</strong><p>{_esc(session["summary"])}</p></div></details>')
        rail = f'<div class="prop"><span class="k">{personas_h}</span><span class="v">{n_voices}</span></div>'
        if mode != "discovery":                               # the vote panel only where a vote/reaction exists
            vc = {v: sum(1 for x in session["votes"] if str(x.get("vote", "")).upper() == v) for v in ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]}
            rail = (f'<h4>{t("council_reactions_h")}</h4>'
                    + "".join(f'<div class="prop"><span class="k">{_vote_label(k)}</span><span class="v">{vc[k]}</span></div>' for k in vc)
                    + rail)
        rail += f'<div class="prop"><span class="k">{created_h}</span><span class="v">{_esc(session["created_at"][:10])}</span></div>'
        # Forward, project-rooted crumb: Projects > [Project] > [Council]. (A Discover council FEEDS
        # the Define synthesis — it is not nested under it; and the project lookup must work for
        # plan-based projects, where the council is scoped directly to the project.)
        crumbs = [(t("projects"), "/projects")]
        proj = (services.parent_project_of_council(session_id, store)
                or (services.parent_project_of_synthesis(ps["id"], store)
                    if (ps := services.parent_study_of_council(session_id, store)) else None))
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((session["prompt"][:50], None))
        return _layout(council_title, _doc(main, rail=rail), store,
                       crumbs=crumbs, active="projects",
                       actions=_star("council", session_id, session["prompt"][:60], f"/councils/{session_id}"))

    @app.get("/syntheses", response_class=HTMLResponse)
    def syntheses() -> str:
        store = Store()
        rows = []
        for s in store.list_syntheses():
            done = s.get("status", "done") == "done"
            rows.append(f'<a class="row" href="/syntheses/{_esc(s["id"])}">{_icon("syntheses")}'
                        f'<span class="title">{_esc(s["title"])}</span>'
                        f'<span class="right">{_label(t("done") if done else t("running"), "var(--green)" if done else "var(--amber)")}'
                        f'<span>{len(s.get("council_ids", []))} {t("councils")}</span><span>{_esc(s["created_at"][:10])}</span>'
                        f'{_star("synthesis", s["id"], s["title"], f"/syntheses/{s['id']}")}</span></a>')
        rows_html = "".join(rows) or f'<div class="row muted">{t("no_synthesis")}</div>'
        body = f'<div class="page"><h1 class="h1">{t("syntheses")}</h1><p class="lead">{t("syntheses_lead")}</p><div class="rows">{rows_html}</div></div>'
        return _layout(t("syntheses"), body, store, crumbs=[(t("projects"), "/projects"), (t("syntheses"), None)], active="projects")

    @app.get("/syntheses/{synthesis_id}", response_class=HTMLResponse)
    def synthesis_detail(synthesis_id: str) -> str:
        store = Store()
        syn = store.get_synthesis(synthesis_id)
        if not syn:
            return _layout(t("not_found"), _empty_state(t("synthesis_not_found"), t("runtime_maybe_cleared")), store, active="syntheses")
        actions = (_star("synthesis", synthesis_id, syn["title"], f"/syntheses/{synthesis_id}")
                   + f'<button class="btn" onclick="window.print()">{t("export_pdf")}</button>')
        crumbs = [(t("projects"), "/projects")]
        proj = services.parent_project_of_synthesis(synthesis_id, store)
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((syn["title"], None))
        return _layout(syn["title"], _synthesis_html(store, syn), store,
                       crumbs=crumbs, active="projects", actions=actions)

    @app.get("/projects", response_class=HTMLResponse)
    def projects() -> str:
        return _projects_page()

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_detail(project_id: str) -> str:
        store = Store()
        try:
            graph = services.get_project_graph(project_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("not_found"), t("runtime_maybe_cleared")), store, active="projects")
        proj = graph["project"]
        # edge legend (shown in the floating open-questions panel)
        used_types = sorted({e["type"] for e in graph["edges"]})
        edge_leg = "".join(
            f'<span class="pill" style="border-color:{_EDGE_COLORS.get(ty, "#9aa0a6")}">{_esc(ty)}</span>'
            for ty in used_types) or f'<span class="muted small">—</span>'
        oqs = [o for o in graph["open_questions"] if o.get("status") == "open"]
        oq_html = "".join(f'<li>{_esc(o["text"])}</li>' for o in oqs[:30]) or f'<li class="muted">—</li>'
        reports = store.list_meta_reports(proj["id"])
        meta_btn = (f'<a class="btn" href="/projects/{_esc(proj["id"])}/meta">{_icon("syntheses")} {t("meta_report")}</a>'
                    if reports else "")
        if services.get_plan(proj["id"], store=store):    # the analyze/act/verify plan view
            meta_btn = f'<a class="btn" href="/projects/{_esc(proj["id"])}/plan">{_icon("projects")} Plan</a>' + meta_btn
        # Linear-style filter: EVERY tag present on a node is a toggleable chip — incl. the
        # methodology's open step tags (capability/role), not just LLM theme tags. No fixed vocab.
        node_tags = []
        for n in graph["nodes"]:
            for tgx in n.get("theme_tags", []):
                if tgx not in node_tags:
                    node_tags.append(tgx)
        vocab_all = list(dict.fromkeys((proj.get("themes") or []) + node_tags))
        chips = "".join(
            f'<button class="rgchip" data-theme="{_esc(th)}" style="--c:{_theme_color(th, vocab_all)}">{_esc(th)}</button>'
            for th in vocab_all)
        left = (f'<span class="ptlabel">{_icon("search")}{t("filter")}</span>{chips}'
                f'<a class="rgclear" style="display:none">{t("clear_filter")}</a>') if chips else ""
        oqbtn = f'<button class="btn" id="oqbtn">{t("legend")} · {t("open_questions_h")} ({len(oqs)})</button>'
        # (No bespoke methodology strip: the graph itself — columns, emergent silhouettes, and the
        # tag filter — conveys the constellation. A linear step strip would mis-imply a sequence.)
        toolbar = f'<div class="ptoolbar">{left}<span class="spacer"></span>{oqbtn}{meta_btn}</div>'
        # Artifact viewer: artifacts + recorded persona sessions (read-only).
        protos = graph.get("prototypes") or []
        proto_html = ""
        if protos:
            rows = []
            for p in protos:
                sess = store.list_prototype_sessions(prototype_id=p["id"])
                run_badge = ('<span class="pill" style="border-color:#3d7b5f">running</span>'
                             + f' <a href="{_esc(p["url"])}" target="_blank">open ↗</a>' if p.get("running") and p.get("url") else "")
                sl = []
                for s in sess[:6]:
                    r = s.get("reaction", {})
                    gv = "✓" if s.get("grounded_verified") else "○"
                    sl.append(f'<li>{_esc(s.get("persona_id",""))}: {_esc(str(r.get("verdict") or r.get("summary","")))[:80]} '
                              f'<span class="muted small">{gv} grounded</span></li>')
                sl_html = ("<ul style='margin:4px 0 0 18px'>" + "".join(sl) + "</ul>") if sl else '<div class="muted small">— keine Sessions —</div>'
                ap = _artifact_present(p)
                pill = ap["disc"] or ap["label"]
                rows.append(f'<div class="strow"><a href="/prototypes/{_esc(p["slug"])}">{_icon("projects")}<b>{_esc(p["name"])}</b></a> '
                            f'<span class="pill">{_esc(pill)}</span> <span class="muted small">{_esc(p.get("version",""))}</span> '
                            f'<a class="btn" style="padding:2px 8px" href="/prototypes/{_esc(p["slug"])}">ansehen ↗</a>{sl_html}</div>')
            proto_html = (f'<div class="oqp-h" style="margin-top:14px">{t("prototypes_h")} ({len(protos)})</div>'
                          + "".join(rows))
        # Sections outline (methodology-independent groupings) — a navigable list in the panel.
        from .. import presentation as _pres
        secs = sorted(graph.get("sections") or [], key=lambda s: s.get("order", 0))
        sec_html = ""
        if secs:
            rows = []
            for s in secs:
                pr = _pres.present(s.get("kind", "theme"), s.get("presentation"))
                rows.append(
                    f'<div class="strow"><a href="/sections/{_esc(s["id"])}"><span class="pill" style="border-color:{pr["color"]};color:{pr["color"]}">'
                    f'{_esc((pr.get("glyph") + " ") if pr.get("glyph") else "")}{_esc(s.get("title",""))}</span></a> '
                    f'<span class="muted small">{_esc(pr.get("short", s.get("kind","")))} · {len(s.get("member_ids",[]))}</span></div>')
            sec_html = (f'<div class="oqp-h" style="margin-top:14px">Sections ({len(secs)})</div>' + "".join(rows))
        # Project pulse (assess_project) — a self-documenting status line for in-flight long runs.
        pulse_html = ""
        try:
            ap = services.assess_project(proj["id"], store=store)
            cov = ap["coverage"]["evidence_by_kind"]
            cov_str = " · ".join(f"{k}:{v}" for k, v in cov.items())
            gaps = ap.get("gaps") or []
            gap_str = ("<div class='muted small' style='margin-top:4px'>Gaps: "
                       + "; ".join(_esc(g) for g in gaps[:4]) + "</div>") if gaps else ""
            pulse_html = (
                f'<div class="oqp-h">Pulse</div>'
                f'<div class="strow"><span class="pill">{_esc(ap["recommendation"])}</span> '
                f'<span class="muted small">{_esc(cov_str)} · Sättigung: {_esc(ap["saturation"]["hint"])}</span>{gap_str}</div>')
        except Exception:
            pulse_html = ""
        # Open questions + legend + prototypes live in a floating panel so the graph keeps the canvas.
        panel = (
            f'<div class="oqpanel" id="oqpanel" hidden>'
            f'{pulse_html}'
            f'<div class="oqp-h" style="margin-top:14px">{t("build_order_h")} (edges)</div>'
            f'<div class="pills" style="margin:6px 0 14px">{edge_leg}</div>'
            f'{sec_html}'
            f'<div class="oqp-h" style="margin-top:14px">{t("open_questions_h")}</div>'
            f'<ul style="margin:6px 0 0 18px">{oq_html}</ul>'
            f'{proto_html}</div>')
        oq_js = ("<script>(function(){var b=document.getElementById('oqbtn'),"
                 "p=document.getElementById('oqpanel');if(!b||!p)return;"
                 "b.addEventListener('click',function(e){e.stopPropagation();p.hidden=!p.hidden;});"
                 "document.addEventListener('click',function(e){"
                 "if(!p.hidden&&!p.contains(e.target)&&e.target!==b)p.hidden=true;});})();</script>")
        # ---- UX2: an always-visible OVERVIEW ("story") — question → path → answer — so a viewer
        # understands the project without decoding the graph. All data-driven from the plan/graph.
        ms = graph.get("methodology_state") or {}
        by_phase: dict[str, list] = {}
        for n in graph["nodes"]:
            by_phase.setdefault(n.get("phase", ""), []).append(n)
        flow = []
        for s in (ms.get("steps") or []):
            nm = (s.get("name") or s["key"]).split("·")[-1].strip()
            cnt = len(by_phase.get(s["key"], []))
            glyph = "◇" if s.get("is_fan") else "◆"      # diverge vs converge
            cnt_s = f' <b>{cnt}</b>' if cnt else ""
            flow.append(f'<span class="ovstep">{glyph} {_esc(nm)}{cnt_s}</span>')
        flow_html = '<span class="ovarr">→</span>'.join(flow) or f'<span class="muted small">{t("no_data")}</span>'
        n_concepts = sum(1 for n in graph["nodes"] if n.get("note_kind") == "concept")
        all_sess = [x for pr in protos for x in store.list_prototype_sessions(prototype_id=pr["id"])]
        n_grounded = sum(1 for x in all_sess if x.get("grounded_verified"))
        stats = (f'{t("ov_concepts")}: <b>{n_concepts}</b> · {t("ov_prototypes")}: <b>{len(protos)}</b> · '
                 f'{t("ov_grounded")}: <b>{n_grounded}/{len(all_sess)}</b> · {t("ov_open")}: <b>{len(oqs)}</b>')
        concl = services.project_conclusion(proj["id"], store=store)
        ans, win = concl["synthesis"], concl["winning_prototype"]
        ans_text = (ans or {}).get("gesamtbild", "") or (ans or {}).get("positionierung", "")
        if ans_text:
            btns = f'<a class="btn" href="/syntheses/{_esc(ans["id"])}">{t("ov_full_solution")} →</a>'
            if win:
                btns += f' <a class="btn" href="/prototypes/{_esc(win["slug"])}" target="_blank">▶ {_esc(win["name"])} ↗</a>'
            answer_html = f'<p>{_esc(ans_text[:560])}{"…" if len(ans_text) > 560 else ""}</p><div style="margin-top:8px">{btns}</div>'
        else:
            answer_html = f'<p class="muted">{t("ov_no_answer")}</p>'
        overview = (
            '<div class="ovcard">'
            f'<div class="ovrow"><span class="ov-k">{t("ov_question")}</span><div class="ov-v"><p class="lead" style="margin:0">{_esc(proj.get("goal", ""))}</p></div></div>'
            f'<div class="ovrow"><span class="ov-k">{t("ov_path")}</span><div class="ov-v"><div class="ovflow">{flow_html}</div><div class="muted small" style="margin-top:7px">{stats}</div></div></div>'
            f'<div class="ovrow"><span class="ov-k">{t("ov_answer")}</span><div class="ov-v">{answer_html}</div></div>'
            '</div>')
        body = (
            f'<div class="proj">'
            f'<div class="proj-head"><h1 class="h1">{_esc(proj["title"])}</h1>'
            f'{toolbar}</div>'
            f'{overview}'
            f'<div class="graphcard proj-graph">{_graph_interactive(graph)}</div>'
            f'{panel}{oq_js}'
            f'</div>')
        return _layout(proj["title"], body, store, crumbs=[(t("projects"), "/projects"), (proj["title"], None)], active="projects")

    @app.get("/projects/{project_id}/meta", response_class=HTMLResponse)
    def project_meta(project_id: str) -> str:
        store = Store()
        try:
            md = services.export_meta_report(project_id, format="md", store=store)
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("meta_report"), t("runtime_maybe_cleared")), store, active="projects")
        body = f'<div class="page"><div class="doc">{_md(md)}</div></div>'
        actions = f'<button class="btn" onclick="window.print()">{t("export_pdf")}</button>'
        return _layout(proj["title"] + " — " + t("meta_report"), body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f"/projects/{project_id}"), (t("meta_report"), None)],
                       active="projects", actions=actions)

    @app.get("/projects/{project_id}/plan", response_class=HTMLResponse)
    def project_plan(project_id: str) -> str:
        store = Store()
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state("Plan", t("runtime_maybe_cleared")), store, active="projects")
        plan = services.get_plan(project_id, store=store)
        if not plan:
            body = f'<div class="page">{_empty_state("Plan", "Dieses Projekt hat noch keinen Plan (Freiform/Legacy).")}</div>'
        else:
            body = _plan_html(plan, store)
        return _layout(proj["title"] + " — Plan", body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f"/projects/{project_id}"), ("Plan", None)],
                       active="projects")

    @app.get("/sections/{section_id}", response_class=HTMLResponse)
    def section_view(section_id: str) -> str:
        store = Store()
        from .. import presentation as _pres
        try:
            data = services.section_members(section_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state("Section", t("runtime_maybe_cleared")), store, active="projects")
        sec, proj, members = data["section"], data["project"], data["members"]
        pr = _pres.present(sec.get("kind", "theme"), sec.get("presentation"))
        chip = (f'<span class="pill" style="border-color:{pr["color"]};color:{pr["color"]}">'
                f'{_esc((pr.get("glyph") + " ") if pr.get("glyph") else "")}{_esc(pr.get("short", sec.get("kind","")))}</span>')
        rows = []
        for m in members:
            head = (f'<a href="{m["href"]}">{_esc(m["title"])}</a>' if m["href"] else _esc(m["title"]))
            rows.append(f'<div class="strow"><b>{head}</b> <span class="muted small">{_esc(m["kind"])}</span>'
                        f'<div class="muted small" style="margin-top:3px">{_esc((m["summary"] or "")[:240])}</div></div>')
        note_html = f'<p class="lead">{_esc(sec.get("note",""))}</p>' if sec.get("note") else ""
        body = (f'<div class="page"><div class="card"><h1 class="h1">{_esc(sec["title"])}</h1>'
                f'<div style="margin:6px 0 14px">{chip} <span class="muted small">{len(members)} Knoten</span></div>'
                f'{note_html}</div><div style="margin-top:14px">{"".join(rows) or _empty_state("Section", "Keine Mitglieder.")}</div></div>')
        return _layout(sec["title"], body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (sec["title"], None)],
                       active="projects")

    @app.get("/notes/{note_id}", response_class=HTMLResponse)
    def note_view(note_id: str) -> str:
        store = Store()
        from .. import presentation as _pres
        pr = _pres.present("note")           # label/color/glyph from data (no hardcoded vocab)
        klabel = pr.get("label") or "note"
        try:
            data = services.get_note(note_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(klabel, t("runtime_maybe_cleared")), store, active="projects")
        note, proj = data["note"], data["project"]
        body = (f'<div class="page"><div class="card">'
                f'<div style="margin-bottom:8px"><span class="pill" style="border-color:{pr["color"]};color:{pr["color"]}">'
                f'{_esc((pr.get("glyph") + " ") if pr.get("glyph") else "")}{_esc(klabel)}</span></div>'
                f'<h1 class="h1">{_esc(note.get("title",""))}</h1>'
                f'<div class="es-prose" style="margin-top:10px">{_md(note.get("text",""))}</div>'
                f'<div class="muted small" style="margin-top:14px">{_esc(note.get("created_at","")[:10])}</div></div></div>')
        return _layout(note.get("title") or klabel, body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (klabel, None)],
                       active="projects")

    @app.get("/prototypes/{slug}", response_class=HTMLResponse)
    def prototype_view(slug: str) -> str:
        store = Store()
        try:
            p = services.get_prototype_artifact(slug, store=store)
        except Exception:
            return _layout(t("not_found"), _empty_state(t("prototypes_h"), t("runtime_maybe_cleared")), store, active="projects")
        crumbs = [(t("projects"), "/projects")]
        proj = store.get_research_project(p["project_id"]) if p.get("project_id") else None
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((p["name"], None))
        _ap = _artifact_present(p)
        fid = f'<span class="pill">{_esc(_ap["disc"] or _ap["label"])}</span>'
        src = f'/proto-files/{_esc(slug)}/{_esc(p.get("entry", "index.html"))}'
        sessions = store.list_prototype_sessions(prototype_id=p["id"])
        sl = []
        for s in sessions:
            r = s.get("reaction", {})
            gv = "✓ grounded" if s.get("grounded_verified") else "○ unbestätigt"
            liked = "".join(f"<li>👍 {_esc(x)}</li>" for x in (r.get("liked") or [])[:3])
            fric = "".join(f"<li>⚠ {_esc(x)}</li>" for x in (r.get("friction") or [])[:3])
            sl.append(f'<div class="strow"><b>{_esc(s.get("persona_id",""))}</b> '
                      f'<span class="muted small">{gv}</span><div class="small" style="margin-top:3px">'
                      f'{_esc(str(r.get("verdict","")))}</div><ul class="small" style="margin:4px 0 0 16px">{liked}{fric}</ul></div>')
        sessions_html = ("".join(sl)) or f'<div class="muted small">— {t("prototypes_h")}: keine Sessions —</div>'
        body = (
            f'<div class="page"><h1 class="h1">{_esc(p["name"])} {fid} '
            f'<span class="muted small">{_esc(p.get("version",""))} · {_esc(slug)}</span></h1>'
            f'<p class="lead"><a class="btn" href="{src}" target="_blank">{_icon("projects")} In neuem Tab öffnen ↗</a></p>'
            f'<div class="protoframe"><iframe src="{src}" title="{_esc(p["name"])}" loading="lazy"></iframe></div>'
            f'<div class="card" style="margin-top:16px"><b>{t("prototypes_h")} · Sessions ({len(sessions)})</b>'
            f'<div style="margin-top:8px">{sessions_html}</div></div></div>')
        return _layout(p["name"], body, store, crumbs=crumbs, active="projects")
