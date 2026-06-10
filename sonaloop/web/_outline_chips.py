"""Outline chip CONTRACT (tracker: outline-chip-contract-every-row-kind-declares-its-chips-enfo).

Every row KIND the project outline emits declares its chips through this ONE registry: either a
builder(item) -> chips html, or an explicit NO-CHIPS sentinel naming WHY the kind carries none
(so the registry stays an inventory, not a loophole). _graph_outline consults it for EVERY row.
An UNREGISTERED kind renders chip-less in production (a page must never crash over a chip) but
lands in UNDECLARED_KINDS, which the contract test (tests/test_outline_chip_contract.py) asserts
empty after a full render — a new row kind cannot ship without declaring its chips.

Pure rendering: builders read what already rides the row item (the graph node dict under `node`,
the session record under `session`); data enrichment stays in services (the sessions pattern)."""
from __future__ import annotations

from .. import artifacts as _A_art
from .. import presentation as _pres
from ._components import _label
from ._html import h, raw
from ._i18n import t


class NoChips:
    """Explicit 'this row kind carries no chips' declaration, with the reason (what other
    affordance already carries the row's signal)."""

    def __init__(self, reason: str):
        self.reason = reason


# Row kinds seen at render time WITHOUT a registered entry — the contract test interrogates
# this set; production falls back to no chips instead of crashing the page.
UNDECLARED_KINDS: set[str] = set()

# Council modes are a bounded code enum (services.council_mode) — membership-guard the dynamic
# t() prefix (tests/test_i18n.py allowlists "council_mode_").
_MODES = ("discovery", "evaluation", "decision")


def _council_chips(item: dict) -> str:
    """Mode (derived the way the council page does — it rides node['mode']) + the statement count."""
    node = item.get("node") or {}
    mode = node.get("mode")
    chips = [_label(t("council_mode_" + mode), "var(--blue)")] if mode in _MODES else []
    chips.append(_label(t("chip_statements_n", n=int(node.get("n_statements") or 0))))
    return "".join(chips)


def _synthesis_chips(item: dict) -> str:
    """Finding count, always (a 0 reads as 'thin', not as a missing chip) + amber while in progress."""
    node = item.get("node") or {}
    chips = [_label(t("chip_findings_n", n=int(node.get("n_findings") or 0)))]
    if node.get("status") == "in_progress":
        chips.append(_label(t("running"), "var(--amber)"))
    return "".join(chips)


def _report_chips(item: dict) -> str:
    return _label(t("n_sections", n=int((item.get("node") or {}).get("n_sections") or 0)))


def _note_chips(item: dict) -> str:
    """A concept note shows its artifact kind (label/color from present() — data, not code);
    a plain note a quiet observation chip; built notes carry the built marker."""
    node = item.get("node") or {}
    ak = str(node.get("artifact_kind") or "")
    if ak:
        pr = _pres.present(ak)
        chips = [_label(pr.get("label") or ak, pr.get("color"))]
    else:
        chips = [_label(t("chip_observation"))]
    if node.get("prototype_ids"):
        chips.append(_label(t("chip_built"), "var(--green)"))
    return "".join(chips)


def _friction_count(sess: dict) -> int:
    # mirror of pages/sessions.py:_friction_count (importing pages from here would cycle)
    return sum(1 for s in sess.get("steps") or []
               if next((r["value"] for r in _A_art.friction_terms()
                        if r["term"] == (s.get("friction") or {}).get("level")), 0) > 0)


def _url_artifact_chips(item: dict) -> str:
    """The A/B label + the capture status (captured green / reference-only amber) — the
    reproducibility signal a council-pool artifact carries. URL artifacts are outline rows on the
    DEFAULT view (tracker: sonaloop/project-presence-contract); `kind` is bounded by the code enum
    services ARTIFACT_KINDS, normalized on add_artifact."""
    node = item.get("node") or {}
    chips = [_label(str(node.get("label") or "?"))]
    if (node.get("snapshot") or {}).get("ok"):
        chips.append(_label(t("artifact_captured"), "var(--green)"))
    else:
        chips.append(_label(t("artifact_capture_failed"), "var(--amber)"))
    return "".join(chips)


def _session_chips(item: dict) -> str:
    """Outcome (completed green / dropped red) + the friction count — the session child-row
    chips that previously lived in _graph_outline_sessions, now routed through the registry."""
    sess = item.get("session") or {}
    out = sess.get("outcome") or {}
    chips = [_label(t("completed"), "var(--green)") if out.get("completed")
             else _label(t("outcome_dropped", n=out.get("dropoff_step", 0)), "var(--red)")]
    n_fr = _friction_count(sess)
    if n_fr:
        chips.append(_label(t("friction_n", n=n_fr), "var(--amber)"))
    return "".join(str(c) for c in chips)


REGISTRY: dict[str, object] = {}


def _register(kind: str, entry) -> None:
    REGISTRY[kind] = entry


_register("council", _council_chips)
_register("synthesis", _synthesis_chips)
_register("report", _report_chips)
_register("note", _note_chips)
_register("session", _session_chips)
_register("url_artifact", _url_artifact_chips)
# Declared chip-less — each reason names the affordance that already carries the signal:
_register("prototype", NoChips("the fidelity kind pill + the parent funnel chip carry it"))
_register("live_url", NoChips("the funnel chip + its session child rows carry the signal"))
_register("flow", NoChips("the funnel chip + its session child rows carry the signal"))


def chips_html(item: dict) -> str:
    """The single consult point for an outline row: its declared chips wrapped in the .ol-chips
    slot, '' for a declared-chipless kind. An unknown kind renders chip-less and is recorded in
    UNDECLARED_KINDS (the contract test fails on it; production never crashes)."""
    kind = str(item.get("rkind") or "")
    entry = REGISTRY.get(kind)
    if entry is None:
        UNDECLARED_KINDS.add(kind)
        return ""
    if isinstance(entry, NoChips):
        return ""
    chips = entry(item)
    return h("span", {"class_": "ol-chips"}, raw(chips)) if chips else ""
