"""Tests for cleanup_boundary_quads — collapse and shift modes."""
from __future__ import annotations

import math

import numpy as np
import pytest

from chilmesh import CHILmesh
from quadmesh.cleanup_boundary_quads import (
    ANGLE_THRESHOLD_DEG,
    _angle_deg,
    _shift_to_target_angle,
    cleanup_boundary_quads,
)


def _regular_quad() -> CHILmesh:
    """Unit square quad. All angles 90 deg — no bad quads."""
    pts = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    return CHILmesh(np.array([[0, 1, 2, 3]], dtype=int), pts)


def _bad_quad_mesh() -> CHILmesh:
    """3-quad mesh with one bad boundary quad.

    Vertices:
      v0=(0,0)=side1, v1=(1,-0.1)=corner (angle~168 deg), v2=(2,0)=side2
      v3=(1,2)=opposing
      v4=(-1,0), v5=(-1,2)  (left quad)
      v6=(3,0), v7=(3,2)    (right quad)

    Quads:
      Q0=[v0,v1,v2,v3] bad quad  -- boundary edges (v0,v1) and (v1,v2)
      Q1=[v4,v0,v3,v5]           -- shares interior edge (v0,v3) with Q0
      Q2=[v2,v6,v7,v3]           -- shares interior edge (v2,v3) with Q0

    MATLAB-aligned collapse: side1=v0 and side2=v2 remapped to corner=v1;
    Q0 deleted; Q1->[v4,v1,v3,v5]; Q2->[v1,v6,v7,v3].
    """
    pts = np.array([
        [0.0, 0.0],   # v0 = side1
        [1.0, -0.1],  # v1 = corner (~168 deg between boundary edges)
        [2.0, 0.0],   # v2 = side2
        [1.0, 2.0],   # v3 = opposing
        [-1.0, 0.0],  # v4
        [-1.0, 2.0],  # v5
        [3.0, 0.0],   # v6
        [3.0, 2.0],   # v7
    ], dtype=float)
    conn = np.array([
        [0, 1, 2, 3],  # Q0 bad quad
        [4, 0, 3, 5],  # Q1
        [2, 6, 7, 3],  # Q2
    ], dtype=int)
    return CHILmesh(conn, pts)


class TestHelpers:
    def test_angle_right_angle(self):
        p = np.array([0.0, 0.0])
        assert abs(_angle_deg(p, np.array([1.0, 0.0]), np.array([0.0, 1.0])) - 90.0) < 1e-6

    def test_angle_straight(self):
        p = np.array([0.0, 0.0])
        assert abs(_angle_deg(p, np.array([1.0, 0.0]), np.array([-1.0, 0.0])) - 180.0) < 1e-6

    def test_shift_reduces_obtuse_angle(self):
        """Shift corner at ~150 deg toward opposing should land near 90 deg."""
        ang = math.radians(75.0)
        p_corner = np.array([0.0, 0.0])
        p_a = np.array([math.cos(ang), math.sin(ang)])
        p_b = np.array([math.cos(-ang), math.sin(-ang)])
        p_opp = np.array([2.0, 0.0])
        assert _angle_deg(p_corner, p_a, p_b) > ANGLE_THRESHOLD_DEG
        new_c = _shift_to_target_angle(p_corner, p_a, p_b, p_opp)
        assert _angle_deg(new_c, p_a, p_b) <= 95.0


class TestNoOp:
    def test_regular_quad_collapse(self):
        m = _regular_quad()
        out = cleanup_boundary_quads(m, can_remove_edges=True)
        assert out.n_elems == m.n_elems

    def test_regular_quad_shift(self):
        m = _regular_quad()
        out = cleanup_boundary_quads(m, can_remove_edges=False)
        assert out.n_elems == m.n_elems
        assert np.allclose(out.points, m.points)


class TestCollapseTopology:
    """Verify MATLAB-aligned collapse: side verts merged into corner, bad quad deleted."""

    def test_elem_count_decreases_by_one(self):
        m = _bad_quad_mesh()
        out = cleanup_boundary_quads(m, can_remove_edges=True)
        assert out.n_elems == m.n_elems - 1

    def test_corner_preserved_at_original_position(self):
        m = _bad_quad_mesh()
        corner_xyz = np.array([1.0, -0.1])
        out = cleanup_boundary_quads(m, can_remove_edges=True)
        pts2d = out.points[:, :2]
        assert any(np.allclose(p, corner_xyz) for p in pts2d), "corner should stay in mesh"

    def test_side_verts_absorbed_into_corner(self):
        m = _bad_quad_mesh()
        side1_xyz = np.array([0.0, 0.0])
        side2_xyz = np.array([2.0, 0.0])
        out = cleanup_boundary_quads(m, can_remove_edges=True)
        pts2d = out.points[:, :2]
        assert not any(np.allclose(p, side1_xyz) for p in pts2d), "side1 should be absorbed"
        assert not any(np.allclose(p, side2_xyz) for p in pts2d), "side2 should be absorbed"

    def test_remaining_quads_have_positive_area(self):
        m = _bad_quad_mesh()
        out = cleanup_boundary_quads(m, can_remove_edges=True)
        areas = out.signed_area()
        assert np.all(np.abs(areas) > 1e-14)


class TestOnRealMesh:
    def test_collapse_produces_valid_mesh(self, test_case_1):
        from quadmesh import tri2quad
        quad = tri2quad(test_case_1)
        out = cleanup_boundary_quads(quad, can_remove_edges=True)
        assert out.n_elems > 0
        areas = out.signed_area()
        assert np.all(np.abs(areas) > 1e-14)

    def test_shift_preserves_elem_count(self, test_case_1):
        from quadmesh import tri2quad
        quad = tri2quad(test_case_1)
        n_before = quad.n_elems
        out = cleanup_boundary_quads(quad, can_remove_edges=False)
        assert out.n_elems == n_before

    def test_shift_valid_areas(self, test_case_1):
        from quadmesh import tri2quad
        quad = tri2quad(test_case_1)
        out = cleanup_boundary_quads(quad, can_remove_edges=False)
        areas = out.signed_area()
        assert np.all(np.abs(areas) > 1e-14)
