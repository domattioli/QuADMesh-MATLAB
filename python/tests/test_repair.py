"""Tests for ``quadmesh.repair``.

Covers ``_ear_clip``, ``_merge_tri_pairs_to_quads``, ``_fix_bowties``,
``_snap_boundary_midpoints``, and the ``repair_mesh`` orchestrator.
"""
from __future__ import annotations

import numpy as np
import pytest

from quadmesh.repair import (
    _ear_clip,
    _fix_bowties,
    _merge_tri_pairs_to_quads,
    _snap_boundary_midpoints,
    repair_mesh,
)


def test_ear_clip_square():
    pts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    tris = _ear_clip([0, 1, 2, 3], pts)
    assert len(tris) == 2
    # union of two tris should cover the square (sum of signed areas = 1.0)
    total = 0.0
    for (a, b, c) in tris:
        p = pts[[a, b, c], :2]
        total += 0.5 * abs(
            (p[1, 0] - p[0, 0]) * (p[2, 1] - p[0, 1])
            - (p[2, 0] - p[0, 0]) * (p[1, 1] - p[0, 1])
        )
    assert abs(total - 1.0) < 1e-12


def test_ear_clip_triangle_passthrough():
    pts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
    tris = _ear_clip([0, 1, 2], pts)
    assert tris == [(0, 1, 2)]


def test_ear_clip_degenerate():
    pts = np.array([[0, 0, 0], [1, 0, 0]], dtype=float)
    assert _ear_clip([0, 1], pts) == []


def test_merge_two_tris_into_quad():
    pts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    tris = [(0, 1, 2), (0, 2, 3)]
    merged = _merge_tri_pairs_to_quads(tris, pts)
    assert len(merged) == 1
    assert len(merged[0]) == 4
    assert set(merged[0]) == {0, 1, 2, 3}


def test_fix_bowtie_quad():
    pts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    # bowtie: swap mid two -> (0, 2, 1, 3) makes edges (0,2) x (1,3) cross
    conn = np.array([[0, 2, 1, 3]], dtype=int)
    conn_fixed, n_fixed = _fix_bowties(conn, pts)
    assert n_fixed == 1
    # fixed quad must be CCW (positive signed area)
    p = pts[conn_fixed[0], :2]
    sa = 0.5 * float(
        np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    )
    assert sa > 0


def test_fix_bowtie_noop_on_valid():
    pts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    conn = np.array([[0, 1, 2, 3]], dtype=int)
    conn_after, n_fixed = _fix_bowties(conn, pts)
    assert n_fixed == 0
    assert np.array_equal(conn_after, conn)


def test_snap_midpoint_on_boundary():
    # 2 quads share interior edge; v5 is a degree-2 boundary midpoint, displaced.
    pts = np.array([
        [0, 0, 0], [1, 0, 0], [2, 0, 0],
        [2, 1, 0], [1, 1, 0], [0, 1, 0],
        # displaced midpoint between v0 (0,0) and v1 (1,0) — true midpoint = (0.5, 0)
        [0.4, 0.3, 0],
    ], dtype=float)
    # Two quads sharing edge (v1, v4):
    #  - left quad: v0, v6, v1, v4, v5  → can't be quad with 5 verts. Use:
    #  - left quad uses v6 in place of v0-v1 split:
    conn = np.array([
        [v0_for, v6, v1, v4]
        for v0_for, v6, v1, v4 in [(0, 6, 1, 5)]
    ] + [[1, 2, 3, 4]], dtype=int)
    # Re-check edges: left = (0,6),(6,1),(1,5),(5,0); right = (1,2),(2,3),(3,4),(4,1)
    # Shared edge: only (1,4)? No — left has (1,5), right has (4,1). No shared edge.
    # Rework: make a chain where vertex 6 sits on the boundary between v0 and v1.
    # Left quad: [v0, v6, v5, ...] only 3 distinct boundary edges touch v6.
    # Simplest: 1 quad covers it.
    conn = np.array([[0, 6, 1, 5]], dtype=int)  # single quad with v6 as midpoint
    pts_before = pts.copy()
    conn_after, pts_after = _snap_boundary_midpoints(conn.copy(), pts.copy(), mid_threshold=6)
    # v6 should be snapped to midpoint of its two boundary neighbors.
    # In this 1-quad setup v6 is between v0 and v1 → expected (0.5, 0).
    assert np.allclose(pts_after[6, :2], [0.5, 0.0])
    # other verts unchanged
    for i in range(6):
        assert np.allclose(pts_after[i], pts_before[i])


def test_repair_mesh_idempotent_on_clean_input():
    """A clean 2x2 quad grid should pass through repair_mesh unchanged
    (no bowties, no displaced midpoints, no violations)."""
    pts = np.array([
        [0, 0, 0], [1, 0, 0], [2, 0, 0],
        [0, 1, 0], [1, 1, 0], [2, 1, 0],
        [0, 2, 0], [1, 2, 0], [2, 2, 0],
    ], dtype=float)
    conn = np.array([
        [0, 1, 4, 3],
        [1, 2, 5, 4],
        [3, 4, 7, 6],
        [4, 5, 8, 7],
    ], dtype=int)
    conn_after, pts_after = repair_mesh(conn.copy(), pts.copy(), mid_threshold=100)
    assert conn_after.shape == conn.shape
    assert np.array_equal(conn_after, conn)
    assert np.allclose(pts_after, pts)


def test_repair_mesh_preserves_padded_tri():
    pts = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0]], dtype=float)
    conn = np.array([[0, 1, 2, 0]], dtype=int)  # padded triangle
    conn_after, pts_after = repair_mesh(conn.copy(), pts.copy())
    assert conn_after.shape == conn.shape
    # padded tri row preserved
    assert conn_after[0, 0] == conn_after[0, 3]
