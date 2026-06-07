"""Syntheses (study arcs) + meta-report.

Split out of the original persona_council/services.py (behavior-preserving).
Cross-module function references are bound at import time by services/__init__.py."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

from ..config import (
    ROOT, utc_now_iso, content_language, ensure_content_language, language_instruction,
    critic_threshold, critic_sample_k,
)
from ._authoring import MARKDOWN_CONTRACT, PRIMITIVES_CONTRACT
from .. import artifacts as _A
from ..models import (
    CalendarEvent,
    CouncilSession,
    DailySummary,
    Evidence,
    ExperienceEvent,
    MetaReport,
    OpenQuestion,
    PainPointObservation,
    Persona,
    PrototypeSession,
    Reflection,
    ResearchProject,
    SimulationResult,
    Synthesis,
)
from ..storage import Store
from ..taxonomy import GENERIC_TOOLS, normalized_tool_ids, normalized_tools
from .. import memory as memory_mod
from .. import evaluation as evaluation_mod
from ..llm_simulation import (
    build_cohort_critic_prompt,
    build_consolidation_prompt,
    build_meta_outline_prompt,
    build_meta_section_prompt,
    validate_meta_outline_payload,
    validate_meta_section_payload,
    build_digest_prompt,
    build_eval_critic_prompt,
    build_evidence_check_prompt,
    build_persona_revision_prompt,
    build_plan_prompt,
    build_profile_prompt,
    build_synthesis_prompt,
    validate_activity_payload,
    validate_cohort_critic_payload,
    validate_digest_payload,
    validate_eval_critic_payload,
    validate_evidence_check_payload,
    validate_memory_deltas_payload,
    validate_persona_revision_payload,
    validate_plan_payload,
    validate_profile_payload,
    validate_synthesis_payload,
)


from ._common import *  # noqa: F401,F403  (shared helpers + constants)



def _council_brief_row(store: Store, cid: str) -> dict[str, Any]:
    c = store.get_council_session(cid)
    if not c:
        return {"council_id": cid, "missing": True}
    # Per-persona material so the host can author the `voices` layer (who/why) — from the statements.
    turns = [{"persona_id": st.get("persona_id"), "stance": (st.get("stance") or {}).get("label"),
              "content": st.get("text")}
             for st in _A.council_statements(c)]
    votes = [{"persona_id": v.get("persona_id"), "speaker": v.get("speaker"),
              "vote": v.get("vote"), "reason": v.get("reason")}
             for v in c.get("votes", [])]
    return {
        "council_id": cid, "prompt": c.get("prompt"), "created_at": c.get("created_at"),
        "exec_summary": c.get("exec_summary") or c.get("summary"),
        "vote_tally": {v: sum(1 for x in c.get("votes", []) if x.get("vote") == v)
                       for v in ["SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]},
        "turns": turns, "votes": votes,
        "proposal": c.get("proposal"),
    }



def _synthesis_provenance(store: Store, council_ids: list[str], topic: str | None) -> dict[str, Any]:
    """Assemble inline-citable provenance for a synthesis: attached real evidence and
    relevant recalled facts (each with a stable id) for every persona in the chain.
    This is what lets generated conclusions cite their source (recall hits + evidence)."""
    persona_ids: list[str] = []
    for cid in council_ids:
        c = store.get_council_session(cid) or {}
        for pid in c.get("persona_ids", []) or []:
            if pid not in persona_ids:
                persona_ids.append(pid)
    evidence: list[dict[str, Any]] = []
    recall: list[dict[str, Any]] = []
    for pid in persona_ids:
        persona = store.get_persona(pid) or {}
        name = persona.get("display_name", pid)
        for ev in store.list_evidence(pid)[:6]:
            evidence.append({"ref": ev["id"], "persona": name, "kind": "evidence",
                             "source_type": ev.get("source_type"),
                             "quote": str(ev.get("content_or_path", ""))[:400]})
        if topic and str(topic).strip():
            try:
                hits = memory_mod.recall(store, pid, topic, k=2).get("hits", [])
            except Exception:
                hits = []
            for h in hits:
                recall.append({"ref": h.get("id", ""), "persona": name, "kind": "recall",
                               "quote": str(h.get("text") or h.get("fact") or "")[:400]})
    return {"evidence": evidence[:30], "recall": recall[:30]}



def brief_synthesis(council_ids: list[str], title: str | None = None, start_input: str | None = None,
                    goal: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """GATHER an ordered chain of councils so the host can author a synthesis."""
    store = store or Store()
    chain = [_council_brief_row(store, cid) for cid in council_ids]
    frame = {
        "title": title, "goal": goal, "start_input": start_input,
        "councils_in_order": chain,
        "provenance": _synthesis_provenance(store, council_ids, goal or start_input or title),
    }
    return {"schema": "synthesis", "council_ids": council_ids,
            "instructions": build_synthesis_prompt(frame) + MARKDOWN_CONTRACT + PRIMITIVES_CONTRACT, "frame": frame}



def record_synthesis(title: str, start_input: str, council_ids: list[str] | None = None,
                     payload: dict[str, Any] | None = None,
                     goal: str = "", synthesis_id: str | None = None, key: str | None = None,
                     created_at: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Persist a host-authored synthesis. A synthesis is a FIRST-CLASS answer/report node and is
    DECOUPLED from councils: `council_ids` is an OPTIONAL list of referenced evidence and may be
    empty — e.g. an affinity-clustering synthesis over observations, a synthesis over other
    syntheses, or a standalone analysis. Councils are independent nodes a synthesis MAY cite (via
    `references`/`citations`/`voices`); they are not sub-parts of it.

    For the iterative driver loop: pass the SAME synthesis_id each round to update
    one growing study arc in place (chain + interim learnings + next_council_question).
    """
    store = store or Store()
    council_ids = list(council_ids or [])
    if key and not synthesis_id:        # deterministic id → idempotent resumable upsert (HX6)
        synthesis_id = stable_id("synthesis", key)
    data = validate_synthesis_payload(payload or {})
    _pl = payload or {}
    # Primitives-only authoring (spec/unified-artifact-schema): the host authors findings/statements/
    # prompts directly — the ONE representation. No legacy list/voice input shapes.
    findings = [_A.validate_finding(f) for f in (_pl.get("findings") or [])]
    statements = [_A.validate_statement(s) for s in (_pl.get("statements") or [])]
    prompts = [_A.validate_prompt(p) for p in (_pl.get("prompts") or [])]
    # Stable part ids so findings/voices are addressable + deep-linkable (spec/artifact-cross-references).
    _A.assign_part_ids(findings, "f")
    _A.assign_part_ids(statements, "st")
    _A.assign_part_ids(prompts, "p")
    existing = store.get_synthesis(synthesis_id) if synthesis_id else None
    # honor an explicit/keyed synthesis_id even on first create (so a keyed run is idempotent)
    sid = (existing or {}).get("id") or synthesis_id or stable_id("synthesis", title or "synthesis", utc_now_iso())
    created = (existing or {}).get("created_at") or created_at or utc_now_iso()
    prev = existing or {}
    rec = Synthesis(
        id=sid, title=title, start_input=start_input, council_ids=council_ids,
        arc_narrative=data["arc_narrative"], gesamtbild=data["gesamtbild"],
        positionierung=data["positionierung"], references=data["references"],
        created_at=created,
        goal=goal or prev.get("goal", ""),
        status=data["status"], next_council_question=data["next_council_question"],
        stop_reason=data["stop_reason"], iterations=len(council_ids),
        citations=data["citations"],
        # The findings/statements/prompts primitives; on an update that omits one, keep the prior value
        # so re-recording an arc in place doesn't wipe it.
        statements=statements or prev.get("statements", []),
        findings=findings or prev.get("findings", []),
        prompts=prompts or prev.get("prompts", []),
    ).to_dict()
    rec["updated_at"] = utc_now_iso()
    store.upsert_synthesis(rec)
    # Soft honesty signal (GAP-3): the synthesis IS the answer — flag (don't block) when it persists with
    # no prose AND no findings AND no voices, so the host notices a hollow answer node.
    out = dict(rec)
    has_substance = any([rec["gesamtbild"].strip(), rec["positionierung"].strip(), rec["arc_narrative"].strip(),
                         rec["findings"], rec["statements"]])
    if not has_substance:
        out["warnings"] = ["SYNTHESIS_THIN: this synthesis persisted with no prose (gesamtbild/"
                           "positionierung) and no structured blocks (clusters/key_problems/ranking/"
                           "shortlist) — the answer node is near-empty. The synthesis IS the answer: "
                           "author it rich here, don't leave the substance only in councils/notes."]
    return out



def get_synthesis(synthesis_id: str, store: Store | None = None) -> dict[str, Any]:
    store = store or Store()
    syn = store.get_synthesis(synthesis_id)
    if not syn:
        raise KeyError(f"Unknown synthesis: {synthesis_id}")
    return syn



def list_syntheses(store: Store | None = None) -> list[dict[str, Any]]:
    store = store or Store()
    return store.list_syntheses()


# Stakeholder-report headers follow the CONTENT language (de|en) so a German
# project gets a German report and an English project an English one.



_SYNTHESIS_EXPORT_LABELS = {
    "de": {
        "report_title": "Synthese-Report",
        "arc_line": "Studien-Bogen aus {n} Councils · Status: {status} · erzeugt {date}.",
        "goal": "Ziel", "next_council": "Vorgeschlagener nächster Council (self-contained)",
        "stop_reason": "Abschlussgrund", "start": "Ausgangspunkt", "arc": "Bogen / Verlauf",
        "big_picture": "Gesamtbild", "recommendations": "Handlungsempfehlungen",
        "effort": "Aufwand", "value": "Nutzen", "positioning": "Positionierung",
        "pain_solvers": "Validierte Pain-Solver / Delight-Engines", "segments": "Segmente",
        "key_problems": "Kernprobleme", "clusters": "Affinity-Cluster",
        "ranking": "Ranking", "shortlist": "Shortlist",
        "voices": "Stimmen (pro Persona)", "relevance": "Relevanz", "argument": "Argument",
        "shift": "Wandel", "open_questions": "Offene Fragen / Nächste Studie",
        "sources": "Quellen (Councils in Reihenfolge)",
    },
    "en": {
        "report_title": "Synthesis report",
        "arc_line": "Study arc across {n} councils · status: {status} · generated {date}.",
        "goal": "Goal", "next_council": "Proposed next council (self-contained)",
        "stop_reason": "Stop reason", "start": "Starting point", "arc": "Arc / trajectory",
        "big_picture": "Overall picture", "recommendations": "Recommendations",
        "effort": "Effort", "value": "Value", "positioning": "Positioning",
        "pain_solvers": "Validated pain-solvers / delight-engines", "segments": "Segments",
        "key_problems": "Key problems", "clusters": "Affinity clusters",
        "ranking": "Ranking", "shortlist": "Shortlist",
        "voices": "Voices (per persona)", "relevance": "Relevance", "argument": "Argument",
        "shift": "Shift", "open_questions": "Open questions / Next study",
        "sources": "Sources (councils in order)",
    },
}



def export_synthesis(synthesis_id: str, format: str = "md", store: Store | None = None) -> str:
    """Render the synthesis as a stakeholder report (Markdown), referencing each council."""
    store = store or Store()
    syn = get_synthesis(synthesis_id, store)
    if format == "json":
        return json.dumps(syn, indent=2, ensure_ascii=False)
    role = {r["council_id"]: r.get("role", "") for r in syn.get("references", [])}
    status = syn.get("status", "done")
    L = _SYNTHESIS_EXPORT_LABELS[content_language()]
    lines = [f"# {L['report_title']}: {syn['title']}", "",
             f"*{L['arc_line'].format(n=len(syn['council_ids']), status=status, date=syn['created_at'])}*", ""]
    if syn.get("goal"):
        lines += [f"## {L['goal']}", syn["goal"], ""]
    if status == "in_progress" and syn.get("next_council_question"):
        lines += [f"## {L['next_council']}", syn["next_council_question"], ""]
    if status == "done" and syn.get("stop_reason"):
        lines += [f"## {L['stop_reason']}", syn["stop_reason"], ""]
    lines += [f"## {L['start']}", syn.get("start_input", ""), "",
             f"## {L['arc']}", syn.get("arc_narrative", ""), "",
             f"## {L['big_picture']}", syn.get("gesamtbild", ""), "",
             f"## {L['recommendations']}"]
    # Report blocks are reconstructed from the stored findings/statements (storage is primitives-only).
    _fs = _A.synthesis_findings(syn)
    def _fmeta(kind, key):  # collect a meta value across findings of a kind
        return [( (f.get("meta") or {}).get(key, ""), f.get("text", "")) for f in _fs if f.get("kind") == kind]
    recs = _A.synthesis_recommendations(syn)
    lines += [f"{i}. " + (f"{txt} _({L['effort']} {a}/5 · {L['value']} {n}/5)_" if a and n else txt)
              for i, (txt, a, n) in enumerate(recs, 1)] or ["—"]
    lines += ["", f"## {L['positioning']}", syn.get("positionierung", "")]
    # Structured convergence blocks (GAP-3): render when present so the methodology's converge output
    # (key problems / affinity clusters / down-select ranking + shortlist) survives into the report.
    if _A.finding_texts(syn, "key_problem"):
        lines += ["", f"## {L['key_problems']}"] + [f"- {x}" for x in _A.finding_texts(syn, "key_problem")]
    if _fmeta("cluster", "detail"):
        lines += ["", f"## {L['clusters']}"] + [f"- **{label}** — {insight}" for insight, label in _fmeta("cluster", "detail")]
    if _fmeta("ranking", "detail"):
        lines += ["", f"## {L['ranking']}"] + [f"- **{ref}**: {rat}" for rat, ref in _fmeta("ranking", "detail")]
    if _A.finding_texts(syn, "shortlist"):
        lines += ["", f"## {L['shortlist']}"] + [f"- {x}" for x in _A.finding_texts(syn, "shortlist")]
    lines += ["", f"## {L['pain_solvers']}"]
    lines += [f"- {x}" for x in _A.finding_texts(syn, "pain_solver")] or ["—"]
    lines += ["", f"## {L['segments']}"]
    lines += [f"- **{seg}**: {why}" for why, seg in _fmeta("segment", "detail")] or ["—"]
    voices = _A.synthesis_statements(syn)
    if voices:
        lines += ["", f"## {L['voices']}"]
        for v in sorted(voices, key=lambda x: -((x.get("stance") or {}).get("value", 0))):
            name = store.get_persona(v.get("persona_id", "")) or {}
            head = f"- **{name.get('name') or v.get('persona_id','')}**"
            if v.get("relevance"):
                head += f" — {L['relevance']}: {v['relevance']}"
            lines.append(head)
            if v.get("text"):
                lines.append(f"  - {L['argument']}: {v['text']}")
            sh = v.get("shift")
            if sh and (sh.get("trigger") or sh.get("to")):
                lines.append(f"  - {L['shift']}: {sh.get('from','')}→{sh.get('to','')} — {sh.get('trigger','')}")
            for e in v.get("refs", []):
                if e.get("kind") == "council" and e.get("quote"):
                    lines.append(f"  - „{e.get('quote','')}“ [{e.get('id','')}]")
    lines += ["", f"## {L['open_questions']}"]
    lines += [f"- {x}" for x in _A.finding_texts(syn, "open_question")] or ["—"]
    cites = syn.get("citations", [])
    if cites:
        cite_label = "Belege (Evidenz / Recall)" if content_language() == "de" else "Citations (evidence / recall)"
        lines += ["", f"## {cite_label}"]
        for c in cites:
            q = f" — „{c['quote']}“" if c.get("quote") else ""
            lines.append(f"- [{c.get('kind','')}:{c.get('ref','')}]{q}")
    lines += ["", f"## {L['sources']}"]
    for cid in syn["council_ids"]:
        c = store.get_council_session(cid)
        prompt = (c.get("prompt") if c else cid)
        lines.append(f"- `{cid}` — {role.get(cid, '')}".rstrip(" —") + (f"  ·  {prompt}" if prompt else ""))
    return "\n".join(lines) + "\n"


# ===================================================================== #
# Council write-back + reads (MCP parity for host-authored councils).    #
# Lets the run-council / synthesize skills persist via MCP instead of    #
# writing the store directly.                                            #
# ===================================================================== #



def delete_synthesis(synthesis_id: str, store: Store | None = None) -> dict[str, Any]:
    """Delete a synthesis (study) and detach it from any project graphs that contain it."""
    store = store or Store()
    detached = []
    for p in store.list_research_projects():
        if synthesis_id in (p.get("study_ids") or []):
            p["study_ids"].remove(synthesis_id)
            p.get("study_tags", {}).pop(synthesis_id, None)
            p["updated_at"] = utc_now_iso()
            store.upsert_research_project(p)
            detached.append(p["id"])
    return {"deleted": store.delete_synthesis(synthesis_id), "detached_from_projects": detached}



def _study_compact(store: Store, study_id: str, tags: list[str]) -> dict[str, Any]:
    syn = store.get_synthesis(study_id) or {}
    return {"study_id": study_id, "title": syn.get("title", study_id), "goal": syn.get("goal", ""),
            "theme_tags": tags, "gesamtbild": syn.get("gesamtbild", ""),
            "positionierung": syn.get("positionierung", ""),
            "top_recommendations": [txt for txt, _a, _n in _A.synthesis_recommendations(syn)[:3]],
            "created_at": syn.get("created_at", "")}



def _study_full(store: Store, study_id: str) -> dict[str, Any]:
    syn = store.get_synthesis(study_id) or {}
    councils = []
    for cid in syn.get("council_ids", []) or []:
        c = store.get_council_session(cid) or {}
        councils.append({"council_id": cid, "prompt": c.get("prompt", ""), "exec_summary": c.get("exec_summary", "")})
    return {"study_id": study_id, "title": syn.get("title", study_id), "goal": syn.get("goal", ""),
            "arc_narrative": syn.get("arc_narrative", ""), "gesamtbild": syn.get("gesamtbild", ""),
            "positionierung": syn.get("positionierung", ""), "pain_solvers": _A.finding_texts(syn, "pain_solver"),
            "handlungsempfehlungen": [{"text": t, "aufwand": a, "nutzen": n} for t, a, n in _A.synthesis_recommendations(syn)],
            "voices": [{"persona_id": v.get("persona_id"),
                        "sentiment": _A._STANCE_SENTIMENT.get((v.get("stance") or {}).get("value"), "neutral"),
                        "key_argument": v.get("text")} for v in _A.synthesis_statements(syn)],
            "offene_fragen": _A.finding_texts(syn, "open_question"), "councils": councils}



def brief_meta_report(project_id: str, store: Store | None = None) -> dict[str, Any]:
    """GATHER the whole project graph + each study's compact content so the host can
    author the meta-report OUTLINE (then author sections)."""
    store = store or Store()
    graph = get_project_graph(project_id, store=store)
    tags = _require_research_project(store, project_id).get("study_tags", {})
    frame = {
        "project": graph["project"], "build_order": graph["build_order"],
        "edges": graph["edges"], "open_questions": [o for o in graph["open_questions"] if o.get("status") == "open"],
        "studies": [_study_compact(store, sid, tags.get(sid, [])) for sid in graph["build_order"]],
    }
    return {"project_id": graph["project"]["id"], "schema": "meta_outline",
            "study_ids": graph["build_order"], "instructions": build_meta_outline_prompt(frame) + MARKDOWN_CONTRACT, "frame": frame}



def record_meta_outline(project_id: str, outline: dict[str, Any], store: Store | None = None) -> dict[str, Any]:
    """Persist the host-authored outline as a new MetaReport (sections to be authored next)."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    data = validate_meta_outline_payload(outline, study_ids=project["study_ids"])
    now = utc_now_iso()
    report = MetaReport(
        id=stable_id("metareport", project["id"], now), project_id=project["id"],
        title=f"{project['title']} — Meta-Report", outline=data["sections"], sections=[],
        build_order_narrative=data["build_order_narrative"],
        graph_snapshot=get_project_graph(project["id"], store=store), created_at=now,
    ).to_dict()
    store.upsert_meta_report(report)
    return report



def _latest_meta_report(store: Store, project_id: str, report_id: str | None) -> dict[str, Any]:
    if report_id:
        r = store.get_meta_report(report_id)
        if not r:
            raise KeyError(f"Unknown meta-report: {report_id}")
        return r
    reports = store.list_meta_reports(project_id)
    if not reports:
        raise KeyError(f"No meta-report for project {project_id} — run brief_meta_report -> record_meta_outline first.")
    return reports[0]



def brief_meta_section(project_id: str, section_id: str, report_id: str | None = None,
                       store: Store | None = None) -> dict[str, Any]:
    """GATHER the full content of a section's source studies (+ their councils) so the
    host can author that section grounded with citations."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    report = _latest_meta_report(store, project["id"], report_id)
    section = next((s for s in report["outline"] if s["id"] == section_id), None)
    if not section:
        raise KeyError(f"Unknown section {section_id} in meta-report {report['id']}")
    frame = {"heading": section["heading"], "intent": section["intent"], "theme_tags": section["theme_tags"],
             "studies": [_study_full(store, sid) for sid in section["source_study_ids"]]}
    return {"project_id": project["id"], "report_id": report["id"], "section_id": section_id,
            "schema": "meta_section", "instructions": build_meta_section_prompt(frame) + MARKDOWN_CONTRACT, "frame": frame}



def record_meta_section(project_id: str, section_id: str, content: dict[str, Any],
                        report_id: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Persist one authored section (markdown + citations) into the meta-report."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    report = _latest_meta_report(store, project["id"], report_id)
    if not any(s["id"] == section_id for s in report["outline"]):
        raise KeyError(f"Unknown section {section_id} in meta-report {report['id']}")
    data = validate_meta_section_payload(content)
    entry = {"section_id": section_id, "markdown": data["markdown"], "citations": data["citations"]}
    report["sections"] = [s for s in report.get("sections", []) if s.get("section_id") != section_id] + [entry]
    store.upsert_meta_report(report)
    return report



def export_meta_report(project_id: str, report_id: str | None = None, format: str = "md",
                       store: Store | None = None) -> str:
    """Assemble the meta-report (outline + authored sections) into a stakeholder document."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    report = _latest_meta_report(store, project["id"], report_id)
    if format == "json":
        return json.dumps(report, indent=2, ensure_ascii=False)
    de = content_language() == "de"
    authored = {s["section_id"]: s for s in report.get("sections", [])}
    lines = [f"# {report['title']}", "",
             f"*{'Meta-Synthese' if de else 'Meta-synthesis'} · {len(report['outline'])} "
             f"{'Abschnitte' if de else 'sections'} · {len(project['study_ids'])} "
             f"{'Studien' if de else 'studies'} · {report['created_at']}*", ""]
    if report.get("build_order_narrative"):
        lines += [f"## {'Wie dieses Verständnis entstand' if de else 'How this understanding was built'}",
                  report["build_order_narrative"], ""]
    titles = {sid: (store.get_synthesis(sid) or {}).get("title", sid) for sid in project["study_ids"]}
    for sec in report["outline"]:
        lines += [f"## {sec['heading']}"]
        body = authored.get(sec["id"])
        if body and body.get("markdown"):
            lines += [body["markdown"]]
            if body.get("citations"):
                lines += ["", f"*{'Belege' if de else 'Citations'}:*"]
                for c in body["citations"]:
                    src = titles.get(c["study_id"], c["study_id"])
                    cc = f" / {c['council_id']}" if c.get("council_id") else ""
                    q = f" — „{c['quote']}“" if c.get("quote") else ""
                    lines.append(f"- {src}{cc}{q}")
        else:
            lines += [f"_({'Abschnitt noch nicht verfasst' if de else 'section not yet authored'})_"]
        if sec.get("source_study_ids"):
            lines += ["", "_" + ("Quellen-Studien" if de else "Source studies") + ": " +
                      ", ".join(titles.get(x, x) for x in sec["source_study_ids"]) + "_"]
        lines += [""]
    return "\n".join(lines) + "\n"
