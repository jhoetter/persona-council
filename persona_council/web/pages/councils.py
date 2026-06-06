"""Council pages: list + detail (spec/roadmap.md R2)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)


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
        main = fragment(
            raw(_hero(session["prompt"], sub=council_sub, hid="sec-question")),
            raw(lead_block), raw(_study_lead(exec_html, vm["answer_label"])), raw(sentiment),
            h("div", {"class_": "sec", "id": "stimmen"}, h("h2", {}, voices_label), raw(turns_html)),
            h("details", {"class_": "sec"}, h("summary", {}, summary_h),
              h("div", {"class_": "card"}, h("strong", {}, summary_h), h("p", {}, session["summary"]))))
        prop_rows = [("councils", t("type_h"), t("council_mode_" + mode)), ("personas", personas_h, str(n_voices))]
        if mode != "discovery":                               # the vote panel only where a vote/reaction exists
            vc = {v: sum(1 for x in session["votes"] if str(x.get("vote", "")).upper() == v) for v in ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]}
            prop_rows += [("dot", _vote_label(k), str(vc[k])) for k in vc]
        prop_rows.append(("dot", created_h, session["created_at"][:10]))
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
