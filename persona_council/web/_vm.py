"""View-models — the typed presentation contract that lets divergent records feed the SAME components
(spec/component-ssr-architecture.md C4; closes methodology-presentation §10).

A council and a synthesis are both *studies* (a question + an answer/finding) but store those roles
under different keys. study_head() maps either into one shape so the UI never branches on field names.
The caller passes is_synthesis explicitly (it already knows which it fetched) — no hardcoded kind
literal, honoring the web grep-gate."""
from __future__ import annotations

from .. import services
from ._i18n import t


def study_head(record: dict, *, is_synthesis: bool = False) -> dict:
    """Map a council OR synthesis record to the shared study-lead view-model:
      {question, answer_md, answer_label, mode}
    - council: the hero title IS the question, so `question` is empty; finding = exec_summary|summary.
    - synthesis: the hero title is the thesis, so `question` = goal|start_input; answer = gesamtbild.
    `answer_md` is raw markdown — the page renders it (so the component stays presentation-only)."""
    if is_synthesis:
        return {
            "question": record.get("goal") or record.get("start_input", ""),
            "answer_md": record.get("gesamtbild", ""),
            "answer_label": t("answer_exec_summary"),
            "mode": "summary",
        }
    return {
        "question": "",
        "answer_md": record.get("exec_summary") or record.get("summary", ""),
        "answer_label": t("council_finding"),
        "mode": services.council_mode(record),
    }
