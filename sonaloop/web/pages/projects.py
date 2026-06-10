"""Project pages: home/index, detail (outline/graph + hypotheses), report, plan (spec/roadmap.md R2)."""
from __future__ import annotations

from fastapi.responses import RedirectResponse

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .sessions import _sessions_section
from .._html import register_css
from .._render import render_ref


register_css(r"""
.hyp{border:1px solid var(--line-2);border-radius:9px;padding:10px 14px;margin:8px 0;background:var(--panel)}
.hypvals{display:flex;gap:16px;flex-wrap:wrap;margin-top:4px;font-size:var(--t-sm)}
.hyprate{display:flex;gap:10px;align-items:center;margin:6px 0 12px}
.hypstrip{display:flex;height:14px;border-radius:7px;overflow:hidden;background:var(--line-2);flex:1;max-width:340px}
.hypseg{height:100%}
""")

# Hypothesis lifecycle pill colors (a lifecycle, not a vocabulary — labels are i18n keys below;
# the hit-rate strip reuses the same colors so verdicts read identically everywhere).
_HYP_STATUS_COLORS = {"open": "var(--accent)", "validated": "var(--green)", "refuted": "var(--red)",
                      "inconclusive": "var(--amber)", "dropped": "var(--muted)"}


def _hyp_status_label(status: str) -> str:
    """Resolved per request so the labels follow the active UI language."""
    labels = {"open": t("hyp_status_open"), "validated": t("hyp_status_validated"),
              "refuted": t("hyp_status_refuted"), "inconclusive": t("hyp_status_inconclusive"),
              "dropped": t("hyp_status_dropped")}
    return labels.get(status, status)


def _hyp_predicted_text(pred: dict) -> str:
    """metric → expectation (value ±tolerance, or the direction word) · confidence."""
    if "expected_value" in pred:
        expected = str(pred.get("expected_value"))
        if pred.get("tolerance"):
            expected += f' ±{pred["tolerance"]:g}'
    else:
        expected = (t("hyp_dir_increase") if pred.get("expected_direction") == "increase"
                    else t("hyp_dir_decrease"))
    out = f'{pred.get("metric", "")} → {expected}'
    conf = pred.get("confidence")
    if conf is not None:
        out += f' · {t("hyp_confidence")} {conf:.0%}'
    return out


def _hypothesis_row(hx: dict, store) -> str:
    pred = hx.get("prediction") or {}
    res = hx.get("result") or {}
    vals = [h("span", {}, h("span", {"class_": "muted"}, t("hyp_predicted"), ": "),
              _hyp_predicted_text(pred))]
    if res:
        vals.append(h("span", {}, h("span", {"class_": "muted"}, t("hyp_observed"), ": "),
                      str(res.get("observed_value", ""))))
    note = (h("p", {"class_": "muted small", "style": "margin:4px 0 0"}, res["note"])
            if res.get("note") else None)
    src = (h("p", {"class_": "muted small turn-refs", "style": "margin:4px 0 0"},
             t("hyp_observed"), ": ", raw(render_ref(res["source"], store)))
           if res.get("source") else None)
    derived = (h("p", {"class_": "muted small turn-refs", "style": "margin:4px 0 0"},
                 t("rel_based_on"), ": ",
                 fragment(*(raw(render_ref(r, store)) for r in hx["derived_from"])))
               if hx.get("derived_from") else None)
    status = hx.get("status", "open")
    return h("div", {"class_": "hyp", "id": f'hyp-{hx["id"]}'},
             h("div", {}, raw(_label(_hyp_status_label(status),
                                     _HYP_STATUS_COLORS.get(status, "var(--muted)"))),
               " ", h("b", {}, hx.get("text", ""))),
             h("div", {"class_": "hypvals"}, fragment(*vals)), note, src, derived)


def _hypotheses_html(project_id: str, store) -> str:
    """The project's bets: open vs resolved, predicted-vs-observed per row, and the hit-rate strip
    (over RESOLVED bets only — open ones haven't been scored by reality yet)."""
    hyps = services.list_hypotheses(project_id, store=store)
    if not hyps:
        return ""
    open_bets = [x for x in hyps if x.get("status") == "open"]
    resolved = [x for x in hyps if x.get("status") != "open"]
    scored = [x for x in resolved if x.get("status") != "dropped"]
    decisive = [x for x in scored if x.get("status") in ("validated", "refuted")]
    hits = sum(1 for x in decisive if x["status"] == "validated")
    if scored:
        segs = []
        for status in ("validated", "refuted", "inconclusive"):
            n = sum(1 for x in scored if x["status"] == status)
            if n:
                segs.append(h("span", {"class_": "hypseg",
                                       "style": (f"width:{n / len(scored) * 100:.1f}%;"
                                                 f"background:{_HYP_STATUS_COLORS[status]}"),
                                       "title": f"{_hyp_status_label(status)}: {n}"}))
        rate = f"{hits}/{len(decisive)}" + (f" · {hits / len(decisive) * 100:.0f}%" if decisive else "")
        strip = h("div", {"class_": "hyprate"},
                  h("span", {"class_": "muted small"}, t("hyp_hit_rate"), f": {rate}"),
                  h("div", {"class_": "hypstrip"}, fragment(*segs)))
    else:
        strip = h("p", {"class_": "muted small"}, t("hyp_no_resolved"))
    groups = []
    if open_bets:
        groups.append(h("div", {"class_": "oqp-h"}, f'{t("hyp_open_bets")} ({len(open_bets)})'))
        groups += [_hypothesis_row(x, store) for x in open_bets]
    if resolved:
        groups.append(h("div", {"class_": "oqp-h", "style": "margin-top:10px"},
                        f'{t("hyp_resolved")} ({len(resolved)})'))
        groups += [_hypothesis_row(x, store) for x in resolved]
    return h("div", {"class_": "outlinecard", "id": "hypotheses", "style": "margin-top:14px"},
             h("h2", {"style": "margin:0 0 6px"}, f'{t("hypotheses_h")} ({len(hyps)})'),
             strip, fragment(*groups))


# Decision lifecycle pill colors (proposed → adopted → superseded; labels are i18n keys below).
_DEC_STATUS_COLORS = {"proposed": "var(--accent)", "adopted": "var(--green)",
                      "superseded": "var(--muted)"}


def _dec_status_label(status: str) -> str:
    """Resolved per request so the labels follow the active UI language."""
    labels = {"proposed": t("dec_status_proposed"), "adopted": t("dec_status_adopted"),
              "superseded": t("dec_status_superseded")}
    return labels.get(status, status)


def _decision_row(d: dict, store, by_id: dict) -> str:
    """One decision: status pill + title, the decision text, evidence chips (render_ref deep-links
    into the source studies), rejected alternatives with their why-not notes, and the supersede
    links in both directions."""
    based = h("p", {"class_": "muted small turn-refs", "style": "margin:4px 0 0"},
              t("rel_based_on"), ": ",
              fragment(*(raw(render_ref(r, store)) for r in d.get("based_on") or [])))
    rejected = fragment(*(
        h("p", {"class_": "muted small turn-refs", "style": "margin:4px 0 0"},
          t("dec_rejected"), ": ", raw(render_ref(r, store)),
          (f' — {r["note"]}' if r.get("note") else ""))
        for r in d.get("rejected") or []))
    def _link(oid: str, label: str) -> str:
        return h("p", {"class_": "muted small", "style": "margin:4px 0 0"}, label, ": ",
                 h("a", {"href": f"#dec-{oid}"}, (by_id.get(oid) or {}).get("title", oid)))

    links = []
    if d.get("superseded_by"):
        links.append(_link(d["superseded_by"], t("dec_superseded_by")))
    if d.get("supersedes"):
        links.append(_link(d["supersedes"], t("dec_supersedes")))
    status = d.get("status", "proposed")
    return h("div", {"class_": "hyp", "id": f'dec-{d["id"]}'},
             h("div", {}, raw(_label(_dec_status_label(status),
                                     _DEC_STATUS_COLORS.get(status, "var(--muted)"))),
               " ", h("b", {}, d.get("title", ""))),
             h("p", {"style": "margin:4px 0 0"}, d.get("decision", "")),
             based, rejected, fragment(*links))


def _decisions_html(project_id: str, store) -> str:
    """The project's decision records, grouped adopted / proposed / superseded — what the research
    led to, on which evidence, rejecting what (ticket decision-record-artifact)."""
    decs = services.list_decisions(project_id, store=store)
    if not decs:
        return ""
    by_id = {d["id"]: d for d in decs}
    groups = []
    for status in ("adopted", "proposed", "superseded"):
        rows = [d for d in decs if d.get("status") == status]
        if not rows:
            continue
        groups.append(h("div", {"class_": "oqp-h", "style": "margin-top:10px"},
                        f'{_dec_status_label(status)} ({len(rows)})'))
        groups += [_decision_row(d, store, by_id) for d in rows]
    return h("div", {"class_": "outlinecard", "id": "decisions", "style": "margin-top:14px"},
             h("h2", {"style": "margin:0 0 6px"}, f'{t("decisions_h")} ({len(decs)})'),
             fragment(*groups))


def register_projects(app) -> None:
    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        # Home is the Projects list (project-centric IA; Overview removed).
        return _projects_page()
    @app.get("/projects", response_class=HTMLResponse)
    def projects() -> str:
        return _projects_page()

    @app.get("/projects/{project_id}", response_class=HTMLResponse)
    def project_detail(project_id: str, view: str = "list") -> str:
        store = Store()
        try:
            graph = services.get_project_graph(project_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("not_found"), t("runtime_maybe_cleared"), icon="projects"), store, active="projects")
        proj = graph["project"]
        # edge legend (shown in the floating open-questions panel)
        used_types = sorted({e["type"] for e in graph["edges"]})
        edge_leg = fragment(*(h("span", {"class_": "pill", "style": f'border-color:{_EDGE_COLORS.get(ty, "#9aa0a6")}'}, ty)
                              for ty in used_types)) or h("span", {"class_": "muted small"}, "—")
        oqs = [o for o in graph["open_questions"] if o.get("status") == "open"]
        oq_html = fragment(*(h("li", {}, o["text"]) for o in oqs[:30])) or h("li", {"class_": "muted"}, "—")
        # Plan opens in a right drawer. Reports are NOT a top-bar button anymore — they're listed
        # inline in the outline as first-class artifacts (add as many as you like; they flow into the project).
        top_btn = ""
        if services.get_plan(proj["id"], store=store):
            plan_url = f'/projects/{proj["id"]}/plan'
            top_btn = h("a", {"class_": "sl-btn", "href": plan_url, "data-drawer": plan_url, "data-drawer-title": "Plan"},
                        raw(_icon("plan")), " Plan")
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
        type_chips = fragment(*(
            h("button", {"class_": "rgchip", "data-theme": ty, "style": f"--c:{c}"},
              (fragment(raw(_icon(glyph_icon(g))), " ") if g else ""), lab)
            for ty, (c, lab, g) in type_meta.items()))
        node_tags = []
        for n in graph["nodes"]:
            for tgx in n.get("theme_tags", []):
                if tgx not in node_tags and tgx not in type_tagset:
                    node_tags.append(tgx)
        tag_vocab = list(dict.fromkeys((proj.get("themes") or []) + node_tags))
        tag_chips = fragment(*(
            h("button", {"class_": "rgchip tagchip", "data-theme": th, "style": f"--c:{_theme_color(th, tag_vocab)}"}, th)
            for th in tag_vocab))
        left = (fragment(h("span", {"class_": "ptlabel"}, raw(_icon("search")), " ", t("type_h")), type_chips,
                         (fragment(h("span", {"class_": "ptlabel ptlabel-2"}, t("tags_h")), tag_chips) if tag_chips else ""),
                         h("a", {"class_": "rgclear", "style": "display:none"}, t("clear_filter"))) if type_chips else "")
        oqbtn = h("button", {"class_": "sl-btn", "id": "oqbtn"}, f'{t("legend")} · {t("open_questions_h")} ({len(oqs)})')
        toolbar = h("div", {"class_": "ptoolbar"}, left, h("span", {"class_": "spacer"}), oqbtn)  # Plan/Meta now in topbar
        # Artifact viewer: artifacts + recorded persona sessions (read-only).
        proto_html = ""
        if protos:
            rows = []
            for p in protos:
                sess = store.list_prototype_sessions(prototype_id=p["id"])
                sl = []
                for s in sess[:6]:
                    r = s.get("reaction", {})
                    gv = _icon("check") if s.get("grounded_verified") else _icon("circle")
                    nm = r.get("persona") or (store.get_persona(s.get("persona_id", "")) or {}).get("display_name") or s.get("persona_id", "")
                    sl.append(h("li", {}, h("b", {}, nm), ": ", raw(_prose(r.get("verdict") or r.get("reaction_text") or "")),
                                " ", h("span", {"class_": "muted small"}, raw(gv), " grounded")))
                sl_html = (h("ul", {"style": "margin:4px 0 0 18px"}, fragment(*sl)) if sl
                           else h("div", {"class_": "muted small"}, "— keine Sessions —"))
                ap = _artifact_present(p)
                pill = ap["disc"] or ap["label"]
                rows.append(h("div", {"class_": "strow"},
                              h("a", {"href": f'/prototypes/{p["slug"]}'}, raw(_icon("projects")), h("b", {}, p["name"])), " ",
                              h("span", {"class_": "pill"}, pill), " ", h("span", {"class_": "muted small"}, p.get("version", "")), " ",
                              h("a", {"class_": "sl-btn", "style": "padding:2px 8px", "href": f'/prototypes/{p["slug"]}'},
                                "ansehen ", raw(_icon("external"))), sl_html))
            proto_html = fragment(h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, f'{t("prototypes_h")} ({len(protos)})'),
                                  fragment(*rows))
        # Artifacts in the council pool: real URLs / prototype links / A/B variants, each with its
        # captured-at + grounded snapshot status (ticket artifacts-into-council). Read-only.
        arts = graph.get("artifacts") or []
        arts_html = ""
        if arts:
            arows = []
            for a in arts:
                snap = a.get("snapshot") or {}
                captured = bool(snap.get("ok"))
                cap_icon = _icon("check") if captured else _icon("circle")
                cap_txt = (f'{t("artifact_captured")} · {(a.get("captured_at") or "")[:16]}' if captured
                           else t("artifact_capture_failed"))
                kind_label = t("artifact_kind_" + (a.get("kind") or "url"))
                arows.append(h("div", {"class_": "strow"},
                               h("span", {"class_": "pill"}, a.get("label", "?")), " ",
                               h("a", {"href": a.get("url", "#"), "target": "_blank", "rel": "noopener"},
                                 raw(_icon("external")), h("b", {}, a.get("title") or a.get("url", ""))), " ",
                               h("span", {"class_": "pill"}, kind_label), " ",
                               h("span", {"class_": "muted small"}, raw(cap_icon), " ", cap_txt)))
            arts_html = fragment(h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, f'{t("artifacts_h")} ({len(arts)})'),
                                 fragment(*arows))
        # Evidence assets: files/images/screenshots attached via MCP (ticket attach-evidence-files-mcp).
        # Read-only, like everything here; image assets render a thumbnail from the static /data mount.
        assets = graph.get("assets") or []
        assets_html = ""
        if assets:
            asrows = []
            for a in assets:
                is_img = a.get("kind") in ("image", "screenshot")
                thumb = (h("a", {"href": a.get("url", "#"), "target": "_blank", "rel": "noopener"},
                           h("img", {"src": a.get("url", ""), "alt": a.get("title", ""), "loading": "lazy",
                                     "style": "max-height:64px;max-width:120px;border-radius:6px;display:block"}))
                         if is_img else raw(_icon("external")))
                size_kb = f'{max(1, int(a.get("bytes", 0)) // 1024)} KB'
                asrows.append(h("div", {"class_": "strow"},
                               thumb, " ",
                               h("a", {"href": a.get("url", "#"), "target": "_blank", "rel": "noopener"},
                                 h("b", {}, a.get("title") or a.get("filename", ""))), " ",
                               h("span", {"class_": "pill"}, t("asset_kind_" + (a.get("kind") or "file"))), " ",
                               h("span", {"class_": "muted small"}, f'{a.get("filename", "")} · {size_kb}'
                                 + (f' · {a.get("notes")}' if a.get("notes") else ""))))
            assets_html = fragment(h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, f'{t("assets_h")} ({len(assets)})'),
                                   fragment(*asrows))
        # Sections outline (methodology-independent groupings) — a navigable list in the panel.
        from ... import presentation as _pres
        secs = sorted(graph.get("sections") or [], key=lambda s: s.get("order", 0))
        sec_html = ""
        if secs:
            rows = []
            for s in secs:
                pr = _pres.present(s.get("kind", "theme"), s.get("presentation"))
                glyph = (pr.get("glyph") + " ") if pr.get("glyph") else ""
                rows.append(h("div", {"class_": "strow"},
                              h("a", {"href": f'/sections/{s["id"]}'},
                                h("span", {"class_": "pill", "style": f'border-color:{pr["color"]};color:{pr["color"]}'},
                                  glyph, s.get("title", ""))), " ",
                              h("span", {"class_": "muted small"}, f'{pr.get("short", s.get("kind",""))} · {len(s.get("member_ids",[]))}')))
            sec_html = fragment(h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, f"Sections ({len(secs)})"), fragment(*rows))
        # Project pulse (assess_project) — a self-documenting status line for in-flight long runs.
        pulse_html = ""
        try:
            ap = services.assess_project(proj["id"], store=store)
            cov = ap["coverage"]["evidence_by_kind"]
            cov_str = " · ".join(f"{k}:{v}" for k, v in cov.items())
            gaps = ap.get("gaps") or []
            gap_str = (h("div", {"class_": "muted small", "style": "margin-top:4px"}, f'{t("gaps")}: ', "; ".join(gaps[:4]))
                       if gaps else "")
            # stalled banner: open work, nobody driving — name the ready step + the resume call
            rs = services.project_run_state(proj["id"], store=store)
            stall_html = ""
            if rs and rs.get("state") == "stalled":
                stall_html = h("div", {"class_": "strow"},
                               h("span", {"class_": "pill", "style": "border-color:var(--amber);color:var(--amber)"},
                                 t("stalled")), " ",
                               h("span", {"class_": "muted small"}, rs.get("note", "")))
            pulse_html = fragment(
                h("div", {"class_": "oqp-h"}, t("pulse")), stall_html,
                h("div", {"class_": "strow"}, h("span", {"class_": "pill"}, ap["recommendation"]), " ",
                  h("span", {"class_": "muted small"}, cov_str, f' · {t("saturation")}: {ap["saturation"]["hint"]}'), gap_str))
        except Exception:
            pulse_html = ""
        # Coverage / diversity check — a deterministic indicator over the study's PERSONA SET (is the panel
        # too narrow to trust?) with concrete gaps + recommended archetypes. German UI by default.
        coverage_html = ""
        try:
            cv = services.assess_coverage(proj["id"], store=store)
            ind = cv["indicator"]
            cgaps = cv.get("gaps") or []
            cgap_str = (h("div", {"class_": "muted small", "style": "margin-top:4px"},
                          f'{t("gaps")}: ', "; ".join(g["reason"] for g in cgaps[:3]))
                        if cgaps else "")
            recs = cv.get("recommendations") or []
            rec_str = (h("div", {"class_": "muted small", "style": "margin-top:4px"},
                         f'{t("coverage_recommend")}: ', "; ".join(r["description"] for r in recs[:2]))
                       if recs else "")
            coverage_html = fragment(
                h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, t("coverage_h")),
                h("div", {"class_": "strow"},
                  h("span", {"class_": "pill"}, t("coverage_level_" + ind["level"])), " ",
                  h("span", {"class_": "muted small"},
                    f'{t("coverage_panel")}: {cv["panel_size"]}'
                    + (f' · {ind["reasons"][0]}' if ind.get("reasons") else "")),
                  cgap_str, rec_str))
        except Exception:
            coverage_html = ""
        # Open questions + legend + prototypes live in a floating panel so the graph keeps the canvas.
        panel = h("div", {"class_": "oqpanel", "id": "oqpanel", "hidden": True}, pulse_html, coverage_html,
                  h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, f'{t("build_order_h")} (edges)'),
                  h("div", {"class_": "pills", "style": "margin:6px 0 14px"}, edge_leg), sec_html,
                  h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, t("open_questions_h")),
                  h("ul", {"style": "margin:6px 0 0 18px"}, oq_html), proto_html, arts_html, assets_html)
        oq_js = ("<script>(function(){var b=document.getElementById('oqbtn'),"
                 "p=document.getElementById('oqpanel');if(!b||!p)return;"
                 "b.addEventListener('click',function(e){e.stopPropagation();p.hidden=!p.hidden;});"
                 "document.addEventListener('click',function(e){"
                 "if(!p.hidden&&!p.contains(e.target)&&e.target!==b)p.hidden=true;});})();</script>")
        # THE project view = the Linear-style ROUND-grouped OUTLINE (clean, chronological, relationships
        # via indentation + hover-highlight). The spatial graph is retired from the UI but still reachable
        # by URL (?view=graph) — code kept, just unlinked — so nothing is destroyed and it's reversible.
        is_graph = view == "graph"
        head_tools = toolbar if is_graph else ""   # graph view keeps the type-filter toolbar; list view has none
        main_view = (fragment(h("div", {"class_": "graphcard proj-graph"}, raw(_graph_interactive(graph))), panel, raw(oq_js))
                     if is_graph else h("div", {"class_": "outlinecard"}, raw(_outline_html(graph))))
        # The project's recorded usability sessions — each row deep-links into the replay view.
        sessions_html = _sessions_section(
            store, services.list_usability_sessions(project_id=proj["id"], store=store))
        body = h("div", {"class_": "proj"},
                 h("div", {"class_": "proj-head"}, h("h1", {"class_": "h1"}, proj["title"]),
                   h("p", {"class_": "lead"}, proj.get("goal", "")), head_tools),
                 main_view, raw(sessions_html), raw(_hypotheses_html(proj["id"], store)),
                 raw(_decisions_html(proj["id"], store)))
        actions = fragment(top_btn, raw(_star("project", proj["id"], proj["title"], f'/projects/{proj["id"]}')))
        return _layout(proj["title"], body, store, active="projects",
                       crumbs=[(t("projects"), "/projects"), (proj["title"], None)], actions=actions)

    # ---- A hypothesis lives on its project page (the bets list); the canonical Ref route
    #      /hypotheses/{id} deep-links into that section (artifacts.ref_href). ----
    @app.get("/hypotheses/{hypothesis_id}")
    def hypothesis_detail(hypothesis_id: str):
        store = Store()
        try:
            hx = services.get_hypothesis(hypothesis_id, store=store)
        except KeyError:
            return HTMLResponse(_layout(t("not_found"),
                                        _empty_state(t("hypotheses_h"), t("runtime_maybe_cleared"),
                                                     icon="projects"),
                                        store, active="projects"))
        return RedirectResponse(f'/projects/{hx["project_id"]}#hyp-{hx["id"]}')

    # ---- A decision lives on its project page (the decisions list); the canonical Ref route
    #      /decisions/{id} deep-links into that section (artifacts.ref_href). ----
    @app.get("/decisions/{decision_id}")
    def decision_detail(decision_id: str):
        store = Store()
        try:
            dec = services.get_decision(decision_id, store=store)
        except KeyError:
            return HTMLResponse(_layout(t("not_found"),
                                        _empty_state(t("decisions_h"), t("runtime_maybe_cleared"),
                                                     icon="projects"),
                                        store, active="projects"))
        return RedirectResponse(f'/projects/{dec["project_id"]}#dec-{dec["id"]}')

    # ---- A report is a project-scope synthesis; its canonical URL is /syntheses/{id} (+ .pdf).
    #      /projects/{id}/meta is a convenience → the project's latest report. ----
    @app.get("/projects/{project_id}/meta")
    def project_meta(project_id: str):
        store = Store()
        reports = store.list_reports(project_id)
        if reports:
            return RedirectResponse(f'/syntheses/{reports[0]["id"]}')
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return HTMLResponse(_layout(t("not_found"), _empty_state(t("synthesis_kind"), t("runtime_maybe_cleared"), icon="overview"), store, active="projects"))
        return HTMLResponse(_layout(proj["title"] + " — " + t("synthesis_kind"),
                                    _empty_state(t("synthesis_kind"), t("report_unavailable"), icon="overview"),
                                    store, active="projects",
                                    crumbs=[(t("projects"), "/projects"), (proj["title"], f"/projects/{project_id}"), (t("synthesis_kind"), None)]))

    @app.get("/projects/{project_id}/plan", response_class=HTMLResponse)
    def project_plan(project_id: str) -> str:
        store = Store()
        try:
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state("Plan", t("runtime_maybe_cleared"), icon="plan"), store, active="projects")
        plan = services.get_plan(project_id, store=store)
        if not plan:
            body = h("div", {"class_": "page"}, raw(_empty_state("Plan", "Dieses Projekt hat noch keinen Plan (Freiform/Legacy).", icon="plan")))
        else:
            body = _plan_html(plan, store)
        return _layout(proj["title"] + " — Plan", body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f"/projects/{project_id}"), ("Plan", None)],
                       active="projects")
