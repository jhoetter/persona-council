"""Q quality bar (spec/refactor-plan.md): no source module is a god-file.

The behavior-preserving package split (S/Q phase) brought every source file under the
~800-LOC target. This guard keeps it that way — if a module grows past the bar, split it
(or record a justified exception here with a reason).
"""
from __future__ import annotations

from pathlib import Path

LOC_BAR = 800
# Justified exceptions (path -> reason). Keep empty; add only with a real justification.
EXCEPTIONS: dict[str, str] = {}


def test_no_source_file_exceeds_loc_bar():
    pkg = Path(__file__).resolve().parent.parent / "sonaloop"
    offenders = []
    for f in sorted(pkg.rglob("*.py")):
        rel = str(f.relative_to(pkg.parent))
        if rel in EXCEPTIONS:
            continue
        n = sum(1 for _ in f.open(encoding="utf-8"))
        if n > LOC_BAR:
            offenders.append(f"{rel}: {n} LOC")
    assert not offenders, "god-file(s) over the LOC bar — split them:\n  " + "\n  ".join(offenders)
