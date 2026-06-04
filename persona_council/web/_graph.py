from __future__ import annotations

import json
import re

from .. import presentation as _pres
from ._i18n import t, _lang
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
        pos[n["study_id"]] = (40 + de * 300, 30 + row * 104)
    return pos


# node box dimensions (must match _RGRAPH_JS NW/NH)
_NW, _NH = 250, 58
# Saved drag-layouts in localStorage are keyed by this; bump on any layout-algorithm change.
_LAYOUT_VERSION = 5


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
    COLW, ROWH, X0, AXIS = 520, 118, 40, 340
    by_step: dict[str, list] = {}
    for n in graph["nodes"]:
        by_step.setdefault(n.get("phase", ""), []).append(n)
    col_x = {s["key"]: X0 + depth[s["key"]] * COLW for s in steps}
    pos: dict[str, tuple] = {}
    fan_half: dict[str, float] = {}
    is_fan: dict[str, bool] = {}
    for s in steps:
        sk = s["key"]
        ns = sorted(by_step.get(sk, []), key=lambda n: n.get("created_at", ""))
        k = len(ns)
        # a diamond emerges only once a fan actually HAS nodes (no empty silhouettes)
        is_fan[sk] = k > 1 or (s.get("is_fan") and k >= 1)
        for i, n in enumerate(ns):
            pos[n["study_id"]] = (col_x[sk], AXIS + (i - (k - 1) / 2.0) * ROWH)
        fan_half[sk] = (((k - 1) / 2.0) * ROWH + 64) if k else 64
    maxdepth = max(depth.values(), default=0)
    extra_x, j = X0 + (maxdepth + 1) * COLW, 0
    for n in graph["nodes"]:
        if n["study_id"] not in pos:
            pos[n["study_id"]] = (extra_x, AXIS + j * ROWH); j += 1
    # Faint silhouette per fan step = the CONVEX HULL of the fan's own nodes plus its bracketing
    # waist nodes (the single-node steps it consumes / that consume it). This is purely structural:
    # it becomes a diamond when a fan sits between two waists, a wedge for a root/terminal fan, and a
    # correct polygon for branches — it never fabricates a "diamond" where the DAG isn't diamond-shaped.
    consumers: dict[str, list[str]] = {s["key"]: [] for s in steps}
    for s in steps:
        for c in s.get("consumes", []):
            consumers.setdefault(c, []).append(s["key"])
    diamonds = []
    for s in steps:
        sk = s["key"]
        if not is_fan.get(sk):
            continue
        node_ids = [n["study_id"] for n in by_step.get(sk, [])]
        if not node_ids:
            continue
        anchors: list[str] = []
        for c in s.get("consumes", []):                       # bracket: upstream WAIST steps
            if not is_fan.get(c):
                anchors += [n["study_id"] for n in by_step.get(c, [])]
        for o in consumers.get(sk, []):                       # bracket: downstream WAIST steps
            if not is_fan.get(o):
                anchors += [n["study_id"] for n in by_step.get(o, [])]
        pts = []
        for sid in node_ids + anchors:
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
    PW = 200
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
        src = _match(pr.get("name", ""), bk)
        cx = (col_x[bk] + _NW + col_x[nxt]) / 2 - PW / 2
        cy2 = pos[src["study_id"]][1] if src else AXIS
        while round(cy2) in used_y.get(round(cx), set()):
            cy2 += 70
        used_y.setdefault(round(cx), set()).add(round(cy2))
        proto_pos[pr["id"]] = (cx, cy2)
        if src:
            proto_edges.append((src["study_id"], pr["id"], False))   # idea → artifact (solid)
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
    return {"pos": pos, "diamonds": diamonds, "proto_pos": proto_pos, "proto_edges": proto_edges, "proto_w": PW}


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
        tags = n.get("theme_tags", [])
        x, y = pos[n["study_id"]]
        sent = max(n.get("sentiment", {}).items(), key=lambda kv: kv[1])[0] if n.get("sentiment") else "—"
        if n.get("kind"):                         # heterogeneous evidence node (plan graph)
            sub = f'{n.get("kind_label", "")} · ' + (", ".join(t for t in tags if t != n["kind"])[:48] or "—")
            color = n.get("color") or "#9aa0a6"
            href = n.get("href") or ""
        else:                                     # legacy synthesis node
            sub = f'{n.get("council_count", 0)} {t("councils")} · {sent} · ' + (", ".join(tags[:3]) or "—")
            color = _theme_color(tags[0], vocab) if tags else "#9aa0a6"
            href = f'/syntheses/{n["study_id"]}'
        jnodes.append({"id": n["study_id"], "x": x, "y": y, "tags": tags,
                       "label": n["title"][:38] + ("…" if len(n["title"]) > 38 else ""),
                       "sub": sub, "color": color, "href": href})
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
            prefix = (ap["glyph"] + " ") if ap["glyph"] else ""
            sub = f'{ap["disc"]} · {ap["label"]} ↗' if ap["disc"] else f'{ap["label"]} ↗'
            jnodes.append({"id": pr["id"], "x": x, "y": y, "tags": [], "w": pw, "h": 46,
                           "label": (prefix + pr["name"])[:30] + ("…" if len(pr["name"]) > 28 else ""),
                           "sub": sub, "color": ap["color"],
                           "href": f'/prototypes/{pr["slug"]}', "proto": True})
        for a, b, dashed in ml.get("proto_edges", []):
            col = acolor.get(a) or acolor.get(b) or "#9aa0a6"
            jedges.append({"from": a, "to": b, "color": col, "type": "artifact", "mid": 0, "dashed": bool(dashed)})
    # Sections — methodology-INDEPENDENT overlay groupings (spec/sections-and-composable-graph.md).
    # A PURE overlay: each section's hull is DERIVED from its member node bounds; sections never
    # affect the layout. Label/color/glyph come from DATA via present(kind) (+ object override).
    from .. import presentation as _pres
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
                          "color": pres["color"], "glyph": pres.get("glyph", ""),
                          "kind": pres.get("short", sec.get("kind", "")),
                          "lx": min(p[0] for p in poly), "ly": min(p[1] for p in poly),
                          "members": present_ids})
    # SEC4 — methodology bridge: derive a labeled kind="phase" section per methodology phase from
    # the SAME plan layout, so phases render through the section mechanism (one mechanism) and
    # coexist with free theme sections (a node can be in a derived phase AND user themes). When
    # present, these replace the unlabeled diamond silhouettes.
    phase_sections = []
    if ml and graph.get("methodology_state"):
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
                                   "color": pres_ph["color"], "glyph": pres_ph.get("glyph", ""),
                                   "kind": pres_ph.get("short", "Phase"), "phase": True,
                                   "lx": min(p[0] for p in poly), "ly": min(p[1] for p in poly),
                                   "members": present_ids})
        if phase_sections:
            diamonds = []                              # one mechanism: labeled phases replace diamonds
    jsections = phase_sections + jsections             # phases behind, user themes on top
    # Bump _LAYOUT_VERSION whenever the layout algorithm changes → stale saved drags are dropped.
    data = json.dumps({"nodes": jnodes, "edges": jedges, "diamonds": diamonds, "sections": jsections,
                       "key": graph["project"].get("id", "x"), "lv": _LAYOUT_VERSION}, ensure_ascii=False)
    de = _lang() == "de"
    hint = ("Ziehen · Hintergrund schieben · Pinch / ⌘+Scroll = Zoom · F = einpassen"
            if de else "drag · pan background · pinch / ⌘+scroll to zoom · F to fit")
    fit_t = "Einpassen (F)" if de else "Fit to view (F)"
    reset_t = "Layout zurücksetzen (R)" if de else "Reset layout (R)"
    zin_t = "Zoom in (+)"
    zout_t = "Zoom out (−)"
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
        + '<g id="rgroot"><g id="rgsections"></g><g id="rgdia"></g><g id="rgedges"></g><g id="rgnodes"></g></g></svg>'
        + f'<div class="rghint">{hint}</div>'
        + '<div class="rgctrls">'
          f'<div class="rgzl" id="rgzl">100%</div>'
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
    STATUS = {"done": ("✓", "var(--green)"), "active": ("◐", "var(--accent)"),
              "todo": ("○", "var(--muted)"), "blocked": ("!", "var(--red)")}
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
        mark, clr = STATUS.get(t["status"], ("○", "var(--muted)"))
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
        return (f'<div class="ptask"><div class="pmark" style="color:{clr}">{mark}</div>'
                f'<div class="pbody"><div class="prow1"><span class="ptitle">{_esc(t.get("title", t["id"]))}</span>'
                f'{cap_html}{gates_html}</div>{cons_html}{ev_html}</div></div>')

    secs = []
    for b, label in [("analyze", "Analyze · verstehen"), ("act", "Act · Councils, Prototypen, Tests"),
                     ("verify", "Verify · verdichten & entscheiden")]:
        rows = "".join(row(t) for t in tasks if t["bucket"] == b)
        if rows:
            secs.append(f'<div class="psec"><div class="psec-h">{label}</div>{rows}</div>')
    pill = ('<span class="pill" style="color:var(--green)">● Plan komplett</span>' if complete
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
