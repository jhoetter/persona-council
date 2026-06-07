"""Playwright harness (spec/methodology-engine-and-prototyping.md, Pillar B §7).

A persona-agent drives the REAL running app and reacts to REAL observed state. Each
session owns a dedicated worker thread that holds the sync Playwright objects (so it works
regardless of the caller's async context). Refs are valid only for the latest snapshot of a
session; acting on a stale ref raises STALE_REF. Degrades gracefully when Playwright/chromium
is unavailable.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Any

from .config import max_browser_sessions

ACTIONABLE = {"button", "link", "textbox", "checkbox", "combobox", "menuitem",
              "tab", "radio", "searchbox", "switch", "option"}


class HarnessError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except Exception:
        return False


class _Session(threading.Thread):
    """Owns one headless page in its own thread; commands arrive on a queue."""

    def __init__(self, session_id: str, url: str, prototype_id: str | None, persona_id: str | None):
        super().__init__(daemon=True)
        self.session_id = session_id
        self.url = url
        self.prototype_id = prototype_id
        self.persona_id = persona_id
        self.refmap: dict[str, dict[str, str]] = {}
        self.log: list[dict[str, Any]] = []
        self._cmd: queue.Queue = queue.Queue()
        self._ready: queue.Queue = queue.Queue()
        self._pw = None
        self._browser = None
        self._page = None

    # ----- thread body -----
    def run(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            self._page = self._browser.new_page()
            self._page.goto(self.url, wait_until="load", timeout=20000)
            self._page.wait_for_timeout(150)
            snap = self._snapshot()
            self._ready.put(("ok", snap))
        except Exception as e:  # launch/navigation failure
            self._ready.put(("err", f"{type(e).__name__}: {e}"))
            self._teardown()
            return
        while True:
            cmd, payload, reply = self._cmd.get()
            if cmd == "close":
                self._teardown()
                reply.put(("ok", {"closed": True}))
                return
            try:
                if cmd == "read":
                    reply.put(("ok", self._snapshot()))
                elif cmd == "act":
                    reply.put(("ok", self._act(payload)))
                else:
                    reply.put(("err", f"unknown command {cmd}"))
            except HarnessError as he:
                reply.put(("err", f"{he.code}:{he.message}"))
            except Exception as e:
                reply.put(("err", f"{type(e).__name__}: {e}"))

    def _teardown(self) -> None:
        for obj, meth in ((self._browser, "close"), (self._pw, "stop")):
            try:
                if obj:
                    getattr(obj, meth)()
            except Exception:
                pass

    # ----- in-thread operations -----
    _SNAP_JS = """() => {
      const out = [];
      const roleFor = (el) => {
        const explicit = el.getAttribute('role'); if (explicit) return explicit;
        const tag = el.tagName.toLowerCase();
        if (tag === 'a') return 'link';
        if (tag === 'button') return 'button';
        if (tag === 'select') return 'combobox';
        if (tag === 'textarea') return 'textbox';
        if (tag === 'input') {
          const t = (el.getAttribute('type') || 'text').toLowerCase();
          if (t === 'checkbox') return 'checkbox';
          if (t === 'radio') return 'radio';
          return 'textbox';
        }
        return tag;
      };
      const sel = 'button, a[href], input, select, textarea, [role=button], [role=link]';
      document.querySelectorAll(sel).forEach(el => {
        if (el.offsetParent === null && el.tagName.toLowerCase() !== 'option') return; // hidden
        const name = (el.getAttribute('aria-label') || el.textContent || el.getAttribute('placeholder') || '').trim();
        out.push({ role: roleFor(el), name, value: ('value' in el ? el.value : null) });
      });
      return { url: location.href, title: document.title,
               text: (document.body ? document.body.innerText : '').slice(0, 4000), nodes: out };
    }"""

    def _snapshot(self) -> dict[str, Any]:
        data = self._page.evaluate(self._SNAP_JS)
        self.refmap = {}
        tree: list[dict[str, Any]] = []
        for n in data.get("nodes", []):
            role, name = n.get("role", ""), (n.get("name") or "").strip()
            node = {"role": role, "name": name}
            if n.get("value") is not None:
                node["value"] = n["value"]
            if role in ACTIONABLE and name:
                ref = f"e{len(self.refmap) + 1}"
                node["ref"] = ref
                self.refmap[ref] = {"role": role, "name": name}
            tree.append(node)
        text = data.get("text", "")
        snap = {"url": data.get("url"), "title": data.get("title"), "tree": tree, "text": text}
        self.log.append({"kind": "snapshot", "url": snap["url"], "title": snap["title"],
                         "refs": list(self.refmap.keys()), "text": text})
        return snap

    def _locator(self, ref: str):
        spec = self.refmap.get(ref)
        if not spec:
            raise HarnessError("STALE_REF", f"ref '{ref}' is not in the latest snapshot; re-read")
        return self._page.get_by_role(spec["role"], name=spec["name"]).first

    def _act(self, a: dict[str, Any]) -> dict[str, Any]:
        typ = a.get("type")
        self.log.append({"kind": "action", "action": a})
        if typ == "click":
            self._locator(a["ref"]).click(timeout=5000)
        elif typ == "type":
            self._locator(a["ref"]).fill(a.get("text", ""), timeout=5000)
        elif typ == "select":
            self._locator(a["ref"]).select_option(a.get("value"), timeout=5000)
        elif typ == "key":
            self._page.keyboard.press(a.get("key", "Enter"))
        elif typ == "scroll":
            self._page.mouse.wheel(0, int(a.get("ms", 400) or 400))
        elif typ == "wait":
            self._page.wait_for_timeout(min(3000, int(a.get("ms", 400) or 400)))
        else:
            raise HarnessError("BAD_ACTION", f"unknown action type {typ}")
        self._page.wait_for_timeout(150)
        return self._snapshot()

    # ----- public (called from other threads) -----
    def start_and_wait(self, timeout: float = 30.0) -> dict[str, Any]:
        self.start()
        status, payload = self._ready.get(timeout=timeout)
        if status != "ok":
            raise HarnessError("OPEN_FAILED", str(payload))
        return payload

    def send(self, cmd: str, payload: Any = None, timeout: float = 30.0) -> Any:
        reply: queue.Queue = queue.Queue()
        self._cmd.put((cmd, payload, reply))
        status, out = reply.get(timeout=timeout)
        if status != "ok":
            code, _, msg = str(out).partition(":")
            raise HarnessError(code if code in {"STALE_REF", "BAD_ACTION"} else "ACT_FAILED", str(out))
        return out


_SESSIONS: dict[str, _Session] = {}
# Logs retained PAST close() so a proband session still verifies its observed states after the browser
# is torn down (spec/exploration-depth-and-prototype-variety GAP-5). Without this, the clean
# drive→close→record order destroyed the groundedness evidence and every session recorded unverified.
_RETAINED_LOGS: dict[str, list[dict[str, Any]]] = {}
_MAX_RETAINED = 128


def _retain_log(session_id: str, log: list[dict[str, Any]]) -> None:
    _RETAINED_LOGS[session_id] = list(log)[-400:]
    while len(_RETAINED_LOGS) > _MAX_RETAINED:
        _RETAINED_LOGS.pop(next(iter(_RETAINED_LOGS)))


def open_session(url: str, prototype_id: str | None = None, persona_id: str | None = None) -> dict[str, Any]:
    if not available():
        raise HarnessError("PLAYWRIGHT_UNAVAILABLE",
                           "Playwright is not installed. Run `make playwright` (pip install playwright && playwright install chromium).")
    if len(_SESSIONS) >= max_browser_sessions():
        raise HarnessError("SESSION_CAP", f"too many live sessions (max {max_browser_sessions()}); close one first")
    from .services import stable_id
    sid = stable_id("psession", url, str(time.time()))
    sess = _Session(sid, url, prototype_id, persona_id)
    snap = sess.start_and_wait()
    _SESSIONS[sid] = sess
    return {"session_id": sid, "snapshot": snap}


def _require(session_id: str) -> _Session:
    s = _SESSIONS.get(session_id)
    if not s:
        raise HarnessError("SESSION_NOT_FOUND", f"no live session '{session_id}'")
    return s


def act(session_id: str, action: dict[str, Any]) -> dict[str, Any]:
    return {"snapshot": _require(session_id).send("act", action)}


def read(session_id: str) -> dict[str, Any]:
    return {"snapshot": _require(session_id).send("read")}


def close(session_id: str) -> dict[str, Any]:
    s = _SESSIONS.pop(session_id, None)
    if not s:
        return {"closed": False}
    _retain_log(session_id, s.log)   # keep the observed-states log so a later record_* still verifies
    try:
        s.send("close", timeout=10)
    except Exception:
        pass
    return {"closed": True, "session_id": session_id}


def list_sessions() -> list[dict[str, Any]]:
    return [{"session_id": s.session_id, "url": s.url, "prototype_id": s.prototype_id,
             "persona_id": s.persona_id, "steps": len(s.log)} for s in _SESSIONS.values()]


def session_log(session_id: str) -> list[dict[str, Any]] | None:
    s = _SESSIONS.get(session_id)
    if s:
        return list(s.log)
    return list(_RETAINED_LOGS[session_id]) if session_id in _RETAINED_LOGS else None
