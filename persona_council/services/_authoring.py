"""Shared host-authoring contract (spec/markdown-authoring-harness.md).

Appended to the `instructions` of every prose-authoring brief so the host writes Markdown body prose
instead of ALL-CAPS-for-emphasis and literal section headers. The web UI renders these fields with a
real Markdown renderer (web/_components._md), so authoring Markdown 'just works' with no UI change."""
from __future__ import annotations

MARKDOWN_CONTRACT = (
    "\n\nAUTHORING STYLE (body prose): write analysis/summary fields as GitHub-flavored **Markdown** — "
    "use **bold** / _italic_ for emphasis, `-` or `1.` lists for enumerations, `>` for quotes, "
    "`code` for verbatim, and blank lines between paragraphs. Do NOT use ALL-CAPS for emphasis, and do "
    "NOT write a literal section header inside the text (e.g. 'SUMMARY:', 'VOTES:', 'WHAT THIS COUNCIL "
    "FOUND') — the UI already renders the headers/labels around your text. This applies to the "
    "moderator/analysis fields (exec_summary, summary, gesamtbild, positionierung, recommendations, "
    "meta-report sections, key problems, open questions, notes). A persona/proband turn `content` may "
    "stay in that persona's own natural voice — it is a quote, not a report."
)
