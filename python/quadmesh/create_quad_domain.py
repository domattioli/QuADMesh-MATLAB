"""Subset selection for tri→quad conversion. Port of createQuadDomain.m.

MATLAB had 3 strategies (all-mesh, distance-from-shoreline, polygon).
v0.1 supports only:
    - None polygon → all triangles
    - polygon ndarray → tris with at least one vert in polygon
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Union

import numpy as np
from matplotlib.path import Path as MplPath

from chilmesh import CHILmesh


PolygonInput = Union[np.ndarray, Sequence[np.ndarray]]


def create_quad_domain(mesh: CHILmesh, polygon: Optional[PolygonInput] = None) -> CHILmesh:
    """Pick the tri subset to convert.

    Args:
        mesh: Triangular CHILmesh.
        polygon: Either a single ``(N,2)`` array of XY points, or a list of
            such arrays (union mask). ``None`` → all tris.

    Returns:
        New CHILmesh of selected tris. Points list unchanged (extra verts get
        pruned by `remove_unused_vertices` downstream if needed).
    """
    if polygon is None:
        return mesh.copy() if hasattr(mesh, "copy") else mesh

    # Normalise to list of polygons.
    if isinstance(polygon, np.ndarray) and polygon.ndim == 2:
        polygons = [polygon]
    else:
        polygons = [np.asarray(p) for p in polygon]

    in_pts = np.zeros(mesh.n_verts, dtype=bool)
    xy = mesh.points[:, :2]
    for poly in polygons:
        path = MplPath(np.asarray(poly)[:, :2])
        in_pts |= path.contains_points(xy)

    elem_in = np.any(in_pts[mesh.connectivity_list[:, :3]], axis=1)
    if not elem_in.any():
        raise ValueError("polygon flagged no triangles")

    sub_conn = mesh.connectivity_list[elem_in]
    return CHILmesh(sub_conn, mesh.points.copy(), grid_name=getattr(mesh, "grid_name", None))
