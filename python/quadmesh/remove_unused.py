"""Drop unreferenced vertices from a mesh. Port of MATLAB RemoveUnusedVertices.

In MATLAB, ``removedVertIDs`` was provided by the caller. Here we simply
detect unreferenced verts from the connectivity list itself — robust to
any path through post-process.
"""

from __future__ import annotations

import numpy as np

from chilmesh import CHILmesh


def remove_unused_vertices(mesh: CHILmesh) -> CHILmesh:
    """Drop verts not referenced by connectivity_list. Renumber + rebuild mesh."""
    used = np.unique(mesh.connectivity_list.ravel())
    if used.size == mesh.n_verts:
        return mesh

    remap = -np.ones(mesh.n_verts, dtype=int)
    remap[used] = np.arange(used.size)
    new_conn = remap[mesh.connectivity_list]
    new_pts = mesh.points[used]
    return CHILmesh(new_conn, new_pts, grid_name=getattr(mesh, "grid_name", None))
