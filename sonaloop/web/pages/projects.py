"""Project pages: home/index, detail (outline/graph), meta-report, plan (spec/roadmap.md R2)."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)


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
        reports = store.list_meta_reports(proj["id"])
        # The Meta-Report button is ALWAYS shown (a fixed affordance) — a live link when a report
        # exists, a disabled button (with a hint) when it doesn't, so the action never disappears.
        meta_btn = (h("a", {"class_": "btn", "href": f'/projects/{proj["id"]}/meta'}, raw(_icon("syntheses")), " ", t("meta_report"))
                    if reports else
                    h("span", {"class_": "btn disabled", "title": t("meta_report_unavailable"), "aria-disabled": "true"},
                      raw(_icon("syntheses")), " ", t("meta_report")))
        if services.get_plan(proj["id"], store=store):    # the analyze/act/verify plan — opens in a right drawer
            plan_url = f'/projects/{proj["id"]}/plan'
            meta_btn = fragment(h("a", {"class_": "btn", "href": plan_url, "data-drawer": plan_url, "data-drawer-title": "Plan"},
                                  raw(_icon("plan")), " Plan"), meta_btn)
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
        oqbtn = h("button", {"class_": "btn", "id": "oqbtn"}, f'{t("legend")} · {t("open_questions_h")} ({len(oqs)})')
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
                              h("a", {"class_": "btn", "style": "padding:2px 8px", "href": f'/prototypes/{p["slug"]}'},
                                "ansehen ", raw(_icon("external"))), sl_html))
            proto_html = fragment(h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, f'{t("prototypes_h")} ({len(protos)})'),
                                  fragment(*rows))
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
            pulse_html = fragment(
                h("div", {"class_": "oqp-h"}, t("pulse")),
                h("div", {"class_": "strow"}, h("span", {"class_": "pill"}, ap["recommendation"]), " ",
                  h("span", {"class_": "muted small"}, cov_str, f' · {t("saturation")}: {ap["saturation"]["hint"]}'), gap_str))
        except Exception:
            pulse_html = ""
        # Open questions + legend + prototypes live in a floating panel so the graph keeps the canvas.
        panel = h("div", {"class_": "oqpanel", "id": "oqpanel", "hidden": True}, pulse_html,
                  h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, f'{t("build_order_h")} (edges)'),
                  h("div", {"class_": "pills", "style": "margin:6px 0 14px"}, edge_leg), sec_html,
                  h("div", {"class_": "oqp-h", "style": "margin-top:14px"}, t("open_questions_h")),
                  h("ul", {"style": "margin:6px 0 0 18px"}, oq_html), proto_html)
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
        body = h("div", {"class_": "proj"},
                 h("div", {"class_": "proj-head"}, h("h1", {"class_": "h1"}, proj["title"]),
                   h("p", {"class_": "lead"}, proj.get("goal", "")), head_tools),
                 main_view)
        actions = fragment(meta_btn, raw(_star("project", proj["id"], proj["title"], f'/projects/{proj["id"]}')))
        return _layout(proj["title"], body, store, active="projects",
                       crumbs=[(t("projects"), "/projects"), (proj["title"], None)], actions=actions)

    @app.get("/projects/{project_id}/meta", response_class=HTMLResponse)
    def project_meta(project_id: str) -> str:
        store = Store()
        try:
            md = services.export_meta_report(project_id, format="md", store=store)
            proj = services.get_research_project(project_id, store=store)
        except KeyError:
            return _layout(t("not_found"), _empty_state(t("meta_report"), t("runtime_maybe_cleared"), icon="overview"), store, active="projects")
        body = h("div", {"class_": "page"}, h("div", {"class_": "doc"}, raw(_md(md))))
        actions = h("button", {"class_": "btn", "onclick": "window.print()"}, t("export_pdf"))
        return _layout(proj["title"] + " — " + t("meta_report"), body, store,
                       crumbs=[(t("projects"), "/projects"), (proj["title"], f"/projects/{project_id}"), (t("meta_report"), None)],
                       active="projects", actions=actions)

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
