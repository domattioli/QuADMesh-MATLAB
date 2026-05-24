"""Topology helpers. CCW edge sorting around verts. Merge tri pairs to quads.

MATLAB src: CCWEdgesAroundVertsFun.m, mergeTrianglesFun.m.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence

import numpy as np


def ccw_edges_around_vert(mesh, vert_ids: Sequence[int]) -> List[np.ndarray]:
    """Sort edges incident to each vert by polar angle, CCW.

    Port of MATLAB ``CCWEdgesAroundVertsFun``. For each ``v`` in ``vert_ids``,
    list its incident edge IDs ordered counter-clockwise around ``v``.

    Args:
        mesh: CHILmesh instance.
        vert_ids: Iterable of global vertex IDs.

    Returns:
        List of 1-D arrays (one per input vert) of edge IDs in CCW order.
    """
    vert_ids = np.asarray(list(vert_ids), dtype=int).ravel()
    edge2vert = mesh.adjacencies["Edge2Vert"]
    points = mesh.points

    out: List[np.ndarray] = []
    for v in vert_ids:
        eids = np.fromiter(mesh.get_vertex_edges(int(v)), dtype=int)
        if eids.size == 0:
            out.append(eids)
            continue
        e2v = edge2vert[eids]
        # Other endpoint per edge.
        other = np.where(e2v[:, 0] == v, e2v[:, 1], e2v[:, 0])
        dx = points[other, 0] - points[v, 0]
        dy = points[other, 1] - points[v, 1]
        theta = np.arctan2(dy, dx)
        order = np.argsort(theta, kind="stable")
        out.append(eids[order])
    return out


def merge_tri_pair(mesh, elem_id_a: int, elem_id_b: int) -> np.ndarray:
    """Merge two tris sharing an edge into one quad. Return 4-vert connectivity.

    Quads are CCW. Shared edge is removed; opposing vertices form the new diagonal.
    """
    conn = mesh.connectivity_list
    t1 = conn[elem_id_a, :3].astype(int)
    t2 = conn[elem_id_b, :3].astype(int)

    shared = np.intersect1d(t1, t2, assume_unique=False)
    if shared.size != 2:
        raise ValueError(
            f"Elems {elem_id_a},{elem_id_b} do not share exactly 2 verts (got {shared.size})"
        )

    unique_b = int(np.setdiff1d(t2, shared, assume_unique=False)[0])
    # Rotate t1 so shared edge sits at positions (0,1); unique-of-t1 ends up at index 2.
    # Then quad = [t1[0], unique_b, t1[1], t1[2]] preserves CCW.
    # Find unique-of-t1.
    unique_a = int(np.setdiff1d(t1, shared, assume_unique=False)[0])
    iu = int(np.where(t1 == unique_a)[0][0])
    rotated = np.roll(t1, -iu)  # rotated[0] = unique_a
    # rotated = [unique_a, s1, s2]. Insert unique_b between s1 and s2 to form quad
    # [unique_a, s1, unique_b, s2] which is CCW if both tris were CCW.
    quad = np.array([rotated[0], rotated[1], unique_b, rotated[2]], dtype=int)
    return quad


def merge_tri_pairs(mesh, pair_elem_ids: np.ndarray) -> np.ndarray:
    """Vector form. ``pair_elem_ids`` is shape ``(n, 2)``.

    Returns ``(n, 4)`` quad connectivity (CCW assuming CCW input).
    """
    pair_elem_ids = np.atleast_2d(np.asarray(pair_elem_ids, dtype=int))
    if pair_elem_ids.shape[1] != 2:
        raise ValueError(f"pair_elem_ids must be (n,2); got {pair_elem_ids.shape}")
    quads = np.empty((pair_elem_ids.shape[0], 4), dtype=int)
    for i, (a, b) in enumerate(pair_elem_ids):
        quads[i] = merge_tri_pair(mesh, int(a), int(b))
    return quads


def edge2elem_pair(mesh, edge_ids: Iterable[int]) -> np.ndarray:
    """Return ``(n, 2)`` elem pair per edge. Sentinel for missing neighbour: ``-1``."""
    eids = np.asarray(list(edge_ids), dtype=int)
    return mesh.adjacencies["Edge2Elem"][eids]


def shared_edge(mesh, elem_id_a: int, elem_id_b: int) -> int:
    """Edge ID shared by two elems. ``-1`` if none."""
    ea = set(mesh.elem2edge(int(elem_id_a)).tolist())
    eb = set(mesh.elem2edge(int(elem_id_b)).tolist())
    common = ea & eb
    return int(next(iter(common))) if common else -1
