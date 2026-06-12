"""Regression: a persona with no avatar (avatar=None, the default when no image is
generated) must still render. Previously `_avatar` did `p.get("avatar", {}).get(...)`
which raised AttributeError on an explicit None, 500-ing the overview page.

P5 audit addition: an avatar RECORD whose image file is missing on disk (snapshots carry
the record, not always the binary) renders the initials fallback — never a broken <img>."""
from __future__ import annotations

from sonaloop import config
from sonaloop.web import _avatar


def test_avatar_handles_missing_none_and_dict(tmp_path, monkeypatch):
    # missing key -> initials fallback, no raise
    assert "av" in _avatar({"display_name": "Markus Brandt", "id": "p1"})
    # explicit None (the regression) -> initials fallback, no raise
    assert "av" in _avatar({"display_name": "Petra Lindner", "id": "p2", "avatar": None})
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    rec = {"display_name": "X", "id": "p3", "avatar": {"path": "data/avatars/x.png"}}
    # avatar record but the file does NOT exist -> initials fallback, no broken <img>
    html = _avatar(rec)
    assert "<img" not in html and "X" in html
    # file exists under DATA_DIR -> the real portrait <img>
    (tmp_path / "avatars").mkdir(parents=True)
    (tmp_path / "avatars" / "x.png").write_bytes(b"\x89PNG")
    html = _avatar(rec)
    assert "<img" in html and "x.png" in html
