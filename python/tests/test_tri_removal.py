"""Unit tests for tri-removal sub-ops (T4.6 from v0.4 backlog).

Covers ``edge_bisection``, ``edge_removal``, ``edge_insertion`` directly, plus
``route_leftover_tri`` for each branch of the MATLAB ``removeTrianglesFun``
switch (notably the v0.3 bug-fix branch: ``n_bdy==1 && !can_remove_edges`` ->
``edge_bisection`` and not ``edge_removal``).

Fixtures are minimal 1- to 3-tri WorkingMesh setups so the topology
assertions are easy to read.
"""

from __future__ import annotations

import numpy as np
import pytest

from chilmesh import CHILmesh

from quadmesh._tri_removal import (
    WorkingMesh,
    edge_bisection,
    edge_insertion,
    edge_removal,
    route_leftover_tri,
)


@pytest.fixture
def three_tri_fan():
    """3 tris in a fan around vert 0. Edge layout (from probe):

        verts: 0=(0,0) 1=(1,0) 2=(1,1) 3=(0,1) 4=(-1,1)
        tris:  T0=(0,1,2) T1=(0,2,3) T2=(0,3,4)
        edges: e0=(0,1)bdy e1=(1,2)bdy e2=(0,2)int
               e3=(2,3)bdy e4=(0,3)int e5=(3,4)bdy e6=(0,4)bdy

    Tri 0's local edges are (e0, e1, e2) i.e. (bdy, bdy, int).
    """
    pts = np.array(
        [[0.0, 0.0, 0.0],
         [1.0, 0.0, 0.0],
         [1.0, 1.0, 0.0],
         [0.0, 1.0, 0.0],
         [-1.0, 1.0, 0.0]],
        dtype=float,
    )
    conn = np.array([[0, 1, 2], [0, 2, 3], [0, 3, 4]], dtype=int)
    return CHILmesh(conn, pts)


def _bdy_edge_local_idx(mesh: CHILmesh, tri_id: int) -> int:
    """Return the position (0/1/2) of the first boundary edge in tri's elem2edge."""
    edge_ids = mesh.elem2edge(tri_id).ravel().astype(int)
    bdy = set(mesh.boundary_edges().ravel().tolist())
    for i, e in enumerate(edge_ids):
        if int(e) in bdy:
            return i
    raise AssertionError(f"tri {tri_id} has no boundary edge")


def _interior_edge_local_idx(mesh: CHILmesh, tri_id: int) -> int:
    edge_ids = mesh.elem2edge(tri_id).ravel().astype(int)
    bdy = set(mesh.boundary_edges().ravel().tolist())
    for i, e in enumerate(edge_ids):
        if int(e) not in bdy:
            return i
    raise AssertionError(f"tri {tri_id} has no interior edge")


# --------------------------------------------------------------------------- #
# edge_bisection                                                              #
# --------------------------------------------------------------------------- #

def test_edge_bisection_returns_new_vertex_id(three_tri_fan):
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    n_pts_before = work.points.shape[0]
    new_v = edge_bisection(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    assert new_v is not None
    assert new_v == n_pts_before  # new vert appended at end


def test_edge_bisection_midpoint_position(three_tri_fan):
    """New vertex sits at midpoint of the bisected edge."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    # Tri 0, local edge 0 == global edge e0 == verts (0, 1) — midpoint (0.5, 0).
    new_v = edge_bisection(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    assert np.allclose(work.points[new_v, :2], [0.5, 0.0])


def test_edge_bisection_produces_one_quad(three_tri_fan):
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    assert len(work.quads) == 0
    edge_bisection(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    assert len(work.quads) == 1
    quad = work.quads[0]
    assert quad.shape == (4,)
    assert len(set(quad.tolist())) == 4  # 4 distinct verts


def test_edge_bisection_quad_contains_new_vertex(three_tri_fan):
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    new_v = edge_bisection(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    assert new_v in work.quads[0].tolist()


def test_edge_bisection_consumes_tri(three_tri_fan):
    """Tri's connectivity row is zeroed so the caller can drop it."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    edge_bisection(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    assert np.all(mesh.connectivity_list[0, :] == 0)


def test_edge_bisection_pads_domain_points(three_tri_fan):
    """domain.points grows by 1 so vert IDs stay aligned with work.points."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    n_before = mesh.points.shape[0]
    edge_bisection(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    assert mesh.points.shape[0] == n_before + 1


def test_edge_bisection_quad_has_positive_area(three_tri_fan):
    """Resulting quad must be CCW (positive signed area)."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    edge_bisection(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    quad = work.quads[0]
    pts = work.points[quad, :2]
    x, y = pts[:, 0], pts[:, 1]
    area = 0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1))
    assert area > 0, f"quad has non-positive area: {area}"


# --------------------------------------------------------------------------- #
# edge_removal                                                                #
# --------------------------------------------------------------------------- #

def test_edge_removal_collapses_endpoint_to_midpoint(three_tri_fan):
    """edge_removal snaps v_a to midpoint and rewrites v_b -> v_a."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    # Tri 0, local edge 0 == verts (0, 1) — midpoint (0.5, 0).
    v_a_before = mesh.points[0].copy()
    edge_removal(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    # v_a (vert 0) should now be at midpoint of (0, 1).
    assert np.allclose(mesh.points[0, :2], [0.5, 0.0])
    # v_a moved from original position.
    assert not np.allclose(mesh.points[0], v_a_before)


def test_edge_removal_rewrites_v_b_to_v_a(three_tri_fan):
    """All references to v_b in connectivity_list rewrite to v_a."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    # Tri 0's bdy_edge_idx_in_tri=0 maps to global edge 0 == verts (0, 1).
    # Tri 0 references vert 1. After removal, vert 1 should be replaced by 0.
    edge_removal(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    assert not np.any(mesh.connectivity_list == 1)


def test_edge_removal_rewrites_existing_quads(three_tri_fan):
    """work.quads also have v_b -> v_a rewriting applied."""
    mesh = three_tri_fan
    # Pre-populate a quad that references vert 1.
    work = WorkingMesh(points=mesh.points.copy(), quads=[np.array([0, 1, 2, 3])])
    edge_removal(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    # Vert 1 should be gone from quad.
    assert 1 not in work.quads[0].tolist()
    # Vert 0 appears twice (once from original + once rewritten from 1).
    assert (work.quads[0] == 0).sum() == 2


def test_edge_removal_does_not_append_quad(three_tri_fan):
    """Tri vanishes — not appended to work.quads."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    edge_removal(mesh, work, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    assert len(work.quads) == 0


# --------------------------------------------------------------------------- #
# edge_insertion                                                              #
# --------------------------------------------------------------------------- #

def test_edge_insertion_adds_new_vertex(three_tri_fan):
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    n_before = work.points.shape[0]
    new_v = edge_insertion(mesh, work, tri_elem_id=0, bdy_vert_id=0)
    assert new_v is not None
    assert new_v == n_before
    assert work.points.shape[0] == n_before + 1


def test_edge_insertion_produces_one_quad(three_tri_fan):
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    edge_insertion(mesh, work, tri_elem_id=0, bdy_vert_id=0)
    assert len(work.quads) == 1
    quad = work.quads[0]
    assert quad.shape == (4,)
    assert len(set(quad.tolist())) == 4


def test_edge_insertion_quad_contains_bdy_vert_and_new_vert(three_tri_fan):
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    new_v = edge_insertion(mesh, work, tri_elem_id=0, bdy_vert_id=0)
    quad = work.quads[0].tolist()
    assert 0 in quad
    assert new_v in quad


def test_edge_insertion_consumes_tri(three_tri_fan):
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    edge_insertion(mesh, work, tri_elem_id=0, bdy_vert_id=0)
    assert np.all(mesh.connectivity_list[0, :] == 0)


def test_edge_insertion_falls_back_when_bdy_vert_not_in_tri(three_tri_fan):
    """If bdy_vert_id is not on the tri, op falls back to conn[0]."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    # Tri 0 verts are (0, 1, 2); vert 99 is bogus.
    new_v = edge_insertion(mesh, work, tri_elem_id=0, bdy_vert_id=99)
    assert new_v is not None  # fallback succeeded


# --------------------------------------------------------------------------- #
# route_leftover_tri                                                          #
# --------------------------------------------------------------------------- #

def test_route_n_bdy_ge_1_interior_calls_edge_bisection(three_tri_fan):
    """on_mesh_boundary=False, n_bdy>=1 -> edge_bisection."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    # Tri 0's local edge 0 maps to global edge e0 (verts 0-1, boundary).
    eid = int(mesh.elem2edge(0).ravel()[0])
    route_leftover_tri(
        mesh, work, tri_elem_id=0, layer_idx=0,
        on_mesh_boundary=False, can_remove_edges=False,
        sub_b_edge_set={eid}, sub_b_vert_set=set(),
    )
    # edge_bisection appended a quad; tri consumed.
    assert len(work.quads) == 1
    assert np.all(mesh.connectivity_list[0, :] == 0)


def test_route_n_bdy_1_on_bdy_no_remove_bisects(three_tri_fan):
    """v0.3 bug fix (T14.2): n_bdy==1 && on_bdy && !can_remove -> bisection.

    Pre-bug-fix this branch called edge_removal, which collapsed two verts and
    destroyed topology. Bisection is the MATLAB-correct behaviour.
    """
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    eid = int(mesh.elem2edge(0).ravel()[0])  # a boundary edge of tri 0
    route_leftover_tri(
        mesh, work, tri_elem_id=0, layer_idx=0,
        on_mesh_boundary=True, can_remove_edges=False,
        sub_b_edge_set={eid}, sub_b_vert_set=set(),
    )
    # Bisection produces a quad and zeros the tri.
    assert len(work.quads) == 1
    assert np.all(mesh.connectivity_list[0, :] == 0)


def test_route_n_bdy_1_on_bdy_can_remove_removes(three_tri_fan):
    """on_mesh_boundary && n_bdy==1 && can_remove_edges -> edge_removal."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    eid = int(mesh.elem2edge(0).ravel()[0])
    route_leftover_tri(
        mesh, work, tri_elem_id=0, layer_idx=0,
        on_mesh_boundary=True, can_remove_edges=True,
        sub_b_edge_set={eid}, sub_b_vert_set=set(),
    )
    # edge_removal does NOT append a quad; the tri is consumed via vert-rewriting.
    assert len(work.quads) == 0
    # Vert b (b == 1 for tri 0 edge 0) rewritten to vert a (0).
    assert not np.any(mesh.connectivity_list == 1)


def test_route_n_bdy_0_on_bdy_inserts(three_tri_fan):
    """on_mesh_boundary && n_bdy==0 with a bdy_vert in tri -> edge_insertion."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    # No sub-mesh boundary edges in this tri; vert 0 marked as bdy vert.
    route_leftover_tri(
        mesh, work, tri_elem_id=0, layer_idx=0,
        on_mesh_boundary=True, can_remove_edges=False,
        sub_b_edge_set=set(), sub_b_vert_set={0},
    )
    assert len(work.quads) == 1
    assert np.all(mesh.connectivity_list[0, :] == 0)


def test_route_n_bdy_0_no_bdy_vert_is_no_op(three_tri_fan):
    """on_mesh_boundary && n_bdy==0 && no bdy_vert_in_tri -> no-op (tri kept)."""
    mesh = three_tri_fan
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    conn_before = mesh.connectivity_list[0, :].copy()
    route_leftover_tri(
        mesh, work, tri_elem_id=0, layer_idx=0,
        on_mesh_boundary=True, can_remove_edges=False,
        sub_b_edge_set=set(), sub_b_vert_set=set(),
    )
    assert len(work.quads) == 0
    assert np.array_equal(mesh.connectivity_list[0, :], conn_before)
