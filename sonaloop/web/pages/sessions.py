"""Usability-session pages: list (+ cross-session funnel) and the replay view — walk the dual
timeline of one recorded session (ticket session-replay-inspector). The session is the deliverable;
this is where you consume it: one row per step (screen panel ⇄ action/think-aloud), friction layered
via the data-driven scale colors, per-step verdicts, and a friction rail that jumps to `#step-N`.
Screenshots are served read-only from data/sessions/ via /sessions-files (traversal-safe)."""
from __future__ import annotations

from pathlib import Path

from fastapi.responses import FileResponse, Response

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._components import _hifi
from .._render import render_statements
from .._synthesis import _stacked, _legend
from .._html import register_css
from ... import artifacts as _A
from ... import config as _config


# Co-located CSS: the dual-timeline replay (screen ⇄ action), friction rail, outcome banner, funnel.
# Friction accent rides on --sfc (set per step from friction_levels.json presentation.color); the
# targeted step highlights via pure CSS :target — no JS.
register_css(r"""
.sess-banner{display:flex;align-items:center;gap:10px;border:1px solid var(--line);border-left:3px solid var(--sbc,var(--line));border-radius:var(--radius);background:var(--panel);padding:10px 14px;margin:0 0 18px;font-size:var(--t-body)}
.sess-banner svg{width:16px;height:16px;flex:none;color:var(--sbc,var(--muted))}
.sess-rail{border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);padding:12px 15px;margin:0 0 18px}
.sess-rail-h{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.05em;color:var(--muted);font-weight:600;margin:0 0 8px}
.sess-rail a{display:flex;align-items:center;gap:9px;padding:5px 0;color:var(--ink);text-decoration:none;font-size:var(--t-sm);border-bottom:1px solid var(--line-2)}
.sess-rail a:last-child{border-bottom:0}
.sess-rail a:hover .sess-rail-note{color:var(--accent)}
.sess-rail-note{color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0;flex:1}
.sess-steps{display:flex;flex-direction:column;gap:14px}
.sess-step{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);border:1px solid var(--line);border-left:3px solid var(--sfc,var(--line));border-radius:var(--radius);background:var(--panel);overflow:hidden;scroll-margin-top:72px}
.sess-step:target{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-weak)}
.sess-screen{background:var(--panel-2);border-right:1px solid var(--line);padding:13px 15px;display:flex;flex-direction:column;gap:8px;min-width:0}
.sess-shot{display:block;max-width:100%;border:1px solid var(--line);border-radius:var(--radius-sm)}
.sess-screen-txt{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:var(--t-sm);line-height:1.5;white-space:pre-wrap;border:1px dashed var(--line);border-radius:var(--radius-sm);background:var(--panel);padding:10px 12px;max-height:230px;overflow:auto}
.sess-cap{color:var(--muted);font-size:var(--t-xs);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sess-act{padding:13px 15px;display:flex;flex-direction:column;gap:9px;min-width:0}
.sess-act-h{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.sess-n{flex:none;width:22px;height:22px;border-radius:50%;background:var(--accent-weak);color:var(--accent);font-size:var(--t-xs);font-weight:700;display:flex;align-items:center;justify-content:center}
.sess-target{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:var(--t-sm);color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sess-detail{color:var(--muted);font-size:var(--t-sm);margin:0}
.sess-mono{margin:0;border-left:3px solid var(--line-2);padding:2px 0 2px 12px;font-style:italic;font-size:var(--t-body);line-height:1.55}
.sess-foot{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:var(--t-sm);color:var(--muted);margin-top:auto}
.sess-funnel{border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);padding:14px 16px;margin:0 0 18px}
.sess-funnel h2{margin:0 0 2px;font-size:var(--t-body)}
.sess-frow{display:grid;grid-template-columns:90px 1fr 140px;gap:12px;align-items:center;padding:6px 0;font-size:var(--t-sm)}
.sess-frow .sfl{color:var(--muted)}
.sess-frow .sfn{text-align:right;color:var(--muted);font-variant-numeric:tabular-nums}
.sess-freason{grid-column:2/-1;color:var(--muted);font-size:var(--t-xs);padding:0 0 4px}
@media(max-width:760px){.sess-step{grid-template-columns:1fr}.sess-screen{border-right:0;border-bottom:1px solid var(--line)}}
""")


# Action type → icon (the recorder's code enum; see services._usability_sessions._ACTION_TYPES).
# The chip label resolves through i18n (t("action_" + type)) only for known enum members — an
# off-enum legacy token renders verbatim instead of painting a raw i18n key.
_ACTION_ICONS = {"look": "eye", "click": "target", "type": "pencil", "select": "check",
                 "scroll": "sort", "key": "command", "navigate": "compass", "back": "back",
                 "wait": "clock", "give_up": "flag"}
_FIDELITY_COLORS = {"artifact": "var(--muted)", "prototype": "var(--accent)", "live": "var(--green)"}


def _action_chip(action: dict) -> str:
    typ = action.get("type") or ""
    label = t("action_" + typ) if typ in _ACTION_ICONS else typ
    return h("span", {"class_": "lbl lbl-soft"},
             raw(_icon(_ACTION_ICONS.get(typ, "dot"))), " ", label)


def _fidelity_chip(fidelity: str) -> str:
    label = t("fidelity_" + fidelity) if fidelity in _FIDELITY_COLORS else fidelity
    return _label(label, _FIDELITY_COLORS.get(fidelity, "var(--muted)"))


def _friction_meta(level: str) -> dict | None:
    """The scale record ({term,value,label_key,color}) for a stored canonical friction level."""
    return next((r for r in _A.friction_terms() if r["term"] == level), None)


def _outcome_chip(sess: dict) -> str:
    out = sess.get("outcome") or {}
    if out.get("completed"):
        return _label(t("completed"), "var(--green)")
    return _label(t("outcome_dropped", n=out.get("dropoff_step", 0)), "var(--red)")


def _friction_count(sess: dict) -> int:
    return sum(1 for s in sess.get("steps") or []
               if ((_friction_meta((s.get("friction") or {}).get("level", "")) or {}).get("value", 0)) > 0)


def _verdict_chip(verdict: dict) -> str:
    cont = bool(verdict.get("would_continue"))
    chip = _label(t("verdict_continue") if cont else t("verdict_drop"),
                  "var(--green)" if cont else "var(--red)")
    reason = (verdict.get("reason") or "").strip()
    return fragment(raw(chip), h("span", {}, reason) if reason else None)


def _subject_link(store: Store, subject: dict):
    """The subject as a link: prototype/flow artifacts → the prototype page (when stored), a live
    URL → the external target; plain label otherwise."""
    label = subject.get("label") or subject.get("id") or subject.get("url") or "—"
    if subject.get("id"):
        proto = store.get_prototype(subject["id"])
        if proto:
            return h("a", {"href": f'/prototypes/{proto["slug"]}'}, label)
    if subject.get("url"):
        return h("a", {"href": subject["url"], "target": "_blank", "rel": "noopener"},
                 label, " ", raw(_icon("external")))
    return h("span", {}, label)


def _screenshot_url(sess_id: str, shot: str) -> str | None:
    """Resolve a stored screenshot reference to a servable URL — only for files that really exist
    under the sessions dir (→ /sessions-files) or the data dir (→ /data). Mirrors the resolution
    order of services._require_screenshots (session dir, then the sessions dir — the harness writes
    <browser_session_id>/step-<n>.png relative to it — then the data dir); anything else renders as
    the text screen instead."""
    sessions_root = _config.sessions_dir().resolve()
    data_root = Path(_config.DATA_DIR).resolve()
    p = Path(shot)
    candidates = ([p] if p.is_absolute() else
                  [_config.sessions_dir() / sess_id / p, _config.sessions_dir() / p,
                   Path(_config.DATA_DIR) / p])
    for c in candidates:
        try:
            r = c.resolve()
        except OSError:
            continue
        if not r.is_file():
            continue
        if r.is_relative_to(sessions_root):
            return "/sessions-files/" + r.relative_to(sessions_root).as_posix()
        if r.is_relative_to(data_root):
            return "/data/" + r.relative_to(data_root).as_posix()
    return None


def _persona_chip(store: Store, persona_id: str):
    p = store.get_persona(persona_id)
    if p:
        return h("a", {"href": f'/personas/{p["id"]}', "class_": "turn-who"},
                 _avatar(p, 22), h("b", {}, p["display_name"]))
    return h("span", {"class_": "turn-who"}, h("b", {}, persona_id or "—"))


def _session_row(s: dict, store: Store) -> str:
    """One list row: persona avatar chip · subject label · fidelity badge · outcome · friction count
    · date (progressive disclosure — the replay itself lives on the detail page)."""
    p = store.get_persona(s.get("persona_id", ""))
    av = _avatar(p or {"display_name": s.get("persona_id", "?"), "id": s.get("persona_id", "x")}, 22)
    n_fr = _friction_count(s)
    right = fragment(
        raw(_fidelity_chip(s.get("fidelity", ""))),
        raw(_outcome_chip(s)),
        raw(_label(t("friction_n", n=n_fr), "var(--amber)")) if n_fr else None,
        h("span", {}, (s.get("date") or s.get("created_at", ""))[:10]),
        raw(_star("session", s["id"], (s.get("subject") or {}).get("label", "")[:60], f'/sessions/{s["id"]}')))
    sub = (p or {}).get("display_name") or s.get("persona_id", "")
    return h("a", {"class_": "row", "href": f'/sessions/{s["id"]}'}, av,
             h("span", {"class_": "title"}, (s.get("subject") or {}).get("label", "—"),
               h("span", {"class_": "muted small"}, f" · {sub}") if sub else None),
             h("span", {"class_": "right"}, right))


def _funnel_html(funnel: dict) -> str:
    """The cross-session funnel for ONE subject (services.get_session_funnel): per step a
    continued/dropped bar against the entered count, with the drop reasons under the row."""
    rows = []
    mx = max((r["entered"] for r in funnel["rows"]), default=0) or 1
    for r in funnel["rows"]:
        parts = [(r["continued"], "var(--green)", t("funnel_continued")),
                 (r["dropped"], "var(--red)", t("funnel_dropped"))]
        bar = h("div", {"style": f'max-width:{r["entered"] / mx * 100:.1f}%'}, _stacked(parts, thin=True))
        rows.append(h("div", {"class_": "sess-frow"},
                      h("span", {"class_": "sfl"}, t("step_n", n=r["step"])), bar,
                      h("span", {"class_": "sfn"},
                        f'{r["entered"]} {t("funnel_entered")} · {r["dropped"]} {t("funnel_dropped")}')))
        for reason in r.get("drop_reasons", []):
            rows.append(h("div", {"class_": "sess-frow"}, h("span", {}),
                          h("span", {"class_": "sess-freason"}, raw(_icon("warning")), " ", reason)))
    legend = _legend([(funnel["completed"], "var(--green)", t("funnel_continued")),
                      (funnel["sessions"] - funnel["completed"], "var(--red)", t("funnel_dropped"))])
    return h("div", {"class_": "sess-funnel", "id": "funnel"},
             h("h2", {}, t("funnel_h"), " · ", (funnel.get("subject") or {}).get("key", "")),
             h("p", {"class_": "ihint"}, t("funnel_hint", n=funnel["sessions"])),
             fragment(*rows), legend)


def _sessions_section(store: Store, sessions: list[dict], sid: str = "sec-sessions") -> str:
    """The cross-link block other detail pages embed (persona / project / prototype): each of their
    sessions as one compact row — date · subject · fidelity · outcome. '' when there are none."""
    if not sessions:
        return ""
    rows = [_session_row(s, store) for s in sessions]
    return h("div", {"class_": "sec", "id": sid},
             h("h2", {}, f'{t("sessions")} ({len(sessions)})'),
             h("div", {"class_": "rows"}, raw("".join(str(r) for r in rows))))


def _step_html(sess: dict, step: dict) -> str:
    """One timeline row (`id="step-N"`): the SCREEN panel (screenshot when the file exists, else the
    recorded screen text as a framed excerpt + url/title caption) beside the ACTION side (typed
    action chip + target/detail, the think-aloud monologue, friction + per-step verdict)."""
    i = step.get("index", 0)
    state = step.get("state") or {}
    fr = step.get("friction") or {}
    meta = _friction_meta(fr.get("level", ""))
    has_friction = bool(meta and meta["value"] > 0)
    shot_url = _screenshot_url(sess["id"], state["screenshot"]) if state.get("screenshot") else None
    screen = (h("img", {"class_": "sess-shot", "src": shot_url, "alt": state.get("title") or f"step {i}",
                        "loading": "lazy"}) if shot_url
              else h("div", {"class_": "sess-screen-txt"}, state.get("screen", "")))
    caption = " · ".join(x for x in (state.get("url"), state.get("title")) if x)
    action = step.get("action") or {}
    target = (action.get("target") or "").strip()
    detail = (action.get("detail") or "").strip()
    monologue = (step.get("monologue") or "").strip()
    foot = h("div", {"class_": "sess-foot"},
             raw(_label(t(meta["label_key"]), meta["color"], title=fr.get("note") or None)) if has_friction else None,
             (h("span", {}, fr["note"]) if has_friction and fr.get("note") else None),
             _verdict_chip(step.get("verdict") or {}))
    style = f'--sfc:{meta["color"]}' if has_friction else None
    return h("div", {"class_": "sess-step", "id": f"step-{i}", "style": style},
             h("div", {"class_": "sess-screen"}, screen,
               h("div", {"class_": "sess-cap", "title": caption}, caption) if caption else None),
             h("div", {"class_": "sess-act"},
               h("div", {"class_": "sess-act-h"},
                 h("span", {"class_": "sess-n"}, str(i)), raw(_action_chip(action)),
                 h("span", {"class_": "sess-target"}, target) if target else None),
               h("p", {"class_": "sess-detail"}, detail) if detail else None,
               h("blockquote", {"class_": "sess-mono"}, monologue) if monologue else None,
               foot))


def _friction_rail(sess: dict) -> str:
    """The jump nav over the session's friction: every step with friction > none, its level chip and
    note, linking to the step's `#step-N` anchor. '' for a friction-free run."""
    items = []
    for step in sess.get("steps") or []:
        meta = _friction_meta((step.get("friction") or {}).get("level", ""))
        if not meta or meta["value"] <= 0:
            continue
        note = (step.get("friction") or {}).get("note") or (step.get("monologue") or "")
        items.append(h("a", {"href": f'#step-{step["index"]}'},
                       h("span", {"class_": "sess-n"}, str(step["index"])),
                       raw(_label(t(meta["label_key"]), meta["color"])),
                       h("span", {"class_": "sess-rail-note"}, note)))
    if not items:
        return ""
    return h("div", {"class_": "sess-rail", "id": "sec-friction"},
             h("div", {"class_": "sess-rail-h"}, t("friction_rail_h"), f" ({len(items)})"),
             fragment(*items))


def _outcome_banner(sess: dict) -> str:
    out = sess.get("outcome") or {}
    summary = (out.get("summary") or "").strip()
    if out.get("completed"):
        return h("div", {"class_": "sess-banner", "style": "--sbc:var(--green)"}, raw(_icon("check")),
                 h("strong", {}, t("completed")), h("span", {"class_": "muted"}, summary) if summary else None)
    drop = out.get("dropoff_step", 0)
    step = next((s for s in sess.get("steps") or [] if s.get("index") == drop), {})
    reason = ((step.get("verdict") or {}).get("reason") or summary or "").strip()
    return h("div", {"class_": "sess-banner", "style": "--sbc:var(--red)"}, raw(_icon("warning")),
             h("strong", {}, h("a", {"href": f"#step-{drop}"}, t("outcome_dropped", n=drop))),
             h("span", {"class_": "muted"}, reason) if reason else None)


def register_sessions(app) -> None:
    @app.get("/sessions", response_class=HTMLResponse)
    def sessions_list(project: str | None = Query(default=None),
                      subject_kind: str | None = Query(default=None),
                      subject: str | None = Query(default=None)) -> str:
        store = Store()
        subj = ({"kind": subject_kind, "id": subject} if (subject_kind and subject)
                else subject or None)
        sessions = services.list_usability_sessions(project_id=project, subject=subj, store=store)
        # The cross-session read: a subject filter with ≥2 recorded walks earns its funnel above the
        # rows (per-step entered/continued/dropped with the drop reasons).
        funnel_html = ""
        if subject_kind and subject and len(sessions) >= 2:
            funnel_html = _funnel_html(services.get_session_funnel(subject_kind, subject, store=store))
        rows = [_session_row(s, store) for s in sessions]
        rows_html = (raw("".join(str(r) for r in rows)) if rows else
                     h("div", {"class_": "sl-empty"},
                       h("div", {"class_": "sl-empty__icon"}, raw(_hifi("activity", 44))),
                       h("p", {"class_": "sl-empty__body"}, t("no_sessions"))))
        cnt = h("span", {"class_": "h1cnt"}, str(len(rows))) if rows else ""
        body = h("div", {"class_": "page"}, h("h1", {"class_": "h1"}, t("sessions"), cnt),
                 h("p", {"class_": "lead"}, t("sessions_lead")), raw(funnel_html),
                 # data-keynav: the keymap's j/k row-focus hook (web/_keymap.py)
                 h("div", {"class_": "rows", "data-keynav": True}, rows_html))
        return _layout(t("sessions"), body, store, crumbs=[(t("sessions"), None)], active="sessions")

    @app.get("/sessions/{session_id}", response_class=HTMLResponse)
    def session_detail(session_id: str) -> str:
        store = Store()
        sess = store.get_usability_session(session_id)
        if not sess:
            return _layout(t("not_found"),
                           _empty_state(t("session_not_found"), t("runtime_maybe_cleared"), icon="activity"),
                           store, active="sessions")
        subject = sess.get("subject") or {}
        title = subject.get("label") or session_id
        caps = sess.get("capabilities_snapshot") or {}
        caps_chip = None
        if caps.get("tech_comfort") is not None:
            cm = _A.tech_comfort_meta(caps["tech_comfort"])
            caps_chip = raw(_label(f'{t("cap_tech_comfort")}: {t(cm["label_key"])}', cm["color"],
                                   title=cm["hint"]))
        sub = h("span", {"class_": "syn-meta"},
                _persona_chip(store, sess.get("persona_id", "")), " ",
                raw(_fidelity_chip(sess.get("fidelity", ""))), " ",
                _subject_link(store, subject), " ", caps_chip, " ",
                h("span", {"class_": "mchip"}, (sess.get("date") or "")[:10]))
        steps = sess.get("steps") or []
        timeline = h("div", {"class_": "sec", "id": "sec-replay"},
                     h("h2", {}, t("replay_h"), h("span", {"class_": "h1cnt"}, str(len(steps)))),
                     h("div", {"class_": "sess-steps"}, fragment(*(_step_html(sess, s) for s in steps))))
        statements_html = ""
        if sess.get("statements"):
            statements_html = h("div", {"class_": "sec", "id": "sec-statements"},
                                h("h2", {}, t("voices")),
                                raw(render_statements(sess["statements"], store)))
        rail = _friction_rail(sess)
        body = fragment(raw(_outcome_banner(sess)), raw(rail), timeline, raw(statements_html))
        proj = store.get_research_project(sess["project_id"]) if sess.get("project_id") else None
        crumbs = [(t("sessions"), "/sessions")]
        if proj:
            crumbs.append((proj["title"], f'/projects/{proj["id"]}'))
        crumbs.append((_display_title(title), None))
        grounded = sess.get("grounded_verified")
        prop_rows = [
            ("square", t("fidelity"), raw(_fidelity_chip(sess.get("fidelity", "")))),
            ("compass", t("subject_h"), _subject_link(store, subject)),
            ("plan", t("steps_h"), str(len(steps))),
            ("projects", t("project"), h("a", {"href": f'/projects/{proj["id"]}'}, proj["title"]) if proj else ""),
            ("check", t("grounded_yes") if grounded else t("grounded_no"),
             raw(_label(t("grounded_yes") if grounded else t("grounded_no"),
                        "var(--green)" if grounded else "var(--muted)")) if grounded is not None else ""),
            ("dot", t("created"), (sess.get("created_at") or "")[:10]),
        ]
        rail_sections = (([("sec-friction", t("friction_rail_h"))] if rail else [])
                         + [("sec-replay", t("replay_h"))]
                         + ([("sec-statements", t("voices"))] if statements_html else []))
        return detail_page(
            store, title=_display_title(title), active="sessions", crumbs=crumbs,
            hero=_hero(title, icon="activity", sub=sub, hid="sec-head"), body=body,
            prop_rows=prop_rows, rel_proj_id=sess.get("project_id") or None,
            rail_sections=rail_sections,
            star=("session", session_id, title[:60], f"/sessions/{session_id}"))

    @app.get("/sessions-files/{path:path}")
    def session_file(path: str):
        """Read-only screenshots from data/sessions/ (the avatar pattern, but with an explicit
        resolve + containment check: a traversal that escapes the sessions dir is a 404, never a
        file read)."""
        base = _config.sessions_dir().resolve()
        try:
            target = (base / path).resolve()
        except OSError:
            return Response(status_code=404)
        if not (target.is_relative_to(base) and target.is_file()):
            return Response(status_code=404)
        return FileResponse(target)
