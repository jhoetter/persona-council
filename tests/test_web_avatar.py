"""Regression: a persona with no avatar (avatar=None, the default when no image is
generated) must still render. Previously `_avatar` did `p.get("avatar", {}).get(...)`
which raised AttributeError on an explicit None, 500-ing the overview page."""
from __future__ import annotations

from sonaloop.web import _avatar


def test_avatar_handles_missing_none_and_dict():
    # missing key -> initials fallback, no raise
    assert "av" in _avatar({"display_name": "Markus Brandt", "id": "p1"})
    # explicit None (the regression) -> initials fallback, no raise
    assert "av" in _avatar({"display_name": "Petra Lindner", "id": "p2", "avatar": None})
    # real avatar dict -> img tag
    html = _avatar({"display_name": "X", "id": "p3", "avatar": {"path": "data/avatars/x.png"}})
    assert "<img" in html and "x.png" in html
