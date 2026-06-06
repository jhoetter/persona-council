from __future__ import annotations

from collections import Counter
from datetime import date, timedelta

from .. import services
from ..storage import Store
from ._i18n import t, _lang
from ._components import (
    _esc, _icon, _avatar, _label, _pills, _md, _layout, _empty_state, _doc, _list_page,
    _star, _stance_color, _EDGE_COLORS, _theme_color, _artifact_present, _study_lead, _hero,
)
from ._synthesis import (
    _area, _vote_label, _sentiment_section, _synthesis_html, _persona_voices_html,
)
from ._graph import _graph_interactive, _plan_html, _outline_html
from ..presentation import glyph_icon
from ._detail import _relations_html, _properties_html, _session_card
from ._rail import _page_rail
from ._routes_lists import _projects_page, _persona_row
from ._html import raw, h, fragment
from ._vm import study_head


# ----------------------------- calendar helpers ----------------------------- #
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


def register_pages(app) -> None:
    from fastapi import Query
    from fastapi.responses import HTMLResponse

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        # Home is the Projects list (project-centric IA; Overview removed).
        return _projects_page()

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
              raw(_pills([x["issue"] for x in data["pain_points"]] or p["pain_points"]))),
            h("div", {"class_": "sec", "id": "tools"}, h("h2", {}, t("tools")), raw(_pills(p["tools"]))),
            h("div", {"class_": "sec", "id": "bez"}, h("h2", {}, t("relationships")), rel_rows),
            h("div", {"class_": "sec", "id": "cal"}, h("h2", {}, t("calendar")),
              h("p", {"class_": "muted"}, date_links or t("no_days_yet")),
              raw(_calendar_tabs(p["id"], selected_date, view)),
              raw(_period_calendar_html(p["id"], selected_date, view, period))))
        props = _properties_html([
            ("personas", t("role"), _esc(p["role"]["title"])),
            ("projects", t("industry"), _esc(p["company_context"]["industry"])),
            ("dot", t("size"), _esc(p["company_context"].get("size", ""))),
            ("memory", t("memory"), f'<a class="bc-link" href="/personas/{_esc(p["id"])}/memory">{_icon("memory")} {t("open")}</a>'),
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
        main = f"""
        {_hero(a["task"], sub=f'{a["timestamp"]} · {a["event_type"]} · {a.get("collaboration_mode","unknown")}')}
        <div class="grid two">
          <div class="card"><h3>{t("what_happened")}</h3><p>{_esc(a.get("what_happened", a["summary"]))}</p></div>
          <div class="card"><h3>{t("thought")}</h3><p class="thought">{_esc(a.get("persona_thought","—"))}</p></div></div>
        <div class="sec"><h2>{t("conversation")}</h2>{''.join(f'<div class="quote"><strong>{_esc(c.get("speaker",""))}</strong><br>{_esc(c.get("text",""))}</div>' for c in a.get("conversation", [])) or f'<p class="muted">{t("none_f")}</p>'}</div>
        <div class="grid"><div class="card"><h3>{t("actions")}</h3>{_pills(a.get("actions_done", [])) or '—'}</div>
          <div class="card"><h3>{t("artifacts")}</h3>{_pills(a.get("artifacts_touched", [])) or '—'}</div>
          <div class="card"><h3>{t("open_loops")}</h3>{_pills(a.get("open_loops", [])) or '—'}</div></div>
        """
        props = _properties_html([
            ("personas", t("persona"), f'<a class="bc-link" href="/personas/{_esc(p["id"])}">{_esc(p["display_name"])}</a>'),
            ("square", t("tool"), _esc(a["tool"])),
            ("dot", t("mood"), _esc(a["impact"]["mood"])),
            ("personas", t("participants"), _pills(a.get("participants", []) or [alone_label])),
            ("check", t("decision"), _esc(a.get("decision") or "")),
        ], aside=True)
        return _layout(a["task"], _doc(main, rail=props), store,
                       crumbs=[(t("personas"), "/personas"), (p["display_name"], f'/personas/{p["id"]}'), (a["task"][:46], None)], active="personas")

    @app.get("/councils", response_class=HTMLResponse)
    def councils() -> str:
        store = Store()
        rows = []
        for c in services.list_councils(store=store):
            v = c["votes"]; tot = max(1, sum(v.values()))
            bar = h("span", {"class_": "votebar", "title": f'SUPPORT {v["SUPPORT"]} · MAYBE {v["MAYBE"]} · OPPOSE {v["OPPOSE"]}'},
                    h("i", {"style": f'width:{v["SUPPORT"]/tot*100}%;background:var(--green)'}),
                    h("i", {"style": f'width:{v["MAYBE"]/tot*100}%;background:var(--amber)'}),
                    h("i", {"style": f'width:{(v["OPPOSE"]+v["ABSTAIN"])/tot*100}%;background:var(--muted)'}))
            rows.append(h("a", {"class_": "row", "href": f'/councils/{c["id"]}'},
                          h("span", {"class_": "rico", "style": "color:var(--blue)"}, raw(_icon("councils"))),
                          h("span", {"class_": "title"}, c["prompt"]),
                          h("span", {"class_": "right"}, bar, h("span", {}, f'{c["personas"]} {t("personas")}'),
                            h("span", {}, c["created_at"][:10]),
                            raw(_star("council", c["id"], c["prompt"][:60], f"/councils/{c['id']}")))))
        return _list_page(store, title=t("councils"), lead=t("councils_lead"), rows=rows,
                          empty_icon="councils", empty_msg=t("no_councils"), active="councils")

    @app.get("/councils/{session_id}", response_class=HTMLResponse)
    def council_detail(session_id: str) -> str:
        store = Store()
        session = store.get_council_session(session_id)
        if not session:
            return _layout(t("not_found"), _empty_state(t("council_not_found"), t("runtime_maybe_cleared")), store, active="councils")
        voices_detail_h = t("voices_in_detail", n=len({tn.get("persona_id") for tn in session["turns"] if tn.get("persona_id")}))
        proposal_short_h = t("proposal_short_summary")
        proposal_h = t("proposal"); summary_h = t("summary")
        sentiment_title = t("sentiment_this_council")
        vote_h = t("vote"); personas_h = t("personas"); created_h = t("created")
        councils_crumb = t("councils"); council_title = t("councils")
        # Each voice shows WHO the persona is + the life-context that shaped them (the per-persona
        # "input") and any recorded input snapshot, so you can see what each was given → what they said.
        pmap = {pid: store.get_persona(pid) for pid in session.get("persona_ids", [])}

        def _is_mod(tn: dict) -> bool:
            return (tn.get("speaker") == "Moderator" or tn.get("stance") in ("moderation", "moderator")
                    or tn.get("type") == "moderator")

        def _qidx(tn: dict):
            """Which moderator question this answer addresses (index into session.questions), or None."""
            q = tn.get("question_index", tn.get("question_idx"))
            return q if isinstance(q, int) and not isinstance(q, bool) else None

        def _answer_html(tn: dict) -> str:
            """One answer (a single turn): optional input snapshot, the text, concerns, memory refs."""
            body = tn.get("content") or tn.get("text") or tn.get("message") or ""   # tolerate body field variants
            given = tn.get("input") or tn.get("context_given") or ""
            given_html = h("details", {"class_": "turn-input"},
                           h("summary", {"class_": "muted small"}, t("council_input_given")),
                           h("p", {"class_": "muted small", "style": "white-space:pre-wrap"}, given)) if given else None
            concerns = fragment(*(h("p", {"class_": "muted small"}, f"• {q}")
                                  for q in (tn.get("questions_or_pushback") or [])[:4]))
            mrefs = (tn.get("memory_refs") or tn.get("memory_used") or [])[:3]
            mem = h("p", {"class_": "muted small"}, raw(_icon("memory")), " ", t("council_drew_on"),
                    ": ", ", ".join(mrefs)) if mrefs else None
            return h("div", {"class_": "turn-ans"}, given_html, h("p", {}, body), concerns, mem)

        def _persona_head(pid, tns: list) -> str:
            """Avatar + name + life-context + first declared stance, for a persona's answer block."""
            p = pmap.get(pid)
            stance_src = next((x for x in tns if x.get("stance") and not _is_mod(x)), None)
            stance = _label(stance_src["stance"], _stance_color(stance_src["stance"])) if stance_src else ""
            if not p:
                return fragment(h("b", {}, tns[0].get("speaker", "")), " ", stance)
            seg = p.get("segment") or {}
            desc = " · ".join(x for x in [seg.get("lebensphase"), seg.get("einstellung")] if x)[:130] \
                or (p.get("source_description") or "")[:130]
            return fragment(
                h("a", {"href": f'/personas/{p["id"]}', "class_": "turn-who"},
                  _avatar(p, 26), h("b", {}, p.get("display_name") or tns[0].get("speaker", ""))),
                " ", stance, h("div", {"class_": "muted small turn-ctx"}, desc))

        def _by_persona(tlist: list) -> list:
            order, by = [], {}
            for tn in tlist:
                pid = tn.get("persona_id")
                if pid not in by:
                    by[pid] = []; order.append(pid)
                by[pid].append(tn)
            return [(pid, by[pid]) for pid in order]

        def _answer_block(pid, tns: list) -> str:
            return h("div", {"class_": "qa-ans"}, h("div", {"class_": "qa-who hd"}, _persona_head(pid, tns)),
                     fragment(*(_answer_html(tn) for tn in tns)))

        answer_turns = [tn for tn in session["turns"] if not _is_mod(tn) and tn.get("persona_id")]
        questions = session.get("questions") or []
        in_range = lambda tn: (_qidx(tn) is not None and 0 <= _qidx(tn) < len(questions))
        indexed = [tn for tn in answer_turns if in_range(tn)]
        help_html = h("p", {"class_": "muted small", "style": "margin:-4px 0 12px"}, t("council_voices_help"))

        if questions and answer_turns and len(indexed) >= 0.6 * len(answer_turns):
            # MODERATED TRANSCRIPT — one round per moderator question: the question (moderator's voice),
            # then the persona answers that addressed it. This is the "how they discussed with the
            # moderator" view; it needs a per-answer question_index (future councils set it — see
            # record_council). Existing councils without indices use the per-persona fallback below.
            rounds = []
            for qi, q in enumerate(questions):
                qts = [tn for tn in answer_turns if _qidx(tn) == qi]
                if not qts:
                    continue
                ans = fragment(*(_answer_block(pid, ts) for pid, ts in _by_persona(qts)))
                rounds.append(h("div", {"class_": "qround"},
                                h("div", {"class_": "qround-q"}, raw(_icon("compass")),
                                  h("div", {}, h("div", {"class_": "qround-n"}, f'{t("question")} {qi + 1}'), h("p", {}, q))),
                                h("div", {"class_": "qround-a"}, ans)))
            rest = [tn for tn in answer_turns if not in_range(tn)]
            if rest:
                ans = fragment(*(_answer_block(pid, ts) for pid, ts in _by_persona(rest)))
                rounds.append(h("div", {"class_": "qround"},
                                h("div", {"class_": "qround-q"}, raw(_icon("bulb")),
                                  h("div", {}, h("div", {"class_": "qround-n"}, t("further_answers")))),
                                h("div", {"class_": "qround-a"}, ans)))
            turns_html = fragment(help_html, h("div", {"class_": "qrounds"}, fragment(*rounds)))
        else:
            # FALLBACK — one clean card per persona (a persona answering several questions used to
            # render as several identical-header blocks). Moderator turns stand on their own.
            grouped: list[tuple] = []
            idx_of: dict = {}
            for tn in session["turns"]:
                pid = tn.get("persona_id")
                if _is_mod(tn) or not pid:
                    grouped.append((pid, [tn], _is_mod(tn)))
                elif pid in idx_of:
                    grouped[idx_of[pid]][1].append(tn)
                else:
                    idx_of[pid] = len(grouped); grouped.append((pid, [tn], False))
            cards = [h("div", {"class_": f'turn{" mod" if is_mod else ""}'},
                       h("div", {"class_": "hd"}, _persona_head(pid, tns)),
                       fragment(*(_answer_html(tn) for tn in tns)))
                     for pid, tns, is_mod in grouped]
            turns_html = fragment(help_html, h("div", {"style": "display:grid;gap:12px"}, fragment(*cards)))
        n_voices = len(session.get("persona_ids", []))
        # A council has THREE honest shapes (derived, no stored type): DISCOVERY (open questions →
        # answers, no vote — listening), EVALUATION (react to a concept), DECISION (a motion put to a
        # vote). Lead the page with the right framing so "what is the question?" is always answered.
        vm = study_head(session)                       # shared study view-model (question/answer/mode)
        mode = vm["mode"]
        exec_html = _md(vm["answer_md"])
        voices_label = t("council_voices_answers") if mode == "discovery" else voices_detail_h
        if mode == "discovery":
            qs = session.get("questions") or ([session.get("prompt")] if session.get("prompt") else [])
            qlist = "".join(f'<li>{_esc(q)}</li>' for q in qs) or f'<li class="muted">—</li>'
            lead_block = (f'<div class="es"><div class="eyebrow">{t("council_questions_h")}</div>'
                          f'<ul class="es-prose">{qlist}</ul>'
                          f'<p class="muted small">{t("council_questions_help", n=n_voices)}</p></div>')
            sentiment = ""                                    # a listening session has no vote/sentiment chart
        else:
            motion = (session.get("proposal") or "").strip()
            label = t("council_eval_h") if mode == "evaluation" else t("council_motion")
            help_ = t("council_eval_help", n=n_voices) if mode == "evaluation" else t("council_motion_help", n=n_voices)
            lead_block = (f'<div class="es"><div class="eyebrow">{label}</div>'
                          f'<div class="es-prose">&bdquo;{_esc(motion)}&ldquo;</div>'
                          f'<p class="muted small">{help_}</p></div>') if motion else ""
            sentiment = _sentiment_section(store, [session], title=sentiment_title) or ""
        council_sub = f'{t("council_kicker_" + mode, n=n_voices)} · {session["selection_reason"]}'
        main = (f'{_hero(session["prompt"], sub=council_sub, hid="sec-question")}'
                f'{lead_block}'
                f'{_study_lead(exec_html, vm["answer_label"])}'
                f'{sentiment}'
                f'<div class="sec" id="stimmen"><h2>{voices_label}</h2>{turns_html}</div>'
                f'<details class="sec"><summary>{summary_h}</summary><div class="card"><strong>{summary_h}</strong><p>{_esc(session["summary"])}</p></div></details>')
        prop_rows = [("councils", t("type_h"), t("council_mode_" + mode)), ("personas", personas_h, str(n_voices))]
        if mode != "discovery":                               # the vote panel only where a vote/reaction exists
            vc = {v: sum(1 for x in session["votes"] if str(x.get("vote", "")).upper() == v) for v in ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]}
            prop_rows += [("dot", _vote_label(k), str(vc[k])) for k in vc]
        prop_rows.append(("dot", created_h, _esc(session["created_at"][:10])))
        cprops = _properties_html(prop_rows, aside=True)
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
        rel = _relations_html(store, f"council:{session_id}", proj["id"] if proj else None, aside=True)
        crail = [("sec-question", t("question")), ("stimmen", t("voices"))]
        if rel:
            crail.append(("sec-relations", t("relations")))
        if cprops:
            crail.append(("sec-properties", t("properties")))
        return _layout(council_title, _doc(main, rail=rel + cprops) + _page_rail(crail), store,
                       crumbs=crumbs, active="projects",
                       actions=_star("council", session_id, session["prompt"][:60], f"/councils/{session_id}"))

    @app.get("/syntheses", response_class=HTMLResponse)
    def syntheses() -> str:
        store = Store()
        rows = []
        for s in store.list_syntheses():
            done = s.get("status", "done") == "done"
            rows.append(h("a", {"class_": "row", "href": f'/syntheses/{s["id"]}'},
                          h("span", {"class_": "rico", "style": "color:var(--violet)"}, raw(_icon("syntheses"))),
                          h("span", {"class_": "title"}, s["title"]),
                          h("span", {"class_": "right"},
                            _label(t("done") if done else t("running"), "var(--green)" if done else "var(--amber)"),
                            h("span", {}, f'{len(s.get("council_ids", []))} {t("councils")}'),
                            h("span", {}, s["created_at"][:10]),
                            raw(_star("synthesis", s["id"], s["title"], f"/syntheses/{s['id']}")))))
        return _list_page(store, title=t("syntheses"), lead=t("syntheses_lead"), rows=rows,
                          empty_icon="syntheses", empty_msg=t("no_synthesis"), active="syntheses")

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
        rel = _relations_html(store, f"synthesis:{synthesis_id}", proj["id"] if proj else None, aside=True)
        props = _properties_html([
            ("check", t("status"), t("done") if syn.get("status", "done") == "done" else t("running")),
            ("councils", t("councils"), str(len(syn.get("council_ids", [])))),
            ("dot", t("created"), _esc(syn.get("created_at", "")[:10])),
            ("projects", t("project"),
             (f'<a href="/projects/{_esc(proj["id"])}">{_esc(proj["title"])}</a>' if proj else "—")),
        ], aside=True)
        content, toc = _synthesis_html(store, syn)
        body = _doc(content, rail=props + rel) + _page_rail(toc)
        return _layout(syn["title"], body, store,
                       crumbs=crumbs, active="projects", actions=actions)

    @app.get("/projects", response_class=HTMLResponse)
    def projects() -> str:
        return _projects_page()

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_detail(project_id: str, view: str = "list") -> str:
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
        protos = graph.get("prototypes") or []
        # Q4: a TYPE filter row (also the LEGEND) — every node KIND present is a colored, glyph'd,
        # toggleable chip that filters the graph by type; capability/theme tags go to a 2nd muted row.
        type_meta: dict[str, tuple] = {}      # type -> (color, label, glyph)
        for n in graph["nodes"]:
            nt = n.get("note_kind") if str(n["study_id"]).startswith("note:") else str(n["study_id"]).split(":", 1)[0]
            if nt and nt not in type_meta:
                type_meta[nt] = (n.get("color", "#9aa0a6"), n.get("kind_label", nt), n.get("glyph", ""))
        if protos:
            ap0 = _artifact_present(protos[0])
            type_meta["prototype"] = (ap0["color"], t("prototypes_h"), ap0.get("glyph", ""))
        type_tagset = set(type_meta)
        type_chips = "".join(
            f'<button class="rgchip" data-theme="{_esc(ty)}" style="--c:{c}">{(_icon(glyph_icon(g)) + " ") if g else ""}{_esc(lab)}</button>'
            for ty, (c, lab, g) in type_meta.items())
        node_tags = []
        for n in graph["nodes"]:
            for tgx in n.get("theme_tags", []):
                if tgx not in node_tags and tgx not in type_tagset:
                    node_tags.append(tgx)
        tag_vocab = list(dict.fromkeys((proj.get("themes") or []) + node_tags))
        tag_chips = "".join(
            f'<button class="rgchip tagchip" data-theme="{_esc(th)}" style="--c:{_theme_color(th, tag_vocab)}">{_esc(th)}</button>'
            for th in tag_vocab)
        left = (f'<span class="ptlabel">{_icon("search")} {t("type_h")}</span>{type_chips}'
                + (f'<span class="ptlabel ptlabel-2">{t("tags_h")}</span>{tag_chips}' if tag_chips else "")
                + f'<a class="rgclear" style="display:none">{t("clear_filter")}</a>') if type_chips else ""
        oqbtn = f'<button class="btn" id="oqbtn">{t("legend")} · {t("open_questions_h")} ({len(oqs)})</button>'
        toolbar = f'<div class="ptoolbar">{left}<span class="spacer"></span>{oqbtn}{meta_btn}</div>'
        # Artifact viewer: artifacts + recorded persona sessions (read-only).
        proto_html = ""
        if protos:
            rows = []
            for p in protos:
                sess = store.list_prototype_sessions(prototype_id=p["id"])
                run_badge = ('<span class="pill" style="border-color:#3d7b5f">running</span>'
                             + f' <a href="{_esc(p["url"])}" target="_blank">open {_icon("external")}</a>' if p.get("running") and p.get("url") else "")
                sl = []
                for s in sess[:6]:
                    r = s.get("reaction", {})
                    gv = _icon("check") if s.get("grounded_verified") else _icon("circle")
                    nm = r.get("persona") or (store.get_persona(s.get("persona_id", "")) or {}).get("display_name") or s.get("persona_id", "")
                    sl.append(f'<li><b>{_esc(nm)}</b>: {_esc(str(r.get("verdict") or r.get("reaction_text") or ""))[:80]} '
                              f'<span class="muted small">{gv} grounded</span></li>')
                sl_html = ("<ul style='margin:4px 0 0 18px'>" + "".join(sl) + "</ul>") if sl else '<div class="muted small">— keine Sessions —</div>'
                ap = _artifact_present(p)
                pill = ap["disc"] or ap["label"]
                rows.append(f'<div class="strow"><a href="/prototypes/{_esc(p["slug"])}">{_icon("projects")}<b>{_esc(p["name"])}</b></a> '
                            f'<span class="pill">{_esc(pill)}</span> <span class="muted small">{_esc(p.get("version",""))}</span> '
                            f'<a class="btn" style="padding:2px 8px" href="/prototypes/{_esc(p["slug"])}">ansehen {_icon("external")}</a>{sl_html}</div>')
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
            gap_str = (f'<div class="muted small" style="margin-top:4px">{t("gaps")}: '
                       + "; ".join(_esc(g) for g in gaps[:4]) + "</div>") if gaps else ""
            pulse_html = (
                f'<div class="oqp-h">{t("pulse")}</div>'
                f'<div class="strow"><span class="pill">{_esc(ap["recommendation"])}</span> '
                f'<span class="muted small">{_esc(cov_str)} · {t("saturation")}: {_esc(ap["saturation"]["hint"])}</span>{gap_str}</div>')
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
        # THE project view = the Linear-style ROUND-grouped OUTLINE (clean, chronological, relationships
        # via indentation + hover-highlight). The spatial graph is retired from the UI but still reachable
        # by URL (?view=graph) — code kept, just unlinked — so nothing is destroyed and it's reversible.
        is_graph = view == "graph"
        head_tools = (f'<div class="ptoolbar"><span class="spacer"></span></div>{toolbar}'
                      if is_graph else f'<div class="ptoolbar"><span class="spacer"></span>{meta_btn}</div>')
        main_view = (f'<div class="graphcard proj-graph">{_graph_interactive(graph)}</div>{panel}{oq_js}'
                     if is_graph else f'<div class="outlinecard">{_outline_html(graph)}</div>')
        body = (
            f'<div class="proj">'
            f'<div class="proj-head"><h1 class="h1">{_esc(proj["title"])}</h1>'
            f'<p class="lead">{_esc(proj.get("goal", ""))}</p>'
            f'{head_tools}</div>'
            f'{main_view}'
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
        note_sub = f'<p class="sub">{_esc(sec.get("note",""))}</p>' if sec.get("note") else ""
        sprops = _properties_html([
            ("dot", t("type_h"), _esc(pr.get("short", sec.get("kind", "")))),
            ("projects", t("project"), f'<a href="/projects/{_esc(proj["id"])}">{_esc(proj["title"])}</a>'),
        ], aside=True)
        sec_sub = raw(f'{chip} <span class="muted small">{t("n_nodes", n=len(members))}</span>')
        main = (f'{_hero(sec["title"], sub=sec_sub)}{note_sub}'
                f'<div style="margin-top:8px">{"".join(rows) or _empty_state(t("section"), t("no_members"))}</div>')
        return _layout(sec["title"], _doc(main, rail=sprops), store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (sec["title"], None)],
                       active="projects")

    @app.get("/notes/{note_id}", response_class=HTMLResponse)
    @app.get("/concepts/{note_id}", response_class=HTMLResponse)        # a concept is a note with kind=concept
    def note_view(note_id: str) -> str:
        store = Store()
        from .. import presentation as _pres
        try:
            data = services.get_note(note_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("not_found"), t("runtime_maybe_cleared")), store, active="projects")
        note, proj = data["note"], data["project"]
        kind = note.get("kind") or "note"                              # present by the record's OWN kind
        pr = _pres.present(kind)
        klabel = t("concept_h") if kind == "concept" else (t("notes_h") if kind == "note" else (pr.get("label") or kind))
        active = "concept" if kind == "concept" else "projects"
        proj_link = f'<a href="/projects/{_esc(proj["id"])}">{_esc(proj["title"])}</a>'
        nprops = _properties_html([
            ("dot", t("created"), _esc(note.get("created_at", "")[:10])),
            ("projects", t("project"), proj_link),
        ], aside=True)
        nrel = _relations_html(store, f"note:{note_id}", proj["id"], aside=True)
        pill = (f'<div style="margin-bottom:6px"><span class="pill" style="border-color:{pr["color"]};color:{pr["color"]}">'
                f'{_esc((pr.get("glyph") + " ") if pr.get("glyph") else "")}{_esc(klabel)}</span></div>')
        main = (f'{_hero(note.get("title",""), hid="sec-content", top=pill)}'
                f'<div class="es-prose" style="margin-top:4px">{_md(note.get("text",""))}</div>')
        nrail = [("sec-content", klabel)]
        if nprops:
            nrail.append(("sec-properties", t("properties")))
        if nrel:
            nrail.append(("sec-relations", t("relations")))
        body = _doc(main, rail=nprops + nrel) + _page_rail(nrail)
        return _layout(note.get("title") or klabel, body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f'/projects/{proj["id"]}'), (klabel, None)],
                       active=active)

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
        sessions_html = ("".join(_session_card(store, s) for s in sessions)
                         or f'<div class="muted small">— {t("prototypes_h")}: {t("no_sessions")} —</div>')
        proto_title = raw(f'{_esc(p["name"])} {fid}')
        proto_sub = f'{p.get("version","")} · {slug}'
        main = (
            f'{_hero(proto_title, icon="prototype", sub=proto_sub)}'
            f'<p style="margin:8px 0 16px"><a class="btn" href="{src}" target="_blank">{_icon("projects")} {t("open_in_new_tab")} {_icon("external")}</a></p>'
            f'<div class="protoframe"><iframe src="{src}" title="{_esc(p["name"])}" loading="lazy"></iframe></div>'
            f'<div class="sec" id="sec-sessions" style="margin-top:22px"><h2>{t("prototypes_h")} · {t("sessions")} ({len(sessions)})</h2>'
            f'<div style="margin-top:8px">{sessions_html}</div></div>')
        concept_in = []
        if proj:                                              # the concept that realises this prototype
            try:
                g = services.get_project_graph(p["project_id"], store=store)
                concept_in = [n for n in g["nodes"] if n.get("prototype_id") == p["id"]]
            except Exception:
                concept_in = []
        n_grounded = sum(1 for s in sessions if s.get("grounded_verified"))
        proj_link = (f'<a href="/projects/{_esc(proj["id"])}">{_esc(proj["title"])}</a>' if proj else "—")
        prop_html = _properties_html([
            ("square", t("fidelity"), _esc(_ap.get("disc") or _ap.get("label") or "")),
            ("personas", t("sessions"), str(len(sessions))),
            ("check", t("grounded_yes"), f"{n_grounded}/{len(sessions)}" if sessions else "—"),
            ("projects", t("project"), proj_link),
        ], aside=True)
        rel_html = _relations_html(store, f"prototype:{p['id']}", p.get("project_id"), extra_in=concept_in, aside=True)
        rail = [("sec-sessions", t("sessions"))]
        if prop_html:
            rail.append(("sec-properties", t("properties")))
        if rel_html:
            rail.append(("sec-relations", t("relations")))
        body = _doc(main, rail=prop_html + rel_html) + _page_rail(rail)
        return _layout(p["name"], body, store, crumbs=crumbs, active="prototype")
