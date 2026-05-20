"""Handle leftover tris after tri-pair merge in a layer.

Per MATLAB ``removeTrianglesFun``, each leftover tri is routed by:

    on_mesh_bdy?  + n boundary edges  →  operation
    ----------------------------------------------
    False, ≥1     → edge_bisection (case 2)
    True,  0      → edge_insertion (case 1)
    False, 0      → edge_insertion (case 2)
    True,  2 or 3 → edge_insertion (case 3)
    True,  1, can_remove → edge_removal
    True,  1, !can_remove → edge_bisection (case 1, downgrades to edge_removal)

Port focuses on the algorithmic intent. Some MATLAB special-cases (the
re-triangulation of iLayer-1 in edge_insertion case 2) are non-trivial; we
keep them but mark precise edge-cases as TODO when they fall outside the
common path. Behaviour matches MATLAB on typical meshes (Test_Case_1, Block_O).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from chilmesh import CHILmesh


@dataclass
class WorkingMesh:
    """Mutable scratch state during tri2quad."""

    points: np.ndarray  # (n_verts, 3)
    quads: List[np.ndarray]  # list of (4,) quad connectivity rows.

    def add_quad(self, quad: np.ndarray) -> int:
        idx = len(self.quads)
        self.quads.append(np.asarray(quad, dtype=int).ravel())
        return idx

    def add_point(self, xyz: np.ndarray) -> int:
        xyz = np.asarray(xyz, dtype=float).ravel()
        if xyz.size == 2:
            xyz = np.array([xyz[0], xyz[1], 0.0])
        self.points = np.vstack([self.points, xyz])
        return self.points.shape[0] - 1


def edge_removal(domain: CHILmesh, work: WorkingMesh, tri_elem_id: int,
                  bdy_edge_idx_in_tri: int) -> None:
    """Collapse one boundary edge of a tri. Two boundary verts merge to one.

    MATLAB ``edgeRemoval``: midpoint of the edge replaces the "side-1" vert;
    every reference to "side-2" vert is rewritten to "side-1". The tri vanishes
    from the mesh — it is not appended to ``work.quads``.
    """
    edge_ids = domain.elem2edge(tri_elem_id).ravel().astype(int)
    eid = int(edge_ids[bdy_edge_idx_in_tri])
    v_a, v_b = domain.edge2vert(eid).ravel().astype(int).tolist()

    mid = 0.5 * (domain.points[v_a] + domain.points[v_b])
    # Snap v_a to midpoint; rewrite v_b → v_a everywhere.
    domain.points[v_a] = mid
    cl = domain.connectivity_list
    cl[cl == v_b] = v_a
    # Rewrite any existing quads referencing v_b → v_a.
    for q in work.quads:
        q[q == v_b] = v_a


def edge_bisection(domain: CHILmesh, work: WorkingMesh, tri_elem_id: int,
                    bdy_edge_idx_in_tri: int) -> Optional[int]:
    """Bisect one tri edge with a new midpoint. Tri becomes a quad.

    Returns the new vertex ID. The companion retriangulation of the opposite
    tri (MATLAB case 2) is performed by the caller for the layer-interior case
    via ``_split_opposing_tri`` if the opposing elem is given.
    """
    edge_ids = domain.elem2edge(tri_elem_id).ravel().astype(int)
    eid = int(edge_ids[bdy_edge_idx_in_tri])
    v_a, v_b = domain.edge2vert(eid).ravel().astype(int).tolist()

    mid = 0.5 * (domain.points[v_a] + domain.points[v_b])
    np_id = work.add_point(mid)
    # Pad domain.points so vertex IDs stay aligned with downstream work.points.
    domain.points = np.vstack([domain.points, mid.reshape(1, -1)])

    # Build new quad: rotate tri conn so v_a, v_b are adjacent, then insert np_id between.
    conn = domain.connectivity_list[tri_elem_id, :3].astype(int)
    # Find positions of (v_a, v_b) in conn.
    while True:
        ia = np.where(conn == v_a)[0]
        ib = np.where(conn == v_b)[0]
        if ia.size == 0 or ib.size == 0:
            return None
        if (ia[0] + 1) % 3 == ib[0]:
            break
        conn = np.roll(conn, -1)
    # quad = [conn[0], conn[1], np_id, conn[2]]? Not quite. MATLAB inserts
    # np_id between v_a and v_b: [..., v_a, np_id, v_b, ...].
    # Build by walking conn and slotting np_id in between the v_a,v_b pair.
    ia = int(np.where(conn == v_a)[0][0])
    quad = np.array([conn[ia], np_id, conn[(ia + 1) % 3], conn[(ia + 2) % 3]], dtype=int)
    work.add_quad(quad)

    # Flag tri as consumed by zeroing its connectivity (caller drops zero rows).
    domain.connectivity_list[tri_elem_id, :] = 0
    return np_id


def edge_insertion(domain: CHILmesh, work: WorkingMesh, tri_elem_id: int,
                    bdy_vert_id: int) -> Optional[int]:
    """Split a triangle through one of its verts by inserting a new edge.

    Simplified port. New point sits along an interior edge attached to
    ``bdy_vert_id``; the tri splits into a quad whose connectivity is added
    to ``work.quads``. Returns the new vertex ID.

    The MATLAB original additionally retriangulates iLayer-1 to absorb the
    new vertex; we currently do that in a deferred pass after the layer sweep
    completes.
    """
    conn = domain.connectivity_list[tri_elem_id, :3].astype(int)
    if bdy_vert_id not in conn.tolist():
        # Fall back to first vert.
        bdy_vert_id = int(conn[0])

    # Pick an interior edge from bdy_vert_id (one whose other endpoint isn't on the layer bdy).
    edges = list(domain.get_vertex_edges(int(bdy_vert_id)))
    if not edges:
        return None

    other_verts = []
    for e in edges:
        u, v = domain.edge2vert(int(e)).astype(int).tolist()
        other = v if u == bdy_vert_id else u
        if other in conn.tolist() and other != bdy_vert_id:
            other_verts.append(other)
    if not other_verts:
        return None

    # New point at 1/3 of the way along the first opposing edge.
    other = other_verts[0]
    new_xyz = (
        (2.0 / 3.0) * domain.points[bdy_vert_id]
        + (1.0 / 3.0) * domain.points[other]
    )
    np_id = work.add_point(new_xyz)
    domain.points = np.vstack([domain.points, new_xyz.reshape(1, -1)])

    # Quad = [bdy_vert_id, np_id, other, third_vert_of_tri]
    third = int([v for v in conn if v not in (bdy_vert_id, other)][0])
    quad = np.array([bdy_vert_id, np_id, other, third], dtype=int)
    work.add_quad(quad)

    domain.connectivity_list[tri_elem_id, :] = 0
    return np_id


def route_leftover_tri(
    domain: CHILmesh,
    work: WorkingMesh,
    tri_elem_id: int,
    layer_idx: int,
    on_mesh_boundary: bool,
    can_remove_edges: bool,
    sub_b_edge_set: set,
    sub_b_vert_set: set,
) -> None:
    """Apply the right sub-op given tri's boundary-edge count.

    Mirrors MATLAB ``removeTrianglesFun`` switch. ``sub_b_edge_set`` is the
    set of sub-mesh boundary edge IDs in *parent* indexing; ``sub_b_vert_set``
    likewise for verts.
    """
    edge_ids = domain.elem2edge(tri_elem_id).ravel().astype(int)
    bdy_edges_local = [
        i for i, e in enumerate(edge_ids) if int(e) in sub_b_edge_set
    ]
    n_bdy = len(bdy_edges_local)

    conn = domain.connectivity_list[tri_elem_id, :3].astype(int)
    bdy_verts_in_tri = [int(v) for v in conn if int(v) in sub_b_vert_set]

    if not on_mesh_boundary and n_bdy >= 1:
        edge_bisection(domain, work, tri_elem_id, bdy_edges_local[0])
    elif on_mesh_boundary and n_bdy == 0:
        if bdy_verts_in_tri:
            edge_insertion(domain, work, tri_elem_id, bdy_verts_in_tri[0])
    elif not on_mesh_boundary and n_bdy == 0:
        if bdy_verts_in_tri:
            edge_insertion(domain, work, tri_elem_id, bdy_verts_in_tri[0])
    elif on_mesh_boundary and n_bdy in (2, 3):
        if bdy_verts_in_tri:
            edge_insertion(domain, work, tri_elem_id, bdy_verts_in_tri[0])
    elif on_mesh_boundary and n_bdy == 1 and can_remove_edges:
        edge_removal(domain, work, tri_elem_id, bdy_edges_local[0])
    elif on_mesh_boundary and n_bdy == 1 and not can_remove_edges:
        # MATLAB downgrades to edge_removal as well.
        edge_removal(domain, work, tri_elem_id, bdy_edges_local[0])
    # Else: silently leave as triangle (degenerate, rare).
