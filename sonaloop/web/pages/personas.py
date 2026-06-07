"""Persona pages: list, detail, memory, activity (spec/roadmap.md R2)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from ._calendar import _calendar_tabs, _period_calendar_html
from .._render import render_findings
from .._html import register_css
from ... import artifacts as _artifacts

# Memory panel — a temporal knowledge graph (entities + fact timelines, superseded facts struck).
register_css(r"""
.mem-bar{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 22px}
.mem-tool{display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:8px;padding:6px 10px;background:var(--panel)}
.mem-tool svg{width:15px;height:15px;color:var(--muted);flex:none}
.mem-tool input{border:0;background:transparent;padding:2px 0;font-size:var(--t-body);color:var(--ink)}
.mem-tool input:focus{outline:none}.mem-tool input[type=text]{min-width:236px}
.mem-group{margin:0 0 22px}
.mem-group-h{display:flex;align-items:center;gap:7px;font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600;margin:0 0 10px}
.mem-n{color:var(--faint);font-weight:550}
.mem-ents{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}
.mem-ent{border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:13px 15px}
.mem-ent-h{display:flex;align-items:center;gap:8px;margin:0 0 11px}
.mem-ent-h svg{width:15px;height:15px;color:var(--muted);flex:none}.mem-ent-h b{font-size:var(--t-body)}
.mem-status{margin-left:auto;font-size:var(--t-xs);color:var(--accent);background:var(--accent-weak);border-radius:99px;padding:1px 9px;font-weight:500;white-space:nowrap}
.mem-tl{display:flex;flex-direction:column;gap:8px;position:relative;padding-left:15px}
.mem-tl::before{content:"";position:absolute;left:3px;top:5px;bottom:5px;border-left:1.5px solid var(--line-2)}
.mem-fact{display:flex;gap:9px;font-size:var(--t-sm);position:relative}
.mem-fact::before{content:"";position:absolute;left:-15px;top:5px;width:7px;height:7px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 2px var(--panel)}
.mem-fact.sup::before{background:var(--line-2)}
.mem-date{flex:none;color:var(--muted);font-variant-numeric:tabular-nums;min-width:74px}
.mem-fx{color:var(--ink)}
.mem-fact.sup .mem-fx{color:var(--faint);text-decoration:line-through;text-decoration-color:var(--line-2)}
.mem-loops{border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.mem-loop{display:flex;align-items:center;gap:9px;padding:9px 13px;font-size:var(--t-body)}
.mem-loop+.mem-loop{border-top:1px solid var(--line)}
.mem-loop-dot{flex:none;width:6px;height:6px;border-radius:50%;background:var(--amber)}
.mem-pane{border:1px solid var(--line);border-radius:10px;background:var(--panel-2);padding:12px 15px;margin:0 0 16px}
.mem-pane-h{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600;margin:0 0 8px}
.mem-hit{padding:7px 0;font-size:var(--t-sm)}.mem-hit+.mem-hit{border-top:1px solid var(--line-2)}
.mem-quality{margin-top:26px;border-top:1px solid var(--line);padding-top:13px}
.mem-quality summary{cursor:pointer;color:var(--muted);font-size:var(--t-sm);font-weight:600;list-style:none}
.mem-quality summary::-webkit-details-marker{display:none}
.mem-quality p{margin:9px 0;font-size:var(--t-sm)}
""")


_MEM_KINDS = [("project", "briefcase"), ("person", "contact"), ("topic", "tag"), ("tool", "settings")]


def _mem_kind_label(kind: str) -> str:                      # explicit t() calls so the i18n usage scan sees them
    return {"project": t("active_projects"), "person": t("mem_people"),
            "topic": t("mem_topics"), "tool": t("mem_tools")}.get(kind, kind)


def _memory_html(store: Store, persona_id: str, as_of: str | None, q: str | None) -> str:
    p = store.get_persona(persona_id)
    if not p:
        return _empty_state(t("profile_not_found"), t("runtime_maybe_cleared"), icon="memory")
    pid = p["id"]
    sup_label = _label(t("outdated"), "var(--muted)", "outline", False)        # superseded fact tag

    # --- the knowledge graph: entities grouped by kind, each a timeline of facts (newest first;
    #     superseded facts dimmed + struck so the persona's belief CHANGES read at a glance) ---
    by_kind: dict[str, list] = {}
    for e in store.list_entities(pid):
        by_kind.setdefault(e.get("kind", ""), []).append(e)

    def _ent_card(e: dict, icon: str) -> str:
        facts = sorted(store.list_entity_facts(e["id"]), key=lambda f: f.get("t_valid", ""), reverse=True)
        rows = []
        for f in facts:
            sup = bool(f.get("t_invalid"))
            rows.append(h("div", {"class_": "mem-fact" + (" sup" if sup else "")},
                          h("span", {"class_": "mem-date"}, (f.get("t_valid") or "")[:10]),
                          h("span", {"class_": "mem-fx"}, f.get("fact", ""),
                            (fragment(" ", sup_label) if sup else None))))
        status = h("span", {"class_": "mem-status"}, e["status"]) if e.get("status") else None
        return h("div", {"class_": "mem-ent"},
                 h("div", {"class_": "mem-ent-h"}, raw(_icon(icon)), h("b", {}, e.get("name", "—")), status),
                 h("div", {"class_": "mem-tl"}, fragment(*rows)) if rows else h("p", {"class_": "muted small"}, "—"))

    know_secs = []
    for kind, icon in _MEM_KINDS:
        ents = by_kind.get(kind) or []
        if ents:
            know_secs.append(h("div", {"class_": "mem-group"},
                               h("div", {"class_": "mem-group-h"}, _mem_kind_label(kind), h("span", {"class_": "mem-n"}, str(len(ents)))),
                               h("div", {"class_": "mem-ents"}, fragment(*(_ent_card(e, icon) for e in ents)))))
    knowledge = fragment(*know_secs) if know_secs else h("p", {"class_": "muted"}, t("none"))

    # --- open threads (loops) ---
    loops = [h("div", {"class_": "mem-loop"}, h("span", {"class_": "mem-loop-dot"}), th["text"],
               h("span", {"class_": "muted small"}, f' · {t("since")} {(th.get("opened_on") or "")[:10]}'))
             for th in store.list_threads(pid, "open")[:20]]

    # --- compact toolbar: recall search + time-travel (one row, not two big cards) ---
    toolbar = h("div", {"class_": "mem-bar"},
        h("form", {"method": "get", "class_": "mem-tool"}, raw(_icon("search")),
          h("input", {"type": "text", "name": "q", "value": q or "", "placeholder": t("recall_placeholder")})),
        h("form", {"method": "get", "class_": "mem-tool"}, raw(_icon("clock")),
          h("input", {"type": "date", "name": "as_of", "value": as_of or ""}),
          h("button", {"class_": "btn btn-sm"}, t("show_state"))))
    panes = []
    if as_of:
        sa = services.get_state_at(pid, as_of, store=store)
        rows = [h("div", {"class_": "mem-fact"}, h("span", {"class_": "mem-date"}, e["kind"]),
                  h("span", {"class_": "mem-fx"}, h("b", {}, e["name"]), " → ", e.get("status_at") or "—"))
                for e in sa["entities"] if e.get("status_at")]
        panes.append(h("div", {"class_": "mem-pane"}, h("div", {"class_": "mem-pane-h"}, t("state_at", date=as_of)),
                       fragment(*rows) if rows else h("p", {"class_": "muted small"}, t("nothing_valid")),
                       h("p", {"class_": "muted small"}, t("open_threads_count", n=len(sa.get("open_threads", []))))))
    if q:
        hits = services.recall_memory(pid, q, store=store, k=8)["hits"]
        rows = [h("div", {"class_": "mem-hit"}, h("span", {"class_": "muted small"}, f'{hit["obj_type"]} · {hit.get("when") or ""}'),
                  h("div", {}, hit["text"])) for hit in hits]
        panes.append(h("div", {"class_": "mem-pane"}, h("div", {"class_": "mem-pane-h"}, t("recall")),
                       fragment(*rows) if rows else h("p", {"class_": "muted small"}, t("nothing"))))

    # --- quality (eval metadata) demoted to a collapsible footer ---
    struct = services.evaluate_simulation(pid, store=store, persist=False)
    crit = services.latest_critic_report(pid, store=store)
    struct_rows = fragment(*(_label(f'{c["name"]}: {c["status"]}', _stance_color(c["status"])) for c in struct["checks"]))
    crit_rows = (fragment(*(_label(f"{k}: {v}/5", "var(--green)" if v >= 4 else "var(--amber)") for k, v in crit["dimensions"].items()))
                 if crit else h("span", {"class_": "muted"}, t("no_critic_run")))
    quality = h("details", {"class_": "mem-quality"}, h("summary", {}, t("quality")),
                h("p", {}, h("strong", {}, f'{t("structure")}:'), " ", struct["verdict"], " ", struct_rows),
                h("p", {}, h("strong", {}, f'{t("critic")}:'), " ", crit_rows))

    main = fragment(
        _hero(t("memory_title", name=p["display_name"]), sub=t("memory_sub"), icon="memory"),
        toolbar, fragment(*panes),
        h("div", {"class_": "sec"}, h("h2", {}, t("knowledge")), knowledge),
        h("div", {"class_": "sec"}, h("h2", {}, t("open_threads")),
          h("div", {"class_": "mem-loops"}, fragment(*loops)) if loops else h("p", {"class_": "muted"}, t("none"))),
        quality)
    return _doc(main)



def register_personas(app) -> None:
    @app.get("/personas", response_class=HTMLResponse)
    def personas_list() -> str:
        store = Store()
        rows = [_persona_row(p, store) for p in services.list_personas(store=store)]
        return _list_page(store, title=t("personas"), lead=t("personas_lead"), rows=rows,
                          empty_icon="personas", empty_msg=t("no_personas"), active="personas")

    @app.get("/personas/{persona_id}", response_class=HTMLResponse)
    def persona_detail(persona_id: str, date_value: str | None = Query(default=None, alias="date"), view: str = Query(default="month")) -> str:
        store = Store()
        try:
            data = services.get_persona(persona_id, store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("profile_not_found"), t("persona_runtime_cleared"), icon="personas"), store, active="personas")
        p = data["persona"]
        state = services.get_current_state(p["id"], store=store)
        selected_date = date_value or (data["daily_summaries"][-1]["date"] if data["daily_summaries"] else date.today().isoformat())
        view = view if view in {"week", "month", "year"} else "month"
        period = services.get_calendar_period(p["id"], selected_date, view, store)
        avatar = (h("img", {"class_": "avatar", "src": f'/{p["avatar"]["path"]}', "alt": ""})
                  if p.get("avatar") else h("div", {}, _avatar(p, 120)))
        has_sim = bool(data["daily_summaries"]) or bool(period.get("days"))
        daycount = Counter()
        for e in store.list_experience_events(p["id"]):
            ts = e.get("timestamp") or ""
            if len(ts) >= 10:
                daycount[ts[:10]] += 1
        act_pts = [(d[5:], daycount[d]) for d in sorted(daycount)]
        # the year heatmap already IS "activity over time", so skip the redundant area chart there
        activity = (h("div", {"class_": "sec", "id": "aktivitaet"}, h("h2", {}, t("activity_over_time")),
                      h("p", {"class_": "ihint"}, t("activities_per_day", n=sum(daycount.values()))), _area(act_pts))
                    if (act_pts and view != "year") else "")
        voices = _persona_voices_html(store, p["id"])
        rel_rows = fragment(*(h("p", {}, h("strong", {}, r["name"]), " ",
                              h("span", {"class_": "muted"}, f'— {r["type"]}: {r["friction"]}')) for r in p["relationships"]))
        cal_section = h("div", {"class_": "sec", "id": "cal"}, h("h2", {}, t("calendar")),
            (fragment(raw(_calendar_tabs(p["id"], selected_date, view, period)),
                      raw(_period_calendar_html(p["id"], selected_date, view, period)))
             if has_sim else h("p", {"class_": "muted"}, t("no_days_yet"))))
        main = fragment(
            _hero(p["display_name"], sub=f'{p["role"]["title"]} · {p["company_context"]["industry"]}'),
            h("div", {"class_": "identity"}, h("div", {}, avatar), h("div", {},
              h("div", {"class_": "card"}, h("h3", {}, t("current_state")),
                h("p", {}, h("strong", {}, state["current_activity"])),
                h("p", {"class_": "muted small"}, " · ".join(x for x in [
                    state.get("current_tool"), state.get("collaboration_mode"),
                    (state["mood"] if state.get("mood") not in (None, "unknown") else None)] if x) or "—"),
                (h("p", {"class_": "thought"}, state["current_thought"])
                 if state.get("current_thought") not in (None, "", "unknown") else "")))),
            # the simulated LIFE (calendar + activity rhythm) is this persona's signature — surface it
            # right after the snapshot, before the analysis voices.
            cal_section, activity,
            raw(voices),
            h("div", {"class_": "sec", "id": "ziele"}, h("h2", {}, t("goals")), raw(_pills(p["goals"]))),
            h("div", {"class_": "sec", "id": "pains"}, h("h2", {}, t("pain_points")),
              # structured observations (issue + opportunity + severity/evidence) → the SAME finding row
              # as the synthesis; the plain profile list stays compact pills.
              (raw(render_findings([_artifacts.pain_point_finding(x) for x in data["pain_points"]]))
               if data["pain_points"] else raw(_pills(p["pain_points"])))),
            h("div", {"class_": "sec", "id": "tools"}, h("h2", {}, t("tools")), raw(_pills(p["tools"]))),
            h("div", {"class_": "sec", "id": "bez"}, h("h2", {}, t("relationships")), rel_rows))
        props = _properties_html([
            ("personas", t("role"), p["role"]["title"]),
            ("projects", t("industry"), p["company_context"]["industry"]),
            ("dot", t("size"), p["company_context"].get("size", "")),
            ("memory", t("memory"), h("a", {"class_": "bc-link", "href": f'/personas/{p["id"]}/memory'}, raw(_icon("memory")), " ", t("open"))),
        ], aside=True)
        prail = [("cal", t("calendar"))]
        prail += [("aktivitaet", t("activity_over_time"))] if activity else []
        prail += [("ziele", t("goals")), ("pains", t("pain_points")), ("tools", t("tools")),
                  ("bez", t("relationships")), ("sec-properties", t("properties"))]
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
            return _layout(t("not_found"), _empty_state(t("activity_not_found"), t("runtime_maybe_cleared"), icon="overview"), store, active="personas")
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
