"""Web UI asset strings (CSS + inline JS) extracted from web.py (spec/refactor-plan.md target 1). Pure constants — no behaviour, imported back into web.py."""

CSS = """
/* Linear-grade design system (spec/linear-design-system.md). Token-driven — one rewrite re-skins
   the whole app. Light defaults; dark (Linear's signature) via prefers-color-scheme + [data-theme]. */
:root{
  --bg:#ffffff;--sidebar:#fbfbfb;--panel:#ffffff;--panel-2:#f6f6f7;--overlay:#ffffff;
  --line:#ececed;--line-2:#f3f3f4;--ink:#1a1c1f;--muted:#6b7076;--faint:#9098a0;
  --accent:#5e6ad2;--accent-ink:#ffffff;--accent-weak:#eef0fb;--hover:#f5f5f6;--sel:#f0f1f4;
  --green:#3d9b6b;--amber:#b87a25;--red:#cf4d5f;--violet:#7a5ed1;--skep:#c2683f;--blue:#3d7fc4;
  --radius:8px;--radius-sm:6px;--row-h:48px;--ease:cubic-bezier(.4,0,.2,1);
  --shadow-sm:0 1px 2px rgba(20,22,26,.05);
  --shadow-lg:0 8px 28px rgba(20,22,26,.14),0 1px 2px rgba(20,22,26,.08);
  /* design-system scales (spec/design-system.md §2) — adopt incrementally; additive, no pixel change */
  --t-xs:11px;--t-sm:12px;--t-body:13px;--t-md:15px;--t-prose:16px;--t-lg:18px;--t-xl:24px;
  --s-1:4px;--s-2:8px;--s-3:12px;--s-4:16px;--s-5:20px;--s-6:24px;--s-8:32px;
}
@media (prefers-color-scheme: dark){:root{
  --bg:#101113;--sidebar:#0d0e10;--panel:#16171a;--panel-2:#1c1d21;--overlay:#1a1b1e;
  --line:#23252a;--line-2:#1b1d21;--ink:#e6e7ea;--muted:#8a8f98;--faint:#6b7076;
  --accent:#7c84e8;--accent-ink:#ffffff;--accent-weak:#1d2030;--hover:#1a1b1f;--sel:#1f2128;
  --green:#4cb782;--amber:#d9a23b;--red:#e0566a;--violet:#9a8cff;--skep:#d98a63;--blue:#5e9fe0;
  --shadow-sm:0 1px 2px rgba(0,0,0,.4);--shadow-lg:0 8px 28px rgba(0,0,0,.45),0 1px 2px rgba(0,0,0,.3);
}}
:root[data-theme="light"]{--bg:#ffffff;--sidebar:#fbfbfb;--panel:#fff;--panel-2:#f6f6f7;--overlay:#fff;--line:#ececed;--line-2:#f3f3f4;--ink:#1a1c1f;--muted:#6b7076;--faint:#9098a0;--accent:#5e6ad2;--accent-ink:#fff;--accent-weak:#eef0fb;--hover:#f5f5f6;--sel:#f0f1f4;--green:#3d9b6b;--amber:#b87a25;--red:#cf4d5f;--violet:#7a5ed1;--skep:#c2683f;--blue:#3d7fc4;}
:root[data-theme="dark"]{--bg:#101113;--sidebar:#0d0e10;--panel:#16171a;--panel-2:#1c1d21;--overlay:#1a1b1e;--line:#23252a;--line-2:#1b1d21;--ink:#e6e7ea;--muted:#8a8f98;--faint:#6b7076;--accent:#7c84e8;--accent-ink:#fff;--accent-weak:#1d2030;--hover:#1a1b1f;--sel:#1f2128;--green:#4cb782;--amber:#d9a23b;--red:#e0566a;--violet:#9a8cff;--skep:#d98a63;--blue:#5e9fe0;}

*{box-sizing:border-box}
html,body{height:100%}
body.spa-loading{cursor:progress}
body{margin:0;font:13px/1.5 "Inter","Inter Variable",-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased;letter-spacing:-0.003em}
a{color:inherit;text-decoration:none}
.muted{color:var(--muted)}.small{font-size:var(--t-sm)}.faint{color:var(--faint)}
svg.ic{width:16px;height:16px;flex-shrink:0;stroke:currentColor;fill:none;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round;vertical-align:-3px}
::selection{background:var(--accent-weak)}

/* ---- app shell ---- */
.app{display:flex;height:100vh;overflow:hidden;--sidebar-w:248px}
.sidebar{width:var(--sidebar-w);min-width:var(--sidebar-w);background:var(--sidebar);border-right:1px solid var(--line);display:flex;flex-direction:column;flex-shrink:0;overflow:hidden;transition:width 200ms var(--ease),min-width 200ms var(--ease),border-right-width 200ms}
.app.collapsed .sidebar{width:0;min-width:0;border-right-width:0}
.brand{height:var(--row-h);flex-shrink:0;display:flex;align-items:center;gap:8px;padding:0 14px;font-weight:680;font-size:var(--t-body);border-bottom:1px solid var(--line);white-space:nowrap}
.brand .mark{display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;color:var(--accent)}
.brand .mark svg{width:22px;height:22px;overflow:visible}
.sb-scroll{overflow:auto;padding:10px 8px;flex:1;min-height:0}
.nav{display:flex;flex-direction:column;gap:1px}
.nav a{display:flex;align-items:center;gap:9px;padding:5px 8px;border-radius:6px;color:var(--ink);font-weight:500;position:relative;min-height:30px}
.nav a .ic{color:var(--faint)}
.nav a:hover{background:var(--hover)}
.nav a.active{background:var(--sel);color:var(--ink);font-weight:600}
.nav a.active::before{content:'';position:absolute;left:-8px;top:7px;bottom:7px;width:2.5px;border-radius:0 3px 3px 0;background:var(--accent)}
.nav a.active .ic{color:var(--accent)}
.navhead{font-size:var(--t-xs);letter-spacing:.05em;text-transform:uppercase;color:var(--faint);margin:18px 9px 6px;font-weight:650}
.sb-quick{display:flex;flex-direction:column;gap:1px}
.sb-quick a{display:block;padding:5px 9px;border-radius:6px;color:var(--muted);font-size:var(--t-sm);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sb-quick a:hover{background:var(--hover);color:var(--ink)}
.sb-foot{padding:10px 14px;border-top:1px solid var(--line);font-size:var(--t-sm)}
.sb-foot a{color:var(--muted)}.sb-foot a:hover{color:var(--accent)}
/* ---- sidebar user / settings menu ---- */
.usermenu{position:relative;flex-shrink:0;border-top:1px solid var(--line);padding:8px}
.um-trigger{width:100%;display:flex;align-items:center;gap:9px;padding:6px 8px;border:1px solid transparent;border-radius:8px;background:transparent;cursor:pointer;color:var(--ink);font-size:var(--t-body);font-weight:500;font-family:inherit}
.um-trigger:hover{background:var(--hover)}
.usermenu.open .um-trigger{background:var(--hover)}
.um-ava{display:flex;align-items:center;justify-content:center;width:22px;height:22px;flex-shrink:0;color:var(--muted)}
.um-ava svg{width:18px;height:18px}
.um-name{flex:1;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.um-caret{color:var(--muted);display:inline-flex;transition:transform .15s var(--ease)}
.um-caret .ic{width:16px;height:16px}
.usermenu.open .um-caret{transform:rotate(180deg)}
.um-pop{position:absolute;left:8px;right:8px;bottom:calc(100% + 4px);background:var(--overlay);border:1px solid var(--line);border-radius:12px;box-shadow:0 16px 44px rgba(0,0,0,.22);padding:10px;z-index:60}
.um-pop[hidden]{display:none}
.um-sec{margin-bottom:10px}
.um-lbl{font-size:var(--t-xs);letter-spacing:.02em;color:var(--faint);font-weight:600;margin:0 2px 6px}
.seg{display:flex;gap:2px;background:var(--panel-2);border:1px solid var(--line);border-radius:9px;padding:3px}
.segbtn{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;padding:7px 4px;border:0;border-radius:6px;background:transparent;color:var(--muted);cursor:pointer;font-size:var(--t-xs);font-weight:500;text-decoration:none;font-family:inherit}
.segbtn .ic{width:17px;height:17px}
.segbtn:hover{color:var(--ink);background:var(--hover)}
.segbtn.on{background:var(--panel);color:var(--accent);box-shadow:0 1px 3px rgba(0,0,0,.10)}
.segbtn.on .ic{color:var(--accent)}
.seg:not(.seg-theme) .segbtn{padding:8px 4px;font-size:var(--t-sm);font-weight:600}
.rgwrap{position:relative;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--panel)}
#rg{display:block;touch-action:none;cursor:grab}
#rg.grabbing{cursor:grabbing}
.rghint{position:absolute;top:10px;left:12px;font-size:var(--t-xs);color:var(--muted);pointer-events:none;background:color-mix(in srgb,var(--panel) 75%,transparent);padding:3px 8px;border-radius:6px;backdrop-filter:blur(2px)}
.rgn{user-select:none;cursor:pointer}
.rgn>rect:first-of-type{transition:stroke .12s,filter .12s}
.rgn,.rge{transition:opacity .16s}
/* Calm-by-default edges (Linear-style): structural edges quiet at rest, the long dashed loop-backs
   barely-there — relationships light UP on hover/select via .on, dim via .off. */
.rge{transition:opacity .16s,stroke-width .12s;opacity:.42}
.rge.dash{opacity:.16}
.rgn:hover>rect:first-of-type{stroke:var(--accent)}
.rgn.off,.rge.off{opacity:.10}
.rgn.on>rect:first-of-type{stroke:var(--accent)}
.rge.on{opacity:1;stroke-width:3}
.rgn.sel>rect:first-of-type{stroke:var(--accent);stroke-width:2.2;filter:drop-shadow(0 3px 9px color-mix(in srgb,var(--accent) 42%,transparent))}
.rgn.rg-hidden{opacity:.07;pointer-events:none}
/* node label/sub live in a foreignObject — clamp so long titles never bleed out of the card */
.rgn-body{box-sizing:border-box;height:100%;display:flex;flex-direction:column;justify-content:center;overflow:hidden;font-family:inherit;pointer-events:none}
.rgn-title{font-size:var(--t-body);font-weight:600;line-height:1.2;color:var(--ink);display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;line-clamp:2;overflow:hidden;overflow-wrap:anywhere}
.rgn-sub{margin-top:2px;font-size:var(--t-sm);line-height:1.3;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rgctrls{position:absolute;left:12px;bottom:12px;display:flex;flex-direction:column;background:var(--panel);border:1px solid var(--line);border-radius:9px;overflow:hidden;box-shadow:0 4px 16px rgba(0,0,0,.12)}
.rgctrls .rgzl{font-size:var(--t-xs);color:var(--muted);text-align:center;padding:3px 0;border-bottom:1px solid var(--line-2);user-select:none}
.rgbtn{width:30px;height:30px;display:flex;align-items:center;justify-content:center;border:0;border-bottom:1px solid var(--line-2);background:var(--panel);color:var(--ink);cursor:pointer;font-size:var(--t-md);line-height:1}
.rgbtn:last-child{border-bottom:0}
.rgbtn:hover{background:var(--hover);color:var(--accent)}
.rgmini{position:absolute;right:12px;bottom:12px;width:172px;height:118px;background:color-mix(in srgb,var(--panel) 90%,transparent);border:1px solid var(--line);border-radius:9px;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.12);backdrop-filter:blur(2px)}
.rgmini .mn{fill:var(--muted);opacity:.5}
#rgmvp{fill:color-mix(in srgb,var(--accent) 15%,transparent);stroke:var(--accent);stroke-width:1.3}
.rgdiamond{fill:var(--accent);opacity:.055;stroke:var(--accent);stroke-opacity:.16;stroke-width:1.2}
.rgwrap:not(.groups-on) #rgsections{display:none}
.rgbtn.on{color:var(--accent);background:var(--accent-weak)}
.rgsection{stroke-width:1.5}
.rgsection-phase{fill-opacity:.05;stroke-opacity:.30;stroke-dasharray:none}
.rgphase-guide{stroke:var(--line);stroke-width:1;stroke-dasharray:2 8;opacity:.5}
.rgphase-label{fill:var(--ink);font-size:var(--t-md);font-weight:700;letter-spacing:-.01em}
.rgphase-sub{fill:var(--muted);font-size:var(--t-xs)}
.rground-sep{stroke:var(--line);stroke-width:1;stroke-dasharray:3 7;opacity:.7}
.rground-label{fill:var(--muted);font-size:var(--t-sm);font-weight:700;letter-spacing:.04em;text-transform:uppercase}
/* Linear-style project OUTLINE (primary view) — grouped, collapsible, never overlaps */
.outlinecard{flex:1;overflow:auto;padding:8px 0 40px}
.outline{max-width:900px;margin:0 auto;padding:0 24px}
.ol-phase{border-bottom:1px solid var(--line-2)}
.ol-phase>summary{list-style:none;cursor:pointer;display:flex;align-items:center;gap:9px;padding:13px 6px;font-size:var(--t-body);position:sticky;top:0;background:var(--bg);z-index:1}
.ol-phase>summary::-webkit-details-marker{display:none}
.ol-phase>summary .ol-gl{color:var(--accent);font-size:var(--t-sm);width:14px;text-align:center}
.ol-phase>summary b{font-weight:650;letter-spacing:-.01em}
.ol-rlabel{font-size:var(--t-xs);font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--faint);padding:10px 6px 4px 34px}
.olrow{display:flex;align-items:center;gap:10px;padding:7px 8px;border-radius:7px;color:var(--ink);text-decoration:none;font-size:var(--t-body)}
.olrow:hover{background:var(--hover)}
.ol-dot{width:8px;height:8px;border-radius:2px;flex-shrink:0}
.olrow .ol-title{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.olrow .ol-kind{color:var(--faint);font-size:var(--t-sm);flex-shrink:0;white-space:nowrap}
.olrow .ol-ts{color:var(--faint);font-size:var(--t-xs);flex-shrink:0;white-space:nowrap;font-variant-numeric:tabular-nums;min-width:96px;text-align:right}
.ol-gl.ol-round{color:var(--muted)}
.ol-cnt{font-size:var(--t-xs);color:var(--faint);font-weight:600;background:var(--panel-2);border-radius:10px;padding:1px 7px;margin-left:2px}
/* Plan drawer (project plan view) — a tight, progress-led checklist */
.plan-hd{margin-bottom:6px}
.plan-goal{font-weight:600;font-size:var(--t-prose);line-height:1.5;color:var(--ink)}
.plan-prog-row{display:flex;align-items:center;gap:12px;margin-top:14px}
.plan-prog{flex:1;max-width:240px;height:6px;border-radius:99px;background:var(--hover);overflow:hidden}
.plan-prog>i{display:block;height:100%;background:var(--accent);border-radius:99px;transition:width .4s var(--ease)}
.plan-prog.full>i{background:var(--green)}
.plan-prog-txt{font-size:var(--t-sm);color:var(--muted);font-variant-numeric:tabular-nums}
.plan-sub{display:flex;align-items:center;gap:8px;margin-top:12px}
.plan-sub>span:last-child{font-size:var(--t-sm);color:var(--faint)}
.psec{margin-top:26px}
.psec-h{display:flex;align-items:center;justify-content:space-between;font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:600;padding:0 2px 2px}
.psec-n{color:var(--faint);font-weight:550;font-variant-numeric:tabular-nums}
.psec-list{border-top:1px solid var(--line)}
.ptask{display:flex;gap:11px;padding:11px 6px;border-bottom:1px solid var(--line);margin:0 -6px;border-radius:var(--radius-sm)}
.ptask.is-last{border-bottom:0}.ptask:hover{background:var(--hover)}
.pt-mark{flex:none;width:18px;line-height:1.35;text-align:center}
.pt-body{flex:1;min-width:0}
.pt-row1{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.pt-title{font-weight:550;font-size:var(--t-md);color:var(--ink)}
.ptask.is-done .pt-title{color:var(--muted)}
.pt-cap{font-size:var(--t-xs);color:var(--accent);background:var(--accent-weak);padding:1px 7px;border-radius:99px;font-weight:500;line-height:1.5}
.pt-sub{font-size:var(--t-xs);color:var(--faint);margin-top:3px;line-height:1.5}
.pt-evs{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}
.pt-evs .ev{font-size:var(--t-xs);color:var(--muted);background:var(--panel-2);border:1px solid var(--line);padding:1px 8px;border-radius:99px;text-decoration:none;white-space:nowrap}
.pt-evs a.ev:hover{color:var(--accent);border-color:var(--accent)}
.ol-rcap{font-size:var(--t-body);font-weight:400;color:var(--muted);margin-left:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ol-ptag{flex-shrink:0;width:74px;font-size:var(--t-xs);font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.02em}
.ol-flat{padding-top:4px}
.olrow.ol-tw{position:relative}
.olrow.ol-tw::before{content:"";position:absolute;left:26px;top:-3px;bottom:50%;width:9px;border-left:1.6px solid var(--line-2);border-bottom:1.6px solid var(--line-2);border-bottom-left-radius:6px}
.olrow.ol-tw:hover::before{border-color:var(--accent)}
/* relationship hover-highlight (replaces graph edges): related rows light up, the rest dim */
.outline .olrow{transition:opacity .12s,background .12s}
.outline .olrow.rel{background:var(--accent-weak)}
.outline .olrow.dim{opacity:.42}
/* themes — cross-cutting labels (Linear-style): a filter bar + per-row dots; activating a theme
   highlights its members (.rel) and dims the rest (.dim). */
.olthemes{display:flex;align-items:center;flex-wrap:wrap;gap:6px;max-width:900px;margin:4px auto 2px;padding:0 24px}
.olth-l{font-size:var(--t-sm);color:var(--faint);margin-right:2px}
.olth-chip{display:inline-flex;align-items:center;gap:6px;max-width:230px;padding:3px 10px;border:1px solid var(--line);border-radius:var(--radius-sm);background:var(--panel);color:var(--muted);font-size:var(--t-sm);cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.olth-chip:hover{background:var(--hover)}
.olth-chip.on{border-color:transparent;background:var(--accent-weak);color:var(--accent);font-weight:600}
.olth-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
/* per-row theme membership = a LABELLED pill (colour + name), not a cryptic bare dot */
.olth-pills{display:inline-flex;gap:5px;flex-shrink:0;margin-right:10px}
.olth-pill{display:inline-flex;align-items:center;gap:5px;padding:1px 9px 1px 7px;border-radius:11px;background:var(--panel-2);color:var(--muted);font-size:var(--t-xs);font-weight:500;white-space:nowrap}.olth-pill i{width:7px;height:7px;border-radius:50%;flex-shrink:0}
/* relations block on detail pages (Linear progressive disclosure) */
.relcard{margin-top:16px}
.relh{font-size:var(--t-sm);font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--faint);margin-bottom:8px;display:flex;align-items:center;gap:6px}.relh svg{width:13px;height:13px}.h1ic{display:inline-flex;vertical-align:-3px;margin-right:7px}.h1ic svg{width:19px;height:19px}
.relgrp{padding:2px 0 8px}
.rellbl{font-size:var(--t-xs);font-weight:600;color:var(--muted);margin:0;padding:5px 14px 3px}
.relrow{display:flex;align-items:center;gap:9px;padding:6px 14px;color:var(--ink);text-decoration:none;font-size:var(--t-body)}
.relrow:hover{background:var(--hover)}
.relrow .relt{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.propcard{margin-top:16px}
.prop{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:7px 14px;font-size:var(--t-sm)}
.prop-k{display:inline-flex;align-items:center;gap:8px;color:var(--muted);flex-shrink:0}.prop-k svg{width:14px;height:14px;color:var(--faint)}
.prop-v{color:var(--ink);font-weight:500;text-align:right;min-width:0;overflow-wrap:anywhere}
.prop-v a{color:var(--accent);text-decoration:none}.prop-v a:hover{text-decoration:underline}
/* view toggle (Outline / Graph) */
.rgsection-theme{fill-opacity:0;stroke-opacity:.6;stroke-width:1.6;stroke-dasharray:6 5}
.rgseclab-bg{fill:var(--panel);fill-opacity:.92;stroke-opacity:.55;stroke-width:1.2}
.rgseclab-t{font-size:var(--t-sm);font-weight:700;letter-spacing:.01em}
.rgseclab-k{font-size:var(--t-xs);font-weight:700;text-transform:uppercase;letter-spacing:.07em;fill:var(--muted)}
.protoframe{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--panel);height:620px;box-shadow:0 4px 16px rgba(0,0,0,.08)}
.protoframe iframe{width:100%;height:100%;border:0;display:block}
.strow{padding:9px 0;border-bottom:1px solid var(--line)}.strow:last-child{border-bottom:0}
.strow a{text-decoration:none}.strow .ic{vertical-align:-3px;margin-right:5px}
.ptoolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:16px 0 10px}
.ptlabel{display:inline-flex;align-items:center;gap:5px;font-size:var(--t-sm);color:var(--muted)}.ptlabel .ic{width:14px;height:14px}
.ptlabel-2{margin-left:8px;padding-left:10px;border-left:1px solid var(--line);opacity:.85}
.rgchip.tagchip{font-size:var(--t-sm);padding:2px 9px;opacity:.82}
.rgchip{border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:var(--radius-sm);padding:3px 11px;font-size:var(--t-sm);cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.rgchip::before{content:"";width:8px;height:8px;border-radius:50%;background:var(--c,#9aa0a6)}
.rgchip:hover{background:var(--hover)}
.rgchip.active{border-color:var(--c,var(--accent));background:color-mix(in srgb,var(--c) 14%,var(--panel));font-weight:600}
.rgclear{font-size:var(--t-sm);color:var(--muted);cursor:pointer;text-decoration:underline}
.graphcard{padding:0;border:0;background:none}
.oqd{margin-top:14px;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
.oqd>summary{cursor:pointer;padding:10px 14px;font-size:var(--t-body);font-weight:600;list-style:none}
.oqd>summary::-webkit-details-marker{display:none}
.oqd[open]>summary{border-bottom:1px solid var(--line)}
.oqd>div{padding:10px 14px}
.resize{width:8px;margin:0 -4px;flex-shrink:0;cursor:col-resize;position:relative;z-index:10}
.app.collapsed .resize{display:none}
.resize::after{content:"";position:absolute;inset:0 50%;width:2px;transform:translateX(-50%);background:var(--accent);opacity:0;transition:opacity 150ms}
.resize:hover::after{opacity:.4}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.topbar{height:var(--row-h);flex-shrink:0;display:flex;align-items:center;gap:10px;padding:0 12px;border-bottom:1px solid var(--line);background:var(--panel)}
.iconbtn{border:1px solid var(--line);background:var(--panel);border-radius:6px;width:28px;height:28px;cursor:pointer;color:var(--muted);flex-shrink:0;display:inline-flex;align-items:center;justify-content:center}
#sbt{display:none}.app.collapsed #sbt{display:inline-flex}   /* the show-sidebar toggle appears only when collapsed */
.iconbtn:hover{background:var(--hover);color:var(--ink)}
.spacer{flex:1}
.tb-actions{display:flex;align-items:center;gap:8px}
.breadcrumb{display:flex;align-items:center;gap:6px;font-size:var(--t-body);min-width:0;overflow:hidden}
.bc-link{color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bc-link:hover{color:var(--accent)}
.bc-cur{color:var(--ink);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bc-sep{color:var(--line);flex-shrink:0;user-select:none}
section{padding:26px 30px;overflow:auto;scroll-behavior:smooth}
.page{max-width:1200px;margin:0 auto}
.page.wide{max-width:none}
/* Project detail = full-bleed graph hero */
.main>section:has(.proj){flex:1;min-height:0;padding:0;display:flex;flex-direction:column;overflow:hidden}
.proj{flex:1;min-height:0;display:flex;flex-direction:column}
.proj-head{flex-shrink:0;width:100%;max-width:900px;margin:0 auto;padding:22px 24px 12px}
.proj-head .stats{margin:0 0 14px}
.proj-head .ptoolbar{margin:0}
.proj-graph{flex:1;min-height:0;display:flex}
.proj-graph .rgwrap{flex:1;border:0;border-top:1px solid var(--line);border-radius:0}
.proj-graph #rg{height:100%}
.oqpanel{position:fixed;right:26px;bottom:26px;width:380px;max-width:calc(100vw - 320px);max-height:62vh;overflow:auto;background:var(--panel);border:1px solid var(--line);border-radius:12px;box-shadow:0 16px 44px rgba(0,0,0,.22);padding:14px 16px;z-index:60}
.oqp-h{font-size:var(--t-sm);font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}

/* ---- generic ---- */
h1,h2,h3,h4{color:var(--ink)}
.h1{font-size:var(--t-xl);line-height:1.2;letter-spacing:-.02em;margin:0 0 4px;font-weight:650}
.lead{color:var(--muted);font-size:var(--t-body);margin:0 0 16px;max-width:74ch;line-height:1.5}
.btn{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);background:var(--panel);border-radius:6px;padding:5px 11px;font-size:var(--t-body);font-weight:500;color:var(--ink);cursor:pointer;min-height:30px;transition:background 120ms,border-color 120ms}
.btn:hover{background:var(--hover)}
.btn.active{background:var(--sel);color:var(--ink);border-color:var(--line)}
.btn.disabled{color:var(--faint);cursor:default;opacity:.65}.btn.disabled:hover{background:var(--panel)}.btn.disabled svg{opacity:.7}
.btn.primary{background:var(--accent);color:var(--accent-ink);border-color:transparent}
.btn.primary:hover{filter:brightness(1.06)}
:focus-visible{outline:none;box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 45%,transparent)}
.card{border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:15px 16px;box-shadow:0 1px 2px rgba(0,0,0,.03)}
.card h3{margin:0 0 8px;font-size:var(--t-body)}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.two{grid-template-columns:1.1fr 1fr}
.pill{display:inline-flex;align-items:center;gap:5px;border:0;border-radius:6px;padding:2px 8px;margin:2px;background:var(--panel-2);color:var(--muted);font-size:var(--t-sm);font-weight:500}

/* ---- document layout (G4): toc | doc | rail ---- */
.doc{display:grid;gap:30px;align-items:start}
.doc.d3{grid-template-columns:200px minmax(0,1fr) 280px}
.doc.d2{grid-template-columns:minmax(0,1fr) 280px}
.doc.d1{grid-template-columns:minmax(0,900px)}
.doc-main{min-width:0;max-width:900px}
.toc{position:sticky;top:0;align-self:start;font-size:var(--t-sm)}
.toc .th{font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;margin:0 0 8px}
.toc a{display:block;padding:4px 8px;border-radius:5px;color:var(--muted);border-left:2px solid transparent}
.toc a:hover{color:var(--ink);background:var(--hover)}
.toc a.active{color:var(--accent);border-left-color:var(--accent);background:var(--accent-weak)}
.rail{position:sticky;top:0;align-self:start;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);overflow:hidden}
.rail h4{margin:0;padding:11px 14px 8px;font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.06em;font-weight:600;color:var(--muted);display:flex;align-items:center;gap:6px}
.rail h4 svg{width:13px;height:13px;color:var(--faint)}
.rail h4:not(:first-child){border-top:1px solid var(--line-2);margin-top:4px;padding-top:13px}
/* .hero h1/.sub now co-located with the _hero component (component-SSR C3) */
.mdtable{border-collapse:collapse;width:100%;margin:16px 0;font-size:var(--t-body);line-height:1.4}
.mdtable th,.mdtable td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
.mdtable th{background:var(--panel-2);font-weight:650;font-size:var(--t-xs);text-transform:uppercase;letter-spacing:.03em;color:var(--muted)}
.mdtable tbody tr:nth-child(even) td{background:var(--panel-2)}
.es-prose .mdtable td,.es-prose .mdtable th{max-width:none}
#favs .favic{display:inline-flex}#favs .favic svg{width:14px;height:14px}
.sec{margin:26px 0 0;padding-top:18px;border-top:1px solid var(--line)}
.sec>h2,.sec>summary{font-size:var(--t-sm);text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:0 0 12px;font-weight:600}
details.sec{padding-top:18px}
details.sec>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:7px}
details.sec>summary::-webkit-details-marker,details.block>summary.bh::-webkit-details-marker{display:none}
details.sec>summary::before,details.block>summary.bh::before{content:"\\25b8";color:var(--muted);transition:transform 150ms;font-size:var(--t-xs)}
details.sec[open]>summary::before,details.block[open]>summary.bh::before{transform:rotate(90deg)}
.doc-main p{max-width:74ch}.es-prose,.detail{overflow-wrap:break-word}.es-prose pre,pre{overflow-x:auto;max-width:100%}.es-prose img,.detail img{max-width:100%;height:auto}.es-prose .mdtable{display:block;overflow-x:auto}
/* .es-prose typography is shared by many pages (note/section/synthesis prose) — stays global.
   .es/.eyebrow/.qa-q now live co-located with _study_lead (component-SSR C2/C3). */
.es-prose{font-size:var(--t-prose);line-height:1.62;color:var(--ink)}.es-prose.sm{font-size:var(--t-md);line-height:1.6}
.es-prose p{margin:0 0 15px;max-width:74ch}.es-prose strong{font-weight:680}.es-prose h3{font-size:var(--t-md);margin:22px 0 8px;font-weight:680}
.es-prose ul,.es-prose ol{margin:0 0 15px;padding-left:22px;max-width:74ch}.es-prose li{margin:0 0 6px}.es-prose li>ul,.es-prose li>ol{margin:6px 0 0}
.es-prose h4{font-size:var(--t-body);margin:18px 0 6px;font-weight:680}
.es-prose em{font-style:italic}.es-prose del{color:var(--muted)}
.es-prose a{color:var(--accent);text-decoration:none}.es-prose a:hover{text-decoration:underline}
.es-prose code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;background:var(--panel-2);border:1px solid var(--line);border-radius:4px;padding:1px 5px}
.es-prose pre{background:var(--panel-2);border:1px solid var(--line);border-radius:var(--radius-sm);padding:12px 14px;overflow-x:auto;margin:0 0 15px}.es-prose pre code{background:none;border:0;padding:0;font-size:var(--t-sm)}
.es-prose blockquote{margin:0 0 15px;padding:8px 14px;border-left:3px solid var(--accent);background:var(--accent-weak);border-radius:0 var(--radius-sm) var(--radius-sm) 0}.es-prose blockquote p{margin:0;max-width:none}
.es-prose hr{border:0;border-top:1px solid var(--line);margin:22px 0}
.rec{display:grid;grid-template-columns:74px 1fr;gap:13px;align-items:start;padding:12px 0;border-bottom:1px solid var(--line-2);max-width:74ch}
.rec:last-child{border-bottom:0}.rec .es-prose,.rec p{max-width:none}
.prio{display:inline-block;font-size:var(--t-xs);font-weight:700;letter-spacing:.03em;color:#fff;border-radius:6px;padding:3px 7px;text-align:center;white-space:nowrap}
.prio-1{background:#b3493f}.prio-2{background:#a66b1f}.prio-3{background:#2f6f9f}.prio-4{background:#3d7b5f}.prio-5{background:#6d7378}
.srcchip{display:inline-block;font-size:var(--t-xs);color:var(--muted);border:1px solid var(--line);border-radius:5px;padding:1px 6px;margin-left:6px;background:var(--panel-2);white-space:nowrap}
a.srcchip{text-decoration:none}a.srcchip:hover{border-color:var(--accent);color:var(--ink)}
.xref .xref-role{opacity:.7;font-variant:all-small-caps;letter-spacing:.02em}
.xref-broken{border-style:dashed;color:var(--red);opacity:.75}
/* deep-link arrival: briefly highlight the referenced statement/finding */
.turn-ans:target,.fitem:target,.rec:target{animation:xreflash 2s ease-out 1}
@keyframes xreflash{0%,40%{background:var(--accent-weak);box-shadow:0 0 0 6px var(--accent-weak)}100%{background:transparent;box-shadow:none}}
[id]{scroll-margin-top:70px}
.psolve{padding:9px 0;border-bottom:1px solid var(--line-2);max-width:74ch}.psolve:last-child{border-bottom:0}
.psolve .es-prose,.psolve p{max-width:none}.psolve p{margin:0}
/* unified finding row (every finding section: key_problem/pain_solver/cluster/segment/ranking/…) */
.fitem{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;padding:9px 0;border-bottom:1px solid var(--line-2);max-width:74ch}
.fitem:last-child{border-bottom:0}.fitem .fbody{min-width:0;flex:1}.fitem .fbody p{margin:0}
.fitem .fchips{display:flex;align-items:center;gap:8px;flex-shrink:0}
.segrow{display:grid;grid-template-columns:1fr auto;gap:10px;align-items:start;padding:11px 0;border-bottom:1px solid var(--line-2);max-width:74ch}
.segrow:last-child{border-bottom:0}
.srclist{list-style:none;padding:0;margin:0;counter-reset:c}
.srclist li{counter-increment:c;padding:10px 0;border-bottom:1px solid var(--line-2);display:grid;grid-template-columns:24px 1fr;gap:10px;align-items:baseline}
.srclist li:last-child{border-bottom:0}
.srclist li::before{content:counter(c);color:var(--muted);font-variant-numeric:tabular-nums;font-size:var(--t-sm)}

@media (max-width:1040px){.doc.d3{grid-template-columns:minmax(0,1fr)}.doc.d2{grid-template-columns:minmax(0,1fr)}.toc,.rail{position:static;display:none}}
@media (max-width:760px){
  .sidebar{position:fixed;top:0;left:0;height:100vh;z-index:100;width:280px!important;min-width:280px!important;transform:translateX(-100%);transition:transform 220ms var(--ease)}
  .app:not(.collapsed) .sidebar{transform:translateX(0);box-shadow:var(--shadow-lg)}
  .resize{display:none}.grid,.two{grid-template-columns:1fr}
}
@media print{
  .sidebar,.resize,.topbar,.toc,.rail,.tb-actions{display:none!important}
  .app{display:block;height:auto;overflow:visible}.main{overflow:visible}
  section{overflow:visible;padding:0}.doc{display:block}.doc-main{max-width:100%}
  body{background:#fff;color:#000}.sec{break-inside:avoid}
}
"""

HEAD_JS = '<script>try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t;}catch(e){}</script>'

_RGRAPH_JS = """<script>
(function(){
  var dataEl=document.getElementById('rgdata'); if(!dataEl) return;
  var D=JSON.parse(dataEl.textContent);
  var svg=document.getElementById('rg'), root=document.getElementById('rgroot'),
      gE=document.getElementById('rgedges'), gN=document.getElementById('rgnodes');
  var NS='http://www.w3.org/2000/svg', NW=320, NH=64, MIN=0.25, MAX=2.6;
  var tx=0, ty=0, scale=1, KEY='rgstate:'+(D.key||'x');
  function el(t,a){ var e=document.createElementNS(NS,t); for(var k in a) e.setAttribute(k,a[k]); return e; }
  // Render a sonaloop-icons glyph (icon name -> path body from D.iconpaths) as a nested
  // <svg> at (x,y,size). color drives both stroke (currentColor) and any inline fill.
  function iconEl(name,x,y,size,color){
    var body=(D.iconpaths||{})[name]; if(!body) return null;
    var s=el('svg',{x:x,y:y,width:size,height:size,viewBox:'0 0 24 24',fill:'none',
      stroke:'currentColor','stroke-width':1.9,'stroke-linecap':'round','stroke-linejoin':'round'});
    if(color) s.setAttribute('style','color:'+color);
    s.innerHTML=body; return s;
  }
  var byId={}; D.nodes.forEach(function(n){ byId[n.id]=n; n.dx=n.x; n.dy=n.y; });

  // ---- persistence (per project): node positions, viewport, active filters ----
  // Discard saved positions when the layout algorithm changed (D.lv) so a stale drag
  // layout never masks a new diamond layout.
  var saved=null; try{ saved=JSON.parse(localStorage.getItem(KEY)||'null'); }catch(_){}
  if(saved && saved.lv !== D.lv) saved=null;
  if(saved&&saved.pos) D.nodes.forEach(function(n){ var p=saved.pos[n.id]; if(p){ n.x=p[0]; n.y=p[1]; } });
  var saveT=null;
  function writeNow(){ if(saveT){ clearTimeout(saveT); saveT=null; }
    var pos={}; D.nodes.forEach(function(n){ pos[n.id]=[Math.round(n.x),Math.round(n.y)]; });
    var f=[]; document.querySelectorAll('.rgchip.active').forEach(function(c){ f.push(c.getAttribute('data-theme')); });
    try{ localStorage.setItem(KEY,JSON.stringify({lv:D.lv,pos:pos,view:{tx:tx,ty:ty,scale:scale},filter:f})); }catch(_){}
  }
  function save(){ if(saveT) return; saveT=setTimeout(writeNow,250); }   // debounced (continuous gestures)
  // Flush any pending write before the page goes away, so a quick refresh never loses a change.
  window.addEventListener('pagehide',function(){ if(saveT) writeNow(); });
  document.addEventListener('visibilitychange',function(){ if(document.visibilityState==='hidden'&&saveT) writeNow(); });

  var zl=document.getElementById('rgzl'), bgp=document.getElementById('rggrid');
  function applyT(){ root.setAttribute('transform','translate('+tx+','+ty+') scale('+scale+')');
    if(bgp) bgp.setAttribute('patternTransform','translate('+tx+' '+ty+') scale('+scale+')');
    if(zl) zl.textContent=Math.round(scale*100)+'%'; drawMini(); }

  // ---- diamond silhouettes (methodology layout) ----
  var gD=document.getElementById('rgdia');
  if(gD && D.diamonds){ D.diamonds.forEach(function(poly){
    gD.appendChild(el('polygon',{points: poly.map(function(p){return p[0]+','+p[1];}).join(' '),'class':'rgdiamond'})); }); }

  // ---- section overlays (methodology-independent groupings) ----
  // ---- Q3: phase-column headers + faint guides (the left→right flow, made explicit) ----
  var gP=document.getElementById('rgphases');
  if(gP && D.phases && D.phases.length){
    var ys=D.nodes.map(function(n){return n.y;}); var ymin=Math.min.apply(null,ys.concat([0]))-80;
    var ymax=Math.max.apply(null,ys.concat([0]))+160;
    D.phases.forEach(function(p){
      var ln=el('line',{x1:p.x,y1:ymin,x2:p.x,y2:ymax,'class':'rgphase-guide'}); gP.appendChild(ln);
      var t=el('text',{x:p.x,y:p.top,'class':'rgphase-label','text-anchor':'middle'});
      t.textContent=p.i+'. '+p.label; gP.appendChild(t);
      var g=el('text',{x:p.x,y:p.top+18,'class':'rgphase-sub','text-anchor':'middle'});
      g.textContent=p.is_fan?'divergieren':'konvergieren'; gP.appendChild(g);
      var gw=0; try{gw=g.getComputedTextLength();}catch(_){}
      var gi=iconEl(p.is_fan?'diamond':'diamondFilled', p.x-gw/2-15, p.top+18-9, 11);
      if(gi) gP.appendChild(gi);
    });
  }
  // ---- iteration swimlanes: "Runde N" labels + faint separators between rounds (only if looped) ----
  var gR=document.getElementById('rgrounds');
  if(gR && D.rounds && D.rounds.length>1){
    var xs2=D.nodes.map(function(n){return n.x;});
    var xmn=Math.min.apply(null,xs2.concat([0]))-44, xmx=Math.max.apply(null,xs2.concat([0]))+300;
    D.rounds.forEach(function(r,idx){
      if(idx>0){ var midY=(r.y+D.rounds[idx-1].y)/2;
        var ln=el('line',{x1:xmn,y1:midY,x2:xmx,y2:midY,'class':'rground-sep'}); gR.appendChild(ln); }
      var lab=el('text',{x:xmn,y:r.y-4,'class':'rground-label'}); lab.textContent=r.label; gR.appendChild(lab);
    });
  }
  var gS=document.getElementById('rgsections');
  if(gS && D.sections){ D.sections.forEach(function(s){
    var pts=s.poly.map(function(p){return p[0]+','+p[1];}).join(' ');
    var cls='rgsection '+(s.phase?'rgsection-phase':'rgsection-theme');
    var poly=el('polygon',{points:pts,'class':cls,style:'fill:'+s.color+';stroke:'+s.color});
    poly.setAttribute('data-section', s.id); gS.appendChild(poly);
    // Group label as a readable PILL floating just above the hull's top-left, so it
    // never overlaps the nodes inside the group (it used to sit on the first node).
    var chip=el('g',{'class':'rgseclab'}); gS.appendChild(chip);
    var PADX=10, CH=24, cx=PADX;
    var rect=el('rect',{x:0,y:0,height:CH,rx:8,'class':'rgseclab-bg',style:'stroke:'+s.color}); chip.appendChild(rect);
    if(s.glyph){ var si=iconEl(s.glyph, cx, CH/2-7, 14, s.color); if(si){ chip.appendChild(si); cx+=19; } }
    var lab=el('text',{x:cx,y:CH/2,'class':'rgseclab-t','dominant-baseline':'central',style:'fill:'+s.color});
    lab.textContent=s.label; chip.appendChild(lab);
    var lw=0; try{lw=lab.getComputedTextLength();}catch(_){} cx+=lw;
    if(s.kind){ cx+=8; var k=el('text',{x:cx,y:CH/2,'class':'rgseclab-k','dominant-baseline':'central'});
      k.textContent=s.kind; chip.appendChild(k); var kw=0; try{kw=k.getComputedTextLength();}catch(_){} cx+=kw; }
    rect.setAttribute('width', cx+PADX);
    chip.setAttribute('transform','translate('+(s.lx+4)+','+(s.ly-CH-6)+')');
  }); }

  // ---- edges (bezier, depth-aware) ----
  var edgeEls=[];
  D.edges.forEach(function(ed){ var a={fill:'none',stroke:ed.color,'stroke-width':'2','marker-end':'url(#rgah-'+ed.mid+')','class':ed.dashed?'rge dash':'rge'}; if(ed.dashed){a['stroke-dasharray']='6 5'; a['stroke-width']='1.6';} var p=el('path',a); gE.appendChild(p); edgeEls.push({ed:ed,p:p}); });
  function route(){ edgeEls.forEach(function(o){ var a=byId[o.ed.from], b=byId[o.ed.to]; if(!a||!b) return;
    o.p.style.display=(a.hidden||b.hidden)?'none':'';
    var aw=a.w||NW, ah=a.h||NH, bw=b.w||NW, bh=b.h||NH;
    var sx,sy,ex,ey,d;
    if(Math.abs(b.x-a.x)<NW*0.6){
      sx=a.x+aw/2; ex=b.x+bw/2;
      if(b.y>=a.y){ sy=a.y+ah; ey=b.y; } else { sy=a.y; ey=b.y+bh; }
      var cv=(ey-sy)*0.5; d='M'+sx+' '+sy+' C '+sx+' '+(sy+cv)+' '+ex+' '+(ey-cv)+' '+ex+' '+ey;
    } else {
      if(b.x>=a.x){ sx=a.x+aw; ex=b.x; } else { sx=a.x; ex=b.x+bw; }
      sy=a.y+ah/2; ey=b.y+bh/2; var ch=(ex-sx)*0.5;
      d='M'+sx+' '+sy+' C '+(sx+ch)+' '+sy+' '+(ex-ch)+' '+ey+' '+ex+' '+ey;
    }
    o.p.setAttribute('d',d);
  }); drawMini(); }

  // ---- theme filter ----
  function applyFilter(){ var act=[]; document.querySelectorAll('.rgchip.active').forEach(function(c){ act.push(c.getAttribute('data-theme')); });
    D.nodes.forEach(function(n){ var show=!act.length||(n.tags||[]).some(function(t){ return act.indexOf(t)>=0; }); n.hidden=!show; if(n.el) n.el.classList.toggle('rg-hidden',!show); });
    var clr=document.querySelector('.rgclear'); if(clr) clr.style.display=act.length?'':'none'; route(); writeNow(); }
  document.addEventListener('click',function(e){ var chip=e.target.closest&&e.target.closest('.rgchip'); if(chip){ chip.classList.toggle('active'); applyFilter(); return; } var clr=e.target.closest&&e.target.closest('.rgclear'); if(clr){ document.querySelectorAll('.rgchip.active').forEach(function(c){c.classList.remove('active');}); applyFilter(); } });

  // ---- neighborhood highlight + selection ----
  function neigh(id){ var s={}; s[id]=1; D.edges.forEach(function(e){ if(e.from===id)s[e.to]=1; if(e.to===id)s[e.from]=1; }); return s; }
  function highlight(id){ if(!id){ D.nodes.forEach(function(n){ n.el.classList.remove('on','off'); }); edgeEls.forEach(function(o){ o.p.classList.remove('on','off'); }); return; }
    var nb=neigh(id);
    D.nodes.forEach(function(n){ var on=!!nb[n.id]; n.el.classList.toggle('on',on); n.el.classList.toggle('off',!on); });
    edgeEls.forEach(function(o){ var on=(o.ed.from===id||o.ed.to===id); o.p.classList.toggle('on',on); o.p.classList.toggle('off',!on); }); }
  var selId=null;
  function select(id){ selId=id; D.nodes.forEach(function(n){ n.el.classList.toggle('sel',n.id===id); }); highlight(id); }
  function deselect(){ selId=null; D.nodes.forEach(function(n){ n.el.classList.remove('sel'); }); highlight(null); }

  // ---- nodes ----
  D.nodes.forEach(function(n){
    var W=n.w||NW, H=n.h||NH;
    var g=el('g',{'class':'rgn'+(n.proto?' proto':''),transform:'translate('+n.x+','+n.y+')'});
    var rectAttrs={width:W,height:H,rx:10,fill:'var(--panel)',stroke:(n.proto?n.color:'var(--line)'),'stroke-width':'1.4'};
    if(n.proto){ rectAttrs['stroke-dasharray']='6 4'; }
    g.appendChild(el('rect',rectAttrs));
    g.appendChild(el('rect',{width:5,height:H,rx:2.5,fill:n.color}));
    // Title + sub live in a foreignObject so long labels clamp/ellipsize INSIDE the
    // card instead of overflowing into neighbours (raw <text> doesn't clip). The glyph
    // and external-link icons stay as SVG overlays, vertically centred.
    var padL=14;
    if(n.glyph){ var ni=iconEl(n.glyph, 14, H/2-7, 15, n.color); if(ni){ g.appendChild(ni); padL=37; } }
    var padR=(n.ext?24:12);
    var fo=el('foreignObject',{x:padL,y:0,width:Math.max(12,W-padL-padR),height:H,'pointer-events':'none'});
    var XH='http://www.w3.org/1999/xhtml';
    var box=document.createElementNS(XH,'div'); box.setAttribute('class','rgn-body');
    var a=document.createElementNS(XH,'div'); a.setAttribute('class','rgn-title'); a.textContent=n.label; box.appendChild(a);
    if(n.sub){ var b=document.createElementNS(XH,'div'); b.setAttribute('class','rgn-sub'); b.textContent=n.sub; box.appendChild(b); }
    fo.appendChild(box); g.appendChild(fo);
    if(n.ext){ var ei=iconEl('external', W-20, 8, 12, 'var(--muted)'); if(ei) g.appendChild(ei); }
    gN.appendChild(g); n.el=g;
    var down=null,moved=false;
    g.addEventListener('pointerdown',function(e){ e.stopPropagation(); down={x:e.clientX,y:e.clientY,nx:n.x,ny:n.y}; moved=false; gN.appendChild(g); try{g.setPointerCapture(e.pointerId);}catch(_){} });
    g.addEventListener('pointermove',function(e){ if(!down) return; var dx=(e.clientX-down.x)/scale, dy=(e.clientY-down.y)/scale; if(Math.abs(dx)+Math.abs(dy)>3) moved=true; n.x=down.nx+dx; n.y=down.ny+dy; g.setAttribute('transform','translate('+n.x+','+n.y+')'); route(); });
    g.addEventListener('pointerup',function(e){ if(down){ if(!moved){ if(selId===n.id) location.href=n.href; else select(n.id); } else writeNow(); } down=null; });
    g.addEventListener('dblclick',function(e){ e.preventDefault(); location.href=n.href; });
    g.addEventListener('pointerenter',function(){ if(!selId&&!down) highlight(n.id); });
    g.addEventListener('pointerleave',function(){ if(!selId&&!down) highlight(null); });
  });

  // ---- view transforms ----
  function go(nx,ny,ns,anim){ ns=Math.max(MIN,Math.min(MAX,ns)); if(!anim){ tx=nx; ty=ny; scale=ns; applyT(); save(); return; }
    var ox=tx,oy=ty,os=scale,t0=null;
    function step(ts){ if(t0===null)t0=ts; var k=Math.min(1,(ts-t0)/300), e=1-Math.pow(1-k,3); tx=ox+(nx-ox)*e; ty=oy+(ny-oy)*e; scale=os+(ns-os)*e; applyT(); if(k<1) requestAnimationFrame(step); else save(); }
    requestAnimationFrame(step); }
  function zoomAt(cx,cy,f){ var ns=Math.max(MIN,Math.min(MAX,scale*f)); tx=cx-(cx-tx)*(ns/scale); ty=cy-(cy-ty)*(ns/scale); scale=ns; applyT(); save(); }
  function bbox(vis){ var mnx=1e9,mny=1e9,mxx=-1e9,mxy=-1e9,any=false;
    D.nodes.forEach(function(n){ if(vis&&n.hidden) return; any=true; mnx=Math.min(mnx,n.x); mny=Math.min(mny,n.y); mxx=Math.max(mxx,n.x+(n.w||NW)); mxy=Math.max(mxy,n.y+(n.h||NH)); });
    if(!any) return bbox(false); return {x:mnx,y:mny,X:mxx,Y:mxy}; }
  function fit(anim){ var r=svg.getBoundingClientRect(); if(!r.width) return; var b=bbox(true), pad=64; var bw=Math.max(1,b.X-b.x), bh=Math.max(1,b.Y-b.y);
    var s=Math.max(MIN,Math.min(MAX,Math.min((r.width-pad*2)/bw,(r.height-pad*2)/bh)));
    go((r.width-bw*s)/2-b.x*s,(r.height-bh*s)/2-b.y*s,s,anim); }
  function resetLayout(){ D.nodes.forEach(function(n){ n.x=n.dx; n.y=n.dy; n.el.setAttribute('transform','translate('+n.x+','+n.y+')'); });
    try{ localStorage.removeItem(KEY); }catch(_){}
    document.querySelectorAll('.rgchip.active').forEach(function(c){ c.classList.remove('active'); });
    deselect(); applyFilter(); fit(true); }

  // ---- control buttons ----
  var ctrls=document.querySelector('.rgctrls');
  if(ctrls) ctrls.addEventListener('click',function(e){ var btn=e.target.closest('.rgbtn'); if(!btn) return; var a=btn.getAttribute('data-act'), r=svg.getBoundingClientRect();
    if(a==='zin') zoomAt(r.width/2,r.height/2,1.25); else if(a==='zout') zoomAt(r.width/2,r.height/2,0.8); else if(a==='fit') fit(true); else if(a==='reset') resetLayout(); else if(a==='groups'){ var w=svg.closest('.rgwrap'); if(w){ var on=w.classList.toggle('groups-on'); btn.classList.toggle('on',on); } } });

  // ---- background pan + wheel/trackpad ----
  var pan=null;
  svg.addEventListener('pointerdown',function(e){ if(e.target.closest('.rgn')) return; pan={x:e.clientX,y:e.clientY,tx:tx,ty:ty,moved:false,pid:e.pointerId}; svg.classList.add('grabbing'); try{svg.setPointerCapture(e.pointerId);}catch(_){} });
  svg.addEventListener('pointermove',function(e){ if(!pan) return; if(Math.abs(e.clientX-pan.x)+Math.abs(e.clientY-pan.y)>3) pan.moved=true; tx=pan.tx+(e.clientX-pan.x); ty=pan.ty+(e.clientY-pan.y); applyT(); });
  function endPan(){ if(!pan) return; if(!pan.moved&&selId) deselect(); else if(pan.moved) writeNow(); try{svg.releasePointerCapture(pan.pid);}catch(_){} svg.classList.remove('grabbing'); pan=null; }
  svg.addEventListener('pointerup',endPan); svg.addEventListener('pointercancel',endPan); window.addEventListener('pointerup',endPan);
  // Detect a trackpad ONCE per session and latch it, so the same device never flip-flops
  // between "two-finger pan" and "mouse-wheel zoom" tick to tick (the main source of jumpiness).
  var trackpadSeen=false;
  svg.addEventListener('wheel',function(e){ e.preventDefault(); var r=svg.getBoundingClientRect(), mx=e.clientX-r.left, my=e.clientY-r.top;
    if(e.ctrlKey){ zoomAt(mx,my,Math.exp(-e.deltaY*0.01)); return; }              // pinch / ctrl+wheel = zoom to cursor
    if(e.shiftKey){ tx-=e.deltaY; applyT(); save(); return; }                      // shift+wheel = horizontal pan
    if(e.deltaX!==0 || !Number.isInteger(e.deltaY)) trackpadSeen=true;             // latch on any trackpad signal
    if(trackpadSeen){ tx-=e.deltaX; ty-=e.deltaY; applyT(); save(); }              // two-finger scroll = pan
    else { zoomAt(mx,my,e.deltaY<0?1.12:0.892); }                                  // mouse wheel = zoom to cursor
  },{passive:false});

  // ---- keyboard ----
  window.addEventListener('keydown',function(e){ if(e.metaKey||e.ctrlKey||e.altKey) return; var ae=document.activeElement; if(ae&&/input|textarea|select/i.test(ae.tagName)) return; var r=svg.getBoundingClientRect();
    if(e.key==='+'||e.key==='=') zoomAt(r.width/2,r.height/2,1.25);
    else if(e.key==='-'||e.key==='_') zoomAt(r.width/2,r.height/2,0.8);
    else if(e.key==='0'||e.key==='f'||e.key==='F') fit(true);
    else if(e.key==='r'||e.key==='R') resetLayout();
    else if(e.key==='Escape') deselect();
    else if(e.key==='Enter'&&selId){ location.href=byId[selId].href; }
    else if(e.key==='ArrowLeft'){ tx+=40; applyT(); save(); }
    else if(e.key==='ArrowRight'){ tx-=40; applyT(); save(); }
    else if(e.key==='ArrowUp'){ ty+=40; applyT(); save(); }
    else if(e.key==='ArrowDown'){ ty-=40; applyT(); save(); }
    else return; e.preventDefault(); });

  // ---- minimap ----
  // Scale to the union of node bbox + current viewport so the viewport rectangle
  // always fits inside the minimap and stays accurate at any zoom level.
  var mini=document.getElementById('rgmini'), gMN=document.getElementById('rgmnodes'), vp=document.getElementById('rgmvp');
  var MMW=172, MMH=118, mm={s:1,ox:0,oy:0};
  function drawMini(){ if(!mini) return;
    var b=bbox(false), r=svg.getBoundingClientRect(), hasV=r.width>0, vx,vy,vw,vh;
    if(hasV){ vx=(-tx)/scale; vy=(-ty)/scale; vw=r.width/scale; vh=r.height/scale;
      b={x:Math.min(b.x,vx),y:Math.min(b.y,vy),X:Math.max(b.X,vx+vw),Y:Math.max(b.Y,vy+vh)}; }
    var pad=10, bw=Math.max(1,b.X-b.x), bh=Math.max(1,b.Y-b.y);
    var s=Math.min((MMW-pad*2)/bw,(MMH-pad*2)/bh);
    var ox=pad+((MMW-pad*2)-bw*s)/2-b.x*s, oy=pad+((MMH-pad*2)-bh*s)/2-b.y*s; mm={s:s,ox:ox,oy:oy};
    while(gMN.firstChild) gMN.removeChild(gMN.firstChild);
    D.nodes.forEach(function(n){ if(n.hidden) return; gMN.appendChild(el('rect',{'class':'mn',x:ox+n.x*s,y:oy+n.y*s,width:NW*s,height:NH*s,rx:1.5})); });
    if(hasV){ vp.style.display=''; vp.setAttribute('x',ox+vx*s); vp.setAttribute('y',oy+vy*s); vp.setAttribute('width',Math.max(3,vw*s)); vp.setAttribute('height',Math.max(3,vh*s)); vp.setAttribute('rx',3); } }
  function miniCenter(e){ var r=mini.getBoundingClientRect(); var cx=((e.clientX-r.left)*(MMW/r.width)-mm.ox)/mm.s, cy=((e.clientY-r.top)*(MMH/r.height)-mm.oy)/mm.s; var sr=svg.getBoundingClientRect(); tx=sr.width/2-cx*scale; ty=sr.height/2-cy*scale; applyT(); save(); }
  if(mini){ var md=null;
    mini.addEventListener('pointerdown',function(e){ md={x:e.clientX,y:e.clientY}; try{mini.setPointerCapture(e.pointerId);}catch(_){} miniCenter(e); md.x=e.clientX; md.y=e.clientY; });
    mini.addEventListener('pointermove',function(e){ if(!md) return; var r=mini.getBoundingClientRect(); var dcx=(e.clientX-md.x)*(MMW/r.width)/mm.s, dcy=(e.clientY-md.y)*(MMH/r.height)/mm.s; tx-=dcx*scale; ty-=dcy*scale; md.x=e.clientX; md.y=e.clientY; applyT(); save(); });
    window.addEventListener('pointerup',function(){ md=null; }); }

  window.addEventListener('resize',function(){ applyT(); });

  // ---- init: restore filter chips, then viewport (saved or fit) ----
  if(saved&&saved.filter&&saved.filter.length) saved.filter.forEach(function(th){ try{ var sel='.rgchip[data-theme="'+(window.CSS&&CSS.escape?CSS.escape(th):th)+'"]'; var c=document.querySelector(sel); if(c) c.classList.add('active'); }catch(_){} });
  applyFilter();
  if(saved&&saved.view){ tx=saved.view.tx; ty=saved.view.ty; scale=saved.view.scale; applyT(); } else { fit(false); }
})();
</script>"""
