"""Boundary-quad cleanup. Port of MATLAB CleanupBoundaryQuads_v2.m, collapse mode.

Removes unsmoothable boundary quads — a quad on the mesh boundary with two
adjacent boundary edges and an interior angle >134° at the shared corner.
Such quads have effectively zero quality and cannot be smoothed.

Only the "collapse" branch is ported in v0.1. The MATLAB "shift" branch
(when ``canRemoveEdges=False``) is a v0.2 follow-up.
"""

from __future__ import annotations

import math

import numpy as np

from chilmesh import CHILmesh

from .remove_unused import remove_unused_vertices


ANGLE_THRESHOLD_DEG = 134.0


def _interior_angle_deg(p_corner, p_a, p_b) -> float:
    """Angle at p_corner between vectors to p_a and p_b. Degrees, in [0, 180]."""
    va = np.asarray(p_a, dtype=float) - p_corner
    vb = np.asarray(p_b, dtype=float) - p_corner
    na = np.linalg.norm(va)
    nb = np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    cos = float(np.dot(va, vb) / (na * nb))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def cleanup_boundary_quads(mesh: CHILmesh, can_remove_edges: bool = True) -> CHILmesh:
    """Single pass. Caller may loop until no more candidates."""
    if not can_remove_edges:
        return mesh  # shift mode TODO v0.2.
    if mesh.connectivity_list.shape[1] != 4:
        return mesh

    bdy_edges = set(int(e) for e in mesh.boundary_edges())
    bdy_verts = set(int(v) for v in mesh.boundary_node_indices())
    cl = mesh.connectivity_list
    points = mesh.points

    to_collapse = []  # (elem_id, corner_vert, opposing_vert)
    consumed = set()

    for elem_id in range(mesh.n_elems):
        row = cl[elem_id]
        if int(row[2]) == int(row[3]):
            continue
        verts = row.astype(int).tolist()
        edges = mesh.elem2edge(elem_id).ravel().astype(int).tolist()
        on_bdy = [i for i, e in enumerate(edges) if int(e) in bdy_edges]
        if len(on_bdy) < 2:
            continue
        # Adjacent edges share a vert. Find the shared corner.
        adj = None
        for i in range(len(on_bdy) - 1):
            if (on_bdy[i] + 1) % 4 == on_bdy[i + 1]:
                adj = (on_bdy[i], on_bdy[i + 1])
                break
        if adj is None and len(on_bdy) >= 2 and on_bdy[0] == 0 and on_bdy[-1] == 3:
            adj = (3, 0)
        if adj is None:
            continue

        # Corner vert is at conn index `adj[1]`.
        ci = adj[1]
        corner = verts[ci]
        p_corner = points[corner]
        p_prev = points[verts[(ci - 1) % 4]]
        p_next = points[verts[(ci + 1) % 4]]
        angle = _interior_angle_deg(p_corner, p_prev, p_next)
        if angle <= ANGLE_THRESHOLD_DEG:
            continue

        opposing = verts[(ci + 2) % 4]
        if elem_id in consumed:
            continue
        # Don't consume quads adjacent to already-flagged ones (greedy disjoint).
        nbrs = set()
        for v in verts:
            nbrs.update(int(e) for e in mesh.get_vertex_elements(int(v)))
        if nbrs & consumed:
            continue

        to_collapse.append((elem_id, corner, opposing))
        consumed.update(nbrs)

    if not to_collapse:
        return mesh

    new_rows = cl.copy()
    deleted = np.zeros(mesh.n_elems, dtype=bool)
    new_points = points.copy()

    for elem_id, corner, opposing in to_collapse:
        # Move corner to opposing's position (collapse the diagonal).
        new_points[corner] = points[opposing]
        # Rewrite opposing → corner everywhere.
        new_rows[new_rows == opposing] = corner
        deleted[elem_id] = True

    new_rows = new_rows[~deleted]
    out = CHILmesh(new_rows, new_points, grid_name=getattr(mesh, "grid_name", None))
    return remove_unused_vertices(out)
