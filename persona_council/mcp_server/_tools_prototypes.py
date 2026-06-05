from __future__ import annotations

import time
from typing import Any

from .. import services
from ._env import _env


def register_prototypes(mcp):
    # ================= Prototypes (real, minimal, locally-runnable apps) =================
    @mcp.tool()
    def scaffold_prototype(slug: str, name: str, concept: dict[str, Any], kind: str = "web",
                           template: str | None = None, project_id: str | None = None,
                           fidelity: str | None = None) -> dict[str, Any]:
        """Generate a real, minimal, runnable web app from a host-authored concept and register it.
        The app is genuinely clickable (real DOM) for Playwright. The renderer template is resolved
        from DATA (suggestions/artifact_types.json): pass a `fidelity` tag (lofi/midfi/hifi → a
        sketchy/clean/polished form) or scaffold a non-form artifact TYPE (flow, dashboard, cards,
        comparison). `template` forces a specific template; concept-level `fidelity` themes any
        template. Concept = {title, summary, start, screens:[{id,title,elements,...rich blocks}]};
        rich blocks read by the non-form templates: screen.metrics / screen.cards / screen.columns."""
        t = time.perf_counter()
        return _env("scaffold_prototype",
                    services.scaffold_prototype(slug, name, concept, kind, template, project_id, fidelity), t)

    @mcp.tool()
    def register_prototype(slug: str, name: str, path: str, entry: str = "index.html", run: str = "static",
                           run_cmd: str | None = None, version: str = "v0.1", project_id: str | None = None,
                           notes: str = "", fidelity: str = "midfi") -> dict[str, Any]:
        """Register a hand-authored app under prototypes/ as a runnable artifact (fidelity tag, e.g. lofi|midfi|hifi)."""
        t = time.perf_counter()
        return _env("register_prototype",
                    services.register_prototype(slug, name, path, entry, run, run_cmd, version, project_id, notes, fidelity), t)

    @mcp.tool()
    def list_prototypes(project_id: str | None = None) -> dict[str, Any]:
        """List registered prototype artifacts (optionally for one project)."""
        t = time.perf_counter()
        return _env("list_prototypes", services.list_prototypes_artifacts(project_id), t)

    @mcp.tool()
    def get_prototype(prototype_id: str) -> dict[str, Any]:
        """One prototype artifact by id or slug."""
        t = time.perf_counter()
        return _env("get_prototype", services.get_prototype_artifact(prototype_id), t)

    @mcp.tool()
    def run_prototype(prototype_id: str) -> dict[str, Any]:
        """Start the app on an ephemeral localhost port; returns {url, pid}. Local-only."""
        t = time.perf_counter()
        return _env("run_prototype", services.run_prototype(prototype_id), t)

    @mcp.tool()
    def stop_prototype(prototype_id: str) -> dict[str, Any]:
        """Stop a running prototype."""
        t = time.perf_counter()
        return _env("stop_prototype", services.stop_prototype(prototype_id), t)

    @mcp.tool()
    def delete_prototype(prototype_id: str) -> dict[str, Any]:
        """Delete a prototype artifact record (files on disk are kept)."""
        t = time.perf_counter()
        return _env("delete_prototype", services.delete_prototype_artifact(prototype_id), t)

    # ================= Playwright harness — agents drive the real app =================
    @mcp.tool()
    def proto_open(prototype_id: str | None = None, url: str | None = None,
                   persona_id: str | None = None) -> dict[str, Any]:
        """Open a real running app in a headless browser session; returns {session_id, snapshot}."""
        t = time.perf_counter()
        return _env("proto_open", services.proto_open(prototype_id, url, persona_id), t)

    @mcp.tool()
    def proto_act(session_id: str, action: dict[str, Any]) -> dict[str, Any]:
        """Act on the latest snapshot: {type: click|type|select|scroll|key|wait, ref?, text?, value?}."""
        t = time.perf_counter()
        return _env("proto_act", services.proto_act(session_id, action), t)

    @mcp.tool()
    def proto_read(session_id: str) -> dict[str, Any]:
        """Re-read the current snapshot of a session."""
        t = time.perf_counter()
        return _env("proto_read", services.proto_read(session_id), t)

    @mcp.tool()
    def proto_close(session_id: str) -> dict[str, Any]:
        """Close a browser session."""
        t = time.perf_counter()
        return _env("proto_close", services.proto_close(session_id), t)

    @mcp.tool()
    def list_proto_sessions() -> dict[str, Any]:
        """List live browser sessions."""
        t = time.perf_counter()
        return _env("list_proto_sessions", services.list_proto_sessions(), t)

    @mcp.tool()
    def brief_prototype_session(persona_id: str, prototype_id: str) -> dict[str, Any]:
        """GATHER persona context + how-to-drive + anti-steering before a persona uses the app."""
        t = time.perf_counter()
        return _env("brief_prototype_session", services.brief_prototype_session(persona_id, prototype_id), t)

    @mcp.tool()
    def record_prototype_session(persona_id: str, prototype_id: str, session_id: str, date: str,
                                 reaction: dict[str, Any], key: str | None = None) -> dict[str, Any]:
        """Persist a persona's grounded prototype use as an experience + memory + artifact; rejects
        claims with no matching observed state in the session log. Pass a stable `key` for a
        DETERMINISTIC id so re-running the step is an idempotent upsert (resumable runs, ESV)."""
        t = time.perf_counter()
        return _env("record_prototype_session",
                    services.record_prototype_session(persona_id, prototype_id, session_id, date, reaction, key), t)

    # M3 — the delete_* CRUD tools moved to _tools_research.py (their project/artifact domain).

    # ----- F3 autonomous loop driver -----
    @mcp.tool()
    def brief_month(persona_id: str, month: str) -> dict[str, Any]:
        """GATHER context to author a whole month bundle (period plan + sample days + digest),
        chained on the prior month. Then record_month_bundle."""
        t = time.perf_counter()
        return _env("brief_month", services.brief_month(persona_id, month), t)

    @mcp.tool()
    def record_month_bundle(persona_id: str, month: str, bundle: dict[str, Any]) -> dict[str, Any]:
        """Persist a host-authored month bundle through the full loop (plan→sample days→
        simulate→consolidate→digest→embed)."""
        t = time.perf_counter()
        return _env("record_month_bundle", services.record_month_bundle(persona_id, month, bundle), t)

    # ----- F5 evidence integration -----
    @mcp.tool()
    def brief_evidence_check(persona_id: str) -> dict[str, Any]:
        """GATHER profile claims + attached evidence to validate synthesis against reality."""
        t = time.perf_counter()
        return _env("brief_evidence_check", services.brief_evidence_check(persona_id), t)

    @mcp.tool()
    def record_evidence_check(persona_id: str, result: dict[str, Any]) -> dict[str, Any]:
        """Persist provenance verdict: confirmed/contradicted/unsupported; flags contradictions."""
        t = time.perf_counter()
        return _env("record_evidence_check", services.record_evidence_check(persona_id, result), t)

    # M2 — backfill_embeddings / prune_memory are MAINTENANCE actions, CLI-only (off the agent surface).
