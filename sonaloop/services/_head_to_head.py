"""Head-to-Head Format (taxonomy id `head_to_head`): run a council on a DIRECT comparison of two
(or more) concrete options — two prices, two messages, two captured A/B variants — and return a
*reasoned, segmented preference* (which option, how decisively, why, and who-prefers-what) instead
of two separate yes/no runs. This is a FORMAT that Job presets compose, NOT a Job of its own.

Built ON TOP OF the artifacts/variant plumbing (services/_artifacts_service.py + brief_council):
- ARTIFACT options reuse `council_artifact_briefs` → the labelled, captured variant briefs, folded
  into each participant's context exactly like a normal artifact council.
- TEXT options (no artifact — "$29/mo" vs "$49/mo", message A vs message B) are built into the SAME
  labelled A/B comparison block so personas compare them side-by-side. Both kinds coexist.

Host-authors-all-text contract (README): the host (Claude) authors the prose verdict; this module is
the SCAFFOLD — it assembles the comparison brief, collects each persona's per-option stance + which
option they prefer, and does the DETERMINISTIC aggregation server-side (tally who preferred which
option → preference + margin, group by persona segment → segment-splits). No server-side text-LLM
call ever happens here; qualitative synthesis stays the host's job.

A recorded head-to-head IS a CouncilSession (so it reuses council persistence, the project graph, and
the inspector UI for free), carrying a `head_to_head` block — the labelled options + the deterministic
aggregate — plus a `finding` of kind `head_to_head` so the result is a stored, queryable seam that a
future calibration/analytics surface can read against real outcomes (none exists yet — clean seam).
"""
from __future__ import annotations

from typing import Any

from ..config import utc_now_iso, ensure_content_language, language_instruction
from ..storage import Store
from .. import artifacts as _artifacts

from ._common import *  # noqa: F401,F403  (stable_id, _require_research_project, list_personas, …)


def _label_for(i: int) -> str:
    """A/B/C… label by index (matches artifact auto-labelling), V<n> past Z."""
    return chr(ord("A") + i) if i < 26 else f"V{i + 1}"


def _normalize_options(project_id: str, options: list[Any], store: Store) -> list[dict[str, Any]]:
    """Turn the host's `options` into a uniform list of labelled comparison options. Each entry is either
    an ARTIFACT (an id/label of an artifact already ingested via add_artifact → reuse its captured brief)
    or a plain TEXT option (a string, or {label?, title?, text}). Labels are assigned/preserved so A/B/…
    line up across kinds; an artifact keeps its own A/B label."""
    art_briefs = {b.get("label"): b for b in council_artifact_briefs(project_id, store=store)}
    art_by_id = {b.get("id"): b for b in art_briefs.values()}
    out: list[dict[str, Any]] = []
    used = set()
    for raw_opt in options:
        brief = None
        text = ""
        title = ""
        label = None
        if isinstance(raw_opt, dict):
            # An explicit artifact reference, or an inline text option.
            ref = raw_opt.get("artifact_id") or raw_opt.get("artifact")
            if ref and (ref in art_by_id or ref in art_briefs):
                brief = art_by_id.get(ref) or art_briefs.get(ref)
            title = (raw_opt.get("title") or "").strip()
            text = (raw_opt.get("text") or raw_opt.get("option") or "").strip()
            label = (raw_opt.get("label") or "").strip() or None
        else:
            tok = str(raw_opt).strip()
            if tok in art_by_id or tok in art_briefs:      # bare artifact id/label
                brief = art_by_id.get(tok) or art_briefs.get(tok)
            else:
                text = tok
        if label is None:
            label = (brief or {}).get("label")
        if label is None or label in used:
            label = next(l for i in range(99) if (l := _label_for(i)) not in used)
        used.add(label)
        if brief is not None:
            out.append({"label": label, "kind": "artifact", "artifact_id": brief.get("id"),
                        "title": title or brief.get("title") or brief.get("url"), "brief": brief})
        else:
            out.append({"label": label, "kind": "text", "title": title or text[:60], "text": text})
    return out


def _render_options_context(options: list[dict[str, Any]]) -> str:
    """Render the options as ONE labelled comparison block the host folds into each persona's context, so
    every persona weighs the SAME options side-by-side. Artifact options carry their captured copy (via
    render_artifacts_context); text options carry their literal text — uniformly labelled OPTION A/B/…."""
    head = ("HEAD-TO-HEAD — compare the options below DIRECTLY and state which one you prefer and WHY. "
            "Do not score them in isolation; weigh A vs B (vs C…) against each other for YOUR context.")
    parts = [head]
    for o in options:
        tag = f"OPTION {o['label']}: {o.get('title') or ''}".strip().rstrip(":")
        if o["kind"] == "artifact":
            body = render_artifacts_context([o["brief"]]) or f"(artifact {o.get('artifact_id')})"
        else:
            body = o.get("text") or "(empty option)"
        parts.append(f"--- {tag} ---\n{body}")
    return "\n\n".join(parts)


def brief_head_to_head(project_id: str, prompt: str, options: list[Any],
                       persona_ids: list[str] | None = None, filters: dict[str, Any] | None = None,
                       count: int = 4, context: str | None = None,
                       store: Store | None = None) -> dict[str, Any]:
    """Gather everything to run a host-authored HEAD-TO-HEAD (X vs Y) over a research project's personas.
    `options` are the things being compared — each is an ARTIFACT (an id/label already ingested via
    add_artifact, e.g. two A/B variants) or a plain TEXT option (a string, or {label?, title?, text} for
    "$29/mo" vs "$49/mo"). They are labelled A/B/… and folded into each participant's context as ONE
    side-by-side comparison block. Without persona_ids: returns candidate personas to select from. With
    persona_ids: returns each participant's loaded context + the labelled options to author per-option
    stances and a per-persona `preference` against, then call record_head_to_head."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    opts = _normalize_options(project["id"], options or [], store)
    if len(opts) < 2:
        raise ValueError("head_to_head needs at least two options to compare (got "
                         f"{len(opts)}). Add artifacts (add_artifact) or pass plain text options.")
    options_context = _render_options_context(opts)
    language = ensure_content_language(" ".join(filter(None, [prompt, context])))
    public_options = [{k: v for k, v in o.items() if k != "brief"} for o in opts]
    label_ids = [o["label"] for o in opts]

    if not persona_ids:
        personas = list_personas(filters, store)
        candidates = [
            {"persona_id": p["id"], "display_name": p["display_name"],
             "source_description": p["source_description"], "segment": p.get("segment", {}),
             "role": p.get("role", {}), "goals": p.get("goals", []), "pain_points": p.get("pain_points", [])}
            for p in personas
        ]
        return {
            "schema": "head_to_head_selection", "language": language, "project_id": project["id"],
            "prompt": prompt, "options": public_options,
            "count": min(max(2, count), len(candidates)) if candidates else 0,
            "candidate_personas": candidates,
            "instructions": (
                "Pick a segment-DIVERSE panel so the preference can be split by segment (cover the "
                "segments the options serve and those they don't). Then call brief_head_to_head again "
                f"with persona_ids=[...]. {language_instruction(language)}"
                if candidates else "No personas exist yet. Create some first."),
        }

    context_block = "\n\n".join(filter(None, [context or "", options_context]))
    participants = []
    for pid in persona_ids:
        p = store.get_persona(pid)
        if not p:
            continue
        ctx = prepare_persona_agent_context(
            p["id"], f"Head-to-head prompt: {prompt}\nOptions:\n{context_block}", store=store)
        agent_context = f"{ctx['agent_context']}\n\n=== HEAD-TO-HEAD OPTIONS ===\n{options_context}"
        participants.append({
            "persona_id": p["id"], "display_name": p["display_name"],
            "segment": p.get("segment", {}), "soul_path": ctx["soul_path"],
            "agent_context": agent_context,
        })
    return {
        "schema": "head_to_head", "language": language, "project_id": project["id"], "prompt": prompt,
        "external_context": context, "options": public_options, "option_labels": label_ids,
        "participants": participants, "options_context": options_context,
        "instructions": (
            "THE OPTIONS ARE IN THE ROOM, labelled A/B/… — each participant's agent_context ends with the "
            "side-by-side comparison. For EACH persona author: (1) one `statement` per option giving that "
            "persona's stance on it (about={kind:'prompt', id:'opt:A'|'opt:B'|…}, stance:{value -2..2}); "
            "(2) the persona's single `preference` = the option label they'd pick, with a one-line reason. "
            "Stay anti-steering — a persona may genuinely prefer either side or be torn. Ground every "
            "statement in agent_context; quote the captured artifact / the literal text option, don't "
            "invent. Then call record_head_to_head(project_id, prompt, options, preferences=[{persona_id, "
            "choice, reason}], statements=[...], exec_summary, summary). The server tallies preference + "
            f"margin + segment-splits; you author the prose verdict. {language_instruction(language)}"),
    }


def _aggregate(options: list[dict[str, Any]], preferences: list[dict[str, Any]],
               personas: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """The DETERMINISTIC head-to-head math (no LLM): tally who preferred which option → overall preference
    + margin, and break the same tally down by persona segment → who-prefers-what. `margin` is the
    winner's lead over the runner-up as a share of the cast votes (0 = a tie, 1 = unanimous); `decisive`
    labels it for the UI. Segment is `persona.segment.customer_type` (the archetype axis), falling back to
    'unspecified'."""
    labels = [o["label"] for o in options]
    title_by = {o["label"]: o.get("title", o["label"]) for o in options}
    valid = set(labels)
    tally = {lab: 0 for lab in labels}
    seg_tally: dict[str, dict[str, int]] = {}
    cast = 0
    for pref in preferences:
        choice = str(pref.get("choice") or pref.get("label") or pref.get("preference") or "").strip()
        if choice not in valid:
            continue                                       # abstention / unparseable → not counted
        cast += 1
        tally[choice] += 1
        seg = "unspecified"
        p = personas.get(pref.get("persona_id", ""))
        if p:
            seg = (p.get("segment") or {}).get("customer_type") or seg
        seg_tally.setdefault(seg, {lab: 0 for lab in labels})[choice] += 1

    ranked = sorted(labels, key=lambda lab: tally[lab], reverse=True)
    winner = ranked[0] if cast else None
    top = tally.get(winner, 0) if winner else 0
    runner = tally[ranked[1]] if len(ranked) > 1 else 0
    margin = round((top - runner) / cast, 3) if cast else 0.0
    tie = bool(winner) and sum(1 for lab in labels if tally[lab] == top) > 1
    decisive = ("tie" if (tie or margin == 0) else "narrow" if margin < 0.34
                else "clear" if margin < 0.67 else "decisive")

    segment_splits = []
    for seg, counts in sorted(seg_tally.items()):
        seg_cast = sum(counts.values())
        seg_winner = max(counts, key=lambda lab: counts[lab]) if seg_cast else None
        seg_tie = bool(seg_winner) and sum(1 for lab in labels if counts[lab] == counts[seg_winner]) > 1
        segment_splits.append({
            "segment": seg, "voters": seg_cast, "tally": counts,
            "prefers": (None if (seg_tie or not seg_cast) else seg_winner),
        })

    return {
        "options": [{"label": lab, "title": title_by[lab], "votes": tally[lab]} for lab in labels],
        "voters": cast,
        "preference": (None if tie else winner),
        "preference_title": (title_by.get(winner) if winner and not tie else None),
        "tally": tally,
        "margin": margin,
        "decisive": decisive,
        "segment_splits": segment_splits,
    }


def record_head_to_head(project_id: str, prompt: str, options: list[Any],
                        preferences: list[dict[str, Any]] | None = None,
                        persona_ids: list[str] | None = None, statements: list | None = None,
                        summary: str = "", exec_summary: str = "", selection_reason: str = "",
                        findings: list | None = None, key: str | None = None,
                        created_at: str | None = None, store: Store | None = None) -> dict[str, Any]:
    """Persist a host-authored HEAD-TO-HEAD as a CouncilSession carrying a `head_to_head` block. The host
    passes the labelled `options`, each persona's `preferences` ([{persona_id, choice (a label), reason}]),
    and the authored `statements` (per-option stances) + exec_summary/summary (the prose verdict). The
    SERVER does the deterministic aggregation (preference + margin + segment-splits) from `preferences`
    and stores it — a queryable result. Pass a stable `key` for a deterministic id (idempotent upsert)."""
    store = store or Store()
    project = _require_research_project(store, project_id)
    opts = _normalize_options(project["id"], options or [], store)
    if len(opts) < 2:
        raise ValueError("head_to_head needs at least two options to compare.")
    public_options = [{k: v for k, v in o.items() if k != "brief"} for o in opts]
    prefs = [dict(p) for p in (preferences or []) if p.get("persona_id")]
    pids = persona_ids or [p["persona_id"] for p in prefs]
    personas = {pid: store.get_persona(pid) for pid in pids}
    personas = {pid: p for pid, p in personas.items() if p}

    aggregate = _aggregate(opts, prefs, personas)

    # The head-to-head result is ALSO surfaced as a council finding so it is queryable next to other
    # study findings (the analytics/calibration seam — no analytics system is built; this is the hook).
    win = aggregate["preference"]
    verdict = (f"Preference: Option {win} — {aggregate['preference_title']} "
               f"({aggregate['decisive']}, margin {aggregate['margin']})." if win
               else f"No clear preference — tie ({aggregate['voters']} voters).")
    ht_finding = _artifacts.finding(verdict, kind="head_to_head",
                                    score={"margin": aggregate["margin"], "voters": aggregate["voters"]},
                                    meta={"aggregate": aggregate})
    findings_in = list(findings or []) + [ht_finding]

    # The labelled options become the council prompts (id 'opt:<label>') so each per-option statement's
    # about-ref resolves and the discovery-style Q→A grouping renders one card-group per option.
    option_prompts = [_artifacts.prompt(o.get("title") or o["label"], kind="proposal", id=f"opt:{o['label']}")
                      for o in opts]

    # Reuse record_council for ALL the persistence/graph wiring; head_to_head rides as extra metadata.
    session = record_council(
        project["id"], prompt, pids, statements=statements, proposal="",
        summary=summary, exec_summary=exec_summary,
        selection_reason=selection_reason or "head-to-head panel",
        prompts=option_prompts, findings=findings_in, key=key, created_at=created_at, store=store)

    session["head_to_head"] = {
        "options": public_options,
        "preferences": prefs,
        "result": aggregate,
        "recorded_at": utc_now_iso(),
    }
    store.insert_council_session(session)
    return session


def get_head_to_head(session_id: str, store: Store | None = None) -> dict[str, Any]:
    """One head-to-head result by council-session id — its options, per-persona preferences and the
    deterministic aggregate (preference + margin + segment-splits). Raises if not a head-to-head."""
    store = store or Store()
    c = store.get_council_session(session_id)
    if not c:
        raise KeyError(f"Unknown council session: {session_id}")
    ht = c.get("head_to_head")
    if not ht:
        raise KeyError(f"Council {session_id} is not a head-to-head")
    return {"id": c["id"], "prompt": c["prompt"], "project_id": c.get("project_id", ""),
            "created_at": c["created_at"], **ht}


def is_head_to_head(council: dict[str, Any]) -> bool:
    """True when a council session carries a recorded head-to-head result (drives the UI branch)."""
    return bool(council.get("head_to_head"))
