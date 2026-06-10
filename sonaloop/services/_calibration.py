"""Calibration against real data — the backtest loop (ticket calibration-backtest-loop).

The one structural moat: predicted behavior is checked against what actually
happened, the gap is measured, and corrections feed back into the personas —
so calibration COMPOUNDS while everything else is a closable lead.

The loop, on machinery that already exists:

1. PREDICT — `predicted_behavior` primitives (canonical likelihood values) and
   hypothesis bets are stamped before reality answers.
2. OBSERVE — `record_prediction_outcome` matches a real outcome (a conversion
   rate, an A/B result, a survey answer) to one prediction; the source Ref must
   resolve, the Brier score is derived, never asserted. Hypotheses keep their
   own verdict path (record_hypothesis_result).
3. MEASURE — `calibration_report` aggregates both sides: mean Brier, hit rate,
   and the reliability curve (predicted likelihood vs observed frequency per
   level); every report persists into eval_reports, so `calibration_trend`
   reads accuracy OVER TIME — calibration quality as a first-class metric.
4. CORRECT — `brief_calibration` gathers the misses (refuted bets, high-error
   predictions, each with its evidence trail); the HOST authors corrections
   (persona patches via update_persona, new grounding via record_grounding —
   the server never generates text); `record_calibration_round` stamps the
   round so the next reports show whether corrections actually improved
   subsequent predictions."""

from __future__ import annotations

from typing import Any

from .. import artifacts as _A
from ..config import utc_now_iso
from ..storage import Store

from ._common import *  # noqa: F401,F403  (stable_id, _require_research_project, …)


GOOD_BRIER = 0.25          # the coin-flip line: (0.5 - outcome)^2 — below it the sims carry signal
HIGH_ERROR_BRIER = 0.25    # outcomes above this line are the correction candidates


def _find_prediction(store: Store, ref: dict[str, Any]) -> dict[str, Any]:
    """Resolve a prediction Ref {kind: session|council|synthesis, id, anchor: <pb id>} to the
    stored predicted_behavior primitive."""
    kind, rid, anchor = ref.get("kind"), ref.get("id"), ref.get("anchor")
    if kind not in ("session", "council", "synthesis") or not rid or not anchor:
        raise ValueError("prediction_ref must be {kind: session|council|synthesis, id, "
                         "anchor: <the prediction's part id, e.g. 'pb1'>}")
    if kind == "session":
        art = store.get_usability_session(rid)
        preds = ((art or {}).get("outcome") or {}).get("predicted_behaviors") or []
    elif kind == "council":
        art = store.get_council_session(rid)
        preds = (art or {}).get("predictions") or []
    else:
        art = store.get_synthesis(rid)
        preds = (art or {}).get("predictions") or []
    if not art:
        raise KeyError(f"Unknown {kind}: {rid}")
    for p in preds:
        if p.get("id") == anchor:
            return p
    raise KeyError(f"No prediction {anchor!r} on {kind}:{rid}")


def record_prediction_outcome(project_id: str, prediction_ref: dict[str, Any], observed: Any,
                              source: dict[str, Any], note: str = "",
                              store: Store | None = None) -> dict[str, Any]:
    """Match ONE real outcome to one predicted behavior and score it. `observed` is a
    bool (it happened / it didn't) or a rate 0..1 (35% of real users abandoned). The
    Brier score (likelihood − observed)² is DERIVED — the host's argument goes in
    `note`, both raw values stay on the record. `source` is a resolvable Ref (a
    survey's imported responses, attached evidence, an external observation as text)."""
    store = store or Store()
    project = _require_research_project(store, project_id)  # noqa: F821 (bound)
    prediction = _find_prediction(store, prediction_ref)
    likelihood = (prediction.get("likelihood") or {}).get("value")
    if not isinstance(likelihood, (int, float)):
        raise ValueError("this prediction has no likelihood — only a quantified prediction is "
                         "scoreable; re-record it with a canonical likelihood first")
    if isinstance(observed, bool):
        observed_value = 1.0 if observed else 0.0
    else:
        try:
            observed_value = float(observed)
        except (TypeError, ValueError):
            raise ValueError("observed must be a bool or a rate 0..1") from None
        if not 0.0 <= observed_value <= 1.0:
            raise ValueError("observed rate must be within 0..1")
    src = _A.validate_ref(source if isinstance(source, dict) else {})
    src.setdefault("role", "observed_in")
    if src.get("kind") != "external" and not src.get("id"):
        raise ValueError("source needs an id (the record reality answered in) — only "
                         "{kind:'external', text} may carry a free observation")
    if not _A.resolve_ref(src, store).get("exists"):
        raise ValueError(f"source does not resolve: {src.get('kind')}:{src.get('id') or ''}")
    brier = round((float(likelihood) - observed_value) ** 2, 4)
    now = utc_now_iso()
    outcome = {"id": stable_id("pbout", project["id"], str(prediction_ref), now),  # noqa: F821 (bound)
               "project_id": project["id"], "prediction_ref": prediction_ref,
               "action": prediction.get("action", ""),
               "persona_id": prediction.get("persona_id", ""),
               "likelihood": float(likelihood),
               "likelihood_label": (prediction.get("likelihood") or {}).get("label", ""),
               "observed": observed_value, "brier": brier,
               "hit": (float(likelihood) >= 0.5) == (observed_value >= 0.5),
               "source": src, "note": str(note or ""), "created_at": now}
    store.insert_prediction_outcome(outcome)
    emit_lifecycle_event("prediction.scored", {"project_id": project["id"],  # noqa: F821 (bound)
                                               "outcome_id": outcome["id"], "brier": brier,
                                               "hit": outcome["hit"]}, store)
    return outcome


def _reliability(outcomes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The reliability curve: per likelihood level, predicted mean vs observed
    frequency — a well-calibrated cohort tracks the diagonal."""
    buckets: dict[str, dict[str, Any]] = {}
    for o in outcomes:
        label = o.get("likelihood_label") or "unlabelled"
        b = buckets.setdefault(label, {"level": label, "n": 0, "predicted": [], "observed": []})
        b["n"] += 1
        b["predicted"].append(o["likelihood"])
        b["observed"].append(o["observed"])
    rows = []
    for b in buckets.values():
        rows.append({"level": b["level"], "n": b["n"],
                     "predicted_mean": round(sum(b["predicted"]) / b["n"], 3),
                     "observed_mean": round(sum(b["observed"]) / b["n"], 3)})
    order = {t["term"]: t["value"] for t in _A.likelihood_terms()}
    rows.sort(key=lambda r: order.get(r["level"], 0.5))
    return rows


def calibration_report(project_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Measure calibration NOW and persist the snapshot (kind='calibration' in
    eval_reports — the series calibration_trend reads). Combines the behavioral side
    (Brier + hit rate + reliability curve over scored predictions) with the
    hypothesis side (the scorecard's decisive hit rate). green = decisive data with
    mean Brier at or under the coin-flip line."""
    store = store or Store()
    if project_id:
        _require_research_project(store, project_id)  # noqa: F821 (bound)
    outcomes = store.list_prediction_outcomes(project_id)
    briers = [o["brier"] for o in outcomes]
    hits = [o for o in outcomes if o.get("hit")]
    hyps = [h for h in store.list_hypotheses(project_id)
            if h.get("status") in ("validated", "refuted")]
    hyp_hit = (sum(1 for h in hyps if h["status"] == "validated") / len(hyps)) if hyps else None
    mean_brier = round(sum(briers) / len(briers), 4) if briers else None
    now = utc_now_iso()
    report = {
        "id": stable_id("evalrep", "calibration", project_id or "global", now),  # noqa: F821 (bound)
        "kind": "calibration", "scope": project_id or "global",
        "persona_id": None, "period_start": None, "period_end": None,
        "predictions": {"n": len(outcomes), "mean_brier": mean_brier,
                        "hit_rate": round(len(hits) / len(outcomes), 3) if outcomes else None,
                        "reliability": _reliability(outcomes)},
        "hypotheses": {"decisive": len(hyps), "hit_rate": round(hyp_hit, 3) if hyp_hit is not None else None},
        "green": bool(outcomes) and mean_brier is not None and mean_brier <= GOOD_BRIER,
        "created_at": now,
    }
    store.insert_eval_report(report)
    store.commit()
    return report


def calibration_trend(project_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Calibration quality OVER TIME: the persisted report series (oldest → newest),
    the Brier delta from first to last, and whether the loop is improving — the
    first-class metric the ticket asks for."""
    store = store or Store()
    scope = project_id or "global"
    series = sorted((r for r in store.list_eval_reports()
                     if r.get("kind") == "calibration" and r.get("scope") == scope),
                    key=lambda r: r["created_at"])
    points = [{"at": r["created_at"], "mean_brier": (r.get("predictions") or {}).get("mean_brier"),
               "hit_rate": (r.get("predictions") or {}).get("hit_rate"),
               "n": (r.get("predictions") or {}).get("n", 0), "green": r.get("green")}
              for r in series]
    briers = [p["mean_brier"] for p in points if p["mean_brier"] is not None]
    delta = round(briers[-1] - briers[0], 4) if len(briers) >= 2 else None
    return {"scope": scope, "points": points, "brier_delta": delta,
            "improving": (delta is not None and delta < 0)}


def brief_calibration(project_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Gather the MISSES — refuted hypothesis bets and high-error scored predictions,
    each with its evidence trail — so the host authors corrections: persona patches
    (update_persona) where a trait drove the miss, new grounding (ingest_corpus +
    record_grounding) where reality IS the new evidence. Then record_calibration_round
    stamps the round; subsequent calibration_report/trend show whether it worked."""
    store = store or Store()
    if project_id:
        _require_research_project(store, project_id)  # noqa: F821 (bound)
    misses = [{"kind": "prediction", "outcome_id": o["id"], "action": o.get("action", ""),
               "persona_id": o.get("persona_id", ""), "predicted": o["likelihood"],
               "observed": o["observed"], "brier": o["brier"],
               "prediction_ref": o.get("prediction_ref"), "source": o.get("source")}
              for o in store.list_prediction_outcomes(project_id)
              if o.get("brier", 0) > HIGH_ERROR_BRIER]
    misses += [{"kind": "hypothesis", "hypothesis_id": h["id"], "text": h.get("text", ""),
                "predicted": h.get("prediction"), "observed": (h.get("result") or {}).get("observed_value"),
                "source": (h.get("result") or {}).get("source")}
               for h in store.list_hypotheses(project_id) if h.get("status") == "refuted"]
    return {
        "schema": "calibration", "scope": project_id or "global",
        "misses": misses, "trend": calibration_trend(project_id, store=store),
        "instructions": (
            "Author the corrections YOURSELF — the server never writes text. For each miss decide "
            "WHY the simulation diverged: a persona trait too eager/timid (patch it via "
            "update_persona with the miss as `reason`), or missing real signal (ingest the observed "
            "reality as a corpus and record_grounding it onto the persona with provenance). Do NOT "
            "overfit a single data point — correct patterns, not noise. Then "
            "record_calibration_round(corrections=[{persona_id, text, refs?}], note) to stamp the "
            "round; the next calibration_report/calibration_trend show whether subsequent "
            "predictions actually improved."),
    }


def record_calibration_round(corrections: list[dict[str, Any]], note: str = "",
                             project_id: str | None = None,
                             store: Store | None = None) -> dict[str, Any]:
    """Stamp one correction round (what was changed, on which personas, why) into the
    eval_reports series and snapshot a fresh calibration report — the before/after
    marker that makes 'corrections measurably improve predictions' checkable."""
    store = store or Store()
    if not corrections:
        raise ValueError("corrections is required: [{persona_id, text, refs?}] — an empty round "
                         "records nothing worth trending")
    cleaned = []
    for i, c in enumerate(corrections):
        pid, text = str(c.get("persona_id") or ""), str(c.get("text") or "").strip()
        if not pid or not text:
            raise ValueError(f"corrections[{i}] needs persona_id + text (what was corrected and why)")
        if not store.get_persona(pid):
            raise KeyError(f"Unknown persona in corrections[{i}]: {pid}")
        cleaned.append({"persona_id": pid, "text": text,
                        "refs": [_A.validate_ref(r) for r in (c.get("refs") or [])]})
    now = utc_now_iso()
    record = {"id": stable_id("evalrep", "calibration_round", project_id or "global", now),  # noqa: F821 (bound)
              "kind": "calibration_round", "scope": project_id or "global",
              "persona_id": None, "period_start": None, "period_end": None, "green": None,
              "corrections": cleaned, "note": str(note or ""), "created_at": now}
    store.insert_eval_report(record)
    store.commit()
    report = calibration_report(project_id, store=store)
    emit_lifecycle_event("calibration.round_recorded", {"scope": project_id or "global",  # noqa: F821 (bound)
                                                        "corrections": len(cleaned),
                                                        "mean_brier": (report.get("predictions") or {}).get("mean_brier")},
                         store)
    return {"round": record, "report": report}
