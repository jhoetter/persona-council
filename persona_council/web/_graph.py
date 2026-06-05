from __future__ import annotations

import json
import re

from .. import presentation as _pres
from ._i18n import t
from ._components import (
    _esc, _icon, _artifact_present, _proto_tags, _EDGE_COLORS, _theme_color,
    _RGRAPH_JS,
)


def _graph_layout(graph: dict) -> dict:
    """Deterministic initial layout: x by longest-path depth, y stacked within depth."""
    nodes = graph["nodes"]
    idx = {n["study_id"]: i for i, n in enumerate(nodes)}
    incoming = {n["study_id"]: [] for n in nodes}
    for e in graph["edges"]:
        if e["from_study"] in incoming and e["to_study"] in incoming:
            incoming[e["to_study"]].append(e["from_study"])
    depth: dict[str, int] = {}

    def d(sid, seen=()):
        if sid in depth:
            return depth[sid]
        if sid in seen or not incoming[sid]:
            depth[sid] = 0
            return 0
        depth[sid] = 1 + max(d(p, seen + (sid,)) for p in incoming[sid])
        return depth[sid]

    for n in nodes:
        d(n["study_id"])
    per_depth: dict[int, int] = {}
    pos = {}
    for n in sorted(nodes, key=lambda x: (depth[x["study_id"]], x["created_at"])):
        de = depth[n["study_id"]]
        row = per_depth.get(de, 0)
        per_depth[de] = row + 1
        pos[n["study_id"]] = (40 + de * 600, 30 + row * 108)
    return pos


# node box dimensions (must match _RGRAPH_JS NW/NH)
_NW, _NH = 320, 64
# Saved drag-layouts in localStorage are keyed by this; bump on any layout-algorithm change.
_LAYOUT_VERSION = 7


def _convex_hull(points: list[tuple]) -> list[tuple]:
    """Andrew's monotone chain — the convex hull of a point set (CCW), no shape assumed."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _expand_hull(hull: list[tuple], margin: float) -> list[list]:
    """Push each hull vertex outward from the centroid by `margin` (a faint surrounding envelope)."""
    import math
    cx = sum(p[0] for p in hull) / len(hull)
    cy = sum(p[1] for p in hull) / len(hull)
    out = []
    for x, y in hull:
        dx, dy = x - cx, y - cy
        d = math.hypot(dx, dy) or 1.0
        out.append([x + dx / d * margin, y + dy / d * margin])
    return out


def _methodology_layout(graph: dict) -> dict | None:
    """Generic DAG layout (spec/methodology-constellations.md §5): x = longest-path depth over
    `consumes`; a step's nodes fan vertically when it has >1 (diverge), sit on the axis when 1
    (a waist) → diamonds emerge for any fan→waist. Artifacts are placed in their PRODUCING step's
    column and routed to the first downstream step that consumes their tag — all read from the
    graph + tags, no phase-key literals. Returns {pos, diamonds, proto_*} or None (no methodology)."""
    ms = graph.get("methodology_state") or {}
    steps = ms.get("steps") or ms.get("phases") or []
    if not steps:
        return None
    by_id = {s["key"]: s for s in steps}
    # longest-path depth over the consumes DAG
    depth: dict[str, int] = {}

    def dep(sid: str) -> int:
        if sid in depth:
            return depth[sid]
        depth[sid] = 0  # guard
        cs = by_id.get(sid, {}).get("consumes", [])
        depth[sid] = (max((dep(c) for c in cs), default=-1) + 1)
        return depth[sid]

    for s in steps:
        dep(s["key"])
    COLW, ROWH, X0, AXIS = 600, 124, 40, 340
    maxdepth = max(depth.values(), default=0)
    depth_of = {s["key"]: depth[s["key"]] for s in steps}
    # ROUND / iteration inference: a new round begins when the flow returns to the ROOT phase (depth 0)
    # AFTER it has reached the terminal phase (max depth) — i.e. a real Deliver→Discover loop. Rounds
    # are laid out as vertical SWIMLANES so iterative loops read top-to-bottom and don't pile up.
    node_round: dict[str, int] = {}
    rnd, reached_end = 0, False
    for n in sorted(graph["nodes"], key=lambda n: n.get("created_at", "")):
        d = depth_of.get(n.get("phase", ""))
        if d is not None:
            if d == 0 and reached_end:
                rnd += 1; reached_end = False
            if d >= maxdepth:
                reached_end = True
        node_round[n["study_id"]] = rnd
    nrounds = max(node_round.values(), default=0) + 1
    col_x = {s["key"]: X0 + depth[s["key"]] * COLW for s in steps}
    by_step: dict[str, list] = {}
    by_cell: dict[tuple, list] = {}                           # (phase, round) -> nodes (one fan per cell)
    for n in graph["nodes"]:
        ph = n.get("phase", "")
        by_step.setdefault(ph, []).append(n)
        by_cell.setdefault((ph, node_round[n["study_id"]]), []).append(n)
    is_fan: dict[str, bool] = {s["key"]: (len(by_step.get(s["key"], [])) > 1) or bool(s.get("is_fan"))
                               for s in steps}
    BAND = max((len(v) for v in by_cell.values()), default=1) * ROWH + 170   # height of one iteration lane
    pos: dict[str, tuple] = {}
    for (ph, r), ns in by_cell.items():
        if ph not in col_x:
            continue
        ns = sorted(ns, key=lambda n: n.get("created_at", ""))
        k = len(ns)
        base = AXIS + r * BAND
        for i, n in enumerate(ns):
            pos[n["study_id"]] = (col_x[ph], base + (i - (k - 1) / 2.0) * ROWH)
    extra_x, j = X0 + (maxdepth + 1) * COLW, 0
    for n in graph["nodes"]:
        if n["study_id"] not in pos:
            pos[n["study_id"]] = (extra_x, AXIS + j * ROWH); j += 1
    # Faint diamond silhouette per (fan step, ROUND): the convex hull of that round's fan plus its
    # bracketing waist nodes IN THE SAME ROUND — so every iteration gets its own clean diamond.
    consumers: dict[str, list[str]] = {s["key"]: [] for s in steps}
    for s in steps:
        for c in s.get("consumes", []):
            consumers.setdefault(c, []).append(s["key"])
    diamonds = []
    for (ph, r), ns in by_cell.items():
        s = by_id.get(ph)
        if not s or not is_fan.get(ph) or not ns:
            continue
        node_ids = [n["study_id"] for n in ns]
        anchors: list[str] = []
        for c in s.get("consumes", []):                       # bracket: upstream WAIST (same round)
            if not is_fan.get(c):
                anchors += [n["study_id"] for n in by_cell.get((c, r), [])]
        for o in consumers.get(ph, []):                       # bracket: downstream WAIST (same round)
            if not is_fan.get(o):
                anchors += [n["study_id"] for n in by_cell.get((o, r), [])]
        pts = []
        for sid in node_ids + anchors:
            if sid not in pos:
                continue
            x, y = pos[sid]
            pts += [(x, y), (x + _NW, y), (x, y + _NH), (x + _NW, y + _NH)]
        hull = _convex_hull(pts)
        if len(hull) >= 3:
            diamonds.append(_expand_hull(hull, 18))

    def _match(name: str, step_key: str):
        cands = by_step.get(step_key, [])
        nw = set(re.findall(r"\w+", name.lower())) - {"lo", "fi", "mid", "der", "die", "das", "idee", "·"}
        best, score = None, 0
        for n in cands:
            sc = len(nw & set(re.findall(r"\w+", n.get("title", "").lower())))
            if sc > score:
                best, score = n, sc
        return best or (cands[0] if cands else None)

    # build steps (declare produces.artifact_type) and the steps that consume each artifact tag
    build_steps = [s for s in steps if (s.get("produces") or {}).get("artifact_type")]
    PW = 232
    proto_pos, proto_edges, used_y = {}, [], {}
    for pr in (graph.get("prototypes") or []):
        ptags = _proto_tags(pr)
        # the producing step: artifact_type matches, disambiguated by a shared discriminator tag
        bs = None
        for s in build_steps:
            prod = s["produces"]
            if prod.get("artifact_type") in ptags:
                disc = set(prod.get("more_tags") or [])
                if not disc or (disc & ptags):
                    bs = s; break
        if bs is None and build_steps:
            bs = build_steps[0]
        if bs is None:
            continue
        bk = bs["key"]
        outs = consumers.get(bk, [])
        nxt = outs[0] if outs else bk
        # prefer the CONCEPT NOTE that realizes this prototype as its upstream idea (ESV: concepts are
        # first-class; this gives the prototype an incoming edge so it doesn't float), else fuzzy-match.
        cnote = next((n for n in graph["nodes"] if n.get("note_kind") == "concept"
                      and n.get("prototype_id") == pr["id"]), None)
        src = cnote or _match(pr.get("name", ""), bk)
        cx = (col_x[bk] + _NW + col_x[nxt]) / 2 - PW / 2
        if cnote:                                                    # round-aware: place in the cnote's lane
            base = AXIS + node_round.get(cnote["study_id"], 0) * BAND
        elif src:
            base = pos[src["study_id"]][1]
        else:
            base = AXIS
        cy2 = base
        while round(cy2) in used_y.get(round(cx), set()):
            cy2 += 70
        used_y.setdefault(round(cx), set()).add(round(cy2))
        proto_pos[pr["id"]] = (cx, cy2)
        if cnote:                                                    # place the concept just left of its prototype
            pos[cnote["study_id"]] = (cx - COLW * 0.5, cy2)
        if src:
            proto_edges.append((src["study_id"], pr["id"], False))   # idea/concept → artifact (solid)
        # tested-at: the nearest downstream decide step requiring a session of one of this artifact's tags
        test_step = None
        for s in sorted(steps, key=lambda s: depth[s["key"]]):
            if depth[s["key"]] <= depth[bk]:
                continue
            req = s.get("requires") or {}
            need = set(req.get("session_of_tags") or []) | set(req.get("artifact_tags") or [])
            if need & ptags and s.get("convergence_node"):
                test_step = s; break
        if test_step:
            proto_edges.append((pr["id"], test_step["convergence_node"], True))  # artifact → tested-at (dashed)
    # un-prototyped concept notes: stack them in the ideation column (their plan_graph edge to the
    # down-select synthesis then renders) so no concept floats in the far-right dump.
    ideate_x = col_x.get(build_steps[0]["key"], X0) if build_steps else X0
    st: dict[int, int] = {}
    for n in graph["nodes"]:
        if n.get("note_kind") == "concept" and not n.get("prototype_id"):
            r = node_round.get(n["study_id"], 0)
            pos[n["study_id"]] = (ideate_x, AXIS + r * BAND - 150 - st.get(r, 0) * 72)
            st[r] = st.get(r, 0) + 1
    # Q3: clean PHASE-COLUMN HEADERS — one labelled lane per step in flow order, so the left→right
    # double-diamond is explicit (not inferred from overlapping hulls). Top sits above all nodes.
    miny = min((y for _x, y in pos.values()), default=AXIS)
    phase_cols = [{"label": (s.get("name") or s["key"]).split("·")[-1].strip() or s["key"],
                   "x": col_x[s["key"]] + _NW / 2, "is_fan": bool(s.get("is_fan")),
                   "i": i + 1, "top": miny - 58}
                  for i, s in enumerate(sorted(steps, key=lambda s: depth[s["key"]]))]
    # ITERATION lanes: a "Runde N" label per round on the far left (only when the run actually looped).
    round_lanes = ([{"label": f"Runde {r + 1}", "x": X0 - 4, "y": AXIS + r * BAND}
                    for r in range(nrounds)] if nrounds > 1 else [])
    return {"pos": pos, "diamonds": diamonds, "proto_pos": proto_pos, "proto_edges": proto_edges,
            "proto_w": PW, "phase_cols": phase_cols, "round_lanes": round_lanes, "node_round": node_round}


def _graph_interactive(graph: dict) -> str:
    """Interactive, drag-and-drop graph (vanilla JS/SVG, no deps): drag nodes, pan the
    background, scroll to zoom; click a node to open its synthesis."""
    nodes = graph["nodes"]
    if not nodes:
        return f'<p class="muted">{_esc(t("no_synthesis"))}</p>'
    vocab = graph["project"].get("themes", [])
    ml = _methodology_layout(graph)
    pos = ml["pos"] if ml else _graph_layout(graph)
    diamonds = ml["diamonds"] if ml else []
    # If an idea has a prototype that feeds the convergence, route THROUGH the prototype:
    # suppress the idea's direct edge to that convergence so there's one clear path.
    suppress = set()
    if ml:
        src_of, conv_of = {}, {}
        for a, b, dashed in ml.get("proto_edges", []):
            (conv_of if dashed else src_of).__setitem__(a, b)  # dashed: proto→conv; solid: idea→proto
        for proto, conv in conv_of.items():
            idea = next((s for s, pr in src_of.items() if pr == proto), None)
            if idea:
                suppress.add((idea, conv))
    jnodes = []
    for n in nodes:
        # node TYPE (council/synthesis/concept/note) is a first-class, filterable tag (Q4).
        ntype = n.get("note_kind") if str(n["study_id"]).startswith("note:") else str(n["study_id"]).split(":", 1)[0]
        tags = list(dict.fromkeys([ntype] + (n.get("theme_tags", []) or []))) if ntype else n.get("theme_tags", [])
        x, y = pos[n["study_id"]]
        sent = max(n.get("sentiment", {}).items(), key=lambda kv: kv[1])[0] if n.get("sentiment") else "—"
        if n.get("kind"):                         # heterogeneous evidence node (plan graph)
            sub = f'{n.get("kind_label", "")} · ' + (", ".join(t for t in tags if t != n["kind"] and t != ntype)[:48] or "—")
            color = n.get("color") or "#9aa0a6"
            href = n.get("href") or ""
        else:                                     # legacy synthesis node
            sub = f'{n.get("council_count", 0)} {t("councils")} · {sent} · ' + (", ".join(tags[:3]) or "—")
            color = _theme_color(tags[0], vocab) if tags else "#9aa0a6"
            href = f'/syntheses/{n["study_id"]}'
        jnodes.append({"id": n["study_id"], "x": x, "y": y, "tags": tags,
                       "label": n["title"][:96], "sub": sub, "color": color, "href": href})
    _colorlist = list(_EDGE_COLORS.values())
    jedges = []
    for e in graph["edges"]:
        if (e["from_study"], e["to_study"]) in suppress:
            continue  # routed through the prototype instead
        if e["from_study"] in pos and e["to_study"] in pos:
            col = _EDGE_COLORS.get(e["type"], "#9aa0a6")
            jedges.append({"from": e["from_study"], "to": e["to_study"], "color": col, "type": e["type"],
                           "mid": _colorlist.index(col) if col in _colorlist else 0})
    # Artifact nodes (placed in their build step) + dashed "tested-at" edges. Every label, glyph
    # and color is resolved from DATA (the artifact's type/tags + presentation hints) — nothing
    # methodology-specific is hardcoded here.
    if ml:
        ppos = ml.get("proto_pos", {})
        pw = ml.get("proto_w", 200)
        acolor: dict[str, str] = {}
        for pr in (graph.get("prototypes") or []):
            if pr["id"] not in ppos:
                continue
            x, y = ppos[pr["id"]]
            ap = _artifact_present(pr)
            acolor[pr["id"]] = ap["color"]
            sub = f'{ap["disc"]} · {ap["label"]}' if ap["disc"] else ap["label"]
            jnodes.append({"id": pr["id"], "x": x, "y": y, "tags": ["prototype"], "w": pw, "h": 52,
                           "label": pr["name"][:60],
                           "sub": sub, "color": ap["color"],
                           "glyph": _pres.glyph_icon(ap["glyph"]), "ext": True,
                           "href": f'/prototypes/{pr["slug"]}', "proto": True})
        for a, b, dashed in ml.get("proto_edges", []):
            col = acolor.get(a) or acolor.get(b) or "#9aa0a6"
            jedges.append({"from": a, "to": b, "color": col, "type": "artifact", "mid": 0, "dashed": bool(dashed)})
    # Sections — methodology-INDEPENDENT overlay groupings (spec/sections-and-composable-graph.md).
    # A PURE overlay: each section's hull is DERIVED from its member node bounds; sections never
    # affect the layout. Label/color/glyph come from DATA via present(kind) (+ object override).
    # (_pres is imported at module top; no local re-import — that would shadow it and make the
    # earlier glyph_icon() use above an UnboundLocalError.)
    bounds = {jn["id"]: (jn["x"], jn["y"], jn.get("w", _NW), jn.get("h", _NH)) for jn in jnodes}
    jsections = []
    for sec in sorted(graph.get("sections") or [], key=lambda s: s.get("order", 0)):
        pts: list = []
        present_ids = [m for m in sec.get("member_ids", []) if m in bounds]
        for mid in present_ids:
            x, y, w, h = bounds[mid]
            pts += [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
        if len(pts) < 3:
            continue
        poly = _expand_hull(_convex_hull(pts), 30)
        pres = _pres.present(sec.get("kind", "theme"), sec.get("presentation"))
        jsections.append({"id": sec["id"], "poly": poly, "label": sec.get("title", ""),
                          "color": pres["color"], "glyph": _pres.glyph_icon(pres.get("glyph", "")),
                          "kind": pres.get("short", sec.get("kind", "")),
                          "lx": min(p[0] for p in poly), "ly": min(p[1] for p in poly),
                          "members": present_ids})
    # SEC4 — methodology bridge: derive a labeled kind="phase" section per methodology phase from
    # the SAME plan layout, so phases render through the section mechanism (one mechanism) and
    # coexist with free theme sections (a node can be in a derived phase AND user themes). When
    # present, these replace the unlabeled diamond silhouettes.
    phase_sections = []
    _nrounds = max((ml.get("node_round") or {}).values(), default=0) + 1 if ml else 1
    # Single-iteration runs get the labelled phase hulls. When the run LOOPED (multiple rounds), those
    # hulls would span the swimlanes ugly — so we keep the per-round DIAMONDS + phase headers + round
    # lane labels instead, which read cleanly top-to-bottom.
    if ml and graph.get("methodology_state") and _nrounds == 1:
        steps = graph["methodology_state"].get("steps") or []
        by_phase: dict[str, list] = {}
        for n in nodes:
            by_phase.setdefault(n.get("phase", ""), []).append(n["study_id"])
        verify_consumes = [(s, s.get("consumes", [])) for s in steps if not s.get("is_fan")]
        pres_ph = _pres.present("phase")
        for i, fs in enumerate(s for s in steps if s.get("is_fan")):
            member_ids = list(by_phase.get(fs["key"], []))
            for v, cons in verify_consumes:           # include the converging waist synthesis
                if fs["key"] in cons:
                    member_ids += by_phase.get(v["key"], [])
            pts: list = []
            present_ids = [m for m in member_ids if m in bounds]
            for mid in present_ids:
                x, y, w, h = bounds[mid]
                pts += [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
            if len(pts) < 3:
                continue
            poly = _expand_hull(_convex_hull(pts), 46)
            label = fs.get("name", fs["key"]).split("·")[-1].strip() or fs["key"]
            phase_sections.append({"id": f"phase__{fs['key']}", "poly": poly, "label": label,
                                   "color": pres_ph["color"], "glyph": _pres.glyph_icon(pres_ph.get("glyph", "")),
                                   "kind": pres_ph.get("short", "Phase"), "phase": True,
                                   "lx": min(p[0] for p in poly), "ly": min(p[1] for p in poly),
                                   "members": present_ids})
        if phase_sections:
            diamonds = []                              # one mechanism: labeled phases replace diamonds
    jsections = phase_sections + jsections             # phases behind, user themes on top
    jphases = (ml.get("phase_cols") if ml else None) or []
    jrounds = (ml.get("round_lanes") if ml else None) or []
    # Icon path bodies for the notation/markers the graph JS renders inline (glyph icon
    # names arrive on nodes/sections; the renderer looks each up here). Single source of
    # truth: persona-icons. Small fixed set, sent once per graph.
    from persona_icons import REGULAR as _ICON_REGULAR
    _GRAPH_ICON_NAMES = ("diamond", "diamondFilled", "square", "squareSplit", "squareRows",
                         "squareCols", "squareGrid", "rectangle", "exchange", "wave",
                         "search", "pencil", "caretRight", "external")
    iconpaths = {n: _ICON_REGULAR[n]["body"] for n in _GRAPH_ICON_NAMES if n in _ICON_REGULAR}
    # Bump _LAYOUT_VERSION whenever the layout algorithm changes → stale saved drags are dropped.
    data = json.dumps({"nodes": jnodes, "edges": jedges, "diamonds": diamonds, "sections": jsections,
                       "phases": jphases, "rounds": jrounds, "iconpaths": iconpaths,
                       "key": graph["project"].get("id", "x"), "lv": _LAYOUT_VERSION},
                      ensure_ascii=False)
    hint = t("graph_hint")
    fit_t = t("graph_fit")
    reset_t = t("graph_reset")
    zin_t = t("graph_zoom_in")
    zout_t = t("graph_zoom_out")
    # The canvas fills its container (CSS height:100%); this fallback only matters
    # if rendered outside the full-bleed project layout.
    maxy = max((y for _x, y in pos.values()), default=0)
    height = max(360, int(maxy) + 64 + 48)
    return (
        '<div class="rgwrap">'
        f'<svg id="rg" width="100%" height="{height}"><defs>'
        + "".join(f'<marker id="rgah-{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                  f'orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{c}"/></marker>'
                  for i, c in enumerate(_EDGE_COLORS.values()))
        + '<pattern id="rggrid" width="26" height="26" patternUnits="userSpaceOnUse">'
          '<circle cx="1.2" cy="1.2" r="1.1" fill="var(--line-2)"/></pattern>'
        + '</defs>'
        + '<rect id="rgbg" x="0" y="0" width="100%" height="100%" fill="url(#rggrid)"/>'
        + '<g id="rgroot"><g id="rgrounds"></g><g id="rgphases"></g><g id="rgsections"></g><g id="rgdia"></g><g id="rgedges"></g><g id="rgnodes"></g></g></svg>'
        + f'<div class="rghint">{hint}</div>'
        + '<div class="rgctrls">'
          f'<div class="rgzl" id="rgzl">100%</div>'
          f'<button class="rgbtn" data-act="groups" title="{t("groups_toggle")}">{_icon("squareGrid")}</button>'
          f'<button class="rgbtn" data-act="zin" title="{zin_t}">+</button>'
          f'<button class="rgbtn" data-act="zout" title="{zout_t}">−</button>'
          f'<button class="rgbtn" data-act="fit" title="{fit_t}">⤢</button>'
          f'<button class="rgbtn" data-act="reset" title="{reset_t}">↺</button>'
          '</div>'
        + '<svg class="rgmini" id="rgmini" viewBox="0 0 172 118" preserveAspectRatio="none">'
          '<g id="rgmnodes"></g><rect id="rgmvp"></rect></svg>'
        + '</div>'
        f'<script type="application/json" id="rgdata">{data}</script>{_RGRAPH_JS}')


def _graph_svg(graph: dict) -> str:
    """Read-only SVG of the project graph: study nodes laid out in build order
    (top→bottom), typed edges as colored right-side arcs. Nodes link to the synthesis."""
    nodes = graph["nodes"]
    if not nodes:
        return f'<p class="muted">{_esc(t("no_synthesis"))}</p>'
    vocab = graph["project"].get("themes", [])
    idx = {n["study_id"]: i for i, n in enumerate(nodes)}
    NW, NH, X0, ROW = 380, 60, 24, 92
    XR = X0 + NW
    H = 24 + len(nodes) * ROW
    W = XR + 120
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:{W}px" '
             f'xmlns="http://www.w3.org/2000/svg" font-family="inherit">',
             '<defs>']
    for typ, col in _EDGE_COLORS.items():
        parts.append(f'<marker id="ah-{typ}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                     f'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{col}"/></marker>')
    parts.append('</defs>')
    # edges (drawn first, behind nodes)
    for e in graph["edges"]:
        if e["from_study"] not in idx or e["to_study"] not in idx:
            continue
        fi, ti = idx[e["from_study"]], idx[e["to_study"]]
        col = _EDGE_COLORS.get(e["type"], "#9aa0a6")
        y1 = 24 + fi * ROW + NH / 2
        y2 = 24 + ti * ROW + NH / 2
        bulge = XR + 24 + 10 * abs(ti - fi)
        parts.append(f'<path d="M{XR} {y1:.0f} C {bulge:.0f} {y1:.0f}, {bulge:.0f} {y2:.0f}, {XR} {y2:.0f}" '
                     f'fill="none" stroke="{col}" stroke-width="1.6" marker-end="url(#ah-{e["type"]})" opacity="0.85"/>')
    # nodes
    for i, n in enumerate(nodes):
        y = 24 + i * ROW
        tags = n.get("theme_tags", [])
        bar = _theme_color(tags[0], vocab) if tags else "#c9cdd6"
        sent = max(n.get("sentiment", {}).items(), key=lambda kv: kv[1])[0] if n.get("sentiment") else "—"
        title = _esc(n["title"][:46] + ("…" if len(n["title"]) > 46 else ""))
        sub = _esc(f'{n.get("council_count", 0)} councils · {sent} · ' + (", ".join(tags[:3]) or "—"))
        parts.append(
            f'<a href="/syntheses/{_esc(n["study_id"])}">'
            f'<rect x="{X0}" y="{y}" width="{NW}" height="{NH}" rx="9" fill="var(--panel)" stroke="var(--line)"/>'
            f'<rect x="{X0}" y="{y}" width="5" height="{NH}" rx="2.5" fill="{bar}"/>'
            f'<text x="{X0 + 16}" y="{y + 24}" font-size="13.5" font-weight="600" fill="var(--ink)">{title}</text>'
            f'<text x="{X0 + 16}" y="{y + 43}" font-size="11.5" fill="var(--muted)">{sub}</text>'
            f'</a>')
    parts.append('</svg>')
    return "".join(parts)


def _plan_html(plan: dict, store) -> str:
    tasks = plan.get("tasks", [])
    done = sum(1 for t in tasks if t["status"] == "done")
    complete = bool(tasks) and done == len(tasks)
    by_title = {t["id"]: t.get("title", t["id"]) for t in tasks}
    # Status marks are persona-icons (single source of truth); colour drives currentColor.
    STATUS = {"done": ("check", "var(--green)"), "active": ("half", "var(--accent)"),
              "todo": ("circle", "var(--muted)"), "blocked": ("alert", "var(--red)")}
    # Resolve evidence links by IDENTITY (which collection the ref lives in), not by a kind
    # literal — the kind LABEL comes from data via present(); storage membership is legitimate.
    _syn_ids = {s["id"] for s in store.list_syntheses()}
    _protos = {p["id"]: p for p in store.list_prototypes(plan["project_id"])}

    def ev_chip(r: dict) -> str:
        rid, kind = r.get("id", ""), r.get("kind", "")
        label = _pres.present(kind)["short"] if kind else rid
        href = None
        if rid in _protos:
            p = _protos[rid]
            href, label = f"/prototypes/{p['slug']}", f"{label} · {p.get('name', p['slug'])}"
        elif rid in _syn_ids:
            href = f"/syntheses/{rid}"
        elif store.get_council_session(rid):
            href = f"/councils/{rid}"
        if href:
            return f'<a class="ev" href="{href}">{_esc(label)} ↗</a>'
        return f'<span class="ev">{_esc(label)}</span>'

    def row(t: dict) -> str:
        mark, clr = STATUS.get(t["status"], ("circle", "var(--muted)"))
        cons = " · ".join(by_title.get(c, c) for c in t.get("consumes", []))
        cons_html = f'<div class="small muted" style="margin-top:4px">⊂ {_esc(cons)}</div>' if cons else ""
        req = t.get("requires", {}) or {}
        gates = []
        if req.get("min_inputs") is not None:
            gates.append(f"min. {req['min_inputs']} Inputs")
        if req.get("gate_tag"):
            gates.append(_pres.present(req["gate_tag"])["short"])
        for tg in (req.get("session_of_tags") or []):
            gates.append(f"Session: {_pres.present(tg)['short']}")
        for tg in (req.get("artifact_tags") or []):
            gates.append(f"Artefakt: {_pres.present(tg)['short']}")
        gates_html = "".join(f'<span class="gate">{_esc(x)}</span>' for x in gates)
        cap = t.get("capability", "")
        cap_html = f'<span class="pcap">{_esc(cap)}</span>' if cap else ""
        # skip the frame self-reference (a frame task produces a ref to itself); link the rest
        evs = "".join(ev_chip(r) for r in t.get("produces", []) if r.get("id") != t["id"])
        ev_html = f'<div class="evs">{evs}</div>' if evs else ""
        return (f'<div class="ptask"><div class="pmark" style="color:{clr}">{_icon(mark)}</div>'
                f'<div class="pbody"><div class="prow1"><span class="ptitle">{_esc(t.get("title", t["id"]))}</span>'
                f'{cap_html}{gates_html}</div>{cons_html}{ev_html}</div></div>')

    secs = []
    for b, label in [("analyze", "Analyze · verstehen"), ("act", "Act · Councils, Prototypen, Tests"),
                     ("verify", "Verify · verdichten & entscheiden")]:
        rows = "".join(row(t) for t in tasks if t["bucket"] == b)
        if rows:
            secs.append(f'<div class="psec"><div class="psec-h">{label}</div>{rows}</div>')
    pill = (f'<span class="pill" style="color:var(--green)">{_icon("dot")} Plan komplett</span>' if complete
            else f'<span class="pill">{len(tasks) - done} offen</span>')
    head = (f'<div class="card plan-head"><div class="ph-goal">{_esc(plan.get("goal", ""))}</div>'
            f'<div class="small muted" style="margin-top:6px">Methodik: '
            f'<b>{_esc(plan.get("methodology") or "freiform")}</b> · {len(tasks)} Tasks · {done} erledigt &nbsp;{pill}</div></div>')
    css = ("<style>.plan-head{margin-bottom:20px}.ph-goal{font-weight:650;font-size:16px;line-height:1.4}"
           ".psec{margin:0 0 24px}.psec-h{font-size:12px;text-transform:uppercase;letter-spacing:.05em;"
           "color:var(--muted);font-weight:600;margin:0 0 10px}"
           ".ptask{display:flex;gap:12px;padding:11px 13px;border:1px solid var(--line);border-radius:var(--radius);"
           "background:var(--panel);margin-bottom:8px}.pmark{font-weight:700;width:16px;text-align:center;flex:none}"
           ".pbody{flex:1;min-width:0}.prow1{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.ptitle{font-weight:550}"
           ".pcap{font-size:11px;color:var(--accent);background:var(--accent-weak);padding:1px 8px;border-radius:999px}"
           ".gate{font-size:11px;color:var(--muted);background:var(--hover);padding:1px 8px;border-radius:999px}"
           ".evs{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}.ev{font-size:11px;color:var(--muted);"
           "background:var(--panel-2);border:1px solid var(--line);padding:2px 8px;border-radius:6px;text-decoration:none}"
           "a.ev:hover{color:var(--accent);border-color:var(--accent)}</style>")
    return f'{css}<div class="page">{head}{"".join(secs)}</div>'


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
    for n in sorted(nodes, key=lambda n: n.get("created_at", "")):
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
    concepts = sorted((n for n in nodes if n.get("note_kind") == "concept"),
                      key=lambda n: n.get("created_at", ""))
    protos = graph.get("prototypes") or []
    pro_of = {c["study_id"]: [p for p in protos if p["id"] == c.get("prototype_id")] for c in concepts}
    used = {p["id"] for ps in pro_of.values() for p in ps}

    items: list[dict] = []

    def add(oid, color, title, kind, href, pk, r, order, indent=0):
        po, plabel = pmeta.get(pk, (99, ""))
        items.append({"oid": oid, "color": color or "#9aa0a6", "title": title, "kind": kind, "href": href,
                      "plabel": plabel, "po": po, "round": r, "order": order, "indent": indent})

    for n in nodes:
        if n.get("note_kind") == "concept" or n.get("phase", "") not in pmeta:
            continue
        add(n["study_id"], n.get("color", ""), n.get("title", ""), n.get("kind_label", n.get("kind", "")),
            n.get("href", ""), n.get("phase", ""), node_round[n["study_id"]], n.get("created_at", ""))
    for c in concepts:
        cr = node_round.get(c["study_id"], 0)
        add(c["study_id"], c.get("color", "#a142f4"), c.get("title", ""), "Konzept", c.get("href", ""),
            ideation, cr, c.get("created_at", ""))
        for p in pro_of.get(c["study_id"], []):
            add(p["id"], "#00897b", p["name"], f'Prototyp · {p.get("fidelity", "")}',
                f'/prototypes/{p["slug"]}', ideation, cr, c.get("created_at", "") + "~", indent=1)
    for p in protos:
        if p["id"] not in used:
            add(p["id"], "#00897b", p["name"], f'Prototyp · {p.get("fidelity", "")}',
                f'/prototypes/{p["slug"]}', ideation, 0, p.get("created_at", ""))

    # THEMES = the cross-cutting semantic sections (kind == "theme"): the "Kern-Insight" thread, the
    # "Prototypen-Leiter", "Konzepte (Ideation)" … (phase/journal sections are skipped — phase already
    # shows as the per-row tag). Shown Linear-style: a filter bar + per-row dots; activating a theme
    # highlights its (coherent) members and dims the rest — deliberate, not the overwhelming raw-edge hover.
    _TH_COLORS = ["#6d5ef0", "#0f9d8f", "#e0820a", "#c0476b", "#3a7bd5", "#8a6d3b", "#4a7d7d"]
    themes = [s for s in graph.get("sections", []) if s.get("kind") == "theme" and s.get("member_ids")]
    th_color = {s["id"]: _TH_COLORS[i % len(_TH_COLORS)] for i, s in enumerate(themes)}
    node_themes: dict[str, list] = {}
    for ti, s in enumerate(themes):
        for m in s.get("member_ids", []):
            node_themes.setdefault(m, []).append(ti)

    def row(it: dict) -> str:
        h = f' href="{_esc(it["href"])}"' if it["href"] else ""
        tw = "ol-tw" if it["indent"] else ""                  # tree connector for nested rows
        tis = node_themes.get(it["oid"], [])
        dots = "".join(f'<span class="olth-dot" style="background:{th_color[themes[i]["id"]]}" '
                       f'title="{_esc(themes[i]["title"])}"></span>' for i in tis)
        return (f'<a class="olrow {tw}" data-oid="{_esc(it["oid"])}" data-th="{" ".join(map(str, tis))}" '
                f'style="padding-left:{10 + it["indent"] * 26}px"{h}>'
                f'<span class="ol-dot" style="background:{it["color"]}"></span>'
                f'<span class="ol-ptag">{_esc(it["plabel"])}</span>'
                f'<span class="ol-title">{_esc(it["title"])}</span>'
                f'<span class="olth-dots">{dots}</span>'
                f'<span class="ol-kind">{_esc(it["kind"])}</span></a>')

    out = []
    if themes:                                                # theme filter bar (cross-cutting lens)
        chips = "".join(
            f'<button class="olth-chip" data-ti="{i}"><span class="olth-dot" '
            f'style="background:{th_color[s["id"]]}"></span>{_esc(s["title"])}</button>'
            for i, s in enumerate(themes))
        out.append(f'<div class="olthemes"><span class="olth-l">{t("themes_h")}</span>{chips}</div>')
    out.append('<div class="outline">')
    if nrounds > 1:
        for r in range(nrounds):
            ris = sorted((it for it in items if it["round"] == r), key=lambda it: (it["po"], it["order"]))
            if not ris:
                continue
            out.append(f'<details class="ol-phase" open><summary><span class="ol-gl ol-round">↻</span>'
                       f'<b>{t("round_n", n=r + 1)}</b> <span class="ol-cnt">{len(ris)}</span></summary>'
                       f'{"".join(row(it) for it in ris)}</details>')
    else:
        ris = sorted(items, key=lambda it: (it["po"], it["order"]))
        out.append(f'<div class="ol-flat">{"".join(row(it) for it in ris)}</div>')
    out.append("</div>")
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
