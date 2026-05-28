"""Faithful-path sub-op tests (T023).

Covers the MATLAB ``edgeBisection`` Case 2 opposite-tri split
(``_tri_removal._split_opposing_tri`` + its wiring in ``route_leftover_tri``).

The split fires when an interior layer-boundary edge is bisected: the new
midpoint lands on the edge shared with the iLayer-1 neighbour, which must be
re-triangulated at that midpoint to keep the working tri domain conforming.
Assertions check that the neighbour is replaced by exactly two tris that
partition it (no overlap, original verts retained, both CCW).
"""

from __future__ import annotations

import numpy as np
import pytest

from chilmesh import CHILmesh

from quadmesh._tri_removal import (
    WorkingMesh,
    _split_opposing_tri,
    edge_bisection,
    route_leftover_tri,
)


def _tri_area(conn: np.ndarray, points: np.ndarray) -> float:
    p = points[np.asarray(conn, dtype=int), :2]
    x, y = p[:, 0], p[:, 1]
    return 0.5 * abs(np.sum(x * np.roll(y, -1) - y * np.roll(x, -1)))


def _signed_area(conn: np.ndarray, points: np.ndarray) -> float:
    p = points[np.asarray(conn, dtype=int), :2]
    x, y = p[:, 0], p[:, 1]
    return 0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1))


@pytest.fixture
def two_tri_pair():
    """Two tris sharing interior edge (1,2):

        2 ---- 3
        |\\    /
        | \\  /
        |  \\/
        0 - 1

    Verts 0,1,2,3 (all referenced). Tris: 0=(0,1,2), 1=(1,3,2).
    Shared edge (1,2) is interior (belongs to both tris); it is stored in the
    reverse cyclic direction inside tri 1 — exercising the edge-orientation
    robustness of ``edge_bisection``.
    """
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.5, 1.0, 0.0],
            [1.5, 1.0, 0.0],
        ],
        dtype=float,
    )
    conn = np.array([[0, 1, 2], [1, 3, 2]], dtype=int)
    return CHILmesh(conn, points)


def _shared_edge_id(mesh: CHILmesh, v_a: int, v_b: int) -> int:
    for eid in range(mesh.n_edges):
        verts = set(mesh.edge2vert(eid).ravel().astype(int).tolist())
        if verts == {v_a, v_b}:
            return eid
    raise AssertionError(f"edge ({v_a},{v_b}) not found")


def test_split_opposing_tri_replaces_neighbor_with_two_tris(two_tri_pair):
    """Bisecting tri 1's shared edge (1,2) must split neighbour tri 0=(0,1,2)
    into two tris that partition it at the inserted midpoint."""
    mesh = two_tri_pair
    eid = _shared_edge_id(mesh, 1, 2)
    opp_area_before = _tri_area([0, 1, 2], mesh.points)
    n_elems_before = mesh.connectivity_list.shape[0]

    # Bisect the shared edge of tri 1 (consumes tri 1, adds midpoint np_id).
    local = mesh.elem2edge(1).ravel().astype(int).tolist().index(eid)
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    np_id = edge_bisection(mesh, work, tri_elem_id=1, bdy_edge_idx_in_tri=local)
    assert np_id is not None

    new_id = _split_opposing_tri(mesh, eid, np_id, consumed_tri_id=1)
    assert new_id is not None

    # Exactly one new element row appended.
    assert mesh.connectivity_list.shape[0] == n_elems_before + 1

    # The neighbour (tri 0) row and the appended row both reference np_id and
    # the apex (vert 0), and together cover verts {0,1,2,np_id}.
    tri_a = mesh.connectivity_list[0, :3].astype(int).tolist()
    tri_b = mesh.connectivity_list[new_id, :3].astype(int).tolist()
    assert np_id in tri_a and np_id in tri_b
    assert 0 in tri_a and 0 in tri_b  # apex shared
    assert set(tri_a) | set(tri_b) == {0, 1, 2, np_id}

    # Partition: the two sub-tri areas sum to the original neighbour area.
    a_a = _tri_area(tri_a, mesh.points)
    a_b = _tri_area(tri_b, mesh.points)
    assert a_a > 1e-9 and a_b > 1e-9  # neither degenerate
    assert abs((a_a + a_b) - opp_area_before) < 1e-9

    # Both replacement tris CCW (positive signed area), matching MATLAB
    # isPolyCCW enforcement.
    assert _signed_area(tri_a, mesh.points) > 0
    assert _signed_area(tri_b, mesh.points) > 0


def test_split_opposing_tri_noop_on_boundary_edge(two_tri_pair):
    """A true mesh-boundary edge (one elem) has no opposite tri → no split."""
    mesh = two_tri_pair
    eid = _shared_edge_id(mesh, 0, 1)  # boundary edge of tri 0 only
    n_before = mesh.connectivity_list.shape[0]
    # midpoint id is irrelevant here; pass an existing vert.
    out = _split_opposing_tri(mesh, eid, np_id=3, consumed_tri_id=0)
    assert out is None
    assert mesh.connectivity_list.shape[0] == n_before


def test_route_case2_splits_opposing_tri(two_tri_pair):
    """route_leftover_tri case 2 (not on_mesh_boundary, n_bdy>=1) bisects the
    edge AND splits the iLayer-1 neighbour: one quad emitted, one tri row added.
    """
    mesh = two_tri_pair
    eid = _shared_edge_id(mesh, 1, 2)
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    n_elems_before = mesh.connectivity_list.shape[0]

    route_leftover_tri(
        mesh,
        work,
        tri_elem_id=1,
        layer_idx=1,
        on_mesh_boundary=False,
        can_remove_edges=True,
        sub_b_edge_set={eid},
        sub_b_vert_set={1, 2},
    )

    # edge_bisection emitted exactly one quad.
    assert len(work.quads) == 1
    # opposite-tri split appended exactly one element row.
    assert mesh.connectivity_list.shape[0] == n_elems_before + 1
    # The appended tri references the new midpoint vertex.
    new_row = mesh.connectivity_list[-1, :3].astype(int).tolist()
    new_vert = mesh.points.shape[0] - 1
    assert new_vert in new_row
