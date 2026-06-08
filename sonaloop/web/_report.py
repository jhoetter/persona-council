"""Report — report-grade renderer (spec/meta-report-presentation-and-pdf.md, Phase 1).

Turns a stored report (a synthesis: outline + authored markdown sections + citations, and/or the
structured findings layer) into a presentation-quality document: a cover, a table of contents,
numbered sections, callout boxes (:::insight / :::recommendation / :::risk), pull-quotes, and
footnote-style citations. Built as clean semantic HTML + a print-first stylesheet so the
headless-Chromium PDF reuses the exact same markup. The host authors all text; this only typesets.
"""
from __future__ import annotations

import re

from ._html import h, raw, fragment, register_css
from ._components import _md, _icon
from ._i18n import t
from ..config import content_language
from ..assets import asset_url

# callout directive kind → (icon, css-suffix). A small fixed PRESENTATION set (not methodology vocab).
_CALLOUT = {"insight": ("bulb", "insight"), "recommendation": ("check", "rec"),
            "risk": ("alert", "risk"), "key": ("target", "key"), "keytakeaway": ("target", "key")}
_DIRECTIVE = re.compile(r":::(\w+)[ \t]*\n(.*?)\n:::", re.DOTALL)


def _ref_titler(report, store):
    node_title = {n["study_id"]: (n.get("title") or "") for n in (report.get("graph_snapshot") or {}).get("nodes", [])}

    def title(ref: str) -> str:
        if node_title.get(ref):
            return node_title[ref]
        rid = ref.split(":", 1)[-1]
        s = store.get_synthesis(rid)
        if s:
            return s.get("title", rid)
        c = store.get_council_session(rid)
        if c:
            return (c.get("prompt") or rid)[:70]
        return rid
    return title


_FIG = re.compile(r"!\[\[fig:(\d+)\]\]")


def _resolve_figure(f: dict, store) -> dict | None:
    """A figure ref → {url, caption} (or None if it can't be shown). Web is read-only: a prototype that
    was never screenshotted simply doesn't render (capture happens via an explicit MCP/CLI action)."""
    kind = f.get("kind")
    cap = f.get("caption", "")
    if kind == "asset" and f.get("id"):
        return {"url": asset_url(f["id"]), "caption": cap}
    if kind == "prototype" and f.get("id"):
        p = store.get_prototype(f["id"])
        if p and p.get("shot"):
            return {"url": asset_url(p["shot"]), "caption": cap or p.get("name", "")}
    if kind == "avatar" and f.get("id"):
        p = store.get_persona(f["id"])
        if p and p.get("avatar", {}).get("path"):
            return {"url": "/" + p["avatar"]["path"], "caption": cap or p.get("display_name", "")}
    if kind == "chart":
        # the analytical 2×2 of a (convergence) synthesis, embedded inline — the payoff of unifying
        # synthesis + report: a report shows a synthesis's structured findings (spec/unified-synthesis-report).
        sid = f.get("source_id") or f.get("id")
        syn = store.get_synthesis(sid) if sid else None
        if syn and f.get("of", "effort_impact") == "effort_impact":
            from ._components import _effort_impact
            from .. import artifacts as _A
            recs = _A.synthesis_recommendations(syn)
            chart = _effort_impact(recs) if recs else ""
            if chart:
                return {"html": chart, "caption": cap or syn.get("title", "")}
    return None


def _figure_html(fig: dict) -> str:
    inner = raw(fig["html"]) if fig.get("html") else h("img", {"src": fig["url"], "alt": fig.get("caption", ""), "loading": "lazy"})
    return h("figure", {"class_": "rp-fig"}, inner,
             h("figcaption", {}, fig["caption"]) if fig.get("caption") else "")


def _segment(md_text: str) -> str:
    """A markdown segment with :::callout::: blocks lifted into styled boxes."""
    out, pos = [], 0
    for m in _DIRECTIVE.finditer(md_text):
        pre = md_text[pos:m.start()].strip()
        if pre:
            out.append(raw(_md(pre)))
        icon, cls = _CALLOUT.get(m.group(1).lower(), ("dot", "insight"))
        out.append(h("div", {"class_": f"rp-call rp-{cls}"},
                     h("div", {"class_": "rp-call-ic"}, raw(_icon(icon))),
                     h("div", {"class_": "rp-call-body"}, raw(_md(m.group(2).strip())))))
        pos = m.end()
    rest = md_text[pos:].strip()
    if rest:
        out.append(raw(_md(rest)))
    return fragment(*out)


def _body(md_text: str, figs: list) -> str:
    """Render a section body: markdown + callouts, with inline ![[fig:N]] placeholders resolved to
    figures; any unreferenced figures append at the end."""
    out, used = [], set()
    parts = _FIG.split(md_text)
    for k, part in enumerate(parts):
        if k % 2 == 0:
            if part.strip():
                out.append(_segment(part))
        else:
            i = int(part) - 1
            if 0 <= i < len(figs):
                out.append(_figure_html(figs[i])); used.add(i)
    for i, fg in enumerate(figs):
        if i not in used:
            out.append(_figure_html(fg))
    return fragment(*out)


def render_report(report: dict, store) -> str:
    """Report-grade render of ANY synthesis (spec/unified-synthesis-report.md §3 — one renderer):
    project scope → narrative sections + figures; convergence scope → the structured analysis
    (findings → 2×2, voices) in the SAME report shell (cover + report typography)."""
    de = content_language() == "de"
    _t = report.get("title", "")           # the default title ends in " — Report"; custom titles show as-is
    for _suffix in (" — Report", " — Meta-Report"):   # legacy meta-report titles kept resolving
        if _t.endswith(_suffix):
            _t = _t[:-len(_suffix)]
            break
    project_title = _t

    if report.get("scope") != "project":
        # a convergence synthesis, rendered in the unified report shell.
        from ._synthesis import _synthesis_html
        status = report.get("status", "done")
        meta_line = " · ".join(x for x in [
            (f'{len(report.get("council_ids", []))} {t("councils")}' if report.get("council_ids") else ""),
            (t("done") if status == "done" else t("running")),
            (report.get("created_at") or "")[:10]] if x)
        cover = h("header", {"class_": "rp-cover"},
                  h("div", {"class_": "rp-eyebrow"}, t("synthesis_kind")),
                  h("h1", {"class_": "rp-title"}, project_title),
                  h("div", {"class_": "rp-metaline"}, meta_line))
        body, _toc = _synthesis_html(store, report, embed=True)
        return h("article", {"class_": "report report-syn"}, cover, raw(body))

    rtitle = _ref_titler(report, store)
    sections = report.get("sections", [])
    n_studies = len({x for sec in sections for x in sec.get("source_study_ids", [])})
    meta_line = " · ".join([
        t("n_sections", n=len(sections)),
        f"{n_studies} " + (("Studie" if n_studies == 1 else "Studien") if de
                           else ("study" if n_studies == 1 else "studies")),
        (report.get("created_at") or "")[:10],
    ])

    cover = h("header", {"class_": "rp-cover"},
              h("div", {"class_": "rp-eyebrow"}, t("synthesis_kind")),
              h("h1", {"class_": "rp-title"}, project_title),
              h("div", {"class_": "rp-metaline"}, meta_line),
              (h("p", {"class_": "rp-lead"}, raw(_md(report["lead"])))
               if report.get("lead") else ""))

    toc = h("nav", {"class_": "rp-toc"}, h("div", {"class_": "rp-toc-h"}, t("toc")),
            h("ol", {}, *[h("li", {}, h("a", {"href": f"#rp-s{i}"}, sec["heading"]))
                          for i, sec in enumerate(sections, 1)]))

    secs = []
    for i, sec in enumerate(sections, 1):
        figs = [rf for rf in (_resolve_figure(f, store) for f in (sec.get("figures") or [])) if rf]
        body_html = (_body(sec["markdown"], figs) if sec.get("markdown")
                     else h("p", {"class_": "muted"}, f"_({'noch nicht verfasst' if de else 'not yet authored'})_"))
        cites = ""
        if sec.get("citations"):
            rows = []
            for n, c in enumerate(sec["citations"], 1):
                council = h("span", {"class_": "rp-cite-src"}, f" · {rtitle(c['council_id'])}") if c.get("council_id") else ""
                quote = h("span", {"class_": "rp-cite-q"}, f"„{c['quote']}“") if c.get("quote") else ""
                rows.append(h("li", {}, h("span", {"class_": "rp-cite-n"}, str(n)),
                              h("span", {}, h("b", {}, rtitle(c["study_id"])), council, " ", quote)))
            cites = h("div", {"class_": "rp-cites"}, h("div", {"class_": "rp-cites-h"}, t("citations")),
                      h("ol", {}, *rows))
        src = ""
        if sec.get("source_study_ids"):
            src = h("div", {"class_": "rp-src"}, ("Quellen: " if de else "Sources: ")
                    + ", ".join(rtitle(x) for x in sec["source_study_ids"]))
        secs.append(h("section", {"class_": "rp-sec", "id": f"rp-s{i}"},
                      h("h2", {}, h("span", {"class_": "rp-num"}, f"{i:02d}"), sec["heading"]),
                      body_html, cites, src))
    return h("article", {"class_": "report"}, cover, toc, *secs)


register_css(r"""
/* Meta-report — report-grade document (spec/meta-report-presentation-and-pdf.md Phase 1) */
.report{max-width:780px;margin:0 auto;color:var(--ink);font-size:15px;line-height:1.7}
.report h2,.report h3,.report p,.report ul,.report ol{max-width:none}
/* cover */
.rp-cover{padding:8px 0 26px;margin-bottom:30px;border-bottom:1px solid var(--line)}
.rp-eyebrow{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.1em;color:var(--accent);font-weight:600}
.rp-title{font-size:34px;line-height:1.12;font-weight:700;margin:10px 0 0;letter-spacing:-.01em}
.rp-metaline{margin-top:12px;color:var(--muted);font-size:var(--t-sm);font-variant-numeric:tabular-nums}
.rp-lead{margin:22px 0 0;font-size:19px;line-height:1.6;color:var(--ink);font-weight:450;
  border-left:3px solid var(--accent);padding-left:18px}
.rp-lead p{margin:0}
/* table of contents */
.rp-toc{margin:0 0 34px;padding:16px 18px;background:var(--panel-2);border:1px solid var(--line);border-radius:var(--radius)}
.rp-toc-h{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:600;margin-bottom:8px}
.rp-toc ol{margin:0;padding:0;list-style:none;counter-reset:toc}
.rp-toc li{counter-increment:toc;padding:3px 0}
.rp-toc li::before{content:counter(toc,decimal-leading-zero);color:var(--faint);font-variant-numeric:tabular-nums;margin-right:10px;font-size:var(--t-sm)}
.rp-toc a{color:var(--ink);text-decoration:none}.rp-toc a:hover{color:var(--accent)}
/* sections */
.rp-sec{margin:0 0 40px;scroll-margin-top:70px}
.rp-sec h2{display:flex;align-items:baseline;gap:12px;font-size:23px;font-weight:650;line-height:1.25;margin:0 0 14px;letter-spacing:-.01em}
.rp-num{color:var(--faint);font-size:16px;font-weight:600;font-variant-numeric:tabular-nums}
.report p{margin:0 0 14px}.report ul,.report ol{margin:0 0 14px;padding-left:22px}.report li{margin:3px 0}
.report h3{font-size:16px;font-weight:600;margin:22px 0 8px}
/* pull-quote (blockquote) */
.report blockquote{margin:22px 0;padding:4px 0 4px 20px;border-left:3px solid var(--line-2);
  font-size:18px;line-height:1.55;color:var(--muted);font-style:italic}
.report blockquote p{margin:0}
/* callouts */
.rp-call{display:flex;gap:12px;margin:18px 0;padding:14px 16px;border:1px solid var(--line);border-left-width:3px;border-radius:var(--radius);background:var(--panel-2)}
.rp-call-ic{flex:none;line-height:0;margin-top:2px}.rp-call-ic svg{width:18px;height:18px}
.rp-call-body{min-width:0}.rp-call-body>:first-child{margin-top:0}.rp-call-body>:last-child{margin-bottom:0}
.rp-insight{border-left-color:var(--accent)}.rp-insight .rp-call-ic{color:var(--accent)}
.rp-rec{border-left-color:var(--green)}.rp-rec .rp-call-ic{color:var(--green)}
.rp-risk{border-left-color:var(--amber)}.rp-risk .rp-call-ic{color:var(--amber)}
.rp-key{border-left-color:var(--accent);background:var(--accent-weak)}.rp-key .rp-call-ic{color:var(--accent)}
/* citations + sources */
.rp-cites{margin:18px 0 0;padding-top:12px;border-top:1px solid var(--line)}
.rp-cites-h{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;margin-bottom:6px}
.rp-cites ol{list-style:none;margin:0;padding:0}
.rp-cites li{display:flex;gap:9px;font-size:var(--t-sm);color:var(--muted);padding:3px 0;line-height:1.5}
.rp-cite-n{flex:none;width:18px;height:18px;border-radius:50%;background:var(--panel-2);border:1px solid var(--line);
  font-size:var(--t-xs);display:inline-flex;align-items:center;justify-content:center;color:var(--faint)}
.rp-cites b{color:var(--ink);font-weight:550}.rp-cite-q{color:var(--muted)}
.rp-src{margin-top:10px;font-size:var(--t-xs);color:var(--faint)}
/* convergence synthesis embedded in the report shell — its blocks inherit report typography;
   drop the first block's top divider so it sits cleanly under the cover (spec/unified-synthesis-report §3) */
.report-syn .syn-main>.block:first-child,.report-syn .syn-main>section:first-child .block{border-top:0;margin-top:6px;padding-top:0}
.report-syn .block{max-width:none}
/* figures (Phase 2) — prototype screenshots, images, charts */
.rp-fig{margin:22px 0}
.rp-fig img{display:block;max-width:100%;height:auto;border:1px solid var(--line);border-radius:var(--radius);box-shadow:0 1px 4px rgba(0,0,0,.07)}
.rp-fig figcaption{margin-top:9px;font-size:var(--t-sm);color:var(--muted);text-align:center}
/* print: drop the app chrome, give the report the page (foundation for the Chromium PDF, Phase 3) */
@media print{
  .sidebar,.topbar,.cmdk,.drawer-wrap,.toc,.rail,.actions,.crumbs{display:none!important}
  .shell,.content,.page,main{margin:0!important;padding:0!important;max-width:none!important}
  body{background:#fff}
  .report{max-width:none}
  .rp-sec{break-inside:avoid}
  .rp-call,.report blockquote,.rp-cites,.rp-fig{break-inside:avoid}
  .rp-cover{break-after:avoid}
}
""")
