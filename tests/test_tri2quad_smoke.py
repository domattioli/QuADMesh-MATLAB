"""Smoke tests for tri2quad: doesn't crash, produces valid CHILmesh."""

from __future__ import annotations

import numpy as np

from quadmesh import tri2quad


def _count_quads(mesh) -> int:
    """A row is a quad iff it has 4 distinct verts; tri otherwise (with padding)."""
    cl = mesh.connectivity_list
    if cl.shape[1] != 4:
        return 0
    return int((cl[:, 2] != cl[:, 3]).sum())


def test_tri2quad_runs(test_case_1):
    out = tri2quad(test_case_1, can_remove_edges=True)
    assert out is not None
    assert out.n_elems > 0
    assert out.n_verts > 0
    assert out.connectivity_list.shape[0] == out.n_elems


def test_tri2quad_outputs_mostly_quads(test_case_1):
    out = tri2quad(test_case_1, can_remove_edges=True)
    n_quads = _count_quads(out)
    ratio = n_quads / max(out.n_elems, 1)
    # Loosely: most elems should be quads (≥50% is a sane lower bound for v0.1).
    assert ratio >= 0.5, f"only {ratio:.1%} quads — too low"


def test_tri2quad_no_zero_area(test_case_1):
    """All output elems should have non-zero signed area."""
    out = tri2quad(test_case_1, can_remove_edges=True)
    areas = out.signed_area()
    assert np.all(np.abs(areas) > 1e-12), f"{(np.abs(areas) <= 1e-12).sum()} zero-area elems"
