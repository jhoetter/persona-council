"""Project presence CONTRACT — nothing project-scoped is invisible on the DEFAULT project page
(tracker: sonaloop/project-presence-contract, user decision 2026-06-10).

Two declared layers, enforced by the gate test (tests/test_project_presence_contract.py, the
house pattern of the chip contract / LOC budget / i18n parity):

  - REGISTRY: every core artifact kind that carries a `project_id` declares WHERE it shows on
    the default project page — one of OUTLINE_ROW, NESTED_CHILD, SECTION_WITH_HEADER_CHIP, or
    (later, by explicit user decision only) HIDDEN_WITH_REASON. ALLOWED_HIDDEN is EMPTY: right
    now NO kind may register hidden.
  - LIST_SOURCES: every `list_*(project_id=…)` function on the services/storage surface maps to
    its registered kind — or to an explicit NotAnArtifact sentinel naming WHY that listing
    carries no artifact kind (so the mapping stays an inventory, not a loophole). The gate
    enumerates the surface (project_scoped_list_functions) and fails on an unmapped function:
    a new project-scoped artifact kind cannot ship without declaring where it shows.

presence_violations() is the single check the gate asserts empty.

The module also owns the tier-3 RESCUE section renderers the default project view embeds below
the outline — open questions, evidence assets and surveys, each following the hypotheses/
decisions idiom (an anchored `outlinecard` section + a header jump-chip on the project head, no
empty chrome). URL artifacts (A/B captures) are rescued as outline ROWS instead (_graph_outline
+ the _outline_chips registry). Pure read-only rendering: the page route fetches the lists (it
holds the Store) and passes them in."""
from __future__ import annotations

import inspect

from ._components import _icon, _label
from ._html import h, raw, fragment
from ._i18n import t

# ------------------------------------------------------------------ the presence declarations

OUTLINE_ROW = "outline_row"                          # a row in the round-grouped outline
NESTED_CHILD = "nested_child"                        # an indented child row under its parent
SECTION_WITH_HEADER_CHIP = "section_with_header_chip"  # an anchored section + header jump-chip
HIDDEN_WITH_REASON = "hidden_with_reason"            # forbidden today (ALLOWED_HIDDEN is empty)
PRESENCES = (OUTLINE_ROW, NESTED_CHILD, SECTION_WITH_HEADER_CHIP, HIDDEN_WITH_REASON)

# Kinds permitted to register hidden. EMPTY by user decision (2026-06-10): the user is mapping
# the product's flows and must not miss an artifact — adding a kind here requires an explicit
# user decision recorded on the tracker, never a layout convenience.
ALLOWED_HIDDEN: frozenset[str] = frozenset()


class Declared:
    """One kind's declared presence on the default project page: the presence class + a `where`
    note naming the concrete affordance that carries it (so the registry reads as a map of the
    page, not a checkbox)."""

    def __init__(self, presence: str, where: str, reason: str = ""):
        self.presence, self.where, self.reason = presence, where, reason


class NotAnArtifact:
    """Explicit 'this project-scoped listing is no artifact kind' declaration, with the reason
    (what the records are and which affordance carries their signal instead)."""

    def __init__(self, reason: str):
        self.reason = reason


REGISTRY: dict[str, Declared] = {
    "council": Declared(OUTLINE_ROW, "a plan-graph node row in the round-grouped outline"),
    "synthesis": Declared(OUTLINE_ROW, "a plan-graph node row in the round-grouped outline"),
    "report": Declared(OUTLINE_ROW, "an inline outline row at the end of its round (po=99)"),
    "note": Declared(OUTLINE_ROW, "an observation/concept row; a built concept pairs its prototype beneath"),
    "prototype": Declared(OUTLINE_ROW, "a standalone row, or nested under the concept note that realises it"),
    "flow": Declared(OUTLINE_ROW, "a session-subject parent row (the live_url idiom) once sessions walk it"),
    "url_artifact": Declared(OUTLINE_ROW, "an artifact-style row with the A/B label + capture-status chips"),
    "session": Declared(NESTED_CHILD, "an indented child row under its subject (prototype/live_url/flow)"),
    "section": Declared(OUTLINE_ROW, "the theme filter bar + phase/round groupings OVER the outline "
                                     "(an overlay grouping of nodes, not a row of its own)"),
    "hypothesis": Declared(SECTION_WITH_HEADER_CHIP, "#hypotheses section below the outline + header jump-chip"),
    "decision": Declared(SECTION_WITH_HEADER_CHIP, "#decisions section below the outline + header jump-chip"),
    "open_question": Declared(SECTION_WITH_HEADER_CHIP, "#open-questions section + header jump-chip (open count)"),
    "asset": Declared(SECTION_WITH_HEADER_CHIP, "#assets thumbnail section + header jump-chip "
                                                "(deliverables out first, then evidence in)"),
    "survey": Declared(SECTION_WITH_HEADER_CHIP, "#surveys section (rows → /surveys/{id}) + header jump-chip"),
}

# Every list_*(project_id=…) family on the services/storage surface → its registered kind.
# Councils/syntheses have no such family (they ride the plan graph) but are registered above —
# the gate asserts the full core-kind inventory separately.
LIST_SOURCES: dict[str, str | NotAnArtifact] = {
    # the services surface
    "list_artifacts": "url_artifact",
    "list_assets": "asset",
    "list_decisions": "decision",
    "list_flows": "flow",
    "list_hypotheses": "hypothesis",
    "list_notes": "note",
    "list_prototypes_artifacts": "prototype",
    "list_sections": "section",
    "list_surveys": "survey",
    "list_usability_sessions": "session",
    # the storage-only surface
    "list_open_questions": "open_question",
    "list_prototypes": "prototype",
    "list_reports": "report",
    # engine/meta RECORDS, not artifact kinds — each names why and what carries the signal:
    "list_runs": NotAnArtifact(
        "engine run STATE, not an artifact — its products (councils/syntheses/reports) are the "
        "registered kinds; the pulse/stalled strip reads it"),
    "list_methodology_judgments": NotAnArtifact(
        "plan-engine gate metadata riding its verify task — surfaced through the synthesis that "
        "convergence produced, not a standalone artifact"),
    "list_prediction_outcomes": NotAnArtifact(
        "calibration-ledger rows scored against reality — surfaced via calibration_report/"
        "calibration_trend, not project-page artifacts"),
}


def project_scoped_list_functions() -> set[str]:
    """The enumerable surface the gate sweeps: every `list_*` callable on the services package
    and on storage.Store whose signature carries `project_id`. A NEW project-scoped artifact
    kind necessarily extends this family — and then fails the gate until LIST_SOURCES +
    REGISTRY declare it."""
    from .. import services
    from ..storage import Store
    names: set[str] = set()
    for name in dir(services):
        if not name.startswith("list_"):
            continue
        fn = getattr(services, name)
        if not callable(fn):
            continue
        try:
            params = inspect.signature(fn).parameters
        except (TypeError, ValueError):
            continue
        if "project_id" in params:
            names.add(name)
    for name, fn in inspect.getmembers(Store, predicate=inspect.isfunction):
        if name.startswith("list_") and "project_id" in inspect.signature(fn).parameters:
            names.add(name)
    return names


def presence_violations() -> list[str]:
    """Every way the contract can be broken, as human-readable findings (the gate asserts this
    empty): an unmapped list function, a stale mapping, a kind without a declaration, a missing
    `where`/reason, an unknown presence value, or a hidden registration outside ALLOWED_HIDDEN."""
    out: list[str] = []
    surface = project_scoped_list_functions()
    for name in sorted(surface - set(LIST_SOURCES)):
        out.append(f"{name}(project_id=…) is on the surface but unmapped in LIST_SOURCES — declare "
                   "its kind's project-page presence (or an explicit NotAnArtifact reason)")
    for name in sorted(set(LIST_SOURCES) - surface):
        out.append(f"LIST_SOURCES maps {name}() which is no longer on the surface — drop the stale entry")
    for name, target in LIST_SOURCES.items():
        if isinstance(target, NotAnArtifact):
            if not target.reason:
                out.append(f"NotAnArtifact for {name}() must carry a reason")
            continue
        if target not in REGISTRY:
            out.append(f"kind {target!r} (listed by {name}) has no presence declaration in REGISTRY")
    for kind, d in REGISTRY.items():
        if d.presence not in PRESENCES:
            out.append(f"kind {kind!r} declares an unknown presence {d.presence!r}")
        if not d.where:
            out.append(f"kind {kind!r} must name WHERE it shows on the default project page")
        if d.presence == HIDDEN_WITH_REASON and kind not in ALLOWED_HIDDEN:
            out.append(f"kind {kind!r} registers hidden — forbidden (user decision 2026-06-10: "
                       "nothing project-scoped is invisible on the default project page)")
    return out


# ------------------------------------------------------- the tier-3 rescue section renderers


def survey_status_pill(status: str) -> str:
    """Survey lifecycle pill (a lifecycle, not a vocabulary). Resolved per request so the labels
    follow the active UI language. Shared by the survey pages and the project surveys section."""
    pills = {"draft": (t("survey_status_draft"), "var(--muted)"),
             "open": (t("survey_status_open"), "var(--green)"),
             "closed": (t("survey_status_closed"), "var(--violet)")}
    label, color = pills.get(status, pills["draft"])
    return _label(label, color)


def asset_direction(asset: dict) -> str:
    """An asset record's flow direction: `out` (deliverable produced from the project) or `in`
    (evidence brought into it). Direction-less records predate the field and ARE evidence —
    back-compat without a migration (ticket project-assets-direction-deliverables-page-section)."""
    return "out" if asset.get("direction") == "out" else "in"


def asset_rows(assets: list) -> str:
    """Asset rows (files/images/screenshots, ticket attach-evidence-files-mcp): image assets
    render a thumbnail from the static /data mount; every row carries kind + direction pills and
    `filename · size`. Deliverables (direction out) link as downloads. Shared by the default-view
    #assets section and the retired graph view's floating panel."""
    rows = []
    for a in assets:
        is_img = a.get("kind") in ("image", "screenshot")
        is_out = asset_direction(a) == "out"
        link = {"href": a.get("url", "#"), "target": "_blank", "rel": "noopener"}
        if is_out:  # a deliverable file: hand it to the user, don't render it in a tab
            link = {"href": a.get("url", "#"), "download": a.get("filename", "")}
        thumb = (h("a", dict(link),
                   h("img", {"src": a.get("url", ""), "alt": a.get("title", ""), "loading": "lazy",
                             "style": "max-height:64px;max-width:120px;border-radius:6px;display:block"}))
                 if is_img else raw(_icon("download" if is_out else "external")))
        size_kb = f'{max(1, int(a.get("bytes", 0)) // 1024)} KB'
        dir_pill = (h("span", {"class_": "pill", "style": "border-color:var(--green);color:var(--green)"},
                      t("asset_dir_out")) if is_out else h("span", {"class_": "pill"}, t("asset_dir_in")))
        rows.append(h("div", {"class_": "strow"},
                      thumb, " ",
                      h("a", dict(link), h("b", {}, a.get("title") or a.get("filename", ""))), " ",
                      h("span", {"class_": "pill"}, t("asset_kind_" + (a.get("kind") or "file"))), " ",
                      dir_pill, " ",
                      h("span", {"class_": "muted small"}, f'{a.get("filename", "")} · {size_kb}'
                        + (f' · {a.get("notes")}' if a.get("notes") else ""))))
    return "".join(rows)


def assets_section_html(assets: list) -> str:
    """The project's assets as a default-view section (anchor #assets): the deliverables that went
    OUT of the project first (download links), then the evidence that came in — each group with its
    own sub-heading when both exist, plain rows when only one direction is present. Empty string
    when there are none (no empty chrome)."""
    if not assets:
        return ""
    outgoing = [a for a in assets if asset_direction(a) == "out"]
    incoming = [a for a in assets if asset_direction(a) == "in"]
    if outgoing and incoming:
        body = fragment(h("div", {"class_": "oqp-h"}, f'{t("asset_deliverables_h")} ({len(outgoing)})'),
                        raw(asset_rows(outgoing)),
                        h("div", {"class_": "oqp-h", "style": "margin-top:10px"},
                          f'{t("asset_evidence_h")} ({len(incoming)})'),
                        raw(asset_rows(incoming)))
    else:
        body = raw(asset_rows(outgoing + incoming))
    return h("div", {"class_": "outlinecard", "id": "assets", "style": "margin-top:14px"},
             h("h2", {"style": "margin:0 0 6px"}, f'{t("assets_h")} ({len(assets)})'), body)


def open_questions_section_html(oqs: list) -> str:
    """The project's open questions as a default-view section (anchor #open-questions): the open
    ones up front (the header counts these), resolved ones muted below — formerly only the
    ?view=graph floating panel showed them. Empty string when there are none."""
    if not oqs:
        return ""
    open_qs = [o for o in oqs if o.get("status") == "open"]
    resolved = [o for o in oqs if o.get("status") != "open"]
    blocks = []
    if open_qs:
        blocks.append(h("ul", {"style": "margin:6px 0 0 18px"},
                        fragment(*(h("li", {}, o.get("text", "")) for o in open_qs))))
    if resolved:
        blocks.append(h("div", {"class_": "oqp-h", "style": "margin-top:10px"},
                        f'{t("oq_resolved_h")} ({len(resolved)})'))
        blocks.append(h("ul", {"class_": "muted", "style": "margin:6px 0 0 18px"},
                        fragment(*(h("li", {}, o.get("text", "")) for o in resolved))))
    return h("div", {"class_": "outlinecard", "id": "open-questions", "style": "margin-top:14px"},
             h("h2", {"style": "margin:0 0 6px"}, f'{t("open_questions_h")} ({len(open_qs)})'),
             fragment(*blocks))


def surveys_section_html(surveys: list) -> str:
    """The project's surveys as a default-view section (anchor #surveys): each row links to its
    /surveys/{id} detail with the lifecycle pill + question/response counts — surveys carry a
    project_id but never appeared on the project page before this contract. Empty when none."""
    if not surveys:
        return ""
    rows = []
    for s in surveys:
        rows.append(h("div", {"class_": "strow"},
                      h("a", {"href": f'/surveys/{s["id"]}'},
                        raw(_icon("plan")), " ", h("b", {}, s.get("title", ""))), " ",
                      raw(survey_status_pill(s.get("status", "draft"))), " ",
                      h("span", {"class_": "muted small"},
                        f'{t("n_questions", n=len(s.get("questions") or []))} · '
                        f'{t("n_responses", n=s.get("response_count") or 0)} · '
                        f'{(s.get("created_at") or "")[:10]}')))
    return h("div", {"class_": "outlinecard", "id": "surveys", "style": "margin-top:14px"},
             h("h2", {"style": "margin:0 0 6px"}, f'{t("surveys_h")} ({len(surveys)})'),
             fragment(*rows))
