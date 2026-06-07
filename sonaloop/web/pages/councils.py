"""Council pages: list + detail (spec/roadmap.md R2)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._render import render_statements
from ... import artifacts as _A


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
        council_sub = f'{t("council_kicker_" + mode, n=n_voices)} · {session["selection_reason"]}'
        short_title = _display_title(session["prompt"])        # short form for breadcrumb / tab / favourite only
        # Executive Summary (the short TL;DR) sits at the TOP — same block/name as the synthesis.
        has_summary = bool((session.get("summary") or "").strip())
        summary_lead = (raw(_study_lead(_md(session["summary"]), t("answer_exec_summary"), qid="sec-summary"))
                        if has_summary else "")
        body = fragment(
            summary_lead, raw(_study_lead(exec_html, vm["answer_label"])), raw(sentiment),
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
                           + [("stimmen", t("voices"))]),
            star=("council", session_id, short_title, f"/councils/{session_id}"))
