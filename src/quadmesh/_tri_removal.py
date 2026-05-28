"""Handle leftover tris after tri-pair merge in a layer.

Per MATLAB ``removeTrianglesFun``, each leftover tri is routed by:

    on_mesh_bdy?  + n boundary edges  →  operation
    ----------------------------------------------
    False, ≥1     → edge_bisection (case 2)
    True,  0      → edge_insertion (case 1)
    False, 0      → edge_insertion (case 2)
    True,  2 or 3 → edge_insertion (case 3)
    True,  1, can_remove → edge_removal
    True,  1, !can_remove → edge_bisection (case 1)

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
    tri (MATLAB case 2) is performed by the caller (``route_leftover_tri``, the
    layer-interior branch) via ``_split_opposing_tri``.
    """
    edge_ids = domain.elem2edge(tri_elem_id).ravel().astype(int)
    eid = int(edge_ids[bdy_edge_idx_in_tri])
    v_a, v_b = domain.edge2vert(eid).ravel().astype(int).tolist()

    mid = 0.5 * (domain.points[v_a] + domain.points[v_b])
    np_id = work.add_point(mid)
    # Pad domain.points so vertex IDs stay aligned with downstream work.points.
    domain.points = np.vstack([domain.points, mid.reshape(1, -1)])

    # Build new quad by slotting np_id between the (v_a, v_b) edge in conn.
    conn = domain.connectivity_list[tri_elem_id, :3].astype(int)
    if v_a not in conn.tolist() or v_b not in conn.tolist():
        return None
    # Orient so v_a is immediately followed by v_b in cyclic order. The edge may
    # be stored in the reverse direction (v_b → v_a); if so, swap endpoints — the
    # midpoint is identical and the emitted quad stays valid.
    ia = int(np.where(conn == v_a)[0][0])
    if conn[(ia + 1) % 3] != v_b:
        v_a, v_b = v_b, v_a
        ia = int(np.where(conn == v_a)[0][0])
    quad = np.array([conn[ia], np_id, conn[(ia + 1) % 3], conn[(ia + 2) % 3]], dtype=int)
    work.add_quad(quad)

    # Flag tri as consumed by zeroing its connectivity (caller drops zero rows).
    domain.connectivity_list[tri_elem_id, :] = 0
    return np_id


def _ccw_tri(tri: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Return ``tri`` reordered to positive (CCW) signed area."""
    p = points[tri, :2]
    area = 0.5 * (
        (p[1, 0] - p[0, 0]) * (p[2, 1] - p[0, 1])
        - (p[2, 0] - p[0, 0]) * (p[1, 1] - p[0, 1])
    )
    return tri[::-1].copy() if area < 0 else tri


def _split_opposing_tri(domain: CHILmesh, edge_id: int, np_id: int,
                         consumed_tri_id: int) -> Optional[int]:
    """Split the iLayer-1 tri sharing ``edge_id`` at midpoint ``np_id``.

    MATLAB ``edgeBisection`` Case 2 (``edgeBisection.m:47-79``). When
    ``edge_bisection`` bisects an interior layer-boundary edge, the new midpoint
    ``np_id`` lands on that edge — leaving a hanging node on the neighbouring
    tri in iLayer-1. That neighbour must be re-triangulated so the working tri
    domain stays conforming.

    Because ``np_id`` lies *on* the shared edge, the only valid split is the
    neighbour's apex joined to ``np_id`` — exactly what MATLAB's
    ``delaunayTriangulation([opp_conn, np_id])`` yields once its degenerate
    collinear tri is dropped, so we build the two tris directly (no Delaunay).

    Returns the appended element id, or ``None`` if ``edge_id`` has no opposite
    tri (a true mesh-boundary edge) or the neighbour is not a clean triangle.
    """
    pair = domain.edge2elem(edge_id).ravel().astype(int).tolist()
    opp = [e for e in pair if e != consumed_tri_id and e >= 0]
    if not opp:
        return None
    opp_id = opp[0]

    opp_conn = domain.connectivity_list[opp_id, :3].astype(int)
    v_a, v_b = domain.edge2vert(edge_id).ravel().astype(int).tolist()
    apex = [v for v in opp_conn.tolist() if v != v_a and v != v_b]
    if len(apex) != 1:
        return None  # opp already consumed / not a tri on this edge.
    apex = apex[0]

    tri1 = _ccw_tri(np.array([apex, v_a, np_id], dtype=int), domain.points)
    tri2 = _ccw_tri(np.array([apex, np_id, v_b], dtype=int), domain.points)

    width = domain.connectivity_list.shape[1]
    domain.connectivity_list[opp_id, :3] = tri1
    if width > 3:  # keep padded-triangle convention (repeat last vert)
        domain.connectivity_list[opp_id, 3:] = tri1[-1]

    new_id = domain.connectivity_list.shape[0]
    row = np.empty((1, width), dtype=domain.connectivity_list.dtype)
    row[0, :3] = tri2
    if width > 3:
        row[0, 3:] = tri2[-1]
    domain.connectivity_list = np.vstack([domain.connectivity_list, row])
    return new_id


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
        u, v = domain.edge2vert(int(e)).ravel().astype(int).tolist()
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
        # MATLAB edgeBisection Case 2: bisect the layer-interior edge, then
        # re-triangulate the iLayer-1 neighbour at the new midpoint so the
        # working tri domain stays conforming (edgeBisection.m:47-79).
        eid = int(edge_ids[bdy_edges_local[0]])
        np_id = edge_bisection(domain, work, tri_elem_id, bdy_edges_local[0])
        if np_id is not None:
            _split_opposing_tri(domain, eid, np_id, tri_elem_id)
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
        # MATLAB removeTrianglesFun: edgeBisection(1) when canRemoveEdges=false.
        edge_bisection(domain, work, tri_elem_id, bdy_edges_local[0])
    # Else: silently leave as triangle (degenerate, rare).
