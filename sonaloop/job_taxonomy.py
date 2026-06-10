"""Job / Framework / Format taxonomy — the canonical three-layer model.

The single source of truth is the data file `taxonomy.json` (this module just loads it) and
its human-readable companion `docs/job-framework-format.md`. The three orthogonal layers:

  - Job        — what the user wants / the use case they buy ("how is my positioning?").
  - Framework  — the process the run follows (a methodology key under methodologies/*.json).
  - Format     — a single move inside a run (council, prototype_test, head_to_head, red_team).

A Job runs THROUGH a Framework USING Formats. Consumers (the website IA, the
`sharpen-question-helper` presets, the methodology surface) should import from here rather than
re-reading the raw JSON, so the ids/labels stay aligned across repos.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any

from .config import taxonomy_path


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    """The full taxonomy document (layers, frameworks, formats, jobs)."""
    return json.loads(taxonomy_path().read_text(encoding="utf-8"))


def layers() -> dict[str, dict[str, Any]]:
    """The three layer definitions, keyed by id (job / framework / format)."""
    return load_taxonomy()["layers"]


def frameworks() -> list[dict[str, Any]]:
    """Frameworks in the taxonomy, each pointing at a real methodology `key`."""
    return load_taxonomy()["frameworks"]


def formats() -> list[dict[str, Any]]:
    """Formats (council, prototype_test, head_to_head, red_team) with implementation status."""
    return load_taxonomy()["formats"]


def jobs() -> list[dict[str, Any]]:
    """The named Jobs the product sells, each resolving to framework(s) + formats + coverage."""
    return load_taxonomy()["jobs"]


def get_job(job_id: str) -> dict[str, Any]:
    """One Job by stable id (e.g. 'positioning'). Raises KeyError if unknown."""
    for job in jobs():
        if job["id"] == job_id:
            return job
    raise KeyError(f"No taxonomy job '{job_id}'")


def framework_descriptions(store: Any | None = None) -> list[dict[str, Any]]:
    """The plain-language description of every Framework, as ONE clean shape the website
    "how it works" page and the job presets both consume:

        {id, name, what, when, stages: [{id, name, what}]}

    `what` is the one-line "what shape it is", `when` is the "when to use it", and `stages` is the
    ordered diverge→converge shape. The data is read from the methodology specs (the live source —
    `sonaloop/methodologies/*.json`) and the framework's display `name` is taken from the canonical
    taxonomy so ids/labels stay in lock-step. Only the Frameworks named in the taxonomy are returned,
    in taxonomy order, so downstream consumers get a stable, deduplicated list."""
    from . import methodology as _meth  # local import to avoid an import cycle at module load

    registry = _meth.registry(store)
    out: list[dict[str, Any]] = []
    for fw in frameworks():
        spec = registry.get(fw["methodology_key"])
        if not spec:
            continue
        stages = [
            {"id": st["id"], "name": st.get("name", st["id"]), "what": st.get("intent", "")}
            for st in spec.get("steps", [])
        ]
        out.append({
            "id": fw["id"],
            "name": fw.get("name", spec.get("name", fw["id"])),
            "what": spec.get("description", ""),
            "when": spec.get("when_to_use", ""),
            "stages": stages,
        })
    return out


def get_framework_description(framework_id: str, store: Any | None = None) -> dict[str, Any]:
    """One Framework's plain-language description by stable id (e.g. 'double_diamond').
    Raises KeyError if the id is unknown. See `framework_descriptions` for the shape."""
    for fw in framework_descriptions(store):
        if fw["id"] == framework_id:
            return fw
    raise KeyError(f"No taxonomy framework '{framework_id}'")


def framework_keys() -> set[str]:
    """The methodology keys referenced by the taxonomy — for cross-checking against the registry."""
    return {fw["methodology_key"] for fw in frameworks()}


def format_ids() -> set[str]:
    """All known Format ids (implemented or planned)."""
    return {fmt["id"] for fmt in formats()}


# Jobs whose discipline is load-bearing: shipping one of these WITHOUT its protocol block would
# silently drop the run rules the Job sells (see docs/job-framework-format.md "Job protocols").
PROTOCOL_REQUIRED_JOBS = frozenset({"ab_test", "pricing", "ideation_hmw"})

_JOB_ID = re.compile(r"^[a-z][a-z0-9_]*$")


def lint_taxonomy(store: Any | None = None, taxonomy: dict[str, Any] | None = None) -> list[str]:
    """Structural-completeness lint for the canonical taxonomy — the "Adding a Job" checklist
    (docs/job-framework-format.md), machine-checked. Returns a list of problems (empty = clean):
    every Framework's methodology_key resolves to a REAL methodology spec; every Job's framework
    and format keys resolve; coverage carries min_personas + persona_axes; a protocol block is
    present where required (PROTOCOL_REQUIRED_JOBS) and well-formed wherever present (named steps,
    each with rule + tooling); and the companion doc has a section per job id. The doc check is
    skipped when the repo doc is absent (installed package data ships without docs/). Pass
    `taxonomy` to lint a candidate document before committing it. CLI: `sonaloop taxonomy-lint`."""
    from . import methodology as _meth   # local import to avoid an import cycle at module load
    from .config import taxonomy_path

    tax = taxonomy or load_taxonomy()
    problems: list[str] = []
    registry = set(_meth.registry(store))
    fw_ids: set[str] = set()
    for fw in tax.get("frameworks", []):
        fw_ids.add(fw.get("id", ""))
        if fw.get("methodology_key") not in registry:
            problems.append(f"framework '{fw.get('id')}': methodology_key "
                            f"{fw.get('methodology_key')!r} resolves to no methodology spec")
    fmt_ids = {f.get("id") for f in tax.get("formats", [])}

    seen: set[str] = set()
    for job in tax.get("jobs", []):
        jid = job.get("id", "")
        where = f"job '{jid}'"
        if not _JOB_ID.match(jid or ""):
            problems.append(f"{where}: id must be lower_snake_case")
        if jid in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(jid)
        for field in ("name", "sells_as", "user_question"):
            if not str(job.get(field) or "").strip():
                problems.append(f"{where}: {field} is missing")
        fws = job.get("frameworks") or []
        if not fws:
            problems.append(f"{where}: no frameworks")
        for f in fws:
            if f not in fw_ids:
                problems.append(f"{where}: framework {f!r} is not a taxonomy framework")
        if job.get("default_framework") not in fws:
            problems.append(f"{where}: default_framework {job.get('default_framework')!r} "
                            "not in frameworks")
        if not job.get("formats"):
            problems.append(f"{where}: no formats")
        for f in job.get("formats") or []:
            if f not in fmt_ids:
                problems.append(f"{where}: format {f!r} is not a taxonomy format")
        cov = job.get("coverage") or {}
        if not (isinstance(cov.get("min_personas"), int) and cov["min_personas"] >= 1):
            problems.append(f"{where}: coverage.min_personas must be an int >= 1")
        if not cov.get("persona_axes"):
            problems.append(f"{where}: coverage.persona_axes is missing")
        proto = job.get("protocol")
        if jid in PROTOCOL_REQUIRED_JOBS and not proto:
            problems.append(f"{where}: protocol block is REQUIRED (the Job sells a run discipline)")
        if proto:
            if not str(proto.get("name") or "").strip() or not str(proto.get("summary") or "").strip():
                problems.append(f"{where}: protocol needs name + summary")
            steps = proto.get("steps") or []
            if not steps:
                problems.append(f"{where}: protocol has no steps")
            step_ids = [s.get("id") for s in steps]
            if len(set(step_ids)) != len(step_ids):
                problems.append(f"{where}: protocol step ids must be unique")
            for s in steps:
                if not (str(s.get("id") or "").strip() and str(s.get("rule") or "").strip()
                        and str(s.get("tooling") or "").strip()):
                    problems.append(f"{where}: protocol step {s.get('id')!r} needs id + rule + tooling")

    doc = taxonomy_path().parent.parent / "docs" / "job-framework-format.md"
    if doc.exists():
        text = doc.read_text(encoding="utf-8")
        for job in tax.get("jobs", []):
            if f"(`{job.get('id')}`)" not in text:
                problems.append(f"job '{job.get('id')}': no section in docs/job-framework-format.md "
                                f"(expected a \"(`{job.get('id')}`)\" mention)")
    return problems
