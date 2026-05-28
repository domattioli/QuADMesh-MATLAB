"""Recombination operators: edge-swap, vertex-duplication, edge-flip.

Ports of thesis Fig 3.2 (p39), Fig 3.3 (p39), Fig 3.6 (p40) / Fig 4.4 (p69).

These are topology-only patches that rearrange triangles so the subsequent
identify_edges sweep can pair them into quads. They do NOT modify the point
array — only the connectivity of a WorkingMesh.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from ._tri_removal import WorkingMesh


# ── helpers ──────────────────────────────────────────────────────────────────

def _find_tri(work: WorkingMesh, v0: int, v1: int, v2: int) -> int:
    """Return index of tri containing exactly these 3 verts, or -1."""
    s = frozenset([v0, v1, v2])
    for i, t in enumerate(work.tris):
        if t is not None and frozenset(t[:3]) == s:
            return i
    return -1


def _tris_sharing_edge(
    work: WorkingMesh, va: int, vb: int
) -> Tuple[int, int]:
    """Return (i, j) of the two live tri indices sharing edge va-vb.

    Returns (-1, -1) if fewer than 2 live tris share that edge.
    """
    if work.tris is None:
        return (-1, -1)
    hits = []
    for i, t in enumerate(work.tris):
        if t is None:
            continue
        verts = set(int(v) for v in t[:3])
        if va in verts and vb in verts:
            hits.append(i)
        if len(hits) == 2:
            return hits[0], hits[1]
    return (-1, -1)


def _opposite_vert(tri: np.ndarray, va: int, vb: int) -> int:
    """Return the vertex of tri NOT equal to va or vb."""
    for v in tri[:3]:
        if int(v) != va and int(v) != vb:
            return int(v)
    return -1


def _ccw_signed_area(pts: np.ndarray, a: int, b: int, c: int) -> float:
    p, q, r = pts[a], pts[b], pts[c]
    return 0.5 * ((q[0]-p[0])*(r[1]-p[1]) - (r[0]-p[0])*(q[1]-p[1]))


# ── T013 — edge-swap ─────────────────────────────────────────────────────────

def edge_swap(
    work: WorkingMesh,
    va: int,
    vb: int,
    pts: np.ndarray,
) -> bool:
    """Reconnect two tris sharing edge va-vb so they share the opposite diagonal.

    Thesis Fig 3.2 (p39). Two tris [va,vb,vc] and [va,vb,vd] → [va,vc,vd] +
    [vb,vd,vc] (or the equivalent CCW orientation). The swap is only performed
    when both resulting tris have positive signed area (non-degenerate).

    Returns True if the swap was performed, False otherwise.
    """
    i, j = _tris_sharing_edge(work, va, vb)
    if i == -1:
        return False
    ti, tj = work.tris[i], work.tris[j]
    vc = _opposite_vert(ti, va, vb)
    vd = _opposite_vert(tj, va, vb)
    if vc == -1 or vd == -1:
        return False

    # Candidate replacement tris.
    if _ccw_signed_area(pts, va, vc, vd) > 1e-14 and _ccw_signed_area(pts, vb, vd, vc) > 1e-14:
        work.tris[i] = np.array([va, vc, vd], dtype=int)
        work.tris[j] = np.array([vb, vd, vc], dtype=int)
        return True
    # Try opposite orientation.
    if _ccw_signed_area(pts, va, vd, vc) > 1e-14 and _ccw_signed_area(pts, vb, vc, vd) > 1e-14:
        work.tris[i] = np.array([va, vd, vc], dtype=int)
        work.tris[j] = np.array([vb, vc, vd], dtype=int)
        return True
    return False


# ── T014 — vertex-duplication ────────────────────────────────────────────────

def vertex_duplication(
    work: WorkingMesh,
    v: int,
    pts: np.ndarray,
    layer_verts: Optional[np.ndarray] = None,
) -> Tuple[bool, int]:
    """Duplicate shared vertex v so two incident tris no longer share it.

    Thesis Fig 3.3 (p39). Used when an isolated tri shares only a vertex (not
    an edge) with its nearest neighbour quad / tri. The new vertex is placed at
    the same coordinates as v; downstream smoothing will resolve it.

    Returns (success, new_vert_idx). If success is False, new_vert_idx is -1.
    """
    incident = [i for i, t in enumerate(work.tris) if t is not None and v in t[:3]]
    if len(incident) < 2:
        return False, -1

    # Duplicate: append new point at same position, reassign first incident tri.
    new_idx = len(pts)
    # Extend pts array (we return the updated pts via work)
    # WorkingMesh.points is a reference — we extend it.
    new_pts = np.vstack([pts, pts[v]])
    # Reassign vertex v → new_idx in the *second* incident tri only.
    ti = incident[1]
    new_tri = work.tris[ti].copy()
    new_tri[new_tri == v] = new_idx
    work.tris[ti] = new_tri
    # Update work.points reference.
    work.points = new_pts
    return True, new_idx


# ── T015 — edge-flip + walk driver ───────────────────────────────────────────

def edge_flip(
    work: WorkingMesh,
    elem_idx: int,
    pts: np.ndarray,
) -> bool:
    """Flip the longest interior edge of tri elem_idx to improve pairing.

    Thesis Fig 3.6 (p40) / Fig 4.4 (p69). Finds the interior (non-boundary)
    edge of the target tri that is longest, then applies edge_swap on it.

    Returns True if a flip was performed.
    """
    if work.tris[elem_idx] is None:
        return False
    tri = work.tris[elem_idx]
    verts = [int(v) for v in tri[:3]]
    edges = [(verts[0], verts[1]), (verts[1], verts[2]), (verts[2], verts[0])]

    best_len = -1.0
    best_edge: Optional[Tuple[int, int]] = None
    for va, vb in edges:
        # Interior = has a neighbour on this edge.
        i, j = _tris_sharing_edge(work, va, vb)
        if i == -1 or j == -1:
            continue
        length = float(np.linalg.norm(pts[va] - pts[vb]))
        if length > best_len:
            best_len = length
            best_edge = (va, vb)

    if best_edge is None:
        return False
    return edge_swap(work, best_edge[0], best_edge[1], pts)


def walk_isolated_tri(
    work: WorkingMesh,
    isolated_idx: int,
    pts: np.ndarray,
    max_hops: int = 4,
) -> bool:
    """Walk edge-flips from an isolated tri until it gains a pairable neighbour.

    Thesis Fig 4.4 (p69). Repeatedly flips the longest interior edge of the
    currently-targeted tri. Stops when a neighbour tri appears that can be
    merged into a quad (i.e. two live tris share that edge), or after max_hops.

    Returns True if the walk resolved the isolation.
    """
    current = isolated_idx
    for _ in range(max_hops):
        if work.tris[current] is None:
            return False
        tri = work.tris[current]
        verts = [int(v) for v in tri[:3]]
        edges = [(verts[0], verts[1]), (verts[1], verts[2]), (verts[2], verts[0])]

        # Already has a pairable neighbour?
        for va, vb in edges:
            i, j = _tris_sharing_edge(work, va, vb)
            if i != -1 and j != -1:
                return True

        # Try to flip.
        if not edge_flip(work, current, pts):
            return False
    return False
