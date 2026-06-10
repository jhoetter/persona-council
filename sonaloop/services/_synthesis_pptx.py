"""PPTX export — the DOMAIN logic for a native PowerPoint deck of any report (which slides, which
data); the slide→.pptx mechanics live in sonaloop/_pptx.py. Split out of services/_synthesis.py to
keep both modules under the LOC bar (spec/refactor-plan.md), behaviour-preserving.
"""
from __future__ import annotations

import re as _re_pptx

from .. import artifacts as _A
from ..config import ROOT, content_language
from ..storage import Store
from ._synthesis import _SYNTHESIS_EXPORT_LABELS, get_synthesis


def _strip_md(s: str) -> str:
    """Inline markdown → clean presenter text (bold/italic/code/links/figure-refs removed) so no raw
    `**`, `_`, `` ` `` or `![[fig]]` markers leak into a slide."""
    s = _re_pptx.sub(r"!\[\[.*?\]\]", "", s or "")
    s = _re_pptx.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = _re_pptx.sub(r"__(.+?)__", r"\1", s)
    s = _re_pptx.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", s)
    s = _re_pptx.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", s)
    s = _re_pptx.sub(r"`(.+?)`", r"\1", s)
    s = _re_pptx.sub(r"\[(.+?)\]\(.*?\)", r"\1", s)
    return s.strip()


# callout directive kind → the colour role the slide paints it (mirrors the report's :::insight /
# :::recommendation / :::risk callout cards).
_CALLOUT_KIND = {"insight": "accent", "recommendation": "green", "rec": "green",
                 "risk": "amber", "key": "accent", "keytakeaway": "accent"}


def _md_blocks(md: str) -> list[dict]:
    """Markdown section body → a list of typed blocks the slide renderer styles like the report:
    {type: p|li|quote|callout|h, text, [kind,label]}. Callout fences (:::insight … :::) and
    blockquotes (>) are PRESERVED (not dropped) and inline markdown is stripped."""
    blocks: list[dict] = []
    lines = (md or "").split("\n")
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1; continue
        if s.startswith(":::"):
            tag = s[3:].strip().lower()
            body = []
            i += 1
            while i < n and lines[i].strip() != ":::":
                if lines[i].strip():
                    body.append(_strip_md(lines[i].strip()))
                i += 1
            i += 1  # closing fence
            if body:
                blocks.append({"type": "callout", "kind": _CALLOUT_KIND.get(tag, "accent"),
                               "label": (tag or "insight").replace("keytakeaway", "key").capitalize(),
                               "text": " ".join(body)})
            continue
        if s.startswith(">"):
            blocks.append({"type": "quote", "text": _strip_md(s.lstrip("> ").strip())})
        elif s[:2] in ("- ", "* "):
            blocks.append({"type": "li", "text": _strip_md(s[2:])})
        elif _re_pptx.match(r"^\d+\.\s", s):
            blocks.append({"type": "li", "text": _strip_md(_re_pptx.sub(r"^\d+\.\s", "", s))})
        elif s.startswith("#"):
            blocks.append({"type": "h", "text": _strip_md(s.lstrip("# ").strip())})
        else:
            blocks.append({"type": "p", "text": _strip_md(s)})
        i += 1
    return [b for b in blocks if b.get("text")]


def _li(texts: list[str]) -> list[dict]:
    return [{"type": "li", "text": _strip_md(t)} for t in texts if (t or "").strip()]


def _figure_to_chart(fig: dict, store: Store) -> dict | None:
    """A report `chart` figure → the neutral _pptx chart model, or None (non-chart / unresolvable).

    Mirrors the design-system chart `of`-kinds (see charts_catalogue / web/_report) so a deck shows
    the SAME chart the report/PDF does — as native, editable PowerPoint shapes."""
    if (fig or {}).get("kind") != "chart":
        return None
    of = fig.get("of", "effort_impact")
    series = [s for s in (fig.get("series") or []) if isinstance(s, dict)]
    if of in ("bar", "pie"):
        rows = [s for s in series if s.get("value") not in (None, "")]
        if not rows:
            return None
        return {"type": of, "categories": [_strip_md(s.get("label", "")) for s in rows],
                "values": [s.get("value") for s in rows]}
    if of == "stacked_bar":
        rows = [{"label": _strip_md(s.get("label", "")),
                 "segments": [{"label": _strip_md(g.get("label", "")), "value": g.get("value")}
                              for g in (s.get("segments") or []) if isinstance(g, dict)]}
                for s in series if s.get("segments")]
        return {"type": "stacked_bar", "rows": rows} if rows else None
    if of == "diverging_bar":
        rows = [{"label": _strip_md(s.get("label", "")), "positive": s.get("positive"), "negative": s.get("negative")}
                for s in series if s.get("positive") is not None or s.get("negative") is not None]
        return {"type": "diverging_bar", "rows": rows} if rows else None
    if of == "gauge":
        items = [{"label": _strip_md(s.get("label", "")), "value": s.get("value"), "max": s.get("max")}
                 for s in series if s.get("value") not in (None, "")]
        return {"type": "gauge", "items": items} if items else None
    if of == "dot_plot":
        rows = [{"label": _strip_md(s.get("label", "")),
                 "values": [v for v in (s.get("values") or []) if isinstance(v, (int, float))]}
                for s in series if s.get("values")]
        rows = [r for r in rows if r["values"]]
        return {"type": "dot_plot", "rows": rows} if rows else None
    if of == "heatmap":
        cols = [_strip_md(str(c)) for c in (fig.get("columns") or [])]
        rows = [{"label": _strip_md(s.get("label", "")), "values": list(s.get("values") or [])}
                for s in series if s.get("values")]
        return {"type": "heatmap", "columns": cols, "rows": rows} if cols and rows else None
    if of == "line":
        lines = [{"label": _strip_md(s.get("label", "")),
                  "points": [p for p in (s.get("points") or []) if isinstance(p, (int, float))]}
                 for s in series if s.get("points")]
        lines = [ln for ln in lines if len(ln["points"]) > 1]
        labels = [_strip_md(str(x)) for x in (fig.get("labels") or [])]
        return {"type": "line", "series": lines, "labels": labels} if lines else None
    if of == "burnup":
        lines = [{"label": _strip_md(s.get("label", "")),
                  "points": [p for p in (s.get("points") or []) if isinstance(p, (int, float))]}
                 for s in series if s.get("points")]
        lines = [ln for ln in lines if len(ln["points"]) > 1]
        if not lines:
            return None
        labels = [_strip_md(str(x)) for x in (fig.get("labels") or [])]
        # The deck reuses the native line model; the dotted ideal renders as a dashed Target series.
        return {"type": "line", "series": lines, "labels": labels, "target": fig.get("target")}
    if of == "stacked_area":
        bands = [{"label": _strip_md(s.get("label", "")),
                  "points": [p for p in (s.get("points") or []) if isinstance(p, (int, float))]}
                 for s in series if s.get("points")]
        bands = [b for b in bands if len(b["points"]) > 1]
        labels = [_strip_md(str(x)) for x in (fig.get("labels") or [])]
        return {"type": "stacked_area", "series": bands, "labels": labels} if bands else None
    if of == "column":
        items = []
        for s in series:
            if s.get("segments"):
                items.append({"label": _strip_md(s.get("label", "")),
                              "segments": [{"label": _strip_md(g.get("label", "")), "value": g.get("value")}
                                           for g in s["segments"] if isinstance(g, dict)]})
            elif s.get("value") not in (None, ""):
                items.append({"label": _strip_md(s.get("label", "")), "value": s.get("value")})
        return {"type": "column", "items": items} if items else None
    if of == "strip":
        rows = [{"label": _strip_md(s.get("label", "")),
                 "values": [v for v in (s.get("values") or []) if isinstance(v, (int, float))]}
                for s in series if s.get("values")]
        rows = [r for r in rows if r["values"]]
        if not rows:
            return None
        allv = [v for r in rows for v in r["values"]]
        mn = fig.get("min") if isinstance(fig.get("min"), (int, float)) else min(allv)
        mx = fig.get("max") if isinstance(fig.get("max"), (int, float)) else max(allv)
        # The continuous strip reuses the dot_plot model with a data-derived scale + unit suffix.
        return {"type": "dot_plot", "rows": rows, "min": mn, "max": mx, "unit": str(fig.get("unit") or "")}
    if of == "progress_strip":
        items = [{"label": _strip_md(s.get("label", "")), "value": s.get("value")}
                 for s in series if isinstance(s.get("value"), (int, float)) and s.get("value") > 0]
        return {"type": "progress_strip", "items": items} if items else None
    if of == "stats":
        items = []
        for s in series:
            if not (s.get("label") or s.get("value") not in (None, "")):
                continue
            it = {"label": _strip_md(s.get("label", "")),
                  "value": _strip_md(s["value"]) if isinstance(s.get("value"), str) else s.get("value")}
            if s.get("sub"):
                it["sub"] = _strip_md(s["sub"])
            items.append(it)
        return {"type": "stats", "items": items} if items else None
    if of == "effort_impact":
        sid = fig.get("source_id") or fig.get("id")
        syn = store.get_synthesis(sid) if sid else None
        if not syn:
            return None
        return _effort_impact_chart(syn)
    return None


def _figure_image(fig: dict, store: Store) -> tuple[str, str] | None:
    """An image figure (asset | prototype screenshot | avatar) → (local_file_path, caption), or None
    if it can't be embedded. Mirrors web/_report._resolve_figure but resolves to a FILE on disk so the
    PPTX can embed the actual bytes (the web/PDF load it by URL; a deck must carry it)."""
    from ..config import DATA_DIR
    kind = (fig or {}).get("kind"); cap = fig.get("caption", "")
    aid = None
    if kind == "asset" and fig.get("id"):
        aid = fig["id"]
    elif kind == "prototype" and fig.get("id"):
        p = store.get_prototype(fig["id"]) or {}
        aid = p.get("shot"); cap = cap or p.get("name", "")
    elif kind == "avatar" and fig.get("id"):
        p = store.get_persona(fig["id"]) or {}
        ap = (p.get("avatar") or {}).get("path")
        if ap:
            path = ROOT / ap
            return (str(path), cap or p.get("display_name", "")) if path.exists() else None
        return None
    if aid:
        path = DATA_DIR / aid
        if path.exists():
            return (str(path), cap)
    return None


def _effort_impact_chart(syn: dict) -> dict | None:
    pts = [{"x": e, "y": v, "label": _strip_md(txt)} for (txt, e, v) in _A.synthesis_recommendations(syn) if e and v]
    if not pts:
        return None
    L = _SYNTHESIS_EXPORT_LABELS[content_language()]
    return {"type": "scatter", "points": pts, "x_label": L["effort"], "y_label": L["value"],
            "quadrants": [L["q_quick"], L["q_big"], L["q_fill"], L["q_sink"]]}


def export_template_deck(out: str = "master-template.pptx") -> dict:
    """Render the deck MASTER TEMPLATE — every layout with its placeholder content (vendored
    _deck.SAMPLE_SLIDES ← sonaloop-design/deck.data.mjs, previewed at #/deck in the design docs)
    — to a real .pptx. The harness demo deck: `sonaloop template-deck` / `make template-deck`."""
    from .. import _deck, _pptx
    if not _pptx.available():
        raise RuntimeError("PPTX export needs the python-pptx package (run `uv sync`).")
    from ._common import write_export_bytes
    data = _pptx.render(_deck.SAMPLE_SLIDES, title=_deck.DECK_TITLE)
    return {"path": write_export_bytes(data, out), "slides": len(_deck.SAMPLE_SLIDES),
            "title": _deck.DECK_TITLE}


def export_synthesis_pptx(synthesis_id: str, store: Store | None = None) -> bytes:
    """Render ANY report (synthesis) as a native PowerPoint deck: a title slide + one slide per section
    (project scope) or per analytic layer (convergence scope), with native charts. Raises if the
    python-pptx package is unavailable (it degrades gracefully at the call sites)."""
    from .. import _pptx
    if not _pptx.available():
        raise RuntimeError("PPTX export needs the python-pptx package (run `uv sync`).")
    store = store or Store()
    syn = get_synthesis(synthesis_id, store)
    de = content_language() == "de"
    L = _SYNTHESIS_EXPORT_LABELS[content_language()]
    title = syn.get("title", "")
    for suffix in (" — Report", " — Meta-Report"):
        if title.endswith(suffix):
            title = title[:-len(suffix)]
            break
    kind_label = "Report"
    slides: list[dict] = []

    if syn.get("scope") == "project":
        secs = syn.get("sections", [])
        node_title = {n["study_id"]: (n.get("title") or "") for n in (syn.get("graph_snapshot") or {}).get("nodes", [])}

        def ref_title(ref: str) -> str:
            if node_title.get(ref):
                return node_title[ref]
            rid = ref.split(":", 1)[-1]
            s = store.get_synthesis(rid)
            if s:
                return s.get("title", rid)
            c = store.get_council_session(rid)
            return (c.get("prompt") or rid)[:60] if c else rid

        meta = f"{len(secs)} {'Abschnitte' if de else 'sections'}"
        slides.append({"kind": "cover", "eyebrow": kind_label, "title": title,
                       "subtitle": _strip_md(syn.get("lead", "")), "meta": meta,
                       "date": syn.get("created_at", "")[:10]})
        if len(secs) >= 3:  # the reader's map — only when there are chapters to map
            slides.append({"kind": "agenda", "heading": "Inhalt" if de else "Contents",
                           "items": [_strip_md(sec.get("heading", "")) for sec in secs]})
        for idx, sec in enumerate(secs, 1):
            figs = sec.get("figures") or []
            charts = [c for c in (_figure_to_chart(f, store) for f in figs) if c]
            images = [im for im in (_figure_image(f, store) for f in figs) if im]
            foot = ""
            if sec.get("source_study_ids"):
                foot = ("Quellen: " if de else "Sources: ") + ", ".join(ref_title(x) for x in sec["source_study_ids"])
            slides.append({"kind": "content", "num": f"{idx:02d}", "heading": sec.get("heading", ""),
                           "blocks": _md_blocks(sec.get("markdown", "")),
                           "chart": charts[0] if charts else None, "footnote": foot})
            for c in charts[1:]:
                slides.append({"kind": "content", "num": f"{idx:02d}", "heading": sec.get("heading", ""),
                               "blocks": [], "chart": c})
            for path, cap in images:   # prototype screenshots / images / avatars — one slide each, fitted
                slides.append({"kind": "image", "num": f"{idx:02d}", "heading": sec.get("heading", ""),
                               "image": path, "caption": cap})
    else:
        meta = f"{len(syn.get('council_ids', []))} {'Councils' if de else 'councils'}"
        slides.append({"kind": "cover", "eyebrow": kind_label, "title": title,
                       "subtitle": _strip_md(syn.get("goal", "")), "meta": meta,
                       "date": syn.get("created_at", "")[:10]})
        n = 0
        for key, heading in (("gesamtbild", L["big_picture"]), ("positionierung", L["positioning"])):
            if (syn.get(key) or "").strip():
                n += 1
                slides.append({"kind": "content", "num": f"{n:02d}", "heading": heading,
                               "blocks": _md_blocks(syn[key])})
        kps = _A.finding_texts(syn, "key_problem")
        if kps:
            n += 1
            slides.append({"kind": "content", "num": f"{n:02d}", "heading": L["key_problems"], "blocks": _li(kps)})
        chart = _effort_impact_chart(syn)
        if chart:
            n += 1
            recs = [(txt, e, v) for (txt, e, v) in _A.synthesis_recommendations(syn) if e and v]
            blocks = [{"type": "li", "text": f"{_strip_md(txt)}  ({L['effort']} {e}/5 · {L['value']} {v}/5)"}
                      for (txt, e, v) in recs]
            slides.append({"kind": "content", "num": f"{n:02d}", "heading": L["recommendations"],
                           "blocks": blocks, "chart": chart})
        oqs = _A.finding_texts(syn, "open_question")
        if oqs:
            n += 1
            slides.append({"kind": "content", "num": f"{n:02d}", "heading": L["open_questions"], "blocks": _li(oqs)})

    slides.append({"kind": "closing",
                   "title": "Vielen Dank" if de else "Thank you",
                   "text": ("Erstellt mit der Sonaloop-Research-Engine — jede Aussage in diesem Deck "
                            "führt auf eine inspizierbare Session zurück." if de else
                            "Built with the Sonaloop research engine — every statement in this deck "
                            "traces back to an inspectable session."),
                   "meta": f"{kind_label} · {title} · {syn.get('created_at', '')[:10]}"})
    return _pptx.render(slides, title=title or kind_label)
