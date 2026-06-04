"""C3 — generic DAG UI layout (spec/methodology-constellations.md §5).

The layout is derived from the consumes-DAG + recorded node counts + artifact tags, with NO
phase-key/tag literals. double_diamond_deep still renders three diamonds with both prototypes
routed (solid idea->artifact, dashed artifact->tested-at); a different-shaped methodology renders
too; the interactive graph builds without error.
"""
from __future__ import annotations

import re
from pathlib import Path

from persona_council import methodology as M
from persona_council import runtime, services, web


def _run(store, tmp_path, key):
    import persona_council.prototypes as P
    P.prototypes_dir = lambda: tmp_path / "protos"
    proj = M.start_methodology_project(key, "How might we test the layout?", key,
                                       persona_ids=["p1"], store=store)
    runtime.run_methodology(proj["id"], store=store)
    return services.get_project_graph(proj["id"], store=store)


def test_deep_renders_three_diamonds_with_routed_artifacts(store, tmp_path):
    g = _run(store, tmp_path, "double_diamond_deep")
    ml = web._methodology_layout(g)
    assert ml is not None
    assert len(ml["diamonds"]) == 3                      # three emergent fan->waist diamonds
    assert len(ml["proto_pos"]) == 2                     # lo-fi + mid-fi placed
    solid = [e for e in ml["proto_edges"] if not e[2]]
    dashed = [e for e in ml["proto_edges"] if e[2]]
    assert len(solid) == 2 and len(dashed) == 2          # idea->artifact + artifact->tested-at
    assert "rgdata" in web._graph_interactive(g)         # interactive graph builds


def test_other_shaped_methodology_renders(store, tmp_path):
    g = _run(store, tmp_path, "dschool_micro")
    ml = web._methodology_layout(g)
    assert ml is not None and len(ml["diamonds"]) == 2 and len(ml["proto_pos"]) == 1
    assert "rgdata" in web._graph_interactive(g)


def test_layout_has_no_phase_key_literals():
    """grep: the layout must not hardcode any methodology's phase keys or fidelity vocab."""
    src = Path(web._graph.__file__).read_text()
    lo = src[src.index("def _methodology_layout"):src.index("def _graph_interactive")]
    for lit in ('"ideate"', '"refine"', '"lofi_select"', '"deliver"', "build_col", "test_conv",
                '"lofi"', '"midfi"'):
        assert lit not in lo, lit
