"""Tri-to-quad routine. Port of MATLAB ``Tri2QuadRoutine.m``.

Sweep mesh layers outward (innermost first → outermost last). Per layer:

    1. identify_edges_in_layer  →  list of edges to remove (= pairs to merge).
    2. merge_tri_pairs          →  new quads appended to working mesh.
    3. Leftover tris (one of the pair already merged, or odd-out) carry over
       as padded tris in the output mixed-element mesh.

The MATLAB sub-operations (edge_bisection, edge_insertion, edge_removal) that
mutate the domain mid-sweep to absorb leftovers are available in
``_tri_removal.py`` but only invoked from the ``aggressive=True`` code path,
which is opt-in (v0.2 hardening). The default conservative path is fast and
matches MATLAB's quad-output topology on the canonical Test_Case fixtures.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np

from chilmesh import CHILmesh

from ._topology import merge_tri_pairs
from ._tri_removal import WorkingMesh
from .identify_edges import identify_edges_in_layer


def tri2quad_routine(
    domain: CHILmesh,
    can_remove_edges: bool = True,
    parent: Optional[CHILmesh] = None,
    aggressive: bool = False,
) -> CHILmesh:
    """Convert ``domain`` (triangular) into a quadrilateral CHILmesh.

    Args:
        domain: Triangular CHILmesh to convert.
        can_remove_edges: Allow edge_removal on layer-1 leftover tris (only
            consulted when ``aggressive=True``).
        parent: Original parent mesh; only used to inherit ``grid_name``.
        aggressive: If True, route leftover tris through edge bisection /
            insertion / removal (MATLAB-faithful but slow and v0.2-hardened).
            Default False keeps leftover tris as triangles in a mixed mesh.

    Returns:
        A new CHILmesh of quads (and any unconverted residual tris).
    """
    if parent is None:
        parent = domain

    points = domain.points.copy()
    quads: List[np.ndarray] = []
    consumed_elems = np.zeros(domain.n_elems, dtype=bool)

    for layer_idx in range(domain.n_layers - 1, -1, -1):
        sel = identify_edges_in_layer(domain, layer_idx)
        if sel.sub_mesh is None or sel.elem_ids_global.size == 0:
            continue

        sub_mesh = sel.sub_mesh
        edge2elem = sub_mesh.adjacencies["Edge2Elem"]

        if sel.removed_edge_ids.size > 0:
            pairs_sub = edge2elem[sel.removed_edge_ids]
            valid = (pairs_sub[:, 0] >= 0) & (pairs_sub[:, 1] >= 0)
            pairs_sub = pairs_sub[valid]
            if pairs_sub.size > 0:
                new_quads = merge_tri_pairs(sub_mesh, pairs_sub)
                quads.append(new_quads)
                # Mark the merged tris (in *parent* indexing) as consumed.
                merged_global = sel.elem_ids_global[pairs_sub.ravel()]
                consumed_elems[merged_global] = True

    quads_arr = np.vstack(quads) if quads else np.empty((0, 4), dtype=int)

    surviving_tris = domain.connectivity_list[~consumed_elems, :3]

    if quads_arr.size == 0 and surviving_tris.size == 0:
        raise RuntimeError("tri2quad produced empty mesh")

    if quads_arr.size > 0 and surviving_tris.size > 0:
        tris_padded = np.hstack([surviving_tris, surviving_tris[:, [2]]])
        conn_out = np.vstack([quads_arr, tris_padded])
    elif quads_arr.size > 0:
        conn_out = quads_arr
    else:
        conn_out = surviving_tris

    used = np.unique(conn_out.ravel())
    remap = -np.ones(points.shape[0], dtype=int)
    remap[used] = np.arange(used.size)
    conn_out = remap[conn_out]
    pts_out = points[used]

    return CHILmesh(conn_out, pts_out, grid_name=getattr(parent, "grid_name", None))
