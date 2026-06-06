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


def _statement_body(st: dict) -> str:
    """One utterance's body: optional focus line, input snapshot, the prose, pushback, shift, refs."""
    meta = st.get("meta") or {}
    focus = h("p", {"class_": "muted small", "style": "font-style:italic;margin:0 0 4px"}, meta["focus"]) if meta.get("focus") else None
    given = h("details", {"class_": "turn-input"},
              h("summary", {"class_": "muted small"}, t("council_input_given")),
              h("p", {"class_": "muted small", "style": "white-space:pre-wrap"}, meta["input"])) if meta.get("input") else None
    pushback = fragment(*(h("p", {"class_": "muted small"}, f"• {q}") for q in (meta.get("pushback") or [])[:4]))
    shift = st.get("shift") or {}
    shift_html = h("p", {"class_": "muted small"}, raw(_icon("exchange")), " ",
                   f'{shift.get("from","")} → {shift.get("to","")}',
                   (f' · {shift["trigger"]}' if shift.get("trigger") else "")) if shift else None
    return h("div", {"class_": "turn-ans"}, focus, given, h("p", {}, raw(_prose(st.get("text", "")))),
             pushback, shift_html, raw(_refs_line(st.get("refs") or [], t("council_drew_on"))))


def _persona_card(sts: list, store, *, head_extra=None) -> str:
    """The ONE .turn statement card — a persona's avatar + name + stance + life-context, then one or more
    utterance bodies (a persona answering several questions merges into a single card, not repeated heads)."""
    head_st = sts[0]
    pid = head_st.get("persona_id", "")
    p = store.get_persona(pid) if pid else None
    name = (p or {}).get("display_name") or pid or "—"
    seg = (p or {}).get("segment") or {}
    ctx = (head_st.get("meta") or {}).get("context") \
        or " · ".join(x for x in [seg.get("lebensphase"), seg.get("einstellung")] if x)[:130] \
        or ((p or {}).get("source_description") or "")[:130]
    who = (h("a", {"href": f'/personas/{p["id"]}', "class_": "turn-who"}, _avatar(p, 26), h("b", {}, name))
           if p else h("span", {"class_": "turn-who"}, h("b", {}, name)))
    st_with_stance = next((s for s in sts if s.get("stance")), None)
    stance_chip = raw(render_stance(st_with_stance["stance"])) if st_with_stance else None
    rel = head_st.get("relevance")
    rel_html = h("span", {"class_": "muted small"}, f" · {rel}") if rel else None
    return h("div", {"class_": "turn"},
             h("div", {"class_": "hd"}, who, " ", stance_chip, head_extra, rel_html,
               h("div", {"class_": "muted small turn-ctx"}, ctx) if ctx else None),
             fragment(*(_statement_body(s) for s in sts)))


def render_statement(st: dict, store, *, head_extra=None) -> str:
    """A single persona statement → the .turn card (used by prototype sessions). `head_extra` is an extra
    header chip (e.g. a session's grounded badge)."""
    return _persona_card([st], store, head_extra=head_extra)


def _by_persona(items: list) -> list:
    order, by = [], {}
    for s in items:
        pid = s.get("persona_id")
        if pid not in by:
            by[pid] = []; order.append(pid)
        by[pid].append(s)
    return [by[pid] for pid in order]


def render_statements(items: list, store, *, group_by: str = "persona", prompts: list | None = None) -> str:
    """Render statements as the SAME .turn cards. group_by='prompt' → a moderated transcript (a question
    header from `prompts` + the statements answering it via Statement.about.id, grouped per persona);
    group_by='persona' → a flat list of per-persona cards."""
    items = [s for s in items if s]
    if group_by == "prompt" and prompts:
        ids = {p.get("id") for p in prompts}
        rounds = []
        for n, p in enumerate(prompts, 1):
            qs = [s for s in items if (s.get("about") or {}).get("id") == p.get("id")]
            if not qs:
                continue
            rounds.append(h("div", {"class_": "qround"}, raw(render_prompt(p, n=n)),
                            h("div", {"class_": "qround-a"}, fragment(*(_persona_card(g, store) for g in _by_persona(qs))))))
        rest = [s for s in items if (s.get("about") or {}).get("id") not in ids]
        if rest:
            rounds.append(h("div", {"class_": "qround"},
                            h("div", {"class_": "qround-q"}, raw(_icon("bulb")),
                              h("div", {}, h("div", {"class_": "qround-n"}, t("further_answers")))),
                            h("div", {"class_": "qround-a"}, fragment(*(_persona_card(g, store) for g in _by_persona(rest))))))
        return h("div", {"class_": "qrounds"}, fragment(*rounds))
    return h("div", {"style": "display:flex;flex-direction:column;gap:10px"},
             fragment(*(_persona_card(g, store) for g in _by_persona(items))))


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


def render_findings(items: list, *, numbered: bool = False) -> str:
    """The rows of a finding list section (one render_finding per item). The caller wraps them in a
    section with the data-driven id (artifacts.finding_kind(kind)['id']) and an i18n label."""
    rows = [render_finding(f, n=(i if numbered else None)) for i, f in enumerate(items, 1)]
    return fragment(*rows)
