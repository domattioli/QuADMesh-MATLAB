"""Element-count parity tests.

v0.4 framework: run the full pipeline on canonical fixtures and assert sane
output bounds (elem count, vert count, quad fraction, mean quality, pct bad).

Real MATLAB-reference asserts require running the MATLAB pipeline once and
recording goldens — see ``MATLAB_REFERENCE_TODO`` in this file. Current
asserts are regression-style against the v0.3 Python baseline:

    Test_Case_1.14: in 2417 tris -> out 1394 quads, mean Q ~ 0.79
    Block_O.14:     in 5214 tris -> out 3918 quads, mean Q ~ 0.84

The session-004 plan calls for ±5% on elem count and ±2% on quad fraction
against MATLAB. Until MATLAB goldens land, those tolerances apply against
the recorded Python baseline.
"""

from __future__ import annotations

import numpy as np
import pytest

from quadmesh.pipeline import run_pipeline
from quadmesh.quality_report import compute_quality_stats


# (fixture name, expected elem count, expected quad fraction, expected mean quality)
# Captured 2026-05-21 on v0.3 + edge_insertion bug-fix.
BASELINES = {
    "test_case_1": {"n_elems": 1394, "quad_frac": 1.00, "mean_q": 0.794},
    "block_o":     {"n_elems": 3918, "quad_frac": 1.00, "mean_q": 0.837},
}


def _count_quads(mesh) -> int:
    cl = mesh.connectivity_list
    if cl.shape[1] != 4:
        return 0
    return int((cl[:, 2] != cl[:, 3]).sum())


def _assert_within_tolerance(actual: float, expected: float, rel_tol: float, label: str):
    delta = abs(actual - expected) / max(abs(expected), 1.0)
    assert delta <= rel_tol, (
        f"{label}: actual={actual}, expected={expected}, rel_delta={delta:.2%} > {rel_tol:.0%}"
    )


# --------------------------------------------------------------------------- #
# Test_Case_1                                                                 #
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def tc1_out(test_case_1):
    """Run pipeline once per module — outer/inner caps tuned for parity test speed."""
    return run_pipeline(test_case_1, n_smooth_iter=3, max_outer_iter=5, max_inner_iter=5)


def test_test_case_1_elem_count_within_tolerance(tc1_out):
    _assert_within_tolerance(
        tc1_out.n_elems, BASELINES["test_case_1"]["n_elems"],
        rel_tol=0.05, label="Test_Case_1 elem count"
    )


def test_test_case_1_quad_fraction(tc1_out):
    n_quads = _count_quads(tc1_out)
    quad_frac = n_quads / max(tc1_out.n_elems, 1)
    _assert_within_tolerance(
        quad_frac, BASELINES["test_case_1"]["quad_frac"],
        rel_tol=0.02, label="Test_Case_1 quad fraction"
    )


def test_test_case_1_mean_quality(tc1_out):
    stats = compute_quality_stats(tc1_out)
    # Loose lower bound — smoother variance can shift mean ~5%.
    assert stats["mean"] >= 0.7, f"Test_Case_1 mean Q dropped to {stats['mean']:.3f}"


def test_test_case_1_no_zero_area(tc1_out):
    areas = tc1_out.signed_area()
    assert np.all(np.abs(areas) > 1e-12)


def test_test_case_1_pct_bad_under_5_percent(tc1_out):
    stats = compute_quality_stats(tc1_out)
    assert stats["pct_bad"] < 5.0, f"Test_Case_1 pct_bad={stats['pct_bad']:.1f}%"


# --------------------------------------------------------------------------- #
# Block_O                                                                     #
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def block_o(request):
    from pathlib import Path
    from chilmesh import CHILmesh
    repo_root = Path(request.fspath).resolve().parents[2]
    path = repo_root / "03_CHILMesh_Test_Cases" / "01_.14_Files" / "Block_O.14"
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    return CHILmesh.read_from_fort14(path)


@pytest.fixture(scope="module")
def blocko_out(block_o):
    return run_pipeline(block_o, n_smooth_iter=3, max_outer_iter=5, max_inner_iter=5)


def test_block_o_elem_count_within_tolerance(blocko_out):
    _assert_within_tolerance(
        blocko_out.n_elems, BASELINES["block_o"]["n_elems"],
        rel_tol=0.05, label="Block_O elem count"
    )


def test_block_o_quad_fraction(blocko_out):
    n_quads = _count_quads(blocko_out)
    quad_frac = n_quads / max(blocko_out.n_elems, 1)
    _assert_within_tolerance(
        quad_frac, BASELINES["block_o"]["quad_frac"],
        rel_tol=0.02, label="Block_O quad fraction"
    )


def test_block_o_mean_quality(blocko_out):
    stats = compute_quality_stats(blocko_out)
    assert stats["mean"] >= 0.7, f"Block_O mean Q dropped to {stats['mean']:.3f}"


def test_block_o_no_zero_area(blocko_out):
    areas = blocko_out.signed_area()
    assert np.all(np.abs(areas) > 1e-12)


def test_block_o_pct_bad_under_5_percent(blocko_out):
    stats = compute_quality_stats(blocko_out)
    assert stats["pct_bad"] < 5.0, f"Block_O pct_bad={stats['pct_bad']:.1f}%"


# --------------------------------------------------------------------------- #
# MATLAB reference                                                            #
# --------------------------------------------------------------------------- #

# MATLAB_REFERENCE_TODO: capture goldens by running QuADMESH+ Main.m on
# Test_Case_1.14 + Block_O.14, then replace BASELINES values with MATLAB
# outputs and tighten rel_tol to 0.05 / 0.02 as the session-004 plan
# specifies. The .mat fixtures in `05_Results/Block_O/7-19-18/` are
# MatlabOpaque (custom CHILmesh class instances) and not directly readable
# via scipy.io — extraction requires a MATLAB session.
