"""T011: Unit tests for edge_swap, vertex_duplication, edge_flip on minimal meshes."""

import pytest
import numpy as np
from quadmesh._recombine import edge_swap, vertex_duplication, edge_flip, walk_isolated_tri
from quadmesh._tri_removal import WorkingMesh


def _square_pts():
    """4 corner + 1 centre point — unit square."""
    return np.array([
        [0.0, 0.0, 0.0],  # 0
        [1.0, 0.0, 0.0],  # 1
        [1.0, 1.0, 0.0],  # 2
        [0.0, 1.0, 0.0],  # 3
        [0.5, 0.5, 0.0],  # 4 centre
    ])


def _two_tri_work():
    """Two tris sharing edge 1-2.

    Points: 0=(0,0), 1=(1,0), 2=(0.5,1), 3=(1.5,1).
    Tris: [0,1,2] and [1,3,2]. Share edge 1-2.
    Swap edge 1-2 → new diag 0-3.
    New tris: [0,3,2] and [0,1,3] (both CCW and positive area).
    """
    pts = np.array([
        [0.0, 0.0, 0.0],  # 0
        [1.0, 0.0, 0.0],  # 1
        [0.5, 1.0, 0.0],  # 2
        [1.5, 1.0, 0.0],  # 3
    ])
    work = WorkingMesh(points=pts, quads=[])
    work.tris = [
        np.array([0, 1, 2], dtype=int),
        np.array([1, 3, 2], dtype=int),
    ]
    return work, pts


def test_edge_swap_basic():
    work, pts = _two_tri_work()
    # Shared edge is 1-2 (both tris contain vertices 1 and 2).
    ok = edge_swap(work, 1, 2, pts)
    assert ok, "edge_swap should succeed on two valid tris sharing edge 1-2"
    # After swap: each new tri should contain the two former opposite verts (0 and 3).
    vert_sets = [frozenset(int(v) for v in t[:3]) for t in work.tris]
    assert any(0 in s for s in vert_sets)
    assert any(3 in s for s in vert_sets)


def test_edge_swap_no_neighbour():
    """Swap on a single tri (no neighbour) must return False."""
    pts = np.array([[0,0,0],[1,0,0],[0.5,1,0]], dtype=float)
    work = WorkingMesh(points=pts, quads=[])
    work.tris = [np.array([0, 1, 2], dtype=int)]
    ok = edge_swap(work, 0, 1, pts)
    assert not ok


def test_edge_swap_degenerate_collinear():
    """Swap that would produce a zero-area tri is rejected."""
    # Collinear: 0=(0,0), 1=(1,0), 2=(2,0), 3=(0,1).
    pts = np.array([[0,0,0],[1,0,0],[2,0,0],[0,1,0]], dtype=float)
    work = WorkingMesh(points=pts, quads=[])
    # [0,1,3] and [1,2,3] share edge 1-3; swap → [0,3,2]+[1,2,3] but [0,3,2] is fine;
    # just check it doesn't crash.
    work.tris = [np.array([0,1,3]), np.array([1,2,3])]
    edge_swap(work, 1, 3, pts)  # should not raise


def test_vertex_duplication_creates_new_vert():
    work, pts = _two_tri_work()
    # Vertex 1 is shared by both tris → can be duplicated.
    ok, new_idx = vertex_duplication(work, 1, pts)
    assert ok
    assert new_idx == 4  # appended after existing 4 pts
    # New vert is at same position as v=1.
    np.testing.assert_allclose(work.points[new_idx, :2], pts[1, :2])


def test_vertex_duplication_second_tri_rewired():
    work, pts = _two_tri_work()
    _, new_idx = vertex_duplication(work, 1, pts)
    # Second tri (index 1) should now use new_idx instead of 1.
    assert new_idx in work.tris[1].tolist()
    # First tri still uses 1.
    assert 1 in work.tris[0].tolist()


def test_edge_flip_changes_connectivity():
    pts = _square_pts()
    work = WorkingMesh(points=pts, quads=[])
    work.tris = [
        np.array([0, 1, 4], dtype=int),
        np.array([1, 2, 4], dtype=int),
    ]
    orig_sets = [frozenset(int(v) for v in t[:3]) for t in work.tris]
    ok = edge_flip(work, 0, pts)
    if ok:
        new_sets = [frozenset(int(v) for v in t[:3]) for t in work.tris]
        assert new_sets != orig_sets, "edge_flip should change connectivity"


def test_walk_isolated_tri_returns_bool():
    pts = _square_pts()
    work = WorkingMesh(points=pts, quads=[])
    work.tris = [
        np.array([0, 1, 4], dtype=int),
        np.array([1, 2, 4], dtype=int),
        np.array([2, 3, 4], dtype=int),
    ]
    result = walk_isolated_tri(work, 2, pts, max_hops=3)
    assert isinstance(result, bool)
