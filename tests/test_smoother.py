"""Tests for fem_smoother."""

from __future__ import annotations

import numpy as np
from chilmesh import CHILmesh

from quadmesh.post_process import fem_smoother


def test_fem_smoother_actually_runs(test_case_1):
    """Smoother runs n_iter=1 without crash; vertex count unchanged."""
    result = fem_smoother(test_case_1, n_iter=1)
    assert result is not None
    assert result.n_verts == test_case_1.n_verts


def test_fem_smoother_zero_iter(test_case_1):
    """Smoother with n_iter=0 is a no-op."""
    result = fem_smoother(test_case_1, n_iter=0)
    assert result.n_verts == test_case_1.n_verts


def test_fem_smoother_drops_unattached_vertices(test_case_1):
    """An element-less vertex would make the stiffness matrix singular (#35).

    fem_smoother must compact it out before solving so the result stays finite.
    """
    pts = np.asarray(test_case_1.points)
    conn = np.asarray(test_case_1.connectivity_list)
    orphan = pts.mean(axis=0, keepdims=True)
    mesh = CHILmesh(conn, np.vstack([pts, orphan]))
    assert mesh.n_verts == test_case_1.n_verts + 1

    result = fem_smoother(mesh, n_iter=1)

    assert result.n_verts == test_case_1.n_verts
    assert np.isfinite(np.asarray(result.points)).all()
