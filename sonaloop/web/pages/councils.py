"""Council pages: list + detail (spec/roadmap.md R2)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._render import render_statements
from .._html import register_css
from ... import artifacts as _A


# Head-to-Head verdict block: the preference headline + the option/segment tally tables.
register_css(r"""
.h2h-pref{font-size:var(--t-body);margin:0 0 12px}
.h2h-table{width:100%;border-collapse:collapse;margin:0 0 8px;font-size:var(--t-sm)}
.h2h-table th{text-align:left;color:var(--muted);font-weight:600;padding:5px 10px;border-bottom:1px solid var(--line-2)}
.h2h-table td{padding:5px 10px;border-bottom:1px solid var(--line-2)}
.h2h-table tr:last-child td{border-bottom:0}
""")


def _h2h_result_html(result: dict) -> str:
    """The deterministic head-to-head verdict: the overall preference + margin headline, the per-option
    vote tally, and the segment-splits (who-prefers-what) table. The server computes these; the prose
    verdict lives in the exec_summary above. UI language is German by default (match the surrounding UI)."""
    options = result.get("options", [])
    title_by = {o["label"]: o.get("title", o["label"]) for o in options}
    pref = result.get("preference")
    decisive = t("h2h_decisive_" + (result.get("decisive") or "tie"))
    if pref:
        headline = h("div", {"class_": "h2h-pref"},
                     h("strong", {}, f"{t('h2h_preference')}: {pref} — {result.get('preference_title') or ''}"),
                     h("span", {"class_": "muted small"}, f" · {decisive} · {t('h2h_margin')} {result.get('margin')}"))
    else:
        headline = h("div", {"class_": "h2h-pref"}, h("strong", {}, t("h2h_no_pref")))

    # Per-option vote tally.
    opt_rows = [h("tr", {}, h("th", {}, t("h2h_options")), h("th", {}, t("h2h_votes")))]
    for o in options:
        is_win = o["label"] == pref
        opt_rows.append(h("tr", {"style": ("font-weight:600" if is_win else "")},
                          h("td", {}, f"{o['label']} — {o.get('title', '')}"),
                          h("td", {}, str(o.get("votes", 0)))))
    opt_table = h("table", {"class_": "h2h-table"}, *opt_rows)

    # Segment-splits: who prefers what, broken down by persona segment/archetype.
    splits = result.get("segment_splits", [])
    seg_html = ""
    if splits:
        labels = [o["label"] for o in options]
        head = [h("th", {}, t("h2h_segment")), h("th", {}, t("h2h_voters"))]
        head += [h("th", {}, lab) for lab in labels]
        head.append(h("th", {}, t("h2h_prefers")))
        seg_rows = [h("tr", {}, *head)]
        for s in splits:
            cells = [h("td", {}, s.get("segment", "")), h("td", {}, str(s.get("voters", 0)))]
            cells += [h("td", {}, str((s.get("tally") or {}).get(lab, 0))) for lab in labels]
            prefers = s.get("prefers")
            cells.append(h("td", {}, (f"{prefers} — {title_by.get(prefers, '')}" if prefers else t("h2h_tie"))))
            seg_rows.append(h("tr", {}, *cells))
        seg_html = fragment(h("h3", {"style": "margin:14px 0 6px"}, t("h2h_segments")),
                            h("table", {"class_": "h2h-table"}, *seg_rows))
    return str(fragment(headline, opt_table, seg_html))


def register_councils(app) -> None:
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
            return _layout(t("not_found"), _empty_state(t("council_not_found"), t("runtime_maybe_cleared"), icon="councils"), store, active="councils")
        proposal_short_h = t("proposal_short_summary")
        proposal_h = t("proposal"); summary_h = t("summary")
        sentiment_title = t("sentiment_this_council")
        vote_h = t("vote"); personas_h = t("personas"); created_h = t("created")
        councils_crumb = t("councils"); council_title = t("councils")
        # Each voice shows WHO the persona is + the life-context that shaped them (the per-persona
        # "input") and any recorded input snapshot, so you can see what each was given → what they said.
        pmap = {pid: store.get_persona(pid) for pid in session.get("persona_ids", [])}

        # Voices render through the ONE statement renderer (spec/unified-artifact-schema): discovery
        # groups the .turn cards under question headers (group_by="prompt"), evaluation/decision show a
        # flat per-persona list — same card either way.
        statements = _A.council_statements(session)
        prompts = _A.council_prompts(session)
        n_voices = len(session.get("persona_ids", []))
        vm = study_head(session)                       # shared study view-model (question/answer/mode)
        mode = vm["mode"]
        exec_html = _md(vm["answer_md"])
        # Head-to-Head Format: a council carrying a deterministic X-vs-Y aggregate (preference + margin +
        # segment-splits). When present we surface the verdict block above the voices.
        is_h2h = services.is_head_to_head(session)
        h2h_html = (_h2h_result_html(session["head_to_head"]["result"]) if is_h2h else "")
        # The Voices section carries the framing for EVERY mode: each persona card is grouped under the
        # prompt it answers — the discovery QUESTIONS or the evaluation/decision PROPOSAL (rendered as
        # Markdown via render_prompt) — so "what was asked" always sits right above the cards. One
        # consistent structure across all councils (no separate lead block to drift out of sync).
        referenced = {(s.get("about") or {}).get("id") for s in statements if s.get("about")}
        group_prompts = [p for p in prompts if p.get("id") in referenced]
        help_text = (t("council_questions_help", n=n_voices) if mode == "discovery"
                     else t("council_eval_help", n=n_voices) if mode == "evaluation"
                     else t("council_motion_help", n=n_voices))
        intro = h("p", {"class_": "muted small", "style": "margin:-4px 0 14px"}, help_text)
        # Reverse cross-refs: each statement learns who cites it (e.g. the synthesis that derives from it).
        _idx = services.ref_backlinks(session.get("project_id", ""), store) if session.get("project_id") else {}
        backlinks = {s["id"]: _idx.get(_A.part_address("council", session["id"], s["id"]), [])
                     for s in statements if s.get("id")}
        backlinks = {k: v for k, v in backlinks.items() if v}
        voices_html = (render_statements(statements, store, group_by="prompt", prompts=group_prompts, backlinks=backlinks)
                       if group_prompts else render_statements(statements, store, group_by="persona", backlinks=backlinks))
        sentiment = "" if mode == "discovery" else (_sentiment_section(store, [session], title=sentiment_title) or "")
        kicker = (t("h2h_kicker", n=n_voices) if is_h2h else t("council_kicker_" + mode, n=n_voices))
        council_sub = f'{kicker} · {session["selection_reason"]}'
        short_title = _display_title(session["prompt"])        # short form for breadcrumb / tab / favourite only
        # Executive Summary (the short TL;DR) sits at the TOP — same block/name as the synthesis.
        has_summary = bool((session.get("summary") or "").strip())
        summary_lead = (raw(_study_lead(_md(session["summary"]), t("answer_exec_summary"), qid="sec-summary"))
                        if has_summary else "")
        h2h_block = (h("div", {"class_": "sec", "id": "h2h"}, h("h2", {}, t("h2h_title")),
                       h("p", {"class_": "muted small", "style": "margin:-4px 0 14px"}, t("h2h_lead")),
                       raw(h2h_html)) if is_h2h else "")
        body = fragment(
            summary_lead, raw(_study_lead(exec_html, vm["answer_label"])), h2h_block, raw(sentiment),
            h("div", {"class_": "sec", "id": "stimmen"}, h("h2", {}, t("voices")), intro, raw(voices_html)))
        prop_rows = [("councils", t("type_h"), t("council_mode_" + mode)), ("personas", personas_h, str(n_voices))]
        if mode != "discovery":                               # the vote panel only where a vote/reaction exists
            vc = {v: sum(1 for x in session["votes"] if str(x.get("vote", "")).upper() == v) for v in ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]}
            prop_rows += [("dot", _vote_label(k), str(vc[k])) for k in vc]
        prop_rows.append(("dot", created_h, session["created_at"][:10]))
        # Forward, project-rooted crumb: Projects > [Project] > [Council]. (A Discover council FEEDS
        # the Define synthesis — it is not nested under it; and the project lookup must work for
        # plan-based projects, where the council is scoped directly to the project.)
        crumbs = [(t("projects"), "/projects")]
        proj = (services.parent_project_of_council(session_id, store)
                or (services.parent_project_of_synthesis(ps["id"], store)
                    if (ps := services.parent_study_of_council(session_id, store)) else None))
        if proj:
            crumbs.append((proj["title"], f"/projects/{proj['id']}"))
        crumbs.append((short_title, None))
        return detail_page(
            store, title=short_title, active="projects", crumbs=crumbs,
            hero=_hero(session["prompt"], icon="councils", sub=council_sub, hid="sec-question"), body=body,
            prop_rows=prop_rows,
            rel_study_id=f"council:{session_id}", rel_proj_id=(proj["id"] if proj else None),
            rail_sections=([("sec-question", t("question"))]
                           + ([("sec-summary", t("answer_exec_summary"))] if has_summary else [])
                           + ([("h2h", t("h2h_title"))] if is_h2h else [])
                           + [("stimmen", t("voices"))]),
            star=("council", session_id, short_title, f"/councils/{session_id}"))
