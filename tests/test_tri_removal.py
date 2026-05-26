"""Aggressive-path sub-op tests (T4.6).

Covers ``_tri_removal.edge_removal``, ``edge_bisection``, ``edge_insertion``,
and the ``route_leftover_tri`` dispatcher. Builds minimal 3-tri CHILmesh
fixtures so each sub-op is exercised in isolation.

The sub-ops mutate ``domain`` (CHILmesh connectivity + points) and append
quads to a ``WorkingMesh``. Tests assert post-conditions on both surfaces.
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def three_tri_strip():
    """3 tris arranged as a horizontal strip:

        3 ---- 4
        |\\    /|
        | \\  / |
        |  \\/  |
        |  /\\  |
        | /  \\ |
        |/    \\|
        0 -1 - 2

    Verts: 0,1,2 on bottom; 3,4 on top.
    Tris: 0=(0,1,3) left, 1=(1,4,3) middle, 2=(1,2,4) right.

    Edge 0=(0,1) bdy, 1=(1,3) interior, 2=(0,3) bdy, 3=(1,4) interior,
    4=(3,4) bdy, 5=(1,2) bdy, 6=(2,4) bdy.
    """
    points = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [0.5, 1.0, 0.0],
            [1.5, 1.0, 0.0],
        ],
        dtype=float,
    )
    conn = np.array(
        [[0, 1, 3], [1, 4, 3], [1, 2, 4]],
        dtype=int,
    )
    return CHILmesh(conn, points)


@pytest.fixture
def work_for(three_tri_strip):
    return WorkingMesh(points=three_tri_strip.points.copy(), quads=[])


# ---------------------------------------------------------------------------
# edge_removal
# ---------------------------------------------------------------------------


def test_edge_removal_collapses_two_verts_to_midpoint(three_tri_strip, work_for):
    """Bdy edge 0 of tri 0 is verts (0,1). After removal:
    - points[0] snaps to midpoint (0.5, 0, 0).
    - Every connectivity reference to vert 1 rewritten to vert 0.
    """
    edge_removal(three_tri_strip, work_for, tri_elem_id=0, bdy_edge_idx_in_tri=0)

    # Midpoint snap.
    assert np.allclose(three_tri_strip.points[0, :2], [0.5, 0.0])
    # Vert 1 no longer appears in connectivity.
    cl = three_tri_strip.connectivity_list
    assert 1 not in cl.ravel().tolist()
    # No quad added.
    assert len(work_for.quads) == 0


def test_edge_removal_rewrites_existing_quads(three_tri_strip, work_for):
    """If a quad already references the dropped vert, it gets remapped too."""
    # Pre-seed a quad referencing vert 1 (the vert that should die).
    work_for.add_quad(np.array([1, 2, 4, 3], dtype=int))
    edge_removal(three_tri_strip, work_for, tri_elem_id=0, bdy_edge_idx_in_tri=0)
    # Vert 1 → vert 0 in the pre-seeded quad.
    assert 1 not in work_for.quads[0].tolist()
    assert 0 in work_for.quads[0].tolist()


# ---------------------------------------------------------------------------
# edge_bisection
# ---------------------------------------------------------------------------


def test_edge_bisection_creates_one_quad_one_new_vert(three_tri_strip, work_for):
    """Bisecting bdy edge 0 of tri 0 produces:
    - One new vertex at midpoint of (0,1).
    - One quad [0, np_id, 1, 3] in CCW order.
    - tri 0 zeroed in domain connectivity (consumed).
    """
    n_pts_before = three_tri_strip.points.shape[0]
    np_id = edge_bisection(
        three_tri_strip, work_for, tri_elem_id=0, bdy_edge_idx_in_tri=0
    )
    assert np_id is not None
    # New vertex buffered (work.n_pts reflects full count before flush).
    assert work_for.n_pts == n_pts_before + 1
    assert np.allclose(work_for.get_extra_point(np_id)[:2], [0.5, 0.0])
    # domain.points grows only after flush_points_to_domain.
    work_for.flush_points_to_domain(three_tri_strip)
    assert three_tri_strip.points.shape[0] == n_pts_before + 1
    # One quad appended.
    assert len(work_for.quads) == 1
    quad = work_for.quads[0]
    assert quad.shape == (4,)
    assert set(quad.tolist()) == {0, 1, 3, np_id}
    # Original tri zeroed.
    assert (three_tri_strip.connectivity_list[0] == 0).all()


def test_edge_bisection_quad_is_ccw(three_tri_strip, work_for):
    """The emitted quad should have positive signed area."""
    np_id = edge_bisection(
        three_tri_strip, work_for, tri_elem_id=0, bdy_edge_idx_in_tri=0
    )
    assert np_id is not None
    quad = work_for.quads[0]
    all_pts = np.vstack([work_for.points] + work_for._extra_pts)
    pts = all_pts[quad, :2]
    x, y = pts[:, 0], pts[:, 1]
    area = 0.5 * np.sum(x * np.roll(y, -1) - y * np.roll(x, -1))
    assert area > 0, f"quad not CCW (area={area})"


def test_edge_bisection_route_leftover_tri_picks_bisection(three_tri_strip, work_for):
    """Regression for v0.3 / T14.2 bug fix: when on_mesh_boundary=True,
    n_bdy=1, can_remove_edges=False, route must pick edge_bisection (NOT
    edge_removal). Pre-fix this case silently called edge_removal."""
    # tri 0 has boundary edges 0 and 2 (n_bdy=2 normally); construct a sub_b
    # set that yields exactly one boundary edge for tri 0.
    edge_ids = three_tri_strip.elem2edge(0).ravel().astype(int)
    sub_b_edge_set = {int(edge_ids[0])}  # only edge 0 is "on boundary"
    sub_b_vert_set = set(three_tri_strip.edge2vert(int(edge_ids[0])).ravel().astype(int).tolist())

    route_leftover_tri(
        three_tri_strip,
        work_for,
        tri_elem_id=0,
        layer_idx=0,
        on_mesh_boundary=True,
        can_remove_edges=False,
        sub_b_edge_set=sub_b_edge_set,
        sub_b_vert_set=sub_b_vert_set,
    )
    # Bisection produces a quad; edge_removal would not.
    assert len(work_for.quads) == 1


# ---------------------------------------------------------------------------
# edge_insertion
# ---------------------------------------------------------------------------


def test_edge_insertion_creates_quad_from_tri(three_tri_strip, work_for):
    """Insert a new edge through bdy_vert_id of tri 1 = (1,4,3).
    The op adds one vertex along an interior edge and emits one quad.
    """
    n_pts_before = three_tri_strip.points.shape[0]
    # Vert 4 is in tri 1 and has interior edge to vert 1.
    np_id = edge_insertion(
        three_tri_strip, work_for, tri_elem_id=1, bdy_vert_id=4
    )
    assert np_id is not None
    assert work_for.n_pts == n_pts_before + 1
    assert len(work_for.quads) == 1
    quad = work_for.quads[0]
    assert quad.shape == (4,)
    # bdy_vert_id and np_id both appear.
    assert 4 in quad.tolist()
    assert np_id in quad.tolist()
    # Original tri zeroed.
    assert (three_tri_strip.connectivity_list[1] == 0).all()


def test_edge_insertion_fallback_when_vert_not_in_tri(three_tri_strip, work_for):
    """If ``bdy_vert_id`` is not in the tri, op falls back to first vert."""
    np_id = edge_insertion(
        three_tri_strip, work_for, tri_elem_id=1, bdy_vert_id=99  # bogus
    )
    # Either succeeds (fallback) or returns None — never raises.
    assert np_id is None or len(work_for.quads) == 1


def test_edge_insertion_new_point_along_opposing_edge(three_tri_strip, work_for):
    """New point sits 1/3 from bdy_vert_id along an interior edge — i.e.
    closer to bdy_vert_id than to the other endpoint."""
    np_id = edge_insertion(
        three_tri_strip, work_for, tri_elem_id=1, bdy_vert_id=4
    )
    assert np_id is not None
    bdy_xyz = three_tri_strip.points[4]
    new_xyz = work_for.get_extra_point(np_id)
    # New point must be on the segment between bdy_vert and one other tri
    # vert. Find which.
    conn = np.array([1, 4, 3], dtype=int)
    others = [v for v in conn if v != 4]
    dists = [np.linalg.norm(new_xyz - three_tri_strip.points[v]) for v in others]
    # Distance from new_xyz to bdy_xyz < distance from new_xyz to nearest other.
    d_bdy = np.linalg.norm(new_xyz - bdy_xyz)
    assert d_bdy < min(dists), (
        f"new point should be closer to bdy_vert (d={d_bdy:.3f}) than to either "
        f"opposing tri vert ({dists})"
    )


# ---------------------------------------------------------------------------
# route_leftover_tri dispatcher
# ---------------------------------------------------------------------------


def test_route_dispatches_edge_removal_when_can_remove(three_tri_strip, work_for):
    """on_mesh_boundary=True, n_bdy=1, can_remove_edges=True → edge_removal."""
    edge_ids = three_tri_strip.elem2edge(0).ravel().astype(int)
    sub_b_edge_set = {int(edge_ids[0])}
    sub_b_vert_set = set(three_tri_strip.edge2vert(int(edge_ids[0])).ravel().astype(int).tolist())

    n_pts_before = three_tri_strip.points.shape[0]
    route_leftover_tri(
        three_tri_strip,
        work_for,
        tri_elem_id=0,
        layer_idx=0,
        on_mesh_boundary=True,
        can_remove_edges=True,
        sub_b_edge_set=sub_b_edge_set,
        sub_b_vert_set=sub_b_vert_set,
    )
    # edge_removal: no quad added, no new vert.
    assert len(work_for.quads) == 0
    assert three_tri_strip.points.shape[0] == n_pts_before


def test_route_dispatches_edge_bisection_when_interior(three_tri_strip, work_for):
    """on_mesh_boundary=False, n_bdy>=1 → edge_bisection (case 2)."""
    edge_ids = three_tri_strip.elem2edge(1).ravel().astype(int)
    sub_b_edge_set = {int(edge_ids[0])}
    sub_b_vert_set = set(three_tri_strip.edge2vert(int(edge_ids[0])).ravel().astype(int).tolist())

    route_leftover_tri(
        three_tri_strip,
        work_for,
        tri_elem_id=1,
        layer_idx=0,
        on_mesh_boundary=False,
        can_remove_edges=True,
        sub_b_edge_set=sub_b_edge_set,
        sub_b_vert_set=sub_b_vert_set,
    )
    # Bisection adds one quad.
    assert len(work_for.quads) == 1


def test_route_silently_skips_unmapped_case(three_tri_strip, work_for):
    """No matching case (e.g. on_mesh_boundary=False, n_bdy=0, no bdy verts)
    → no-op, no crash."""
    sub_b_edge_set: set = set()
    sub_b_vert_set: set = set()
    n_pts_before = three_tri_strip.points.shape[0]
    route_leftover_tri(
        three_tri_strip,
        work_for,
        tri_elem_id=1,
        layer_idx=0,
        on_mesh_boundary=False,
        can_remove_edges=False,
        sub_b_edge_set=sub_b_edge_set,
        sub_b_vert_set=sub_b_vert_set,
    )
    assert len(work_for.quads) == 0
    assert three_tri_strip.points.shape[0] == n_pts_before
