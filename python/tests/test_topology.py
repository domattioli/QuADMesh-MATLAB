"""Tests for _topology helpers: CCW edges, merge_tri_pair."""

from __future__ import annotations

import numpy as np
import pytest

from chilmesh import CHILmesh

from quadmesh._topology import (
    ccw_edges_around_vert,
    merge_tri_pair,
    merge_tri_pairs,
)


@pytest.fixture
def two_tri_mesh():
    """Two tris sharing edge (1,2). Vert layout:
        0 ---- 1
        |    / |
        |   /  |
        |  /   |
        2 ---- 3
    Tris: (0,2,1) CCW; (1,2,3) CCW.
    """
    points = np.array(
        [[0.0, 1.0, 0.0],
         [1.0, 1.0, 0.0],
         [0.0, 0.0, 0.0],
         [1.0, 0.0, 0.0]],
        dtype=float,
    )
    conn = np.array([[0, 2, 1], [1, 2, 3]], dtype=int)
    return CHILmesh(conn, points)


def test_ccw_edges_around_vert_returns_arrays(two_tri_mesh):
    res = ccw_edges_around_vert(two_tri_mesh, [0, 1, 2, 3])
    assert len(res) == 4
    for arr in res:
        assert arr.ndim == 1
        assert arr.dtype.kind == "i"


def test_ccw_edges_unique(two_tri_mesh):
    """Each vert's listed edges are unique."""
    for arr in ccw_edges_around_vert(two_tri_mesh, [0, 1, 2, 3]):
        assert len(set(arr.tolist())) == arr.size


def test_merge_tri_pair_returns_quad(two_tri_mesh):
    quad = merge_tri_pair(two_tri_mesh, 0, 1)
    assert quad.shape == (4,)
    assert len(set(quad.tolist())) == 4  # 4 distinct verts
    assert set(quad.tolist()) == {0, 1, 2, 3}


def test_merge_tri_pair_is_ccw(two_tri_mesh):
    """Resulting quad has positive signed area (CCW)."""
    quad = merge_tri_pair(two_tri_mesh, 0, 1)
    pts = two_tri_mesh.points[quad, :2]
    # Shoelace.
    x = pts[:, 0]
    y = pts[:, 1]
    area = 0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1))
    assert area > 0


def test_merge_tri_pairs_batch(two_tri_mesh):
    res = merge_tri_pairs(two_tri_mesh, np.array([[0, 1]]))
    assert res.shape == (1, 4)


def test_merge_tri_pair_non_adjacent_raises():
    """Tris that don't share an edge can't be merged."""
    points = np.array(
        [[0.0, 0.0, 0.0],
         [1.0, 0.0, 0.0],
         [0.0, 1.0, 0.0],
         [3.0, 0.0, 0.0],
         [4.0, 0.0, 0.0],
         [3.0, 1.0, 0.0]],
        dtype=float,
    )
    conn = np.array([[0, 1, 2], [3, 4, 5]], dtype=int)
    mesh = CHILmesh(conn, points)
    with pytest.raises(ValueError):
        merge_tri_pair(mesh, 0, 1)
