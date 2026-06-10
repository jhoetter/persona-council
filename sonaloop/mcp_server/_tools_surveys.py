from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_surveys(mcp):
    # ================= Surveys — the outbound instrument (collects REAL data back) =================
    # House triplet: brief_survey (gather: open questions + contested findings + the stance
    # vocabulary) → the host authors the questions → record_survey (validate + persist). Then
    # export_survey emits a sendable, self-contained HTML form; import_survey_responses ingests the
    # real answers; survey_results aggregates (predicted-vs-actual for stance_mapped questions);
    # attach_survey_evidence loops the responses back onto a persona as calibration Evidence.
    # Hosted collection endpoints are sonaloop-cloud's job — core stays serverless.
    @mcp.tool()
    def brief_survey(project_id: str) -> dict[str, Any]:
        """GATHER everything needed to author a survey that is answerable against the graph: the
        project's open questions, its contested findings (councils whose statements span support AND
        opposition), and the canonical stance vocabulary (for stance_mapped scale options). Author
        the questions, then record_survey."""
        t = time.perf_counter()
        return _env("brief_survey", services.brief_survey(project_id), t)

    @mcp.tool()
    def record_survey(project_id: str, title: str, questions: list[dict[str, Any]],
                      intro: str = "", derived_from: list[dict[str, Any]] | None = None,
                      status: str = "draft", slug: str | None = None,
                      key: str | None = None) -> dict[str, Any]:
        """Persist a host-authored survey. `questions` = [{id?, text, kind: single|multi|scale|text,
        options (>= 2 for non-text), stance_mapped (scale only)}] — a stance_mapped scale's options
        must map CLEANLY onto the canonical stance scale (suggest_stances names the terms/aliases;
        unmappable or ambiguous options are REJECTED). `derived_from` = Refs to what the instrument
        operationalizes ({kind: open_question|council|synthesis, id, anchor?, role}); unresolvable
        refs are REJECTED. Re-recording the same slug updates in place; a stable `key` gives a
        deterministic id (idempotent upsert)."""
        t = time.perf_counter()
        return _env("record_survey",
                    services.record_survey(project_id, title, questions, intro, derived_from,
                                           status, slug, key), t)

    @mcp.tool()
    def get_survey(survey_id: str) -> dict[str, Any]:
        """One survey by id or slug — the instrument document + its live response_count."""
        t = time.perf_counter()
        return _env("get_survey", services.get_survey(survey_id), t)

    @mcp.tool()
    def list_surveys(project_id: str | None = None) -> dict[str, Any]:
        """List surveys (optionally per project), each with its live response_count."""
        t = time.perf_counter()
        return _env("list_surveys", {"surveys": services.list_surveys(project_id)}, t)

    @mcp.tool()
    def export_survey(survey_id: str, post_url: str | None = None,
                      out: str | None = None) -> dict[str, Any]:
        """Render the survey as a SENDABLE, self-contained static HTML form (spa-min template) —
        works from file://, host it anywhere. Submissions produce a JSON payload shaped exactly
        like a SurveyResponse row: POSTed to `post_url` (overridable at fill-time via ?post=) or
        downloaded as a file to send back; either round-trips through import_survey_responses.
        Exporting a draft flips its status to open. No collection server in core."""
        t = time.perf_counter()
        return _env("export_survey", services.export_survey(survey_id, post_url, out), t)

    @mcp.tool()
    def import_survey_responses(survey_id: str, responses: list[dict[str, Any]] | None = None,
                                csv_text: str | None = None,
                                source: str = "import") -> dict[str, Any]:
        """Ingest a batch of REAL responses — a JSON list (the export form's payload shape:
        {respondent_key?, submitted_at?, answers: [{question_id, value}], source?}) and/or CSV text
        (one column per question id; ';' separates multi-select options). Every answer is validated
        against the instrument; re-importing the same batch is idempotent (deterministic ids).
        `source` labels the batch."""
        t = time.perf_counter()
        return _env("import_survey_responses",
                    services.import_survey_responses(survey_id, responses, csv_text, source), t)

    @mcp.tool()
    def survey_results(survey_id: str) -> dict[str, Any]:
        """Per-question aggregates of the imported responses — and for stance_mapped questions the
        PREDICTED-VS-ACTUAL strip: the persona stance distribution from the derived_from councils'
        statements next to the real answer distribution, with refs into the predicting councils."""
        t = time.perf_counter()
        return _env("survey_results", services.survey_results(survey_id), t)

    @mcp.tool()
    def attach_survey_evidence(survey_id: str, persona_id: str,
                               notes: str | None = None) -> dict[str, Any]:
        """Loop the imported REAL responses back onto a persona as Evidence (source_type='survey')
        for calibration — a compact JSON of the per-question aggregates (incl. predicted-vs-actual),
        so the next brief/revision sees how reality answered where the council only predicted."""
        t = time.perf_counter()
        return _env("attach_survey_evidence",
                    services.attach_survey_evidence(survey_id, persona_id, notes), t)
