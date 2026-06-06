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

        # Voices render through the ONE statement renderer (spec/unified-artifact-schema): discovery
        # groups the .turn cards under question headers (group_by="prompt"), evaluation/decision show a
        # flat per-persona list — same card either way.
        statements = _A.council_statements(session)
        prompts = _A.council_prompts(session)
        q_prompts = [p for p in prompts if str(p.get("id", "")).startswith("q")]
        help_html = h("p", {"class_": "muted small", "style": "margin:-4px 0 12px"}, t("council_voices_help"))
        if q_prompts and any(st.get("about") for st in statements):
            turns_html = fragment(help_html, render_statements(statements, store, group_by="prompt", prompts=q_prompts))
        else:
            turns_html = fragment(help_html, render_statements(statements, store, group_by="persona"))
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
            qlist = [h("li", {}, q) for q in qs] or [h("li", {"class_": "muted"}, "—")]
            lead_block = h("div", {"class_": "es"}, h("div", {"class_": "eyebrow"}, t("council_questions_h")),
                           h("ul", {"class_": "es-prose"}, qlist),
                           h("p", {"class_": "muted small"}, t("council_questions_help", n=n_voices)))
            sentiment = ""                                    # a listening session has no vote/sentiment chart
        else:
            motion = (session.get("proposal") or "").strip()
            label = t("council_eval_h") if mode == "evaluation" else t("council_motion")
            help_ = t("council_eval_help", n=n_voices) if mode == "evaluation" else t("council_motion_help", n=n_voices)
            lead_block = (h("div", {"class_": "es"}, h("div", {"class_": "eyebrow"}, label),
                            h("div", {"class_": "es-prose"}, "„", motion, "“"),
                            h("p", {"class_": "muted small"}, help_)) if motion else "")
            sentiment = _sentiment_section(store, [session], title=sentiment_title) or ""
        council_sub = f'{t("council_kicker_" + mode, n=n_voices)} · {session["selection_reason"]}'
        short_title = _display_title(session["prompt"])        # short form for breadcrumb / tab / favourite only
        # Executive Summary (the short TL;DR) sits at the TOP — same block/name as the synthesis — not a
        # bottom toggle. The long exec_summary stays below as "what this council found" (the detail).
        has_summary = bool((session.get("summary") or "").strip())
        summary_lead = (raw(_study_lead(_md(session["summary"]), t("answer_exec_summary"), qid="sec-summary"))
                        if has_summary else "")
        body = fragment(
            raw(lead_block), summary_lead, raw(_study_lead(exec_html, vm["answer_label"])), raw(sentiment),
            h("div", {"class_": "sec", "id": "stimmen"}, h("h2", {}, voices_label), raw(turns_html)))
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
