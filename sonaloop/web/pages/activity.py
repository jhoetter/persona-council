"""Activity feed: the recent cross-process lifecycle events (ticket live-event-stream).

Renders the same capped `events` table the SSE endpoint streams — one row per event
(time, localised event type, short label) linking to the entity it concerns. The
page itself is live: the chrome's EventSource module reloads it on every new event.
Read-only like every inspector page."""
from __future__ import annotations

from ._ctx import *  # noqa: F401,F403  (shared render toolkit)
from .._live import event_labels


def register_activity(app) -> None:
    @app.get("/activity", response_class=HTMLResponse)
    def activity() -> str:
        store = Store()
        labels = event_labels()
        rows = []
        for ev in store.list_recent_events(limit=200):
            label = ev["data"].get("label") or ""
            rows.append(h("a", {"class_": "row", "href": ev["data"].get("url") or "/projects"},
                          h("span", {"class_": "rico", "style": "color:var(--accent)"},
                            raw(_icon("activity"))),
                          h("span", {"class_": "title"}, labels.get(ev["event"], ev["event"]),
                            h("span", {"class_": "muted small"}, f" · {label}") if label else None),
                          h("span", {"class_": "right"},
                            h("span", {}, ev["ts"][:16].replace("T", " ")))))
        return _list_page(store, title=t("activity_h"), lead=t("activity_lead"), rows=rows,
                          empty_icon="activity", empty_msg=t("no_activity"), active="activity")
