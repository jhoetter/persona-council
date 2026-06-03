"""Simulation quality & evaluation harness (spec §12.5, §12.7).

Deterministic critics that measure whether a simulation is "top": uniformity,
phrasing repetition, continuity (loops close, projects move), consistency
(duplicates/contradictions), and anti-steering drift. Runs without authoring —
this is how we *prove* quality and catch regressions over long horizons.

A richer LLM-critic pass can be layered on later via brief_*/record_* tools; the
deterministic core below already yields a green/red verdict.
"""
from __future__ import annotations

import re
import statistics
from collections import Counter
from typing import Any

from .config import utc_now_iso
from .memory import mem_id, normalize_name
from .storage import Store

_WORD = re.compile(r"[0-9a-zäöüß]+", re.IGNORECASE)


def _shingles(text: str, n: int = 6) -> list[str]:
    toks = _WORD.findall((text or "").lower())
    return [" ".join(toks[i:i + n]) for i in range(0, max(0, len(toks) - n + 1))]


def _verdict(reds: int, warns: int) -> str:
    if reds:
        return "red"
    if warns:
        return "warn"
    return "green"


def _check_time_uniformity(store: Store, personas: list[dict]) -> dict[str, Any]:
    start_minutes, end_minutes, ends = [], [], []
    for p in personas:
        cals = store.list_calendar_events(p["id"])
        by_day: dict[str, list[dict]] = {}
        for c in cals:
            by_day.setdefault(c["start"][:10], []).append(c)
        for _day, evs in by_day.items():
            evs.sort(key=lambda e: e["start"])
            sm = int(evs[0]["start"][11:13]) * 60 + int(evs[0]["start"][14:16])
            em = int(evs[-1]["end"][11:13]) * 60 + int(evs[-1]["end"][14:16])
            start_minutes.append(sm)
            end_minutes.append(em)
            ends.append(evs[-1]["end"][11:16])
    if len(start_minutes) < 3:
        return {"name": "time_uniformity", "status": "na", "detail": "zu wenig Tage", "metrics": {}}
    start_std = round(statistics.pstdev(start_minutes), 1)
    end_std = round(statistics.pstdev(end_minutes), 1)
    distinct_ends = len(set(ends)) / len(ends)
    status = "green"
    if start_std < 20 or end_std < 20:
        status = "red"
    elif distinct_ends < 0.5:
        status = "warn"
    return {"name": "time_uniformity", "status": status,
            "detail": f"start_std={start_std}min end_std={end_std}min distinct_end_ratio={round(distinct_ends,2)}",
            "metrics": {"start_std_min": start_std, "end_std_min": end_std, "distinct_end_ratio": round(distinct_ends, 2)}}


def _check_phrasing_repetition(store: Store, personas: list[dict]) -> dict[str, Any]:
    counter: Counter = Counter()
    total = 0
    for p in personas:
        for e in store.list_experience_events(p["id"]):
            for field in ("persona_thought", "what_happened"):
                for sh in _shingles(e.get(field, "")):
                    counter[sh] += 1
                    total += 1
    if total < 50:
        return {"name": "phrasing_repetition", "status": "na", "detail": "zu wenig Text", "metrics": {}}
    repeated = sum(c for c in counter.values() if c > 1) - sum(1 for c in counter.values() if c > 1)
    ratio = repeated / total if total else 0.0
    top = [{"phrase": s, "count": c} for s, c in counter.most_common(5) if c > 1]
    status = "red" if ratio > 0.08 else "warn" if ratio > 0.03 else "green"
    return {"name": "phrasing_repetition", "status": status,
            "detail": f"dupe_shingle_ratio={round(ratio,3)}", "metrics": {"ratio": round(ratio, 3), "top_repeated": top}}


def _check_block_pattern_uniformity(store: Store, personas: list[dict]) -> dict[str, Any]:
    seqs: Counter = Counter()
    n = 0
    for p in personas:
        by_day: dict[str, list[tuple[str, str]]] = {}
        for e in store.list_experience_events(p["id"]):
            by_day.setdefault(e["timestamp"][:10], []).append((e["timestamp"], e["event_type"]))
        for _day, evs in by_day.items():
            evs.sort()
            seqs["|".join(t for _, t in evs)] += 1
            n += 1
    if n < 3:
        return {"name": "block_pattern_uniformity", "status": "na", "detail": "zu wenig Tage", "metrics": {}}
    most = seqs.most_common(1)[0][1]
    share = most / n
    status = "red" if share > 0.5 else "warn" if share > 0.3 else "green"
    return {"name": "block_pattern_uniformity", "status": status,
            "detail": f"max_identical_event_type_sequence_share={round(share,2)}",
            "metrics": {"share": round(share, 2), "distinct_sequences": len(seqs), "days": n}}


def _check_continuity(store: Store, personas: list[dict]) -> dict[str, Any]:
    opened = resolved = 0
    summaries_days = completed_days = all_open_days = 0
    for p in personas:
        for t in store.list_threads(p["id"]):
            opened += 1
            if t["status"] == "resolved":
                resolved += 1
        for s in store.list_daily_summaries(p["id"]):
            summaries_days += 1
            if s.get("completed"):
                completed_days += 1
            if s.get("open_loops") and not s.get("completed"):
                all_open_days += 1
    if summaries_days < 3:
        return {"name": "continuity", "status": "na", "detail": "zu wenig Tage", "metrics": {}}
    completion_day_ratio = completed_days / summaries_days
    everything_open_ratio = all_open_days / summaries_days
    status = "green"
    if completion_day_ratio < 0.2 or everything_open_ratio > 0.7:
        status = "warn"
    if completion_day_ratio == 0.0:
        status = "red"
    return {"name": "continuity", "status": status,
            "detail": f"days_with_completion={round(completion_day_ratio,2)} all_open_days={round(everything_open_ratio,2)} threads={resolved}/{opened}",
            "metrics": {"completion_day_ratio": round(completion_day_ratio, 2),
                        "everything_open_ratio": round(everything_open_ratio, 2),
                        "threads_opened": opened, "threads_resolved": resolved}}


def _check_project_movement(store: Store, personas: list[dict]) -> dict[str, Any]:
    projects = moved = closed = 0
    for p in personas:
        for ent in store.list_entities(p["id"], "project"):
            projects += 1
            facts = store.list_entity_facts(ent["id"])
            statuses = {f.get("status") for f in facts if f.get("status")}
            if len(facts) >= 2 or len(statuses) >= 2:
                moved += 1
            if (ent.get("status") or "").lower() in {"abgeschlossen", "verloren", "abgebrochen", "done", "lost"}:
                closed += 1
    if projects == 0:
        return {"name": "project_movement", "status": "na", "detail": "noch keine Projekt-Entitäten (Konsolidierung ausstehend)", "metrics": {}}
    moved_ratio = moved / projects
    status = "green" if moved_ratio >= 0.4 else "warn"
    return {"name": "project_movement", "status": status,
            "detail": f"projects={projects} moved={moved} closed={closed}",
            "metrics": {"projects": projects, "moved": moved, "closed": closed, "moved_ratio": round(moved_ratio, 2)}}


def _check_consistency(store: Store, personas: list[dict]) -> dict[str, Any]:
    dup_entities = 0
    contradictions = 0
    examples: list[str] = []
    for p in personas:
        seen: dict[str, str] = {}
        for ent in store.list_entities(p["id"]):
            key = f"{ent['kind']}:{normalize_name(ent['name'])}"
            if key in seen:
                dup_entities += 1
                examples.append(f"Dublette: {ent['name']} ({p['display_name']})")
            seen[key] = ent["id"]
            valid_status = [f.get("status") for f in store.list_entity_facts(ent["id"], valid_only=True) if f.get("status")]
            if len({normalize_name(s) for s in valid_status}) > 1:
                contradictions += 1
                examples.append(f"Widerspruch: {ent['name']} hat gültige Status {set(valid_status)}")
    status = "green"
    if dup_entities or contradictions:
        status = "warn" if (dup_entities + contradictions) <= 2 else "red"
    return {"name": "consistency", "status": status,
            "detail": f"duplicate_entities={dup_entities} contradictions={contradictions}",
            "metrics": {"duplicate_entities": dup_entities, "contradictions": contradictions, "examples": examples[:8]}}


# NOTE: anti-steering / believability is a SEMANTIC judgment and cannot be done
# both generically (industry-agnostic, no hardcoded marker list) AND reliably with
# deterministic lexical checks — those flood with ordinary work vocabulary. It is
# therefore the LLM-critic's responsibility (spec §12.5, feature #2), not this
# deterministic harness, which covers structural integrity only.

CHECKS = [
    _check_time_uniformity,
    _check_phrasing_repetition,
    _check_block_pattern_uniformity,
    _check_continuity,
    _check_project_movement,
    _check_consistency,
]


def evaluate_simulation(persona_id: str | None = None, period: dict[str, str] | None = None,
                        store: Store | None = None, persist: bool = True) -> dict[str, Any]:
    store = store or Store()
    personas = [store.get_persona(persona_id)] if persona_id else store.list_personas()
    personas = [p for p in personas if p]
    if not personas:
        raise KeyError("No personas to evaluate.")
    results = [check(store, personas) for check in CHECKS]
    reds = sum(1 for r in results if r["status"] == "red")
    warns = sum(1 for r in results if r["status"] == "warn")
    green = reds == 0
    report = {
        "id": mem_id("eval", persona_id or "all", utc_now_iso()),
        "persona_id": persona_id,
        "period_start": (period or {}).get("start"),
        "period_end": (period or {}).get("end"),
        "green": green,
        "verdict": _verdict(reds, warns),
        "personas_evaluated": [p["display_name"] for p in personas],
        "summary": {"green_checks": sum(1 for r in results if r["status"] == "green"),
                    "warn": warns, "red": reds, "na": sum(1 for r in results if r["status"] == "na")},
        "checks": results,
        "created_at": utc_now_iso(),
    }
    if persist:
        store.insert_eval_report(report)
        for r in results:
            if r["status"] in {"warn", "red"}:
                store.insert_anomaly({
                    "id": mem_id("anom", persona_id or "all", r["name"], utc_now_iso()),
                    "persona_id": persona_id,
                    "kind": f"eval:{r['name']}",
                    "severity": 3 if r["status"] == "red" else 2,
                    "detail": r["detail"], "metrics": r.get("metrics", {}),
                    "created_at": utc_now_iso(),
                })
        store.commit()
    return report
