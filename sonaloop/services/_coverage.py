"""Coverage / diversity check (taxonomy id `coverage`): a DETERMINISTIC analysis over a study's persona
set that flags when the panel is too narrow to be trustworthy. Founders tend to model clones of themselves,
producing a council that agrees because it's homogeneous; this check inspects the *who* behind a study and
surfaces concrete gaps, over-concentration, an overall coverage indicator, and recommended archetypes to add.

In the taxonomy this supplies the COVERAGE dimension — the "who" every Job preset declares alongside its
Framework and Formats (`taxonomy.json` jobs each carry a `coverage` block: min_personas + persona_axes, read
via `job_taxonomy`). The check runs in two modes that compose:

  - GENERAL homogeneity / over-concentration analysis (no job): for each coverage dimension, how is the panel
    distributed and does one value DOMINATE beyond a threshold? Plus is the panel simply too small?
  - DECLARED-coverage comparison (a Job id): also evaluate the panel against that Job's DECLARED coverage —
    fewer than its declared min_personas, or a declared axis that maps to a dimension the panel can't fill,
    is a gap.

This is NOT a Format/council — it's an analysis over the project's persona set, so it records nothing; it
just RETURNS the structured assessment (consumable by the presets ticket, which declares/verifies coverage,
and a clean pairing for red-team). No server-side text-LLM call ever happens here — the host can narrate on
top of the deterministic result.

Coverage dimensions map to REAL persona fields (see the Persona model + the host-authored profile shape):

  - segment        — persona.segment.customer_type (the archetype axis head_to_head/red_team group by),
                     falling back to the most populated value in persona.segment when customer_type is absent
                     (project-specific segment schemas, e.g. the German lebensphase/einstellung axes).
  - demographics   — persona.demographics.* + firmographic hints (segment.firm_size/market, company size).
  - attitude       — persona.personality.risk_tolerance (+ segment.einstellung when present): the disposition
                     axis a homogeneous founder-panel collapses on.
  - needs          — derived from the SPREAD of persona.goals (a panel whose goals all rhyme is narrow);
                     "thin" when there is no goal variety, not a fabricated category.
  - jtbd           — derived from the SPREAD of pain_points/goals as job-to-be-done signals; there is no
                     structured JTBD field, so it is assessed as a derived spread and flagged "not assessable"
                     when there is nothing to derive from (we never fabricate a value).
"""
from __future__ import annotations

from typing import Any

from ..storage import Store
from .. import job_taxonomy as _jobs

from ._common import *  # noqa: F401,F403  (_require_research_project, list_personas, …)


# ----------------------------------------------------------------------------- thresholds (explicit, tested)
# Over-concentration: one value holding MORE than this share of the panel on a dimension is a dominance flag
# (e.g. 8 of 10 = 0.8 > 0.6). Kept deliberately lenient so it fires on real homogeneity, not minor skew.
DOMINANCE_THRESHOLD = 0.6
# A dimension with fewer DISTINCT values than this (across a panel large enough to have spread) is "thin".
MIN_DISTINCT_VALUES = 2
# A panel smaller than this is structurally too small to be trustworthy regardless of spread.
MIN_PANEL = 3
# Coverage indicator levels (worst-first): a study lands on the worst level any reason triggers.
_LEVELS = ("thin", "ok", "strong")


# ----------------------------------------------------------------------------- coverage dimensions
# Each dimension declares how to READ its value off a persona. `derived` dimensions have no single structured
# field (needs/jtbd) — they read a SPREAD of list fields; `assessable=False` is set per-persona when nothing
# can be derived, so we report "not assessable" instead of fabricating a value.
COVERAGE_DIMENSIONS: list[dict[str, Any]] = [
    {"id": "segment", "label": "Segment", "kind": "categorical"},
    {"id": "demographics", "label": "Demografie/Firmografie", "kind": "categorical"},
    {"id": "attitude", "label": "Einstellung", "kind": "categorical"},
    {"id": "needs", "label": "Bedürfnisse", "kind": "derived"},
    {"id": "jtbd", "label": "JTBD", "kind": "derived"},
]
_DIM_IDS = [d["id"] for d in COVERAGE_DIMENSIONS]

# Declared Job persona-axes (taxonomy `coverage.persona_axes`) map onto our dimensions where they overlap, so
# a declared axis that lands on a dimension the panel can't fill becomes a concrete gap. Axes with no mapping
# (e.g. "current-alternative", "trigger-moment") are reported as declared-but-unmapped, not silently dropped.
_AXIS_TO_DIM: dict[str, str] = {
    "segment": "segment",
    "buying-stage": "attitude",
    "willingness-to-pay": "attitude",
    "budget-authority": "demographics",
    "expertise-level": "demographics",
    "lifecycle-stage": "segment",
    "tenure": "demographics",
    "churn-reason": "needs",
}


def _segment_value(p: dict[str, Any]) -> str | None:
    """The segment archetype axis: persona.segment.customer_type (what head_to_head/red_team split on),
    falling back to the first non-empty value of persona.segment for project-specific segment schemas
    (e.g. the German lebensphase/einstellung axes used by the food-delivery study)."""
    seg = p.get("segment") or {}
    val = seg.get("customer_type")
    if val:
        return str(val).strip() or None
    for v in seg.values():
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _demographics_value(p: dict[str, Any]) -> str | None:
    """A demographic/firmographic bucket: company size / firm_size / market / a demographic field — whatever
    structured signal exists. Returns None when nothing structured is present (→ not assessable)."""
    seg = p.get("segment") or {}
    company = p.get("company_context") or {}
    demo = p.get("demographics") or {}
    for v in (company.get("size"), seg.get("firm_size"), seg.get("market"),
              demo.get("beruf"), demo.get("alter"), demo.get("age")):
        if v not in (None, "", "unspecified"):
            return str(v).strip()
    return None


def _attitude_value(p: dict[str, Any]) -> str | None:
    """The disposition axis a homogeneous founder-panel collapses on: personality.risk_tolerance, falling
    back to segment.einstellung (the German attitude axis). None when neither is present."""
    pers = p.get("personality") or {}
    rt = pers.get("risk_tolerance")
    if rt not in (None, "", "unspecified"):
        return str(rt).strip()
    ein = (p.get("segment") or {}).get("einstellung")
    if isinstance(ein, str) and ein.strip():
        return ein.strip()
    return None


def _derived_signal(p: dict[str, Any], dim_id: str) -> str | None:
    """Derived dimensions (needs/jtbd) have no single field; we read a SPREAD-bearing signal so the
    distribution math can tell whether the panel's needs/jobs actually differ. We use the FIRST goal /
    pain_point as the representative signal (lower-cased, trimmed) — a panel whose representative needs all
    coincide is narrow. None (→ not assessable) when there's nothing to derive from."""
    if dim_id == "needs":
        items = p.get("goals") or []
    else:  # jtbd: pain_points are the closest job-to-be-done signal, then goals
        items = (p.get("pain_points") or []) or (p.get("goals") or [])
    for it in items:
        if isinstance(it, str) and it.strip():
            return it.strip().lower()
    return None


_READERS = {
    "segment": _segment_value,
    "demographics": _demographics_value,
    "attitude": _attitude_value,
    "needs": lambda p: _derived_signal(p, "needs"),
    "jtbd": lambda p: _derived_signal(p, "jtbd"),
}


def _distribution(personas: list[dict[str, Any]], dim_id: str) -> dict[str, Any]:
    """The per-dimension distribution: how the (assessable) personas spread across values, the dominant value
    + its share, and how many personas were not assessable on this dimension (no structured/derived value)."""
    read = _READERS[dim_id]
    counts: dict[str, int] = {}
    not_assessable = 0
    for p in personas:
        val = read(p)
        if val is None:
            not_assessable += 1
            continue
        counts[val] = counts.get(val, 0) + 1
    assessed = sum(counts.values())
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    dominant, dominant_count = (ranked[0] if ranked else (None, 0))
    dominant_share = round(dominant_count / assessed, 3) if assessed else 0.0
    return {
        "dimension": dim_id,
        "counts": dict(ranked),
        "distinct": len(counts),
        "assessed": assessed,
        "not_assessable": not_assessable,
        "dominant": dominant,
        "dominant_share": dominant_share,
    }


def _analyze_dimension(dist: dict[str, Any], panel: int) -> dict[str, Any]:
    """Flag a single dimension. Two deterministic checks:
      - OVER-CONCENTRATION: one value holds > DOMINANCE_THRESHOLD of the assessed personas (e.g. 8/10).
      - THIN: too few distinct values to be diverse (on a panel large enough to have had spread), or the
        whole dimension is not assessable (no structured/derived field for any persona)."""
    assessed = dist["assessed"]
    over_concentration = bool(assessed >= MIN_PANEL and dist["dominant_share"] > DOMINANCE_THRESHOLD)
    no_signal = assessed == 0
    thin = bool(no_signal or (panel >= MIN_PANEL and dist["distinct"] < MIN_DISTINCT_VALUES))
    return {**dist, "over_concentration": over_concentration, "no_signal": no_signal, "thin": thin}


def _job_declared(job_id: str | None) -> dict[str, Any] | None:
    """The Job's declared coverage block (min_personas + persona_axes + note) from the taxonomy, or None when
    no job is given / the id is unknown (general analysis still runs)."""
    if not job_id:
        return None
    try:
        job = _jobs.get_job(job_id)
    except KeyError:
        return None
    cov = job.get("coverage") or {}
    return {"job_id": job["id"], "job_name": job.get("name", job["id"]),
            "min_personas": cov.get("min_personas"), "persona_axes": list(cov.get("persona_axes") or []),
            "note": cov.get("note", "")}


def _detect_gaps(dims: list[dict[str, Any]], panel: int, declared: dict[str, Any] | None) -> list[dict[str, Any]]:
    """The concrete gaps: per-dimension thinness/over-concentration AND (when a Job is known) declared-axis
    gaps — too-few personas vs the declared minimum, and declared axes that land on a dimension the panel
    can't fill (thin / not assessable). Each gap carries a stable {kind, dimension, reason} the UI/host narrate."""
    by_id = {d["dimension"]: d for d in dims}
    gaps: list[dict[str, Any]] = []

    if panel < MIN_PANEL:
        gaps.append({"kind": "panel_too_small", "dimension": None,
                     "reason": f"Nur {panel} Personas im Panel (Minimum {MIN_PANEL} für Aussagekraft)."})

    for d in dims:
        dim_id = d["dimension"]
        label = next((x["label"] for x in COVERAGE_DIMENSIONS if x["id"] == dim_id), dim_id)
        if d["over_concentration"]:
            gaps.append({"kind": "over_concentration", "dimension": dim_id,
                         "reason": (f"{label}: '{d['dominant']}' dominiert "
                                    f"{int(round(d['dominant_share'] * 100))}% des Panels — zu einseitig.")})
        elif d["no_signal"]:
            gaps.append({"kind": "not_assessable", "dimension": dim_id,
                         "reason": f"{label}: keine erfassbaren Werte — Dimension nicht beurteilbar."})
        elif d["thin"]:
            gaps.append({"kind": "thin", "dimension": dim_id,
                         "reason": (f"{label}: nur {d['distinct']} unterschiedlicher Wert — zu wenig Streuung.")})

    if declared:
        min_p = declared.get("min_personas")
        if isinstance(min_p, int) and panel < min_p:
            gaps.append({"kind": "below_declared_min", "dimension": None,
                         "reason": (f"Job '{declared['job_name']}' verlangt mindestens {min_p} Personas; "
                                    f"das Panel hat {panel}.")})
        for axis in declared.get("persona_axes", []):
            dim_id = _AXIS_TO_DIM.get(axis)
            if dim_id is None:
                gaps.append({"kind": "declared_axis_unmapped", "dimension": None, "axis": axis,
                             "reason": (f"Geforderte Achse '{axis}' lässt sich nicht aus den Persona-Feldern "
                                        f"ableiten — manuell prüfen.")})
                continue
            d = by_id.get(dim_id)
            if d and (d["thin"] or d["no_signal"]):
                label = next((x["label"] for x in COVERAGE_DIMENSIONS if x["id"] == dim_id), dim_id)
                gaps.append({"kind": "declared_axis_gap", "dimension": dim_id, "axis": axis,
                             "reason": (f"Geforderte Achse '{axis}' ({label}) ist im Panel zu dünn besetzt.")})
    return gaps


def _recommend_archetypes(dims: list[dict[str, Any]], gaps: list[dict[str, Any]],
                          declared: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Deterministic gap-filling suggestions. There is no persona/archetype CATALOG in the repo (the host
    authors personas via brief_persona/record_persona), so we suggest archetype DESCRIPTIONS derived from the
    detected gaps — a concrete "add a persona unlike X on dimension Y" the host can turn into a real persona.
    Each carries the dimension, the value to AVOID (the dominant/only one), and a host-ready description."""
    by_id = {d["dimension"]: d for d in dims}
    recs: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(dim_id: str | None, description: str, avoid: str | None = None) -> None:
        key = f"{dim_id}|{description}"
        if key in seen:
            return
        seen.add(key)
        label = next((x["label"] for x in COVERAGE_DIMENSIONS if x["id"] == dim_id), dim_id)
        recs.append({"dimension": dim_id, "dimension_label": label, "avoid_value": avoid,
                     "description": description})

    for g in gaps:
        dim_id = g.get("dimension")
        kind = g["kind"]
        if kind == "panel_too_small":
            _add(None, f"Erweitere das Panel auf mindestens {MIN_PANEL} Personas mit unterschiedlichen Profilen.")
        elif kind == "below_declared_min" and declared:
            _add(None, (f"Füge Personas hinzu, bis das Panel die {declared['min_personas']} für Job "
                        f"'{declared['job_name']}' geforderten Personas erreicht."))
        elif kind == "over_concentration":
            d = by_id.get(dim_id) or {}
            dom = d.get("dominant")
            label = next((x["label"] for x in COVERAGE_DIMENSIONS if x["id"] == dim_id), dim_id)
            _add(dim_id, (f"Füge eine Persona hinzu, die sich in der Dimension {label} klar von '{dom}' "
                          f"unterscheidet, um die Einseitigkeit aufzubrechen."), avoid=dom)
        elif kind in ("thin", "declared_axis_gap"):
            d = by_id.get(dim_id) or {}
            dom = d.get("dominant")
            label = next((x["label"] for x in COVERAGE_DIMENSIONS if x["id"] == dim_id), dim_id)
            axis = g.get("axis")
            extra = f" (geforderte Achse '{axis}')" if axis else ""
            _add(dim_id, (f"Füge mindestens eine Persona mit einem anderen Wert in der Dimension {label}{extra} "
                          f"hinzu — aktuell überwiegt '{dom}'."), avoid=dom)
        elif kind == "not_assessable":
            label = next((x["label"] for x in COVERAGE_DIMENSIONS if x["id"] == dim_id), dim_id)
            _add(dim_id, (f"Erfasse die Dimension {label} explizit in den Persona-Profilen, damit sie "
                          f"beurteilbar wird."))
    return recs


def _indicator(panel: int, dims: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> dict[str, Any]:
    """The overall coverage indicator: a level (thin|ok|strong) + the reasons. STRONG = no gaps and every
    assessable dimension has real spread; THIN = the panel is too small, a dimension is over-concentrated, or
    several dimensions are thin/not-assessable; OK otherwise. Deterministic — the host narrates on top."""
    over = [d for d in dims if d["over_concentration"]]
    thin = [d for d in dims if d["thin"]]
    reasons: list[str] = []

    if panel < MIN_PANEL:
        level = "thin"
        reasons.append(f"Panel zu klein ({panel} < {MIN_PANEL}).")
    elif over:
        level = "thin"
        reasons.append(f"Über-Konzentration in: {', '.join(d['dimension'] for d in over)}.")
    elif len(thin) >= 2:
        level = "thin"
        reasons.append(f"Mehrere dünne Dimensionen: {', '.join(d['dimension'] for d in thin)}.")
    elif thin:
        level = "ok"
        reasons.append(f"Eine dünne Dimension: {thin[0]['dimension']}.")
    else:
        level = "strong"
        reasons.append("Alle beurteilbaren Dimensionen streuen ausreichend.")

    return {"level": level, "score": _LEVELS.index(level), "gap_count": len(gaps), "reasons": reasons}


def assess_coverage(project: str, job: str | None = None,
                    persona_ids: list[str] | None = None,
                    store: Store | None = None) -> dict[str, Any]:
    """Assess whether a study's PERSONA SET is diverse enough to be trustworthy — a deterministic coverage /
    diversity check that flags a homogeneous "council of clones".

    Pass a research-project id as `project` (its persona_ids define the panel; override with `persona_ids`).
    With a `job` taxonomy id, the panel is ALSO evaluated against that Job's DECLARED coverage (min_personas +
    persona_axes); without one, only the general homogeneity / over-concentration analysis runs.

    Returns the structured assessment (no prose generation, no persistence):
      {schema, project_id, job, panel_size, indicator{level,score,reasons}, dimensions[per-dimension
       distribution + flags], gaps[concrete missing/thin/over-concentrated axes], recommendations[archetypes
       to add], declared_coverage}. Consumable by the presets ticket and a clean pairing for red-team."""
    store = store or Store()
    proj = _require_research_project(store, project)
    pids = persona_ids if persona_ids is not None else (proj.get("persona_ids") or [])
    personas = [p for p in (store.get_persona(pid) for pid in pids) if p]
    panel = len(personas)

    declared = _job_declared(job)
    dims = [_analyze_dimension(_distribution(personas, dim_id), panel) for dim_id in _DIM_IDS]
    gaps = _detect_gaps(dims, panel, declared)
    recommendations = _recommend_archetypes(dims, gaps, declared)
    indicator = _indicator(panel, dims, gaps)

    return {
        "schema": "coverage_assessment",
        "project_id": proj["id"],
        "job": (declared["job_id"] if declared else None),
        "panel_size": panel,
        "indicator": indicator,
        "dimensions": dims,
        "gaps": gaps,
        "recommendations": recommendations,
        "declared_coverage": declared,
    }
