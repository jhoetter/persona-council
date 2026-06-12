#!/usr/bin/env python3
"""Spacing-conformance harness (spec/ux-contract.md §10 W1) — the DOM-measured sweep.

Boots the same seeded app as scripts/ux_shots.py (same canonical screens) and walks the
RENDERED DOM: for every structural element (page chrome, headers, tabs row, filter bar,
list containers, rows, section gaps, card paddings, drawer/topbar chrome) it reads the
computed paddings / margins / gaps and classifies each value against the density system
(sonaloop-design "Spacing & density"):

  token    on the px grid — 0 or one of 4/8/12/16/20/24/28/32/40/48
  optical  a documented 1-3px hairline / micro-nudge (allowed by the spacing contract)
  em       fractional px from an em-sized rule — the design system's density-adaptive
           layer (buttons, inputs, entity rows, ⌘K) deliberately stays OFF the px grid
  center   resolved `margin: auto` centering of a measure (.page/.outline/.proj-head)
  exempt   an explicitly documented per-rule exemption (EXEMPT below, with the reason)
  FLAG     everything else — an off-grid value that must be fixed or documented

Usage:  uv run python scripts/ux_spacing.py [--out /tmp/ux/w1-spacing-table.txt]
Exit 1 while any FLAG remains. The final zero-flag table is committed into
spec/ux-audit.md (Round 4 · spacing conformance).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ux_shots  # noqa: E402  (env + temp store configured on import)

TOKENS = {0, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48}
OPTICAL = {1, 2, 3}

# Structural selectors (label, css selector). Micro-typography (icon-to-text gaps inside a
# chip) is not rhythm; this list is the page STRUCTURE the owner's screenshots judge.
SELECTORS: list[tuple[str, str]] = [
    ("page-chrome", ".sl-main > section"),
    ("topbar", ".sl-topbar"),
    ("page", ".page"),
    ("h1", ".h1"),
    ("lead", ".lead"),
    ("page-header", ".sl-page-header"),
    ("page-header-main", ".sl-page-header__main"),
    ("tabs", ".sl-tabs"),
    ("tab", ".sl-tab"),
    ("filter-bar", ".sl-filter-bar"),
    ("filter-search", ".sl-filter-search"),
    ("rows", ".rows"),
    ("row-group", ".group"),
    ("entity-row", ".rows .sl-entity"),
    ("file-row", ".rows .sl-file--row .sl-file__body"),
    ("proj-head", ".proj-head"),
    ("proj-chips", ".proj-head .pills"),
    ("outlinecard", ".outlinecard"),
    ("outline", ".outline"),
    ("phase-summary", ".ol-phase > summary"),
    ("round-label", ".ol-rlabel"),
    ("outline-row", ".olrow"),
    ("section", ".sec"),
    ("section-quiet", ".sl-section"),
    ("card", ".sl-card"),
    ("stats", ".stats"),
    ("stat", ".stat"),
    ("doc-grid", ".doc"),
    ("rail", ".rail"),
    ("rail-h4", ".rail h4"),
    ("props-quiet", ".sl-props--quiet"),
    ("prop", ".sl-props--quiet .sl-prop"),
    ("relations-group", ".relgrp"),
    ("relations-row", ".relrow"),
    ("turn-card", ".turn"),
    ("turn-rounds", ".qrounds"),
    ("turn-round", ".qround"),
    ("turn-q", ".qround-q"),
    ("turn-answers", ".qround-a"),
    ("turn-refs", ".turn-refs"),
    ("study-lead", ".es"),
    ("finding-row", ".fitem"),
    ("rec-row", ".rec"),
    ("plan-task", ".ptask"),
    ("plan-section", ".psec"),
    ("drawer-head", ".sl-drawer__head"),
    ("drawer-body", ".sl-drawer__body"),
    ("run-chip-wrap", ".runchip-wrap"),
    ("toolbar", ".ptoolbar"),
    ("empty-state", ".sl-empty"),
]

PROPS = ("padding-top", "padding-right", "padding-bottom", "padding-left",
         "margin-top", "margin-right", "margin-bottom", "margin-left",
         "row-gap", "column-gap")

# Documented per-rule exemptions (selector-label, property) -> reason. Every entry is a
# deliberate decision recorded in spec/ux-audit.md, not an escape hatch.
EXEMPT: dict[tuple[str, str], str] = {}

_MEASURE_JS = """
(sels) => {
  const out = [];
  for (const [label, sel] of sels) {
    const seen = new Set();
    let taken = 0;
    for (const el of document.querySelectorAll(sel)) {
      if (taken >= 4) break;
      const cs = getComputedStyle(el);
      if (cs.display === 'none') continue;
      const vals = {};
      for (const p of %PROPS%) vals[p] = cs.getPropertyValue(p);
      // resolved auto-centering: equal large left/right margins on a measure
      const ml = parseFloat(vals['margin-left']) || 0, mr = parseFloat(vals['margin-right']) || 0;
      const centered = ml > 48 && Math.abs(ml - mr) < 1.5;
      const key = JSON.stringify(vals) + centered;
      if (seen.has(key)) continue;
      seen.add(key); taken++;
      out.push({label, sel, vals, centered});
    }
  }
  return out;
}
""".replace("%PROPS%", str(list(PROPS)))


def classify(label: str, prop: str, px: float, centered: bool) -> str:
    if (label, prop) in EXEMPT:
        return "exempt"
    v = abs(px)
    if centered and prop in ("margin-left", "margin-right") and v > 48:
        return "center"
    # tree-indented outline rows: base pad 8 + n×24 indent steps — grid-derived
    if label == "outline-row" and prop == "padding-left" and (v - 8) % 24 < 0.02:
        return "token"
    if abs(v - round(v)) > 0.02:
        return "em"
    iv = round(v)
    if iv in TOKENS:
        return "token"
    if iv in OPTICAL:
        return "optical"
    return "FLAG"


def main() -> int:
    out_path = Path("/tmp/ux/w1-spacing-table.txt")
    if "--out" in sys.argv:
        out_path = Path(sys.argv[sys.argv.index("--out") + 1])
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ids = ux_shots.seed()
    port = ux_shots.free_port()
    proc = ux_shots.boot(port)
    base = f"http://127.0.0.1:{port}"
    rows: list[tuple[str, str, str, str, float, str]] = []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport=ux_shots.VIEWPORT, device_scale_factor=1)
            page = ctx.new_page()
            for name, path, *click in ux_shots.screens(ids):
                page.goto(base + path, wait_until="load")
                page.wait_for_timeout(300)
                if click:
                    page.click(click[0] + " >> nth=0")
                    page.wait_for_selector(click[1] if len(click) > 1
                                           else "#drawer.is-open .sl-slide")
                    page.wait_for_timeout(300)
                for m in page.evaluate(_MEASURE_JS, [list(s) for s in SELECTORS]):
                    for prop, raw_v in m["vals"].items():
                        try:
                            px = float(str(raw_v).replace("px", "") or 0)
                        except ValueError:
                            continue
                        if abs(px) < 0.01:
                            continue
                        status = classify(m["label"], prop, px, m["centered"])
                        rows.append((name, m["label"], m["sel"], prop, px, status))
            ctx.close()
            browser.close()
    finally:
        proc.terminate()
        proc.wait(timeout=10)

    # ---- the table: per screen, the distinct (selector, prop, value, status) tuples ----
    lines = ["W1 spacing conformance — DOM-measured (1440x900, light)",
             "tokens: 0/4/8/12/16/20/24/28/32/40/48 px · optical: 1-3px · em: density-adaptive em layer",
             ""]
    flags = 0
    per_screen: dict[str, int] = {}
    seen_globally: set = set()
    for name in dict.fromkeys(r[0] for r in rows):
        screen_rows = sorted({(r[1], r[3], r[4], r[5]) for r in rows if r[0] == name})
        n_flags = sum(1 for r in screen_rows if r[3] == "FLAG")
        per_screen[name] = n_flags
        lines.append(f"## {name}  ({n_flags} flags)")
        for label, prop, px, status in screen_rows:
            key = (label, prop, px, status)
            mark = " *" if key not in seen_globally else ""
            seen_globally.add(key)
            if status in ("FLAG", "exempt") or mark:
                lines.append(f"  {status:<8} {label:<18} {prop:<15} {px:g}px{mark}")
        flags += n_flags
        lines.append("")
    lines.append("summary: " + " · ".join(f"{k}={v}" for k, v in per_screen.items()))
    lines.append(f"TOTAL FLAGS: {flags}")
    lines.append("exemptions: " + ("; ".join(f"{k[0]}/{k[1]}: {v}" for k, v in EXEMPT.items()) or "none"))
    text = "\n".join(lines)
    out_path.write_text(text, encoding="utf-8")
    print(text)
    print(f"\nwrote {out_path}")
    return 1 if flags else 0


if __name__ == "__main__":
    raise SystemExit(main())
