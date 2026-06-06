"""Phase 1 — the ONE renderer per primitive (spec/unified-artifact-schema-rollout.md).

Every artifact draws its content through these functions, so a Statement / Finding / Prompt / Ref / Stance
looks identical everywhere (consistency by construction). Reads the primitives produced by the adapters in
`persona_council.artifacts`; emits HTML via the existing h()/_prose toolkit.
"""
from __future__ import annotations

from .. import artifacts as _A
from ._i18n import t
from ._html import h, raw, fragment
from ._components import _prose, _avatar, _label, _icon


def render_stance(st: dict | None) -> str:
    """The one stance chip — color + label from the data-driven scale (artifacts.stance_meta)."""
    if not st:
        return ""
    meta = _A.stance_meta(st.get("value", 0))
    return _label(t("stance_" + st.get("label", "neutral")), meta["color"])   # t("stance_"+term) → label_key


def render_ref(r: dict) -> str:
    """A grounding chip: a memory/observed-state note, an internal link, or a quote. The kind→route
    mapping lives in the domain layer (artifacts.ref_href) so no kind literal is hardcoded here."""
    href = _A.ref_href(r)
    txt = r.get("quote") or r.get("text") or r.get("id") or ""
    if href:
        return h("a", {"class_": "srcchip", "href": href}, raw(_icon("link")), " ", txt)
    ico = "memory" if r.get("kind") == "memory" else ("compass" if r.get("kind") == "prototype_state" else "link")
    return h("span", {"class_": "srcchip"}, raw(_icon(ico)), " ", txt)


def _refs_line(refs: list, label: str) -> str:
    if not refs:
        return ""
    return h("p", {"class_": "muted small turn-refs"}, label, ": ",
             fragment(*(raw(render_ref(r)) for r in refs)))


def render_prompt(p: dict, *, n: int | None = None) -> str:
    """A posed prompt. As a transcript header (question/proposal) with an optional ordinal."""
    ey = {"question": t("question"), "proposal": t("council_motion"),
          "goal": t("question"), "focus": t("question"), "hypothesis": t("council_motion")}.get(p.get("kind"), t("question"))
    label = f'{ey} {n}' if n is not None else ey
    ico = "compass" if p.get("kind") in ("question", "goal", "focus") else "bulb"
    return h("div", {"class_": "qround-q"}, raw(_icon(ico)),
             h("div", {}, h("div", {"class_": "qround-n"}, label),
               h("p", {}, raw(_prose(p.get("text", ""))))))


def render_statement(st: dict, store) -> str:
    """A persona statement — the ONE .turn card used by council answers, synthesis voices and prototype
    sessions: avatar + name + stance + life-context, then the prose body, grounding refs and any extras."""
    pid = st.get("persona_id", "")
    p = store.get_persona(pid) if pid else None
    name = (p or {}).get("display_name") or pid or "—"
    seg = (p or {}).get("segment") or {}
    ctx = " · ".join(x for x in [seg.get("lebensphase"), seg.get("einstellung")] if x)[:130] \
        or ((p or {}).get("source_description") or "")[:130]
    who = (h("a", {"href": f'/personas/{p["id"]}', "class_": "turn-who"}, _avatar(p, 26), h("b", {}, name))
           if p else h("span", {"class_": "turn-who"}, h("b", {}, name)))
    stance_chip = raw(render_stance(st.get("stance"))) if st.get("stance") else None
    rel = h("span", {"class_": "muted small"}, f' · {st["relevance"]}') if st.get("relevance") else None
    meta = st.get("meta") or {}
    given = h("details", {"class_": "turn-input"},
              h("summary", {"class_": "muted small"}, t("council_input_given")),
              h("p", {"class_": "muted small", "style": "white-space:pre-wrap"}, meta["input"])) if meta.get("input") else None
    pushback = fragment(*(h("p", {"class_": "muted small"}, f"• {q}") for q in (meta.get("pushback") or [])[:4]))
    shift = st.get("shift") or {}
    shift_html = h("p", {"class_": "muted small"}, raw(_icon("exchange")), " ",
                   f'{shift.get("from","")} → {shift.get("to","")}', (f' · {shift["trigger"]}' if shift.get("trigger") else "")) if shift else None
    return h("div", {"class_": "turn"},
             h("div", {"class_": "hd"}, who, " ", stance_chip, rel,
               h("div", {"class_": "muted small turn-ctx"}, ctx) if ctx else None),
             given,
             h("div", {"class_": "turn-ans"}, h("p", {}, raw(_prose(st.get("text", "")))), pushback, shift_html,
               raw(_refs_line(st.get("refs") or [], t("council_drew_on")))))


def render_statements(items: list, store, *, group_by: str = "persona", prompts: list | None = None) -> str:
    """Render a list of statements. group_by='prompt' → a moderated transcript (question header + the
    statements answering it, via Statement.about.id); group_by='persona'/None → a flat list of cards."""
    items = [s for s in items if s]
    if group_by == "prompt" and prompts:
        rounds = []
        for n, p in enumerate(prompts, 1):
            qs = [s for s in items if (s.get("about") or {}).get("id") == p.get("id")]
            if not qs:
                continue
            rounds.append(h("div", {"class_": "qround"}, raw(render_prompt(p, n=n)),
                            h("div", {"class_": "qround-a"}, fragment(*(render_statement(s, store) for s in qs)))))
        rest = [s for s in items if not (s.get("about") and any((s.get("about") or {}).get("id") == p.get("id") for p in prompts))]
        if rest:
            rounds.append(h("div", {"class_": "qround"},
                            h("div", {"class_": "qround-q"}, raw(_icon("bulb")),
                              h("div", {}, h("div", {"class_": "qround-n"}, t("further_answers")))),
                            h("div", {"class_": "qround-a"}, fragment(*(render_statement(s, store) for s in rest)))))
        return h("div", {"class_": "qrounds"}, fragment(*rounds))
    return h("div", {"style": "display:flex;flex-direction:column;gap:10px"},
             fragment(*(render_statement(s, store) for s in items)))


def render_finding(f: dict, *, n: int | None = None) -> str:
    """One authored finding: prose + optional effort·impact score chip + grounding refs. The list-row form
    used by every synthesis finding section."""
    score = f.get("score")
    chip = ""
    if isinstance(score, dict) and score.get("effort") and score.get("value"):
        chip = h("span", {"class_": "axchip"}, t("effort_value", a=score["effort"], n=score["value"]))
    num = h("span", {"class_": "recnum"}, str(n)) if n is not None else None
    body = h("div", {}, raw(_prose(f.get("text", ""))), chip,
             raw(_refs_line(f.get("refs") or [], t("rel_based_on"))))
    cls = "rec" if (n is not None or chip) else "psolve"
    return h("div", {"class_": cls}, num, body) if num else h("div", {"class_": cls}, body)


def render_findings(items: list, kind: str) -> tuple[str, str, str]:
    """A whole finding SECTION for one kind → (section_id, label, html). id+label come from
    artifacts.finding_kind() (data-driven; the synthesis minimap anchors)."""
    meta = _A.finding_kind(kind)
    numbered = kind in ("recommendation",)
    rows = [render_finding(f, n=(i if numbered else None)) for i, f in enumerate(items, 1)]
    return meta["id"], t(meta["label_key"]), fragment(*rows)
