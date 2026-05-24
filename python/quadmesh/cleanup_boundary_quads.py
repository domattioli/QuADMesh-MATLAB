"""Boundary-quad cleanup. Port of MATLAB CleanupBoundaryQuads_v2.m.

Two modes:
  collapse (can_remove_edges=True):  merge side verts into corner; delete bad quad. MATLAB subroutineCleanupBoundaryQuads.
  shift    (can_remove_edges=False): move corner vert inward to reduce angle. v0.2 addition (MATLAB never implemented).

Bad quad: two adjacent boundary edges whose shared corner has angle > 134 deg.
"""
from __future__ import annotations

import math

import numpy as np

from chilmesh import CHILmesh

from .remove_unused import remove_unused_vertices

ANGLE_THRESHOLD_DEG = 134.0


def _seg_cross(a, b, c, d) -> bool:
    """Strict segment intersection (open segments, not endpoints)."""
    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])
    return (cr(c, d, a) > 0) != (cr(c, d, b) > 0) and (cr(a, b, c) > 0) != (cr(a, b, d) > 0)


def _is_bowtie(p4: np.ndarray) -> bool:
    return _seg_cross(p4[0], p4[1], p4[2], p4[3]) or _seg_cross(p4[1], p4[2], p4[3], p4[0])


def _angle_deg(p_corner: np.ndarray, p_a: np.ndarray, p_b: np.ndarray) -> float:
    va = np.asarray(p_a, dtype=float) - p_corner
    vb = np.asarray(p_b, dtype=float) - p_corner
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    cos = float(np.dot(va, vb) / (na * nb))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos))))


def _shift_to_target_angle(
    p_corner: np.ndarray,
    p_a: np.ndarray,
    p_b: np.ndarray,
    p_opposing: np.ndarray,
    target_deg: float = 90.0,
) -> np.ndarray:
    """Binary search: move p_corner toward p_opposing until angle(p_a, corner, p_b) ~= target_deg."""
    p_c = np.asarray(p_corner, dtype=float)
    p_opp = np.asarray(p_opposing, dtype=float)
    p_a = np.asarray(p_a, dtype=float)
    p_b = np.asarray(p_b, dtype=float)
    lo, hi = 0.0, 1.0
    for _ in range(24):
        t = 0.5 * (lo + hi)
        new_c = p_c + t * (p_opp - p_c)
        if _angle_deg(new_c, p_a, p_b) > target_deg:
            lo = t
        else:
            hi = t
    return p_c + 0.5 * (lo + hi) * (p_opp - p_c)


def _scan_bad_quads(mesh: CHILmesh):
    """Yield (elem_id, corner, opposing, ci, verts, p_prev, p_next) for bad boundary quads."""
    bdy_edges = set(int(e) for e in mesh.boundary_edges())
    cl = mesh.connectivity_list
    pts = mesh.points
    consumed: set[int] = set()

    for elem_id in range(mesh.n_elems):
        row = cl[elem_id]
        if int(row[2]) == int(row[3]):
            continue  # padded tri
        verts = row.astype(int).tolist()
        edges = mesh.elem2edge(elem_id).ravel().astype(int).tolist()
        on_bdy = [i for i, e in enumerate(edges) if int(e) in bdy_edges]
        if len(on_bdy) < 2:
            continue

        # Find two adjacent boundary edges (share a corner vertex).
        adj = None
        for i in range(len(on_bdy) - 1):
            if (on_bdy[i] + 1) % 4 == on_bdy[i + 1]:
                adj = (on_bdy[i], on_bdy[i + 1])
                break
        if adj is None and len(on_bdy) >= 2 and on_bdy[0] == 0 and on_bdy[-1] == 3:
            adj = (3, 0)
        if adj is None:
            continue

        ci = adj[1]
        corner = verts[ci]
        p_prev = pts[verts[(ci - 1) % 4]]
        p_next = pts[verts[(ci + 1) % 4]]
        if _angle_deg(pts[corner], p_prev, p_next) <= ANGLE_THRESHOLD_DEG:
            continue

        opposing = verts[(ci + 2) % 4]

        if elem_id in consumed:
            continue
        nbrs: set[int] = set()
        for v in verts:
            nbrs.update(int(e) for e in mesh.get_vertex_elements(int(v)))
        if nbrs & consumed:
            continue
        consumed |= nbrs

        yield elem_id, corner, opposing, ci, verts, p_prev, p_next


def cleanup_boundary_quads(mesh: CHILmesh, can_remove_edges: bool = True) -> CHILmesh:
    """Single pass. Loop caller until stable.

    Args:
        mesh: Quad (or padded-tri) CHILmesh.
        can_remove_edges: True -> collapse mode (MATLAB-faithful).
                          False -> shift mode (v0.2, Python-only).
    """
    if mesh.connectivity_list.shape[1] != 4:
        return mesh

    bad = list(_scan_bad_quads(mesh))
    if not bad:
        return mesh

    new_pts = mesh.points.copy()
    new_rows = mesh.connectivity_list.copy()

    if can_remove_edges:
        # MATLAB subroutineCleanupBoundaryQuads:
        # side1 = verts[(ci-1)%4], side2 = verts[(ci+1)%4] remapped to corner.
        # Corner stays in place. Bad quad deleted.
        # Each op simulated on neighbors first; skipped if remap would bowtie
        # any surviving quad (global remap can deform neighbour geometry).
        deleted = np.zeros(mesh.n_elems, dtype=bool)
        for elem_id, corner, opposing, ci, verts, p_prev, p_next in bad:
            side1 = verts[(ci - 1) % 4]
            side2 = verts[(ci + 1) % 4]
            # Rows affected by the remap (excluding the quad being deleted).
            mask = (
                np.any((new_rows == side1) | (new_rows == side2), axis=1) & ~deleted
            )
            mask[elem_id] = False
            ok = True
            for r_idx in np.where(mask)[0]:
                sim = new_rows[r_idx].copy()
                sim[sim == side1] = corner
                sim[sim == side2] = corner
                vs = list(dict.fromkeys(int(v) for v in sim))
                if len(vs) < 4:
                    ok = False
                    break
                p4 = new_pts[np.array(vs[:4], dtype=int), :2]
                if _is_bowtie(p4):
                    ok = False
                    break
            if not ok:
                continue  # skip: remap would create bowtie in a neighbour
            new_rows[new_rows == side1] = corner
            new_rows[new_rows == side2] = corner
            deleted[elem_id] = True
        new_rows = new_rows[~deleted]
        out = CHILmesh(new_rows, new_pts, grid_name=getattr(mesh, "grid_name", None))
        return remove_unused_vertices(out)
    else:
        # Shift: move corner toward opposing until angle <= target.
        for elem_id, corner, opposing, ci, verts, p_prev, p_next in bad:
            new_pts[corner] = _shift_to_target_angle(
                mesh.points[corner], p_prev, p_next, mesh.points[opposing]
            )
        return CHILmesh(new_rows, new_pts, grid_name=getattr(mesh, "grid_name", None))
