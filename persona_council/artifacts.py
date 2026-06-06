"""Unified artifact primitives (spec/unified-artifact-schema.md + -rollout.md).

The whole research corpus reduces to five content primitives — Statement, Finding, Prompt, Ref, Stance —
that every artifact composes. This module is the DOMAIN layer (no web imports): the primitive
constructors, the data-driven vocabularies (stance scale, finding kinds), and — added in Phase 1 — the
read adapters that map current records onto the primitives. Reusable by web, export, meta-report, search.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .config import suggestions_dir


# --------------------------------------------------------------------------- vocabularies (data-driven)

@lru_cache(maxsize=1)
def _stance_scale() -> dict[str, Any]:
    """Load suggestions/stance_scale.json → {"by_term": {term: {value,label,color}}, "by_value": {...},
    "aliases": {alias: term}}. The ONE positivity vocabulary; no stance words hardcoded in engine/UI."""
    p = suggestions_dir() / "stance_scale.json"
    by_term: dict[str, dict] = {}
    by_value: dict[int, dict] = {}
    aliases: dict[str, str] = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        for it in data.get("items", []) or []:
            term = it.get("tag")
            if not term:
                continue
            pres = it.get("presentation") or {}
            rec = {"value": int(it.get("value", 0)), "term": term,
                   "label_key": it.get("label_key") or term, "color": pres.get("color") or "var(--muted)"}
            by_term[term] = rec
            by_value[rec["value"]] = rec
            aliases[term] = term
        for alias, term in (data.get("aliases") or {}).items():
            aliases[str(alias).lower()] = term
    return {"by_term": by_term, "by_value": by_value, "aliases": aliases}


def resolve_stance(term: Any) -> dict[str, Any] | None:
    """Map any legacy stance/sentiment/vote token (or a numeric value) onto a canonical Stance dict
    {value,label}. Unknown non-empty tokens fall back to neutral (value 0). Returns None for empty input."""
    if term in (None, "", []):
        return None
    sc = _stance_scale()
    if isinstance(term, (int, float)) and not isinstance(term, bool):
        rec = sc["by_value"].get(int(term))
        return {"value": int(term), "label": (rec or {}).get("term", str(term))}
    key = str(term).strip()
    canon = sc["aliases"].get(key) or sc["aliases"].get(key.lower())
    rec = sc["by_term"].get(canon) if canon else None
    if rec is None:
        neutral = sc["by_value"].get(0) or {"value": 0, "term": "neutral"}
        return {"value": neutral["value"], "label": neutral["term"]}
    return {"value": rec["value"], "label": rec["term"]}


def stance_meta(value: int) -> dict[str, str]:
    """Render fields for a stance value: an i18n `label_key` + `color`. Data-driven via the scale; the
    web layer resolves label_key through t() (this module stays web-free)."""
    rec = _stance_scale()["by_value"].get(int(value))
    return {"label_key": (rec or {}).get("label_key", "stance_neutral"),
            "color": (rec or {}).get("color", "var(--muted)")}


@lru_cache(maxsize=1)
def _finding_kinds() -> dict[str, dict[str, Any]]:
    """Load suggestions/finding_kinds.json → {kind: {id, label_key}}. The section id/label vocabulary for
    Finding lists (the synthesis minimap anchors come from here)."""
    p = suggestions_dir() / "finding_kinds.json"
    out: dict[str, dict] = {}
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        for it in data.get("items", []) or []:
            k = it.get("tag")
            if k:
                out[k] = {"id": it.get("id") or k, "label_key": it.get("label_key") or k}
    return out


def finding_kind(kind: str) -> dict[str, Any]:
    """{id, label_key} for a finding kind; generic fallback for an invented kind (no code change needed)."""
    return _finding_kinds().get(kind, {"id": kind, "label_key": kind})


def reload_vocab() -> None:                # mirror presentation.reload_hints() for tests
    _stance_scale.cache_clear()
    _finding_kinds.cache_clear()


# --------------------------------------------------------------------------- primitive constructors

def _clean(d: dict) -> dict:
    """Drop empty optionals so the stored JSON stays lean (None / "" / [] / {})."""
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}


_REF_ROUTES = {"council": "/councils/", "synthesis": "/syntheses/", "persona": "/personas/"}


def ref_href(r: dict) -> str | None:
    """The internal link for a record-pointing Ref (kept in the DOMAIN layer so the web renderer never
    hardcodes a kind→route literal — the kind-vocabulary grep gate)."""
    base = _REF_ROUTES.get(r.get("kind"))
    return (base + r["id"]) if base and r.get("id") else None


def ref(kind: str, *, id: str | None = None, text: str | None = None, quote: str | None = None) -> dict:
    """A grounding pointer. kind: memory|council|synthesis|prototype_state|persona|external. Carries an
    `id` (points at a record) or `text` (a free observed-state string), and an optional `quote`."""
    return _clean({"kind": kind, "id": id, "text": text, "quote": quote})


def stance(value: int, *, label: str | None = None) -> dict:
    """A point on the one positivity scale (-2 oppose … +2 support). label = canonical term (stable id)."""
    rec = _stance_scale()["by_value"].get(int(value))
    return {"value": int(value), "label": label or (rec or {}).get("term", str(value))}


def prompt(text: str, *, kind: str = "question", id: str | None = None) -> dict:
    """The thing posed. kind: question|proposal|goal|focus|hypothesis."""
    return _clean({"text": text or "", "kind": kind, "id": id})


def statement(persona_id: str, text: str, *, stance: dict | None = None, about: dict | None = None,
              refs: list | tuple = (), relevance: str | None = None, shift: dict | None = None,
              meta: dict | None = None) -> dict:
    """A persona's utterance — the unifier for council turns, synthesis voices and prototype reactions.
    `about` is a Ref/Prompt-id it responds to; `refs` is the grounding; artifact extras go in `meta`."""
    return _clean({"persona_id": persona_id or "", "text": text or "", "stance": stance,
                   "about": about, "refs": list(refs), "relevance": relevance,
                   "shift": shift, "meta": meta})


def finding(text: str, *, kind: str, score: dict | int | None = None, refs: list | tuple = (),
            meta: dict | None = None) -> dict:
    """An authored analysis item (key_problem, recommendation, open_question, cluster, …): markdown text,
    optional score (e.g. {effort,value}), optional grounding refs, kind-specific extras in `meta`."""
    return _clean({"text": text or "", "kind": kind, "score": score, "refs": list(refs), "meta": meta})


# --------------------------------------------------------------------------- validators (Phase 2 native authoring)
# Lenient normalizers for host-authored primitives — re-run input dicts through the constructors so a
# recorded record is always well-shaped (stance resolved through the scale, empties dropped).

def validate_ref(d: dict) -> dict:
    return ref(d.get("kind", "external"), id=d.get("id"), text=d.get("text"), quote=d.get("quote"))


def validate_stance(d) -> dict | None:
    if d in (None, "", []):
        return None
    if isinstance(d, dict) and "value" in d:
        return stance(int(d["value"]), label=d.get("label"))
    return resolve_stance(d)


def validate_prompt(d: dict) -> dict:
    return prompt(d.get("text", ""), kind=d.get("kind", "question"), id=d.get("id"))


def validate_statement(d: dict) -> dict:
    return statement(d.get("persona_id", ""), d.get("text", ""), stance=validate_stance(d.get("stance")),
                     about=(validate_ref(d["about"]) if d.get("about") else None),
                     refs=[validate_ref(r) for r in (d.get("refs") or [])],
                     relevance=d.get("relevance"), shift=d.get("shift") or None, meta=d.get("meta") or None)


def validate_finding(d: dict) -> dict:
    return finding(d.get("text", ""), kind=d.get("kind", "note"), score=d.get("score") or None,
                   refs=[validate_ref(r) for r in (d.get("refs") or [])], meta=d.get("meta") or None)


# --------------------------------------------------------------------------- read adapters (legacy → primitives)
# Pure transforms record-dict → primitives (persona lookup happens at render time). Each adapter PREFERS
# a record's native primitive field when present (forward-compat for Phase 2), else derives from legacy.

def _is_moderator(turn: dict) -> bool:
    return not turn.get("persona_id") or bool(turn.get("is_moderator")) or turn.get("role") == "moderator"


def council_prompts(c: dict) -> list[dict]:
    if c.get("prompts"):
        return list(c["prompts"])
    out = []
    if c.get("prompt"):
        out.append(prompt(c["prompt"], kind="question", id="prompt"))
    if c.get("proposal"):
        out.append(prompt(c["proposal"], kind="proposal", id="proposal"))
    for i, q in enumerate(c.get("questions") or []):
        out.append(prompt(q, kind="question", id=f"q{i}"))
    return out


def council_statements(c: dict) -> list[dict]:
    if c.get("statements"):
        return list(c["statements"])
    votes = {v.get("persona_id"): v.get("vote") for v in (c.get("votes") or []) if v.get("persona_id")}
    out = []
    for tn in c.get("turns") or []:
        if _is_moderator(tn):
            continue
        pid = tn.get("persona_id")
        text = tn.get("content") or tn.get("text") or tn.get("message") or ""
        qidx = tn.get("question_index", tn.get("question_idx"))
        about = ref("prompt", id=f"q{qidx}") if isinstance(qidx, int) else None
        st_term = tn.get("stance") or votes.get(pid)
        refs = [ref("memory", text=str(m)) for m in (tn.get("memory_refs") or tn.get("memory_used") or [])]
        meta = {}
        if tn.get("input"):
            meta["input"] = tn["input"]
        if tn.get("questions_or_pushback"):
            meta["pushback"] = tn["questions_or_pushback"]
        out.append(statement(pid, text, stance=resolve_stance(st_term) if st_term else None,
                             about=about, refs=refs, meta=meta or None))
    return out


_SYN_LIST_KINDS = [("key_problems", "key_problem"), ("pain_solvers", "pain_solver"),
                   ("offene_fragen", "open_question"), ("shortlist", "shortlist")]


def synthesis_prompts(s: dict) -> list[dict]:
    if s.get("prompts"):
        return list(s["prompts"])
    out = []
    if s.get("start_input"):
        out.append(prompt(s["start_input"], kind="question", id="start"))
    if s.get("goal"):
        out.append(prompt(s["goal"], kind="goal", id="goal"))
    return out


def synthesis_statements(s: dict) -> list[dict]:
    if s.get("statements"):
        return list(s["statements"])
    out = []
    for v in s.get("voices") or []:
        refs = [ref("council", id=e.get("council_id"), quote=e.get("quote"))
                for e in (v.get("evidence") or []) if isinstance(e, dict)]
        sh = v.get("shift") or None
        meta = {"context": v["segment"]} if v.get("segment") else None   # → the card's ctx line
        out.append(statement(v.get("persona_id", ""), v.get("key_argument", ""),
                             stance=resolve_stance(v.get("sentiment")) if v.get("sentiment") else None,
                             refs=refs, relevance=v.get("relevance"), shift=sh, meta=meta))
    return out


def synthesis_findings(s: dict) -> list[dict]:
    """The synthesis LIST findings (key_problems/pain_solvers/open_questions/shortlist/recommendations).
    Prose blocks (gesamtbild/positionierung/arc) and the 2-col clusters/segmente stay separate for now."""
    if s.get("findings"):
        return list(s["findings"])
    out = []
    for field_name, kind in _SYN_LIST_KINDS:
        for x in s.get(field_name) or []:
            out.append(finding(str(x), kind=kind))
    for rec in s.get("handlungsempfehlungen") or []:
        if isinstance(rec, dict):
            score = {"effort": rec.get("aufwand"), "value": rec.get("nutzen")} if rec.get("aufwand") and rec.get("nutzen") else None
            out.append(finding(rec.get("text", ""), kind="recommendation", score=score))
        else:
            out.append(finding(str(rec), kind="recommendation"))
    for c in s.get("clusters") or []:
        out.append(finding(c.get("label", ""), kind="cluster",
                           meta={"detail": c.get("insight", ""), "members": c.get("member_node_ids") or c.get("members") or []}))
    for sg in s.get("segmente") or []:
        out.append(finding(sg.get("segment", ""), kind="segment",
                           meta={"detail": sg.get("why", ""), "stance": resolve_stance(sg.get("stance")) if sg.get("stance") else None}))
    for rk in s.get("ranking") or []:
        out.append(finding(rk.get("prototype_id", ""), kind="ranking", meta={"detail": rk.get("score_rationale", "")}))
    return out


def session_statements(se: dict, persona_name: str | None = None) -> list[dict]:
    if se.get("statements"):
        return list(se["statements"])
    r = se.get("reaction") if isinstance(se.get("reaction"), dict) else {}
    refs = [ref("prototype_state", text=str(x)) for x in (se.get("observed_state_refs") or r.get("observed_state_refs") or [])]
    text = r.get("verdict") or r.get("reaction_text") or r.get("summary") or ""
    extra = {k: v for k, v in r.items()
             if k not in ("persona", "fidelity", "version", "observed_state_refs", "self_authored",
                          "session_id", "grounded_verified", "grounded", "verdict", "reaction_text", "summary", "focus")
             and v not in (None, "", [], {})}
    meta = {}
    ctx = " · ".join(x for x in [r.get("fidelity"), r.get("version")] if x)
    if ctx:
        meta["context"] = ctx                       # → the card's ctx line (fidelity · version)
    if r.get("focus"):
        meta["focus"] = r["focus"]                  # → a muted "focus" line in the body
    meta.update(extra)
    return [statement(se.get("persona_id", ""), text, refs=refs, meta=meta or None)]


def note_findings(n: dict) -> list[dict]:
    if n.get("findings"):
        return list(n["findings"])
    return [finding(n.get("text", ""), kind=(n.get("kind") or "note"))] if n.get("text") else []
