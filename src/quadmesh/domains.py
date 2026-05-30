"""Synthetic hero/demo domain boundary generators.

Returns (N,2) CCW XY polygons in matplotlib-Path / PSLG convention
compatible with quadmesh.create_quad_domain.
"""

from __future__ import annotations

import numpy as np


def onion_polygon(
    n: int = 240,
    a: float = 1.0,
    b: float = 0.70,
    stem_height: float = 0.08,
    stem_width: float = 0.16,
    root_depth: float = 0.04,
    root_width_frac: float = 0.30,
    *,
    close: bool = False,
) -> np.ndarray:
    """Onion silhouette: oblate body + centered top stem nub + shallow bottom root-plate dimple.

    Returns (n,2) float64, counter-clockwise, watertight ring (first point NOT duplicated
    unless close=True, then (n+1,2) with last==first). No self-intersections.

    Parameters
    ----------
    n : int, default 240
        Number of samples on the boundary (endpoint excluded unless close=True).
    a : float, default 1.0
        Body half-width (x-direction).
    b : float, default 0.70
        Body half-height (y-direction), typically b < a (oblate).
    stem_height : float, default 0.08
        Maximum height of the top convex bump (stem nub).
    stem_width : float, default 0.16
        Lateral falloff scale (std dev) of the stem Gaussian bump.
    root_depth : float, default 0.04
        Maximum depth of the bottom concave indent (root plate dimple).
    root_width_frac : float, default 0.30
        Lateral extent of root dimple as fraction of body half-width a.
    close : bool, default False
        If True, return (n+1,2) with last row == first row. If False, return (n,2).

    Returns
    -------
    np.ndarray
        Shape (n,2) or (n+1,2) if close=True, dtype float64. Counter-clockwise,
        no self-intersections.
    """
    # Parametric ellipse: t in [0, 2π), exactly n samples (endpoint excluded).
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x = a * np.cos(t)
    y = b * np.sin(t)

    # Stem nub: convex bump at top (y >= 0), centered at x=0, magnitude stem_height.
    # Use Gaussian falloff in x.
    stem_mask = y >= 0
    stem_bump = stem_height * np.exp(-((x / stem_width) ** 2)) * stem_mask
    y_with_stem = y + stem_bump

    # Root plate: concave dimple at bottom (y < 0), centered at x=0,
    # applied only where |x| < root_width_frac*a.
    root_mask = (y < 0) & (np.abs(x) < root_width_frac * a)
    # Parabolic indent: maximum root_depth at x=0, falls to 0 at |x| = root_width_frac*a.
    # Pushes boundary upward (positive y direction), reducing negativity.
    root_indent = root_depth * (1.0 - (x / (root_width_frac * a)) ** 2) * root_mask
    y_final = y_with_stem + root_indent

    # Stack into (n,2) array.
    polygon = np.column_stack((x, y_final)).astype(np.float64)

    if close:
        polygon = np.vstack((polygon, polygon[0:1]))

    return polygon
