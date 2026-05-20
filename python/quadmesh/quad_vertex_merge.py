"""Quad-vertex merge. Port of MATLAB QuadVertexMerge_v2.m.

Identify quads whose diagonal verts are both valence-3 (i.e. surrounded by
exactly 3 quads each). Removing such a quad and rewiring its 4 neighbours
yields a net 5-quad → 4-quad reduction.

Algorithm:
    1. List diagonals (pairs of opposing verts in each quad) where both endpoints
       are interior + valence-3.
    2. Greedy disjoint selection: a quad is eligible only if it AND its 4
       neighbours have not been used by an earlier merge in this pass.
    3. For each eligible quad q with diagonal (v1, v2):
         - Quads sharing v2 (the "side-2" neighbours) get v2 replaced with v1.
         - Quad q is removed.
"""

from __future__ import annotations

import numpy as np

from chilmesh import CHILmesh

from .remove_unused import remove_unused_vertices


def quad_vertex_merge(mesh: CHILmesh) -> CHILmesh:
    """One pass of QVM. Caller may loop until no eligible diagonals remain."""
    if mesh.connectivity_list.shape[1] != 4:
        return mesh

    bdy_verts = set(int(v) for v in mesh.boundary_node_indices())
    cl = mesh.connectivity_list

    # Collect candidate diagonals per quad: (v0, v2) and (v1, v3).
    eligible_quads = []  # (elem_id, v_keep, v_drop, side2_elems, side1_elems)
    consumed = np.zeros(mesh.n_elems, dtype=bool)

    for elem_id in range(mesh.n_elems):
        row = cl[elem_id]
        if int(row[2]) == int(row[3]):
            continue  # tri (padded)
        verts = row.astype(int).tolist()

        for v1, v2 in ((verts[0], verts[2]), (verts[1], verts[3])):
            if v1 in bdy_verts or v2 in bdy_verts:
                continue
            elems_v1 = list(mesh.get_vertex_elements(v1))
            elems_v2 = list(mesh.get_vertex_elements(v2))
            if len(elems_v1) != 3 or len(elems_v2) != 3:
                continue

            # All neighbours must be quads.
            neighbours = set(int(e) for e in elems_v1 + elems_v2) - {elem_id}
            if any(int(cl[n, 2]) == int(cl[n, 3]) for n in neighbours):
                continue

            # Disjointness with already-claimed quads.
            if consumed[elem_id] or any(consumed[n] for n in neighbours):
                continue

            side1 = [int(e) for e in elems_v1 if int(e) != elem_id]
            side2 = [int(e) for e in elems_v2 if int(e) != elem_id]
            eligible_quads.append((elem_id, v1, v2, side2, side1))

            consumed[elem_id] = True
            for n in neighbours:
                consumed[n] = True
            break  # one diagonal per quad max

    if not eligible_quads:
        return mesh

    new_rows = cl.copy()
    to_delete = np.zeros(mesh.n_elems, dtype=bool)
    for elem_id, v_keep, v_drop, side2, _side1 in eligible_quads:
        for n in side2:
            row = new_rows[n].copy()
            row[row == v_drop] = v_keep
            new_rows[n] = row
        to_delete[elem_id] = True

    new_rows = new_rows[~to_delete]
    out = CHILmesh(new_rows, mesh.points.copy(), grid_name=getattr(mesh, "grid_name", None))
    return remove_unused_vertices(out)
