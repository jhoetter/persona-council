"""`search` + `fetch` — the cross-host retrieval contract.

ChatGPT's connector / Deep Research mode REQUIRES two tools named exactly `search` and
`fetch` with a fixed output shape; without them ChatGPT rejects the server outside
Developer Mode and Deep Research cannot run. These wrappers expose that contract over the
workspace's own research records (services._retrieval). They return the OpenAI shape
DIRECTLY — NOT wrapped in the _env envelope — so a ChatGPT client parses the structured
content verbatim (`{results:[...]}` / `{id,title,text,url,metadata}`). Claude reads them
fine too (a plain tool result). Read-only.
"""
from __future__ import annotations

from typing import Any

from .. import services


def register_retrieval(mcp) -> None:
    @mcp.tool()
    def search(query: str) -> dict[str, Any]:
        """Find the workspace's research records (projects, councils, syntheses, hypotheses,
        personas) matching `query`. Returns {results:[{id,title,url,text}]} — each `url` is the
        page to open, each `id` is fetchable. This is the cross-host retrieval entry point
        (ChatGPT Deep Research requires it); for the curated 300+ persona library use
        catalog_search instead, and to drive a project use start_project/start_run."""
        return services.retrieval_search(query)

    @mcp.tool()
    def fetch(id: str) -> dict[str, Any]:
        """Fetch ONE research record by id (a project/council/synthesis/hypothesis/persona id,
        e.g. from a `search` result). Returns {id,title,text,url,metadata}: `text` is a readable
        rendering you can quote, `url` is its page, `metadata.kind` says what it is."""
        return services.retrieval_fetch(id)
