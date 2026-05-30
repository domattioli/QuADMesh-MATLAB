"""Image/geometry-defined medial axis of a CHILmesh domain via interior Voronoi
ridges of densified boundary samples.

Approximation; fidelity scales with boundary sample density.
Ref QuADMesh #55, specs/004.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import Voronoi


def _boundary_segments(domain) -> np.ndarray:
    """(S,2,2) float array of boundary segment endpoint xy coords."""
    P = np.asarray(domain.points, dtype=float)[:, :2]
    be = np.asarray(domain.boundary_edges())
    e2v = np.asarray(domain.edge2vert())
    seg = e2v[be]                      # (S,2) vertex-index pairs
    return P[seg]                      # (S,2,2)


def _points_in_polygon(pts, seg_xy) -> np.ndarray:
    """Even-odd ray cast. pts (M,2), seg_xy (S,2,2). Returns bool (M,).
    Counts crossings of +x ray from each pt against every boundary segment;
    odd => inside. Handles holes/multiloops (all segments counted)."""
    pts = np.asarray(pts, float)
    a = seg_xy[:, 0, :]; b = seg_xy[:, 1, :]   # (S,2)
    x = pts[:, 0][:, None]; y = pts[:, 1][:, None]   # (M,1)
    ax, ay = a[:, 0][None, :], a[:, 1][None, :]      # (1,S)
    bx, by = b[:, 0][None, :], b[:, 1][None, :]
    # segment straddles the horizontal line y?
    cond = (ay > y) != (by > y)
    # x coord of intersection of segment with horizontal line at y
    denom = (by - ay)
    denom = np.where(denom == 0, np.nan, denom)
    xint = ax + (y - ay) * (bx - ax) / denom
    crosses = cond & (x < xint)
    return (np.nansum(crosses, axis=1).astype(int) % 2) == 1


def medial_axis_graph(domain, *, sample_spacing: float | None = None,
                      prune_tol: float | None = None):
    """Return (nodes (M,2) float64, edges (K,2) int64) of interior medial axis.
    sample_spacing: boundary resample target (default median boundary edge len).
    prune_tol: drop kept segments shorter than this (default None = keep all)."""
    seg_xy = _boundary_segments(domain)            # (S,2,2)
    lens = np.linalg.norm(seg_xy[:,1]-seg_xy[:,0], axis=1)
    target = float(sample_spacing) if sample_spacing else float(np.median(lens))
    target = target if target > 0 else 1.0
    # densify boundary -> sample points
    samples = []
    for (p0, p1), L in zip(seg_xy, lens):
        n = max(1, int(np.ceil(L / target)))
        t = np.linspace(0.0, 1.0, n + 1)[:-1]      # drop dup endpoint (next seg covers)
        samples.append(p0[None,:]*(1-t)[:,None] + p1[None,:]*t[:,None])
    pts = np.vstack(samples)
    # dedup (stable, rounded) for clean Voronoi
    _, idx = np.unique(np.round(pts, 9), axis=0, return_index=True)
    pts = pts[np.sort(idx)]
    vor = Voronoi(pts)
    V = vor.vertices                               # (NV,2)
    inside = _points_in_polygon(V, seg_xy)         # bool (NV,)
    kept = []
    for r in vor.ridge_vertices:
        if -1 in r:                                # infinite ridge
            continue
        i, j = r
        if inside[i] and inside[j]:
            kept.append((i, j))
    if not kept:
        return np.empty((0,2)), np.empty((0,2), dtype=np.int64)
    kept = np.asarray(kept, dtype=np.int64)
    if prune_tol:
        seglen = np.linalg.norm(V[kept[:,0]]-V[kept[:,1]], axis=1)
        kept = kept[seglen >= float(prune_tol)]
    # compact to used vertices only
    used = np.unique(kept)
    remap = {int(o): k for k, o in enumerate(used)}
    nodes = V[used].astype(np.float64)
    edges = np.array([[remap[int(a)], remap[int(b)]] for a, b in kept], dtype=np.int64)
    return nodes, edges
