"""The Linear-style ROUND-grouped project outline (split out of _graph.py — behavior-preserving;
the LOC bar keeps every module under ~800 lines, tests/test_loc_budget.py)."""
from __future__ import annotations

from .. import artifacts as _A_art
from ._components import _avatar
from ._html import h, raw, fragment
from ._i18n import t


def _outline_html(graph: dict) -> str:
    """Linear-style ROUND-grouped outline — the single primary project view. Always chronological by
    iteration (Runde 1 full pass → Runde 2 …; flat when there's only one round). Relationships are shown
    the Linear way: HIERARCHY via indentation + tree connector (concept → its prototype), and CROSS-LINKS
    via HOVER-HIGHLIGHT (hover a row → its related rows light up, the rest dim) — never permanent edges.
    Concepts + their prototypes get a definitive home under the ideation phase."""
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

    def add(oid, color, title, kind, href, pk, r, order, ts, indent=0, last_child=False):
        # `order` = the SORT key (a built note's prototype borrows the note's slot via a '#seq' suffix so it
        # nests right under it); `ts` = the row's OWN created_at, shown to the reader. `last_child` ends the
        # tree spine (the connector continues down through earlier siblings, stops at the last).
        po, plabel = pmeta.get(pk, (99, ""))
        items.append({"oid": oid, "color": color or "#9aa0a6", "title": title, "kind": kind, "href": href,
                      "plabel": plabel, "po": po, "round": r, "order": order, "ts": ts, "indent": indent,
                      "last_child": last_child})

    for n in nodes:
        if n.get("phase", "") not in pmeta:        # councils/syntheses; notes (phase-free) added below
            continue
        add(n["study_id"], n.get("color", ""), n.get("title", ""), n.get("kind_label", n.get("kind", "")),
            n.get("href", ""), n.get("phase", ""), node_round[n["study_id"]], n.get("created_at", ""), n.get("created_at", ""))
    for p in protos:                               # prototypes NOT paired under a built note → standalone
        if p["id"] not in used:
            add(p["id"], "#00897b", p["name"], f'Prototyp · {p.get("fidelity", "")}',
                f'/prototypes/{p["slug"]}', ideation, 0, p.get("created_at", ""), p.get("created_at", ""))
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
            f'{nt.get("created_at", "")}#{seq:04d}', nt.get("created_at", ""))
        seq += 1
        for i, p in enumerate(built):
            add(p["id"], "#00897b", p["name"], f'Prototyp · {p.get("fidelity", "")}',
                f'/prototypes/{p["slug"]}', ideation, cr, f'{nt.get("created_at", "")}#{seq:04d}',
                p.get("created_at", ""), indent=1, last_child=(i == len(built) - 1))
            seq += 1

    # Reports — first-class project artifacts: listed inline at the end (po=99 → after the
    # methodology rows, in the last round), each opening its own report page. Add as many as you like.
    for mr in sorted(graph.get("reports", []), key=lambda m: m.get("created_at", "")):
        items.append({"oid": mr["id"], "color": "#6d5ef0", "title": mr.get("title", "") or t("synthesis_kind"),
                      "kind": t("synthesis_kind"), "href": f'/syntheses/{mr["id"]}', "plabel": t("synthesis_kind"),
                      "po": 99, "round": max(nrounds - 1, 0), "order": f'~{mr.get("created_at", "")}',
                      "ts": mr.get("created_at", ""), "indent": 0, "last_child": False})

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
        attrs = {"class_": f"olrow {tw}", "data-oid": it["oid"], "data-th": " ".join(map(str, tis)),
                 "style": f'padding-left:{10 + it["indent"] * 26}px'}
        if it["href"]:
            attrs["href"] = it["href"]
        ts_short, ts_full = _fmt_ts(it["ts"])
        return h("a", attrs,
                 h("span", {"class_": "ol-dot", "style": f'background:{it["color"]}'}),
                 h("span", {"class_": "ol-ptag"}, it["plabel"]),
                 h("span", {"class_": "ol-title"}, it["title"]),
                 h("span", {"class_": "olth-pills"}, fragment(*pills)),
                 crew,
                 h("span", {"class_": "ol-ts", "title": ts_full}, ts_short),
                 h("span", {"class_": "ol-kind"}, it["kind"]))

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
    inner = []
    if nrounds > 1:
        for r in range(nrounds):
            ris = sorted((it for it in items if it["round"] == r), key=lambda it: (it["po"], it["order"]))
            if not ris:
                continue
            cap = round_cap.get(r, "")
            capH = h("span", {"class_": "ol-rcap"}, f"— {cap}") if cap else ""
            inner.append(h("details", {"class_": "ol-phase", "open": True},
                           h("summary", {}, h("span", {"class_": "ol-gl ol-round"}, "↻"),
                             h("b", {}, t("round_n", n=r + 1)), " ", h("span", {"class_": "ol-cnt"}, str(len(ris))), capH),
                           fragment(*(row(it) for it in ris))))
    else:
        ris = sorted(items, key=lambda it: (it["po"], it["order"]))
        inner.append(h("div", {"class_": "ol-flat"}, fragment(*(row(it) for it in ris))))
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
