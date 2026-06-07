from __future__ import annotations

from .. import services


def register_api(app) -> None:
    from fastapi import Query
    from fastapi.responses import JSONResponse

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
