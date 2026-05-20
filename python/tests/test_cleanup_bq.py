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
