"""Council votes are unified onto the stance scale (suggestions/stance_scale.json — the ONE
positivity vocabulary). Guards the invariants:
  - record_council normalizes every vote through the scale (canonical `vote` term + a `stance`
    {value,label}; an unresolvable token survives as stance.label_raw — never silently dropped).
  - the vote charts bucket by stance VALUE in scale order (+2 → −2) with scale colors/labels —
    all five terms representable, so a "conditional" vote can no longer vanish from the donut.
  - legacy stored uppercase tokens (SUPPORT/MAYBE/ABSTAIN/OPPOSE) chart identically via the aliases.
  - the per-persona score is the MEAN of the resolved stance values (−2..+2), its color the nearest
    scale value's — no token-specific coefficients, no label-keyword matching.
"""
from __future__ import annotations

from sonaloop import artifacts as A
from sonaloop import services
from sonaloop.web._i18n import t
from sonaloop.web._synthesis import _personas_by_sentiment_html, _vote_parts


def _sessions(votes):
    return [{"votes": [{"persona_id": "p1", "vote": v} for v in votes]}]


def test_record_council_normalizes_votes_onto_the_scale(store):
    pid = services.start_project("M", "hmw?", None, persona_ids=[], store=store)["id"]
    c = services.record_council(pid, "Bauen?", [], [], proposal="X", store=store, key="v",
                                votes=[{"persona_id": "pa", "vote": "MAYBE"},
                                       {"persona_id": "pb", "vote": "lieber nicht??"}])
    v1, v2 = c["votes"]
    # legacy token → canonical term + resolved stance; the reader-compatible shape is kept
    assert v1["persona_id"] == "pa" and v1["vote"] == "conditional"
    assert v1["stance"] == {"value": 1, "label": "conditional"}
    # unresolvable token → neutral VALUE bucket, the raw token traced — never silently dropped
    assert v2["vote"] == "neutral"
    assert v2["stance"] == {"value": 0, "label": "neutral", "label_raw": "lieber nicht??"}


def test_conditional_vote_appears_in_the_distribution():
    # "conditional" — the canonical stance term! — used to be dropped from donut/legend/stacked bars
    tot, parts = _vote_parts(_sessions(["conditional"]))
    assert tot[1] == 1
    cnt, color, label = next(p for p in parts if p[0] == 1)
    assert color == A.stance_meta(1)["color"] and label == t(A.stance_meta(1)["label_key"])


def test_legacy_uppercase_votes_bucket_identically():
    # the pre-change stored shape: uppercase tokens in `vote`, no stance sub-dict
    tot, parts = _vote_parts(_sessions(["SUPPORT", "SUPPORT", "MAYBE", "ABSTAIN", "OPPOSE"]))
    assert dict(tot) == {2: 2, 1: 1, 0: 1, -2: 1}                  # token → value bucket via aliases
    assert [c for c, _, _ in parts] == [2, 1, 1, 0, 1]             # scale order +2 → −2, all five terms
    assert [c for _, c, _ in parts] == [A.stance_meta(v)["color"] for v in (2, 1, 0, -1, -2)]


def test_unresolvable_vote_token_does_not_vanish_from_the_charts():
    tot, parts = _vote_parts(_sessions(["banana!!"]))
    assert tot[0] == 1                                             # neutral value bucket (label_raw path)
    assert sum(c for c, _, _ in parts) == 1


def test_persona_score_is_the_mean_of_stance_values(store):
    html = _personas_by_sentiment_html(store, _sessions(["SUPPORT", "conditional", "OPPOSE"]))
    assert "+0.3" in html                                          # mean(+2, +1, −2) = +0.333
    # 0.33 sits nearest the neutral scale value → its color (value bucket, not keyword matching)
    assert f'color:{A.stance_meta(0)["color"]}' in html


def test_vote_tally_keys_are_canonical_terms():
    tally = A.vote_tally([{"vote": "SUPPORT"}, {"vote": "conditional"}, {"vote": ""}])
    assert tally == {"support": 1, "conditional": 1, "neutral": 0, "skeptical": 0, "oppose": 0}
    assert list(tally) == ["support", "conditional", "neutral", "skeptical", "oppose"]   # +2 → −2
