"""Doublet collapse. Port of MATLAB DoubletCollapse.m.

Two quads share 3 vertices → collapse to 1 quad. Triggered when an interior
vertex has valence exactly 2 and both incident elems are quads. The shared
"diagonal" vert is removed; the two quads merge.

In MATLAB the test was: ``interior valence-2 vertex, both elems quads``.
Output: collapsed mesh; the consumed vert ID added to ``removed_vert_ids``.
"""

from __future__ import annotations

import numpy as np

from chilmesh import CHILmesh

from .remove_unused import remove_unused_vertices


def _is_quad_row(row: np.ndarray) -> bool:
    """4-col conn row is a quad iff its 3rd and 4th verts differ."""
    return row.shape[0] == 4 and int(row[2]) != int(row[3])


def doublet_collapse(mesh: CHILmesh) -> CHILmesh:
    """Collapse every valence-2 interior vert whose two adjacent elems are quads.

    Returns a new CHILmesh with affected pairs merged into single quads, and
    unreferenced verts pruned.
    """
    if mesh.connectivity_list.shape[1] != 4:
        return mesh  # No quads, nothing to do.

    bdy_verts = set(int(v) for v in mesh.boundary_node_indices())
    int_verts = [v for v in range(mesh.n_verts) if v not in bdy_verts]

    n_elems = mesh.n_elems
    consumed = np.zeros(n_elems, dtype=bool)
    new_rows = mesh.connectivity_list.copy()

    for v in int_verts:
        elems = list(mesh.get_vertex_elements(v))
        if len(elems) != 2:
            continue
        ea, eb = int(elems[0]), int(elems[1])
        if consumed[ea] or consumed[eb]:
            continue
        if not (_is_quad_row(new_rows[ea]) and _is_quad_row(new_rows[eb])):
            continue

        ra = new_rows[ea]
        rb = new_rows[eb]
        ra_set = set(ra.tolist())
        rb_set = set(rb.tolist())
        common = ra_set & rb_set
        # Need exactly 3 shared verts for the doublet pattern.
        if len(common) != 3:
            continue

        # Vert in rb but not in ra:
        unique_b = next(iter(rb_set - ra_set))

        # Replace v in ra with unique_b.
        merged = ra.copy()
        merged[merged == v] = unique_b
        # Sanity: merged should still be 4 distinct verts.
        if len(set(merged.tolist())) != 4:
            continue

        new_rows[ea] = merged
        new_rows[eb] = 0  # Mark for deletion.
        consumed[eb] = True

    if not consumed.any():
        return mesh

    keep_mask = ~consumed
    new_rows = new_rows[keep_mask]
    out = CHILmesh(new_rows, mesh.points.copy(), grid_name=getattr(mesh, "grid_name", None))
    return remove_unused_vertices(out)
