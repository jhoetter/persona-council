from __future__ import annotations

import asyncio
import json
import os
import time

from fastapi import Request

from .. import services


def _events_poll_interval() -> float:
    """The SSE table-poll cadence. Env-tunable (tests poll fast); ~1s in production —
    cheap (one indexed read on an at-most-1000-row table) and feels instant."""
    try:
        return max(0.02, min(10.0, float(os.getenv("SONALOOP_EVENTS_POLL", 1.0))))
    except (TypeError, ValueError):
        return 1.0


def _events_heartbeat_every() -> float:
    """Seconds between SSE heartbeat comments (keeps idle proxies/browsers from
    timing the stream out). Env-tunable so tests can observe one immediately."""
    try:
        return max(0.0, float(os.getenv("SONALOOP_EVENTS_HEARTBEAT", 15.0)))
    except (TypeError, ValueError):
        return 15.0


async def _event_stream(request, last_id: int | None):
    """Tail the cross-process `events` table as SSE frames. `id:` carries the bus row
    id, so EventSource reconnects replay via Last-Event-ID; a fresh connection (no
    last id) starts at the current high-water mark — live tail, no history dump."""
    from ..storage import Store
    if last_id is None:
        store = Store()
        cursor = store.latest_event_id()
        store.close()
    else:
        cursor = last_id
    yield ": connected\n\n"                         # immediate flush → onopen fires
    last_beat = time.monotonic()
    while True:
        if await request.is_disconnected():
            return
        store = Store()                              # fresh per poll: never hold a
        try:                                         # connection across the sleep
            rows = store.list_events_after(cursor)
        finally:
            store.close()
        for row in rows:
            cursor = row["id"]
            payload = {"id": row["id"], "ts": row["ts"], "event": row["event"],
                       "entity_type": row["entity_type"], "entity_id": row["entity_id"],
                       "project_id": row["project_id"], **row["data"]}
            yield f"id: {row['id']}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            last_beat = time.monotonic()
        if time.monotonic() - last_beat >= _events_heartbeat_every():
            yield ": ping\n\n"
            last_beat = time.monotonic()
        await asyncio.sleep(_events_poll_interval())


def register_api(app) -> None:
    from fastapi import Query
    from fastapi.responses import JSONResponse, StreamingResponse

    @app.get("/api/events")
    async def api_events(request: Request):
        """Live event stream (SSE) for the inspector: new bus rows as they land,
        Last-Event-ID replay, heartbeat comments. Plain StreamingResponse — no deps."""
        raw_last = request.headers.get("last-event-id") or request.query_params.get("last_event_id")
        try:
            last_id = int(raw_last) if raw_last is not None else None
        except ValueError:
            last_id = None
        return StreamingResponse(
            _event_stream(request, last_id), media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.get("/api/personas")
    def api_personas():
        return JSONResponse(services.list_personas())

    @app.get("/api/personas/{persona_id}")
    def api_persona(persona_id: str):
        try:
            return JSONResponse(services.get_persona(persona_id))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/calendar")
    def api_calendar(persona_id: str, date_value: str | None = Query(default=None, alias="date")):
        try:
            return JSONResponse(services.get_calendar(persona_id, date_value))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/calendar-period")
    def api_calendar_period(persona_id: str, date_value: str | None = Query(default=None, alias="date"), view: str = "day"):
        try:
            return JSONResponse(services.get_calendar_period(persona_id, date_value, view))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/memory")
    def api_memory(persona_id: str):
        try:
            return JSONResponse(services.get_persona_memory(persona_id))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/projects")
    def api_projects(persona_id: str):
        try:
            return JSONResponse(services.list_active_projects(persona_id))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/state-at")
    def api_state_at(persona_id: str, as_of: str = Query(...)):
        try:
            return JSONResponse(services.get_state_at(persona_id, as_of))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/recall")
    def api_recall(persona_id: str, q: str = Query(...), as_of: str | None = Query(default=None), k: int = 8):
        try:
            return JSONResponse(services.recall_memory(persona_id, q, as_of, k))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/personas/{persona_id}/evaluate")
    def api_evaluate(persona_id: str):
        try:
            return JSONResponse(services.evaluate_simulation_full(persona_id))
        except KeyError:
            return JSONResponse({"error": "profile_not_found"}, status_code=404)

    @app.get("/api/activities/{activity_id}")
    def api_activity(activity_id: str):
        try:
            return JSONResponse(services.get_activity(activity_id))
        except KeyError:
            return JSONResponse({"error": "activity_not_found"}, status_code=404)

    @app.get("/api/councils")
    def api_councils():
        return JSONResponse(services.list_councils())

    @app.get("/api/syntheses")
    def api_syntheses():
        return JSONResponse(services.list_syntheses())

    @app.get("/api/syntheses/{synthesis_id}")
    def api_synthesis(synthesis_id: str):
        try:
            return JSONResponse(services.get_synthesis(synthesis_id))
        except KeyError:
            return JSONResponse({"error": "synthesis_not_found"}, status_code=404)

    @app.get("/api/search")
    def api_search(q: str = Query(default="")):
        """Global command-palette search: title-substring match across every entity type."""
        from ..storage import Store
        ql = q.strip().lower()
        if not ql:
            return JSONResponse([])
        store = Store()
        out: list[dict] = []

        def add(typ, title, subtitle, url):
            sub = subtitle if isinstance(subtitle, str) else ""
            if title and ql in title.lower():
                out.append({"type": typ, "title": title, "subtitle": sub, "url": url})

        for p in store.list_research_projects():
            add("project", p.get("title", ""), (p.get("goal", "") or "")[:90], f"/projects/{p['id']}")
        for p in store.list_personas():
            role = p.get("role")
            role_t = role.get("title", "") if isinstance(role, dict) else (role or "")
            add("persona", p.get("display_name", ""), role_t, f"/personas/{p['id']}")
        for c in store.list_council_sessions():
            add("council", c.get("prompt", ""), "", f"/councils/{c['id']}")
        for sy in store.list_syntheses():
            add("synthesis", sy.get("title", ""), "", f"/syntheses/{sy['id']}")
        for pr in store.list_prototypes():
            add("prototype", pr.get("name", ""), pr.get("version", ""), f"/prototypes/{pr['slug']}")
        for proj in store.list_research_projects():
            for sec in services.list_sections(proj["id"], store=store):
                add("section", sec.get("title", ""), proj.get("title", ""), f"/sections/{sec['id']}")
            for nt in services.list_notes(proj["id"], store=store):
                add("note", nt.get("title", ""), proj.get("title", ""), f"/notes/{nt['id']}")
        out.sort(key=lambda r: (0 if r["title"].lower().startswith(ql) else 1, len(r["title"])))
        return JSONResponse(out[:20])
