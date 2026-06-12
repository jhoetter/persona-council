"""The Linear-style ROUND-grouped project outline (split out of _graph.py — behavior-preserving;
the LOC bar keeps every module under ~800 lines, tests/test_loc_budget.py)."""
from __future__ import annotations

from itertools import groupby

from .. import artifacts as _A_art
from .. import presentation as _pres
from ._components import _avatar, _icon
from ._graph_outline_extras import extra_outline_items, peek_url, producing_step
from ._graph_outline_sessions import merge_session_items
from ._html import h, raw, fragment
from ._i18n import t
from ._outline_chips import chips_html

# Per-kind leading icon (the §3.2 row-atom visual; sessions lead with the persona avatar and
# assets with a thumb/file icon instead — both ride the item's `lead` slot). Built via dict()
# kwargs: the kind-vocabulary grep gates ban kind-literal dict/set heads in web/*.py.
_KIND_ICONS = dict(council="councils", synthesis="syntheses", report="syntheses",
                   note="panel", prototype="prototype", url_artifact="link",
                   decision="flag", survey="plan", hypothesis="target",
                   open_question="help", live_url="external", flow="compass")


def _outline_html(graph: dict, sessions: dict | None = None, decisions: list | None = None,
                  hypotheses: list | None = None, surveys: list | None = None) -> str:
    """Linear-style PHASE-grouped outline — the single primary project view (ux-contract §3.4: the
    project page IS the outline; every primitive is a row in its phase context). Chronological by
    iteration (phase groups carry a `· Runde N` suffix when the project looped; flat when there is no
    plan). Relationships are shown the Linear way: HIERARCHY via indentation + tree connector (concept
    → its prototype, subject → its usability sessions), and CROSS-LINKS via HOVER-HIGHLIGHT (hover a
    row → its related rows light up, the rest dim) — never permanent edges. `sessions` = the prepared
    subject groups (outline_session_groups); decisions/hypotheses/surveys = the project's record lists
    (absorbed as phase rows via _graph_outline_extras) — all built by the page route which holds the
    Store, and optional so other callers keep the bare signature."""
    nodes = graph["nodes"]
    steps = (graph.get("methodology_state") or {}).get("steps") or []
    by_id = {s["key"]: s for s in steps}
    depth: dict[str, int] = {}

    def dep(k: str) -> int:
        if k in depth:
            return depth[k]
        depth[k] = 0
        depth[k] = max((dep(c) for c in by_id.get(k, {}).get("consumes", [])), default=-1) + 1
        return depth[k]

    for s in steps:
        dep(s["key"])
    maxdepth = max(depth.values(), default=0)
    depth_of = {s["key"]: depth[s["key"]] for s in steps}
    node_round: dict[str, int] = {}
    rnd, reached = 0, False
    # Detect ITERATIONS chronologically. Break created_at ties by DAG DEPTH so a single
    # Discover→Define→Develop→Deliver pass authored in one batch (identical timestamps) stays ONE round in
    # flow order — otherwise the round split falls back to list order (e.g. syntheses before councils) and
    # a synthesis wrongly lands a round BEFORE the council it consolidates.
    for n in sorted(nodes, key=lambda n: (n.get("created_at", ""), depth_of.get(n.get("phase", ""), 99))):
        d = depth_of.get(n.get("phase", ""))
        if d is not None:
            if d == 0 and reached:
                rnd += 1; reached = False
            if d >= maxdepth:
                reached = True
        node_round[n["study_id"]] = rnd
    nrounds = max(node_round.values(), default=0) + 1
    build_steps = [s["key"] for s in steps if (s.get("produces") or {}).get("artifact_type")]
    ideation = (build_steps[-1] if build_steps
                else next((s["key"] for s in reversed(steps) if s.get("is_fan")), None))
    ordered = sorted(steps, key=lambda s: depth[s["key"]])
    pmeta = {s["key"]: (i, (s.get("name") or s["key"]).split("·")[-1].strip() or s["key"])
             for i, s in enumerate(ordered)}
    protos = graph.get("prototypes") or []
    # ONE note entity: a BUILT note (data.prototype_id) pairs with its prototype, indented beneath it
    # (the former concept→prototype pairing); plain notes are standalone observation rows.
    note_nodes = [n for n in nodes if str(n["study_id"]).startswith("note:")]
    pro_of = {n["study_id"]: [p for p in protos if p["id"] in (n.get("prototype_ids") or [])]
              for n in note_nodes if n.get("prototype_ids")}
    used = {p["id"] for ps in pro_of.values() for p in ps}

    items: list[dict] = []

    def add(oid, color, title, kind, href, pk, r, order, ts, indent=0, last_child=False, plabel=None,
            rkind="", node=None):
        # `order` = the SORT key (a built note's prototype borrows the note's slot via a '#seq' suffix so it
        # nests right under it); `ts` = the row's OWN created_at, shown to the reader. `last_child` ends the
        # tree spine (the connector continues down through earlier siblings, stops at the last). `rkind` is
        # the row's machine kind for the chip CONTRACT (_outline_chips); `node` the data its builder reads.
        po, pl = pmeta.get(pk, (99, ""))
        items.append({"oid": oid, "color": color or "#9aa0a6", "title": title, "kind": kind, "href": href,
                      "plabel": plabel if plabel is not None else pl, "po": po, "round": r, "order": order,
                      "ts": ts, "indent": indent, "last_child": last_child, "rkind": rkind, "node": node or {}})

    # Plan-less projects (hand-built data / the study_ids report path) have NO methodology steps, so
    # pmeta is empty — their nodes must still render (parity with ?view=graph): one flat chronological
    # round, the kind label standing in for the phase column (tracker: outline-drops-study-nodes-on-
    # plan-less-projects). A phase-less legacy study node IS a synthesis (services._study_node).
    planless = not pmeta
    for n in nodes:
        if str(n["study_id"]).startswith("note:"):  # notes (phase-free) added below
            continue
        if n.get("phase", "") not in pmeta and not planless:   # plan graphs: phase-less rows have no slot
            continue
        kind = n.get("kind_label") or (t("synthesis_kind") if planless else n.get("kind", ""))
        href = n.get("href") or (f'/syntheses/{n["study_id"]}' if planless else "")
        add(n["study_id"], n.get("color", ""), n.get("title", ""), kind, href,
            n.get("phase", ""), node_round[n["study_id"]], n.get("created_at", ""), n.get("created_at", ""),
            plabel=kind if planless else None, rkind=n.get("kind", ""), node=n)
    # A standalone prototype sits in the phase whose act task built it (the plan's produces ref —
    # the same linkage the evidence nodes use), falling back to the ideation/build step.
    plan = graph.get("plan")
    for p in protos:                               # prototypes NOT paired under a built note → standalone
        if p["id"] not in used:
            pk = producing_step(plan, p["id"], ("artifact", "prototype")) or ideation
            add(p["id"], "#00897b", p["name"], _pres.present("prototype")["label"],
                f'/prototypes/{p["slug"]}', pk, 0, p.get("created_at", ""), p.get("created_at", ""),
                rkind="prototype", node=p)
    # Notes (phase-free): a CONCEPT (built, or carrying an artifact_kind) sits at the ideation/develop phase;
    # a plain observation at the FIRST (discover) phase, so the phase column reads meaningfully.
    notes_phase = ordered[0]["key"] if ordered else ""
    # Sequence the note→prototype pairs so each prototype sorts IMMEDIATELY after ITS note. The prototype
    # keeps its OWN created_at for DISPLAY (ts) but borrows the note's slot for SORT (order) — versions are
    # ordered by their own created_at (v0.1 before v0.2), nested under the concept they realise.
    seq = 0
    for nt in sorted(note_nodes, key=lambda n: n.get("created_at", "")):
        cr = node_round.get(nt["study_id"], 0)
        built = sorted(pro_of.get(nt["study_id"]) or [], key=lambda p: p.get("created_at", ""))
        is_concept = bool(built) or nt.get("artifact_kind")
        add(nt["study_id"], nt.get("color", "#f29900"), nt.get("title", "") or "—",
            nt.get("kind_label", ""), nt.get("href", ""), ideation if is_concept else notes_phase, cr,
            f'{nt.get("created_at", "")}#{seq:04d}', nt.get("created_at", ""),
            plabel=nt.get("kind_label", "") if planless else None, rkind=nt.get("kind", ""), node=nt)
        seq += 1
        for i, p in enumerate(built):
            add(p["id"], "#00897b", p["name"], _pres.present("prototype")["label"],
                f'/prototypes/{p["slug"]}', ideation, cr, f'{nt.get("created_at", "")}#{seq:04d}',
                p.get("created_at", ""), indent=1, last_child=(i == len(built) - 1),
                rkind="prototype", node=p)
            seq += 1

    # Reports — first-class project artifacts: listed in the FINAL phase group (the Deliver group,
    # after the methodology rows, before the deliverable assets), each opening its own report page.
    last_key = max(pmeta, key=lambda k: pmeta[k][0]) if pmeta else ""
    for mr in sorted(graph.get("reports", []), key=lambda m: m.get("created_at", "")):
        add(mr["id"], "#6d5ef0", mr.get("title", "") or t("synthesis_kind"), t("synthesis_kind"),
            f'/syntheses/{mr["id"]}', last_key, max(nrounds - 1, 0), f'~{mr.get("created_at", "")}',
            mr.get("created_at", ""), plabel=t("synthesis_kind") if planless else None,
            rkind="report", node=mr)

    # URL artifacts (A/B captures) in the council pool — first-class rows on the DEFAULT view
    # (tracker: sonaloop/project-presence-contract: nothing project-scoped is invisible). External
    # link target; the A/B label + capture-status chips come from the chip registry (rkind
    # "url_artifact"). Evidence INPUTS, so they sit at the first (discover) phase, round 0.
    for a in sorted(graph.get("artifacts") or [], key=lambda x: x.get("created_at", "")):
        po, pl = pmeta.get(notes_phase, (99, ""))
        kindlab = t("artifact_kind_" + (a.get("kind") or "url"))
        items.append({"oid": a["id"], "color": "#3a7bd5", "title": a.get("title") or a.get("url", ""),
                      "kind": kindlab, "href": a.get("url", ""), "external": True,
                      "plabel": pl or kindlab, "po": po, "round": 0,
                      "order": a.get("created_at", ""), "ts": a.get("created_at", ""),
                      "indent": 0, "last_child": False, "rkind": "url_artifact", "node": a})

    # Usability sessions nest under their SUBJECT row (tracker: project-page-sessions-live-under-
    # their-subject-in-the-outlin): prototype subjects under the existing prototype row (matched by
    # id or slug), live_url/flow subjects under a synthesized artifact-style parent.
    if sessions:
        proto_of = {k: p["id"] for p in protos for k in (p.get("id"), p.get("slug")) if k}
        merge_session_items(items, sessions, ideation, pmeta, proto_of)

    # UX P2 (§3.4): decisions / surveys / hypotheses / open questions / assets are outline rows in
    # their phase context (placement + fallbacks live in _graph_outline_extras) — no appendix.
    items.extend(extra_outline_items(
        graph, decisions=decisions or [], hypotheses=hypotheses or [], surveys=surveys or [],
        pmeta=pmeta, node_round=node_round, default_phase=notes_phase))

    # THEMES = the cross-cutting semantic sections (kind == "theme"): the "Kern-Insight" thread, the
    # "Prototypen-Leiter", "Konzepte (Ideation)" … (phase/journal sections are skipped — phase already
    # shows as the per-row tag). Shown Linear-style: a filter bar + per-row dots; activating a theme
    # highlights its (coherent) members and dims the rest — deliberate, not the overwhelming raw-edge hover.
    _TH_COLORS = ["#6d5ef0", "#0f9d8f", "#e0820a", "#c0476b", "#3a7bd5", "#8a6d3b", "#4a7d7d"]
    themes = [s for s in graph.get("sections", []) if s.get("kind") == "theme" and s.get("member_ids")]
    th_color = {s["id"]: _TH_COLORS[i % len(_TH_COLORS)] for i, s in enumerate(themes)}

    def _short(title: str) -> str:                            # compact, legible theme label for the pill
        s = title.split(":")[0].split("(")[0].strip()
        return s[:16] + ("…" if len(s) > 16 else "")

    th_short = [_short(s["title"]) for s in themes]
    node_themes: dict[str, list] = {}
    for ti, s in enumerate(themes):
        for m in s.get("member_ids", []):
            node_themes.setdefault(m, []).append(ti)

    def _fmt_ts(order: str) -> tuple[str, str]:
        """(short, full) from the row's created_at (order may carry a '#seq' pairing suffix)."""
        iso = str(order).split("#")[0]
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso)
            return f"{dt.day} {dt:%b} · {dt:%H:%M}", dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            return iso[:16].replace("T", " "), iso

    by_oid = {n["study_id"]: n for n in nodes}

    def row(it: dict) -> str:
        tw = ("ol-tw" + (" ol-last" if it.get("last_child") else "")) if it["indent"] else ""  # tree connector
        tis = node_themes.get(it["oid"], [])
        # Persona presence + stance lean (tracker: sonaloop/inspector-cinematic-
        # detail-density): councils show WHO debated (avatar cluster) and how it
        # leaned (stance dots, scale colors) — detail worth a close look, kept quiet.
        extra = by_oid.get(it["oid"]) or {}
        crew = ""
        pers = extra.get("personas") or []
        if pers:
            avs = fragment(*(raw(_avatar(pp, 18)) for pp in pers))
            more = (h("span", {"class_": "ol-more"}, f'+{extra.get("voices", 0) - len(pers)}')
                    if extra.get("voices", 0) > len(pers) else "")
            sc = extra.get("stance_counts") or {}
            dots = fragment(*(h("i", {"class_": "ol-sd",
                                      "style": f'background:{_A_art.stance_meta(int(v))["color"]}',
                                      "title": str(n)})
                              for v, n in sorted(sc.items(), key=lambda kv: -int(kv[0])) if n))
            crew = h("span", {"class_": "ol-crew"}, avs, more,
                     h("span", {"class_": "ol-sds"}, dots) if sc else "")
        pills = [                                             # labelled pills (colour + name), not cryptic dots
            h("span", {"class_": "olth-pill", "title": themes[i]["title"]},
              h("i", {"style": f'background:{th_color[themes[i]["id"]]}'}), th_short[i])
            for i in tis]
        # --ti feeds the tree-spine x-offset so a depth-2 child (session under a paired prototype)
        # draws its connector one indent step deeper than a depth-1 child.
        pk_url = peek_url(it.get("rkind", ""), it["oid"])
        attrs = {"class_": f"olrow {tw}", "data-oid": it["oid"], "data-th": " ".join(map(str, tis)),
                 "data-rkind": it.get("rkind", ""), "id": it.get("anchor"),
                 "style": f'padding-left:{10 + it["indent"] * 26}px'
                          + (f';--ti:{it["indent"]}' if it["indent"] else "")
                          + (";cursor:pointer" if pk_url and not it["href"] else "")}
        # Click = peek (§3.3): the row keeps its href as the deep link (middle-click / no-JS),
        # the data-drawer attribute additionally opens the kind's peek in the shared drawer.
        peek_attrs = ({"data-drawer": pk_url, "data-drawer-title": str(it["title"])[:90]}
                      if pk_url else {})
        ts_short, ts_full = _fmt_ts(it["ts"])
        ic = _KIND_ICONS.get(it.get("rkind", ""))
        lead = (raw(it["lead"]) if it.get("lead")           # session/asset rows: avatar / thumb lead
                else h("span", {"class_": "ol-ico", "style": f'color:{it["color"]}'}, raw(_icon(ic)))
                if ic else h("span", {"class_": "ol-dot", "style": f'background:{it["color"]}'}))
        # The label column carries the row's KIND (§3.2 / the §4 mockup: icon · kind · title);
        # the phase heads the group, so nothing repeats. Child rows (indent ≥1) leave the column
        # empty — the tree spine says whose child they are — and carry their kind (e.g. the
        # session fidelity) as a quiet trailing chip instead.
        cells = [lead,
                 h("span", {"class_": "ol-ptag"}, "" if it["indent"] else it["kind"]),
                 h("span", {"class_": "ol-title"}, it["title"]),
                 h("span", {"class_": "olth-pills"}, fragment(*pills)),
                 crew,
                 raw(chips_html(it)),                       # the chip CONTRACT (_outline_chips registry)
                 h("span", {"class_": "ol-ts", "title": ts_full}, ts_short)]
        if it["indent"]:
            cells.append(h("span", {"class_": "ol-kind"}, it["kind"]))
        ext = {"target": "_blank", "rel": "noopener"} if it.get("external") else {}
        chip = it.get("chip")
        if chip:
            # the funnel chip is a REAL link and <a> cannot nest — the row becomes a positioned <div>
            # whose main target is a stretched overlay link (.ol-stretch) layered UNDER the chip
            # (the peek rides the stretch link, so the funnel chip keeps its own target).
            link = (h("a", {"class_": "ol-stretch", "href": it["href"] or None,
                            "aria-label": it["title"], **ext, **peek_attrs})
                    if (it["href"] or pk_url) else "")
            chip_a = h("a", {"class_": "ol-funnel", "href": chip["href"]}, chip["text"])
            return h("div", attrs, *cells[:6], chip_a, *cells[6:], link)
        if it["href"]:
            attrs["href"] = it["href"]
            attrs.update(ext)
        attrs.update(peek_attrs)
        return h("a", attrs, *cells)

    # ROUND CAPTION (Linear: a group header should carry MEANING) — the essence of each round's most
    # converged output (its highest-depth synthesis, else its highest-depth node). Derived from the
    # node titles, never hardcoded; turns "Round 1 · 9" into the iteration's actual story.
    def _essence(title: str) -> str:
        parts = title.split(":")
        cand = parts[-1].strip() if len(parts) > 1 and len(parts[-1].strip()) > 12 else title.strip()
        return cand[:96] + ("…" if len(cand) > 96 else "")

    round_cap: dict[int, str] = {}
    for r in range(nrounds):
        # the round's most-converged node = its deepest phase node (a verify/decide synthesis sits at the
        # diamond's waist, i.e. max depth); no kind literal needed (and none allowed in the UI).
        pool = [n for n in nodes if node_round.get(n["study_id"]) == r and n.get("phase", "") in pmeta]
        best = max(pool, key=lambda n: depth_of.get(n.get("phase", ""), -1), default=None)
        if best:
            round_cap[r] = _essence(best.get("title", ""))

    out = []
    if themes:                                                # theme filter bar (cross-cutting lens)
        chips = [h("button", {"class_": "olth-chip", "data-ti": str(i)},
                   h("span", {"class_": "olth-dot", "style": f'background:{th_color[s["id"]]}'}), s["title"])
                 for i, s in enumerate(themes)]
        out.append(h("div", {"class_": "olthemes"}, h("span", {"class_": "olth-l"}, t("themes_h")), fragment(*chips)))
    def cluster_rows(ris: list[dict]) -> list:
        """One phase group's rows; evidence assets sit in a quiet *Evidence* sub-group at the
        end of their phase (decision §7.2 — cheap, predictable, forward-compatible); deliverable
        assets close the group (they close the Deliver group, which may coincide with it)."""
        main = [it for it in ris if not it.get("evidence") and not it.get("deliverable")]
        ev = [it for it in ris if it.get("evidence")]
        deliv = [it for it in ris if it.get("deliverable")]
        rows_html = [row(it) for it in main]
        if ev:
            rows_html.append(h("div", {"class_": "ol-rlabel"}, f'{t("asset_evidence_h")} ({len(ev)})'))
            rows_html += [row(it) for it in ev]
        rows_html += [row(it) for it in deliv]
        return rows_html

    # PHASE groups (ux-contract §3.4 / the §4 mockup): every row sits under its phase header,
    # whose count chip is the honest inventory (C8 — the retired header jump-chips' job). When
    # the project looped, the first group of each iteration carries `· Runde N` + the round's
    # essence caption. Plan-less projects stay one flat chronological list.
    inner = []
    if not pmeta:
        ris = sorted(items, key=lambda it: (it["po"], it["order"]))
        inner.append(h("div", {"class_": "ol-flat"}, fragment(*(row(it) for it in ris))))
    else:
        po_label = {po: lab for (po, lab) in pmeta.values()}
        for r in range(nrounds):
            ris = sorted((it for it in items if it["round"] == r), key=lambda it: (it["po"], it["order"]))
            first = True
            for po, cluster in groupby(ris, key=lambda it: it["po"]):
                cluster = list(cluster)
                label = po_label.get(po) or t("asset_deliverables_h")
                rmark = capH = ""
                if nrounds > 1 and first:
                    rmark = h("span", {"class_": "ol-gl ol-round"}, "↻")
                    label = f'{label} · {t("round_n", n=r + 1)}'
                    cap = round_cap.get(r, "")
                    capH = h("span", {"class_": "ol-rcap"}, f"— {cap}") if cap else ""
                first = False
                inner.append(h("details", {"class_": "ol-phase", "open": True},
                               h("summary", {}, rmark, h("b", {}, label), " ",
                                 h("span", {"class_": "ol-cnt"}, str(len(cluster))), capH),
                               fragment(*cluster_rows(cluster))))
    out.append(h("div", {"class_": "outline"}, fragment(*inner)))
    if themes:
        out.append(
            "<script>(function(){"
            "var chips=document.querySelectorAll('.olth-chip'),rows=document.querySelectorAll('.outline .olrow[data-oid]'),act=null;"
            "function apply(){rows.forEach(function(r){if(act===null){r.classList.remove('rel','dim');return;}"
            "var on=(' '+r.getAttribute('data-th')+' ').indexOf(' '+act+' ')>=0;"
            "r.classList.toggle('rel',on);r.classList.toggle('dim',!on);});}"
            "chips.forEach(function(c){var ti=c.getAttribute('data-ti');"
            "function hi(){if(act!==null)return;rows.forEach(function(r){var on=(' '+r.getAttribute('data-th')+' ').indexOf(' '+ti+' ')>=0;"
            "r.classList.toggle('rel',on);r.classList.toggle('dim',!on);});}"
            "function lo(){if(act===null)rows.forEach(function(r){r.classList.remove('rel','dim');});}"
            "c.addEventListener('mouseenter',hi);c.addEventListener('mouseleave',lo);"
            "c.addEventListener('click',function(){act=(act===ti?null:ti);"
            "chips.forEach(function(x){x.classList.toggle('on',x.getAttribute('data-ti')===act);});apply();});});"
            "})();</script>"
        )
    return "".join(out)
