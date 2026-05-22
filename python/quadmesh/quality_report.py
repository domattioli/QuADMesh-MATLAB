"""Mesh quality stats. Port of MATLAB plotQualityProgress minus the plot."""

from __future__ import annotations

from chilmesh import CHILmesh


def compute_quality_stats(mesh: CHILmesh) -> dict:
    """Compute element quality statistics.

    Calls mesh.elem_quality() and returns aggregated stats.
    """
    quality_arr, _, stats_dict = mesh.elem_quality()
    import numpy as np
    n_bad = int(np.sum(quality_arr < 0.3))
    n_elems = mesh.n_elems
    pct_bad = 100.0 * n_bad / n_elems if n_elems > 0 else 0.0

    return {
        "mean": float(stats_dict["mean"]),
        "min": float(stats_dict["min"]),
        "max": float(stats_dict["max"]),
        "std": float(stats_dict["std"]),
        "n_bad": int(n_bad),
        "pct_bad": float(pct_bad),
        "n_elems": int(n_elems),
    }


def format_quality_report(stats: dict) -> str:
    """Format quality stats as single-line string."""
    return (
        f"quality: mean={stats['mean']:.3f}  "
        f"min={stats['min']:.3f}  "
        f"std={stats['std']:.3f}  "
        f"bad(<0.3)={stats['n_bad']}/{stats['n_elems']} ({stats['pct_bad']:.1f}%)"
    )
