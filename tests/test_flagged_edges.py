"""Regression: faithful tri2quad must not merge across fold seams (QuADMesh #31).

A self-folding layer's two bordering strips meet along a *flagged edge* (thesis
p39 / Figure 4.1): an interior edge whose both endpoints are inner vertices.
Merging the two triangles across such an edge stitches the strips into a single
quad that spans the fold. The faithful matcher forbids those merges.
"""

from __future__ import annotations

import numpy as np
import pytest

from quadmesh.tri2quad import (
    _layer_priority,
    _match_tris_to_quads,
    _sweep_pairs,
    count_fold_bridge_quads,
)


@pytest.mark.parametrize("fixture_name", ["test_case_1", "test_case_2", "_block_o"])
def test_faithful_never_merges_across_fold(fixture_name, request):
    """No faithful-matched quad uses a flagged (fold-seam) edge as its diagonal."""
    mesh = request.getfixturevalue(fixture_name)
    tris = np.asarray(mesh.connectivity_list)[:, :3].astype(int)
    pts = mesh.points.copy()
    prio = _layer_priority(mesh, len(tris))
    seed, flagged = _sweep_pairs(mesh)
    # The canonical fixtures all contain at least one self-folding layer.
    assert flagged, f"{fixture_name}: expected a self-folding layer (flagged edges)"
    quads, _ = _match_tris_to_quads(
        tris, pts, prio, seed_pairs=seed, forbidden_edges=flagged
    )
    assert count_fold_bridge_quads(quads, flagged) == 0


def test_forbidden_edges_blocks_merge():
    """Two adjacent tris sharing a forbidden edge are left unmatched, not merged."""
    pts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]], dtype=float)
    tris = np.array([[0, 1, 2], [1, 3, 2]])  # share edge (1, 2)

    quads_free, leftover_free = _match_tris_to_quads(tris, pts)
    assert len(quads_free) == 1 and not leftover_free  # merged by default

    quads_block, leftover_block = _match_tris_to_quads(
        tris, pts, forbidden_edges={(1, 2)}
    )
    assert quads_block == [] and sorted(leftover_block) == [0, 1]  # blocked
