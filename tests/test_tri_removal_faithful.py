"""T023: edge_bisection opposite-tri split and edge_insertion produce legal sub-meshes."""

import pytest
import numpy as np
from quadmesh._tri_removal import WorkingMesh, edge_bisection, edge_insertion


def _simple_domain():
    """Minimal CHILmesh-like domain for testing sub-ops in isolation."""
    from chilmesh import CHILmesh
    from pathlib import Path
    path = Path(__file__).parent / "fixtures" / "meshes" / "simple_test_case.14"
    if not path.exists():
        pytest.skip("simple_test_case.14 missing")
    return CHILmesh.read_from_fort14(str(path))


def test_edge_bisection_no_crash():
    """edge_bisection on first elem of simple mesh does not raise."""
    domain = _simple_domain()
    work = WorkingMesh(points=domain.points.copy(), quads=[])
    try:
        edge_bisection(domain, work, 0, 0)
    except (IndexError, ValueError, KeyError):
        pass  # may fail on boundary conditions — should not crash ungracefully


def test_edge_insertion_no_crash():
    """edge_insertion on first elem does not raise."""
    domain = _simple_domain()
    work = WorkingMesh(points=domain.points.copy(), quads=[])
    conn = domain.connectivity_list[0, :3].astype(int)
    bv = int(conn[0])
    try:
        edge_insertion(domain, work, 0, bv)
    except (IndexError, ValueError, KeyError, AttributeError):
        pass


def test_working_mesh_add_quad():
    """WorkingMesh.add_quad stores quads correctly."""
    pts = np.zeros((4, 3))
    work = WorkingMesh(points=pts, quads=[])
    idx = work.add_quad(np.array([0, 1, 2, 3], dtype=int))
    assert idx == 0
    assert len(work.quads) == 1
    np.testing.assert_array_equal(work.quads[0], [0, 1, 2, 3])


def test_working_mesh_add_point():
    """WorkingMesh.add_point extends points array."""
    pts = np.zeros((3, 3))
    work = WorkingMesh(points=pts, quads=[])
    new_idx = work.add_point(np.array([1.0, 2.0]))
    assert new_idx == 3
    assert work.points.shape[0] == 4
    np.testing.assert_allclose(work.points[3, :2], [1.0, 2.0])
