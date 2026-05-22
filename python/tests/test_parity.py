"""Element-count parity scaffold (v0.4).

Goal: assert Python output stays within tolerance of MATLAB output on
canonical fixtures (Test_Case_1, Block_O).

State: MATLAB ground-truth elem counts are not yet captured (Block_O .mat
artifact is MATLAB-opaque; cannot extract from Python). Until they are,
these tests act as regression baselines pinning *current* Python output.
When MATLAB counts land, update ``EXPECTED`` to point at them and tighten
``ELEM_TOL`` / ``QUAD_FRAC_TOL`` per the session-004 plan (±5% / ±2%).

Tolerances are deliberately loose so legitimate algorithmic improvements
(e.g. fewer leftover tris under aggressive routing) don't trip the test.
"""

from __future__ import annotations

import pytest

from quadmesh import compute_quality_stats, post_process, tri2quad


# Baselines captured 2026-05-22 with quadmesh 0.3.0 + chilmesh 0.4.1.
# Keys: input n_elems, output n_elems, quad fraction, mean quality.
# Source: ``python -m quadmesh.cli`` smoke runs on each fixture.
EXPECTED = {
    "Test_Case_1.14": {
        "n_elems_in": 2417,
        "n_elems_out": 1394,
        "quad_frac": 1.000,
        "mean_quality": 0.794,
    },
    "Block_O.14": {
        "n_elems_in": 5214,
        "n_elems_out": 3918,
        "quad_frac": 1.000,
        "mean_quality": 0.837,
    },
}

# Loose tolerances for regression. Tighten on MATLAB ground-truth landing.
ELEM_TOL = 0.05  # +/- 5% on output elem count
QUAD_FRAC_TOL = 0.02  # +/- 2% absolute on quad fraction
QUALITY_TOL = 0.05  # +/- 0.05 absolute on mean quality


def _count_quads(mesh) -> int:
    cl = mesh.connectivity_list
    if cl.shape[1] != 4:
        return 0
    return int((cl[:, 2] != cl[:, 3]).sum())


@pytest.mark.parametrize("fixture_name", list(EXPECTED.keys()))
def test_pipeline_elem_count_parity(fixture_name, request):
    """Output elem count within tolerance of baseline."""
    # Use the fixture loader from conftest, by name.
    mesh = request.getfixturevalue(
        {"Test_Case_1.14": "test_case_1", "Block_O.14": "_block_o"}[fixture_name]
    )
    expected = EXPECTED[fixture_name]
    assert mesh.n_elems == expected["n_elems_in"], (
        f"input n_elems drift: {mesh.n_elems} != {expected['n_elems_in']}"
    )

    q = tri2quad(mesh, can_remove_edges=True)
    pp = post_process(q, n_smooth_iter=3)

    tol_lo = int(expected["n_elems_out"] * (1 - ELEM_TOL))
    tol_hi = int(expected["n_elems_out"] * (1 + ELEM_TOL))
    assert tol_lo <= pp.n_elems <= tol_hi, (
        f"{fixture_name}: output n_elems {pp.n_elems} outside ±{ELEM_TOL:.0%} "
        f"of baseline {expected['n_elems_out']} ([{tol_lo},{tol_hi}])"
    )


@pytest.mark.parametrize("fixture_name", list(EXPECTED.keys()))
def test_pipeline_quad_fraction_parity(fixture_name, request):
    """Quad fraction within tolerance of baseline."""
    mesh = request.getfixturevalue(
        {"Test_Case_1.14": "test_case_1", "Block_O.14": "_block_o"}[fixture_name]
    )
    expected = EXPECTED[fixture_name]

    q = tri2quad(mesh, can_remove_edges=True)
    pp = post_process(q, n_smooth_iter=3)

    quad_frac = _count_quads(pp) / max(pp.n_elems, 1)
    assert abs(quad_frac - expected["quad_frac"]) <= QUAD_FRAC_TOL, (
        f"{fixture_name}: quad_frac {quad_frac:.3f} outside ±{QUAD_FRAC_TOL} "
        f"of baseline {expected['quad_frac']:.3f}"
    )


@pytest.mark.parametrize("fixture_name", list(EXPECTED.keys()))
def test_pipeline_mean_quality_parity(fixture_name, request):
    """Mean quality within tolerance of baseline."""
    mesh = request.getfixturevalue(
        {"Test_Case_1.14": "test_case_1", "Block_O.14": "_block_o"}[fixture_name]
    )
    expected = EXPECTED[fixture_name]

    q = tri2quad(mesh, can_remove_edges=True)
    pp = post_process(q, n_smooth_iter=3)

    stats = compute_quality_stats(pp)
    assert abs(stats["mean"] - expected["mean_quality"]) <= QUALITY_TOL, (
        f"{fixture_name}: mean_quality {stats['mean']:.3f} outside ±{QUALITY_TOL} "
        f"of baseline {expected['mean_quality']:.3f}"
    )
