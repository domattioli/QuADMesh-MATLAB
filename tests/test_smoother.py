"""Tests for two_part_smoother."""

from __future__ import annotations

import pytest

from quadmesh.post_process import two_part_smoother


def test_two_part_smoother_actually_runs(test_case_1):
    """Smoother runs n_iter=1 without crash; vertex count unchanged."""
    result = two_part_smoother(test_case_1, n_iter=1)
    assert result is not None
    assert result.n_verts == test_case_1.n_verts


def test_two_part_smoother_zero_iter(test_case_1):
    """Smoother with n_iter=0 is a no-op."""
    result = two_part_smoother(test_case_1, n_iter=0)
    assert result.n_verts == test_case_1.n_verts
