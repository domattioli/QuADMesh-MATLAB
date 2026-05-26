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

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from chilmesh import CHILmesh


@dataclass
class LayerState:
    """Snapshot of OE/IE/OV/IV membership per layer. Tracks mutations.

    Route ops (edge_removal, edge_bisection, edge_insertion) can shift vertex
    membership across layers. Call ``sync`` after each layer to refresh the
    snapshot so subsequent identify_edges_in_layer calls see consistent state.
    """

    oe: List[np.ndarray]  # per-layer outer elements
    ie: List[np.ndarray]  # per-layer inner elements
    ov: List[np.ndarray]  # per-layer outer vertices
    iv: List[np.ndarray]  # per-layer inner vertices
    mutated: bool = False

    @classmethod
    def from_domain(cls, domain: CHILmesh) -> "LayerState":
        """Snapshot current layer membership from a domain CHILmesh."""
        layers = domain.layers
        nl = int(getattr(domain, "n_layers", 0) or 0)
        return cls(
            oe=[np.asarray(layers["OE"][i], dtype=int) for i in range(nl)],
            ie=[np.asarray(layers["IE"][i], dtype=int) for i in range(nl)],
            ov=[np.asarray(layers["OV"][i], dtype=int) for i in range(nl)],
            iv=[np.asarray(layers["IV"][i], dtype=int) for i in range(nl)],
        )

    def sync(self, domain: CHILmesh) -> None:
        """Refresh snapshot from domain after route ops have mutated it."""
        layers = domain.layers
        nl = int(getattr(domain, "n_layers", 0) or 0)
        for i in range(min(nl, len(self.oe))):
            self.oe[i] = np.asarray(layers["OE"][i], dtype=int)
            self.ie[i] = np.asarray(layers["IE"][i], dtype=int)
            self.ov[i] = np.asarray(layers["OV"][i], dtype=int)
            self.iv[i] = np.asarray(layers["IV"][i], dtype=int)
        self.mutated = False

    def mark_mutated(self) -> None:
        self.mutated = True


@dataclass
class WorkingMesh:
    """Mutable scratch state during tri2quad."""

    points: np.ndarray  # (n_verts, 3) — original points; not grown during sweep
    quads: List[np.ndarray]  # list of (4,) quad connectivity rows.
    tris: Optional[List[Optional[np.ndarray]]] = None
    _n_pts: int = field(default=0, init=False, repr=False)
    _extra_pts: List[np.ndarray] = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_n_pts", self.points.shape[0])

    def add_quad(self, quad: np.ndarray) -> int:
        idx = len(self.quads)
        self.quads.append(np.asarray(quad, dtype=int).ravel())
        return idx

    def add_point(self, xyz: np.ndarray) -> int:
        # Buffer new points in a list; domain.points is synced once at end of
        # _faithful_per_layer via flush_points_to_domain().  New point coords are
        # never read back from domain.points during the sweep.
        xyz = np.asarray(xyz, dtype=float).ravel()
        if xyz.size == 2:
            xyz = np.array([xyz[0], xyz[1], 0.0])
        idx = self._n_pts
        self._extra_pts.append(xyz)
        object.__setattr__(self, "_n_pts", idx + 1)
        return idx

    @property
    def n_pts(self) -> int:
        """Total point count including buffered new points."""
        return self._n_pts

    def get_extra_point(self, idx: int) -> np.ndarray:
        """Coordinates for a buffered new vertex (idx >= original n_pts)."""
        offset = idx - self.points.shape[0]
        return self._extra_pts[offset]

    def flush_points_to_domain(self, domain) -> None:
        """Extend domain.points with all buffered new points in one vstack."""
        if not self._extra_pts:
            return
        extra = np.stack(self._extra_pts)
        domain.points = np.vstack([domain.points, extra])
        self._extra_pts.clear()


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
    # np_id only used in work.quads connectivity; domain.points[np_id] never
    # read back so no need to grow domain.points here.

    # Build new quad: rotate tri conn so v_a, v_b are adjacent, then insert np_id between.
    conn = domain.connectivity_list[tri_elem_id, :3].astype(int)
    # Find positions of (v_a, v_b) in conn. Cap at 3 rolls (one full cycle); if the
    # edge appears reversed (ib → ia CCW) swap v_a/v_b so the insertion is consistent.
    for _ in range(3):
        ia = np.where(conn == v_a)[0]
        ib = np.where(conn == v_b)[0]
        if ia.size == 0 or ib.size == 0:
            return None
        if (ia[0] + 1) % 3 == ib[0]:
            break
        if (ib[0] + 1) % 3 == ia[0]:
            v_a, v_b = v_b, v_a  # edge is CCW as v_b→v_a; swap to match convention
            break
        conn = np.roll(conn, -1)
    else:
        return None  # degenerate — v_a or v_b not adjacent in this tri
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
        # MATLAB removeTrianglesFun: edgeBisection(1) when canRemoveEdges=false.
        edge_bisection(domain, work, tri_elem_id, bdy_edges_local[0])
    # Else: silently leave as triangle (degenerate, rare).


# ── T019 — isolated-tri handling ─────────────────────────────────────────────

def handle_isolated_tris(
    layer_conn: np.ndarray,
    layer_global_ids: np.ndarray,
    consumed: set,
    pts: np.ndarray,
    work: WorkingMesh,
) -> set:
    """Pair remaining isolated tris in a layer via edge-swap fixup (CR-5, p66).

    After the main pairing sweep, some tris may be isolated (no eligible
    neighbour in the same layer). For each such tri, attempt walk_isolated_tri
    to flip its neighbourhood so it gains a pairable neighbour, then merge.

    Thesis CR-5 (p66): intentional vertex-pairing + post-match edge-swap fixup.
    Returns the set of newly consumed global IDs.
    """
    from ._recombine import walk_isolated_tri

    adj: dict = {}
    edge2tris: dict = {}
    for i, row in enumerate(layer_conn):
        a, b, c = int(row[0]), int(row[1]), int(row[2])
        for e in (tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((a, c)))):
            edge2tris.setdefault(e, []).append(i)
    for tris_list in edge2tris.values():
        if len(tris_list) == 2:
            adj.setdefault(tris_list[0], []).append(tris_list[1])
            adj.setdefault(tris_list[1], []).append(tris_list[0])

    global_to_local = {int(g): i for i, g in enumerate(layer_global_ids)}
    local_consumed = set(
        global_to_local[g] for g in consumed if g in global_to_local
    )

    work.tris = [row.copy() for row in layer_conn]
    newly_consumed: set = set()

    n = len(layer_conn)
    for li in range(n):
        if li in local_consumed:
            continue
        nbs = [nb for nb in adj.get(li, []) if nb not in local_consumed]
        if nbs:
            continue  # has neighbour — will be handled by main sweep
        # Isolated: attempt walk.
        walk_isolated_tri(work, li, pts, max_hops=4)
        # Refresh adjacency for this tri after potential flip.
        tri_new = work.tris[li]
        if tri_new is None:
            continue
        a, b, c = int(tri_new[0]), int(tri_new[1]), int(tri_new[2])
        new_nbs = []
        for e in (tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((a, c)))):
            for nb in edge2tris.get(e, []):
                if nb != li and nb not in local_consumed:
                    new_nbs.append(nb)
        if not new_nbs:
            continue
        nb = new_nbs[0]
        # Merge li + nb → quad.
        try:
            va_set = set(int(v) for v in work.tris[li][:3])
            vb_set = set(int(v) for v in work.tris[nb][:3])
            shared = list(va_set & vb_set)
            if len(shared) != 2:
                continue
            unique_a = list(va_set - vb_set)[0]
            unique_b = list(vb_set - va_set)[0]
            s1, s2 = shared
            quad = np.array([unique_a, s1, unique_b, s2], dtype=int)
            work.add_quad(quad)
            local_consumed.add(li)
            local_consumed.add(nb)
            ga = int(layer_global_ids[li])
            gb = int(layer_global_ids[nb])
            newly_consumed.add(ga)
            newly_consumed.add(gb)
        except (IndexError, ValueError):
            continue

    return newly_consumed
