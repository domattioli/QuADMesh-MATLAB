"""Tests for quality_report module."""

from __future__ import annotations

import pytest

from quadmesh.quality_report import compute_quality_stats, format_quality_report


def test_compute_quality_stats_keys(test_case_1):
    """Stats dict contains all required keys."""
    stats = compute_quality_stats(test_case_1)
    required = {"mean", "min", "max", "std", "n_bad", "pct_bad", "n_elems"}
    assert required.issubset(stats.keys())


def test_compute_quality_stats_values_sane(test_case_1):
    """Stats values are within reasonable ranges."""
    stats = compute_quality_stats(test_case_1)
    assert 0 < stats["mean"] < 1
    assert stats["min"] >= 0
    assert stats["max"] <= 1
    assert stats["n_bad"] >= 0
    assert stats["n_elems"] == test_case_1.n_elems


def test_format_quality_report(test_case_1):
    """Report formatting includes expected substrings."""
    stats = compute_quality_stats(test_case_1)
    line = format_quality_report(stats)
    assert "quality:" in line
    assert "mean=" in line
    assert "bad(" in line
