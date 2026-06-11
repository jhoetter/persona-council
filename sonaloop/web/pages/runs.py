"""Runs page — every project's DRIVER status on one read-only surface (ticket
agents-running-panel). The stalled Codex project sat invisible for hours; this page
makes the silent failure mode loud: stalled projects lead (amber, with the existing
resume-affordance note rendered as a copyable `start_run(...)` snippet), active runs
follow (last activity + next-ready steps), finished plans collapse at the bottom.
Every row links to its project page; the data is services.project_run_state, read
through the shared collect_run_states() (web/_runs_widget.py).

Extension seam (mirrors the nav registry in web/_ext.py): downstream private packages
contribute extra sections to /runs WITHOUT the core importing them —

    from sonaloop.web import register_runs_section
    register_runs_section("assignments", render_assignments, order=50)

`provider(store) -> str` returns trusted HTML (extensions are trusted code, same rule
as layout slots); sections render below the core ones, ordered by `order`; idempotent
by section_id so a re-import or an override never duplicates. A broken provider is
skipped rather than taking down the page (the load_extensions fail-soft rule).
sonaloop-cloud will register its "assignments" section through this seam."""
from __future__ import annotations

from typing import Any, Callable

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._html import register_css
from .._runs_widget import collect_run_states

# ---------------------------------------------------------------- extension seam

_RUNS_SECTIONS: list[dict[str, Any]] = []


def register_runs_section(section_id: str, provider: Callable[[Any], str], order: int = 100) -> None:
    """Register (or replace) an extra /runs section. Idempotent by section_id."""
    for s in _RUNS_SECTIONS:
        if s["id"] == section_id:
            s.update(provider=provider, order=order)
            return
    _RUNS_SECTIONS.append({"id": section_id, "provider": provider, "order": order})


def _extension_sections(store) -> str:
    parts = []
    for s in sorted(_RUNS_SECTIONS, key=lambda s: s["order"]):
        try:
            parts.append(s["provider"](store))
        except Exception:  # noqa: BLE001 — never let one extension break the core page
            continue
    return "".join(parts)


# ---------------------------------------------------------------- core rendering

def _meta_line(r: dict) -> str:
    """`Last activity · timestamp` plus the next-ready step pills (when known)."""
    ready = fragment(*(h("span", {"class_": "pill"}, step) for step in r["next_ready"][:4]))
    return h("div", {"class_": "run-meta"},
             h("span", {"class_": "muted small"},
               f'{t("run_last_activity")}: {r["last_activity"][:16].replace("T", " ")}'),
             fragment(h("span", {"class_": "muted small"}, f' · {t("run_next_ready")}: '), ready)
             if r["next_ready"] else None)


def _resume_html(note: str) -> str:
    """The stalled row's resume affordance: the run-state note verbatim, with its
    `start_run(...)` call rendered as a copyable snippet (one click → clipboard)."""
    if "resume with " in note:
        prefix, snippet = note.rsplit("resume with ", 1)
        prefix += "resume with"
    else:
        prefix, snippet = note, ""
    return h("div", {"class_": "run-resume"},
             h("span", {"class_": "muted small"}, prefix),
             fragment(h("code", {}, snippet),
                      h("button", {"type": "button", "class_": "run-copy", "data-copy": snippet,
                                   "data-copied": t("copied")}, t("copy_btn")))
             if snippet else None)


def _run_row(r: dict, *, stalled: bool = False) -> str:
    return h("div", {"class_": "runrow" + (" runrow-stalled" if stalled else "")},
             h("div", {"class_": "runrow-head"},
               h("a", {"href": r["url"]}, raw(_icon("projects")), " ", h("b", {}, r["title"])),
               _label(t("stalled"), "var(--amber)") if stalled else
               _label(t("runs_active_h"), "var(--green)")),
             _meta_line(r),
             raw(_resume_html(r["note"])) if stalled and r.get("note") else None)


_RUNS_CSS = register_css(r"""
/* ---- /runs page (ticket agents-running-panel) ---- */
.runrow{border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);padding:11px 13px;margin:0 0 8px}
.runrow-stalled{border-color:var(--amber)}
.runrow-head{display:flex;align-items:center;gap:10px;justify-content:space-between}
.runrow-head a{display:inline-flex;align-items:center;gap:8px;color:var(--ink);text-decoration:none;min-width:0}
.runrow-head a:hover b{color:var(--accent)}
.runrow-head svg{width:15px;height:15px;color:var(--accent);flex:none}
.run-meta{margin-top:5px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.run-resume{margin-top:7px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.run-resume code{font-size:var(--t-sm);background:var(--panel-2);border:1px solid var(--line);border-radius:var(--radius-sm);padding:2px 7px}
.run-copy{border:1px solid var(--line);background:var(--panel-2);color:var(--muted);border-radius:var(--radius-sm);font-size:var(--t-xs);padding:2px 8px;cursor:pointer}
.run-copy:hover{color:var(--ink);background:var(--hover)}
.runs-sec{margin:18px 0 6px;font-size:var(--t-md);font-weight:600;display:flex;align-items:center;gap:8px}
.runs-sec .cnt{color:var(--muted);font-weight:500}
details.runs-fin summary{cursor:pointer;margin:18px 0 6px;font-size:var(--t-md);font-weight:600;color:var(--muted)}
""")

# Copy-to-clipboard for the resume snippets. Delegated + window-guarded: the SPA
# re-executes page scripts on every visit, so a bare listener would stack.
_COPY_JS = """<script>(function(){
if(window.__slRunCopy) return; window.__slRunCopy=1;
document.addEventListener('click',function(e){
  var b=e.target.closest&&e.target.closest('[data-copy]'); if(!b) return;
  var txt=b.getAttribute('data-copy'), done=b.getAttribute('data-copied')||'';
  function ok(){ var old=b.textContent; b.textContent=done; setTimeout(function(){ b.textContent=old; },1400); }
  if(navigator.clipboard&&navigator.clipboard.writeText){ navigator.clipboard.writeText(txt).then(ok); }
  else{ var ta=document.createElement('textarea'); ta.value=txt; document.body.appendChild(ta);
        ta.select(); try{ document.execCommand('copy'); ok(); }catch(_){ } document.body.removeChild(ta); }
});
})();</script>"""


def _section(label: str, rows: list) -> str:
    if not rows:
        return ""
    return fragment(h("div", {"class_": "runs-sec"}, label, h("span", {"class_": "cnt"}, str(len(rows)))),
                    fragment(*rows))


def register_runs(app) -> None:
    @app.get("/runs", response_class=HTMLResponse)
    def runs_page() -> str:
        store = Store()
        states = collect_run_states(store)
        stalled = [_run_row(r, stalled=True) for r in states["stalled"]]
        active = [_run_row(r) for r in states["active"]]
        finished = [h("div", {"class_": "runrow"},
                      h("div", {"class_": "runrow-head"},
                        h("a", {"href": r["url"]}, raw(_icon("projects")), " ", h("b", {}, r["title"])),
                        h("span", {"class_": "muted small"}, r["last_activity"][:16].replace("T", " "))))
                    for r in states["finished"]]
        if not (stalled or active or finished):
            core = h("div", {"class_": "sl-empty"},
                     h("div", {"class_": "sl-empty__icon"}, raw(_icon("play"))),
                     h("p", {"class_": "sl-empty__body"}, t("no_runs")))
        else:
            core = fragment(
                raw(_section(t("runs_stalled_h"), stalled)),   # stalled first: the loud lane
                raw(_section(t("runs_active_h"), active)),
                h("details", {"class_": "runs-fin"},
                  h("summary", {}, f'{t("runs_finished_h")} ({len(finished)})'),
                  fragment(*finished)) if finished else None)
        body = h("div", {"class_": "page"},
                 h("h1", {"class_": "h1"}, t("runs_h")),
                 h("p", {"class_": "lead"}, t("runs_lead")),
                 core, raw(_extension_sections(store)), raw(_COPY_JS))
        return _layout(t("runs_h"), body, store, crumbs=[(t("runs_h"), None)], active="runs")
