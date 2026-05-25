"""Identify interior edges to remove in a layer, merging tri pairs to quads.

Port of MATLAB ``identifyEdgesFun_v2``. Walks each layer's outer-vertex path
and flags interior edges for removal so the two tris sharing each flagged edge
can be merged into a quad. At each path vertex, all interior edges between the
up- and down-path boundary edges are taken; elem/edge flagging prevents any
triangle from being merged twice.

Outputs go to the caller (typically the tri2quad sweep), which then performs
the merges and routes remaining tris through edge-insertion/bisection/removal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from chilmesh import CHILmesh
from chilmesh.layer_paths import paths_on_outer_vertices

from ._topology import ccw_edges_around_vert


@dataclass
class LayerEdgeSelection:
    """Output of one layer's identify_edges pass.

    Fields are wrt the *subdomain* (a CHILmesh of just this layer's OE+IE
    elements) unless noted.
    """

    sub_mesh: CHILmesh
    elem_ids_global: np.ndarray  # Layer's elem IDs in the parent Domain.
    boundary_edge_ids: np.ndarray  # Boundary edges of subdomain (outer ring only).
    boundary_vert_ids_global: np.ndarray  # Boundary verts (parent indexing).
    removed_edge_ids: np.ndarray  # Subdomain edges flagged for removal.
    paths: List[np.ndarray] = field(default_factory=list)  # Outer-vert paths.
    # Flagged edges (thesis §3.2.2, p39): interior sub-mesh edges whose BOTH
    # endpoints are inner vertices (IV) of this layer. When a layer folds onto
    # itself, the seam between its two bordering strips is exactly such an edge;
    # the two triangles across it must stay "invisible" to each other so the
    # matcher never merges across the fold (QuADMesh #31, thesis Figure 4.1).
    flagged_edge_ids: np.ndarray = field(
        default_factory=lambda: np.empty(0, dtype=int)
    )  # Sub-mesh edge IDs of flagged (two-IV) interior edges.
    flagged_vert_pairs: List[tuple] = field(default_factory=list)  # (min,max) parent verts.


def identify_edges_in_layer(domain: CHILmesh, layer_idx: int) -> LayerEdgeSelection:
    """Select edges for removal in layer ``layer_idx``.

    Algorithm:
        1. Build sub-mesh from layer's OE ∪ IE elems.
        2. Get outer-vertex paths from chilmesh.
        3. Filter boundary edges of sub-mesh to outer ring (both endpoints in OV).
        4. Rotate each path to start at a "corner" (vert with only one elem).
        5. Walk each path; at each vert, sort incident edges from up-path to
           down-path and flag all interior edges for removal — skipping
           already-flagged edges or elems whose neighbour was already merged.
    """
    layers = domain.layers
    oe = np.asarray(layers["OE"][layer_idx], dtype=int)
    ie = np.asarray(layers["IE"][layer_idx], dtype=int)
    elem_ids = np.concatenate([oe, ie])

    if elem_ids.size == 0:
        return LayerEdgeSelection(
            sub_mesh=None,  # type: ignore[arg-type]
            elem_ids_global=elem_ids,
            boundary_edge_ids=np.empty(0, dtype=int),
            boundary_vert_ids_global=np.empty(0, dtype=int),
            removed_edge_ids=np.empty(0, dtype=int),
        )

    # Sub-mesh defined over layer's elements (uses parent's points list).
    # Skip skeletonization (irrelevant for sub-region) but build adjacencies
    # via the public CHILmesh ctor flag (CHILmesh #134 / QuADMesh #15).
    sub_conn = domain.connectivity_list[elem_ids]
    sub_mesh = CHILmesh(
        sub_conn,
        domain.points.copy(),
        compute_layers=False,
        compute_adjacencies=True,
    )

    ov_global = np.asarray(layers["OV"][layer_idx], dtype=int)
    iv_global = np.asarray(layers["IV"][layer_idx], dtype=int)

    # Flagged edges (thesis p39): an interior sub-mesh edge whose BOTH endpoints
    # are inner vertices of this layer. In a layer that does not fold, the inner
    # ring (IV-IV) edges are sub-mesh BOUNDARY edges; an IV-IV edge shared by two
    # layer triangles only arises where the layer self-intersects, so it is the
    # seam between the two bordering strips. Forbidding merges across it keeps the
    # two strips "invisible" to each other (QuADMesh #31, thesis Figure 4.1).
    iv_set = set(int(v) for v in iv_global)
    edge2elem_all = sub_mesh.adjacencies["Edge2Elem"]
    all_e2v = sub_mesh.edge2vert(np.arange(sub_mesh.n_edges))
    flagged_mask = np.zeros(sub_mesh.n_edges, dtype=bool)
    flagged_pairs: List[tuple] = []
    for eid in range(sub_mesh.n_edges):
        u, v = int(all_e2v[eid, 0]), int(all_e2v[eid, 1])
        if u not in iv_set or v not in iv_set:
            continue
        pair = edge2elem_all[eid]
        if int(pair[0]) < 0 or int(pair[1]) < 0:
            continue  # boundary IV-IV edge (inner ring) — not a fold seam
        flagged_mask[eid] = True
        flagged_pairs.append((min(u, v), max(u, v)))
    flagged_edge_ids = np.where(flagged_mask)[0].astype(int)

    # Outer-vertex paths in parent indexing (chilmesh helper already uses parent IDs).
    paths = paths_on_outer_vertices(domain, layer_idx)

    # Rotate each path so it starts at a vertex with only one layer-element attached
    # (an outer corner), matching the MATLAB heuristic.
    # Pre-build the layer elem-set once: per-vertex set() recreation is O(|OV|*|layer|).
    elem_id_set = set(int(e) for e in elem_ids)
    rotated_paths: List[np.ndarray] = []
    for path in paths:
        verts = np.asarray(path, dtype=int)
        if verts.size <= 1:
            rotated_paths.append(verts)
            continue
        # Drop closing duplicate if present.
        if verts[0] == verts[-1]:
            verts = verts[:-1]
        # Count layer-elems incident to each vert.
        counts = np.array(
            [sum(1 for e in domain.get_vertex_elements(int(v)) if int(e) in elem_id_set)
             for v in verts],
            dtype=int,
        )
        corner = np.where(counts == 1)[0]
        if corner.size > 0:
            i = int(corner[0])
            verts = np.concatenate([verts[i + 1:], verts[:i + 1]])
        rotated_paths.append(verts)

    # Sub-mesh boundary edges & verts (parent indexing of verts).
    b_edges = sub_mesh.boundary_edges()
    b_e2v = sub_mesh.edge2vert(b_edges)

    ov_set = set(int(v) for v in ov_global)
    keep_mask = np.array(
        [(int(u) in ov_set) and (int(v) in ov_set) for u, v in b_e2v],
        dtype=bool,
    )
    b_edges = b_edges[keep_mask]
    b_e2v = b_e2v[keep_mask]

    # Adjacency tables wrt sub-mesh.
    edge2elem = sub_mesh.adjacencies["Edge2Elem"]
    n_sub_edges = sub_mesh.n_edges

    # Flag state: edge "used" if removed; elem "used" if its pair already merged.
    edge_used = np.zeros(n_sub_edges, dtype=bool)
    elem_used = np.zeros(sub_mesh.n_elems, dtype=bool)
    removed: List[int] = []

    b_edge_set = set(int(e) for e in b_edges)

    for path in rotated_paths:
        if path.size < 2:
            continue
        # Wrap with src/dst guards (MATLAB style).
        path_wrap = np.concatenate([[path[-1]], path, [path[0]]])

        # Seed up-edge: the boundary edge linking path_wrap[0] and path_wrap[1].
        up_edge = _find_boundary_edge(b_edges, b_e2v, int(path_wrap[0]), int(path_wrap[1]))

        for k in range(1, len(path_wrap) - 1):
            cur_v = int(path_wrap[k])
            nxt_v = int(path_wrap[k + 1])

            ccw = ccw_edges_around_vert(sub_mesh, [cur_v])[0]
            if ccw.size == 0:
                continue

            # Down-edge: boundary edge from cur_v toward nxt_v.
            down_edge = _find_boundary_edge(b_edges, b_e2v, cur_v, nxt_v)

            if up_edge < 0 or down_edge < 0:
                up_edge = down_edge
                continue

            # Sort CCW so up_edge is first; if down_edge ends up at index 1 (only
            # one interior edge), no removal possible — skip.
            if up_edge not in ccw or down_edge not in ccw:
                up_edge = down_edge
                continue
            iu = int(np.where(ccw == up_edge)[0][0])
            ordered = np.concatenate([ccw[iu:], ccw[:iu]])
            idown = int(np.where(ordered == down_edge)[0][0])
            if idown <= 1:
                up_edge = down_edge
                continue
            # MATLAB idownEdgeID==2 reversal (identifyEdgesFun_v2.m:86-88): when a
            # single interior edge sits between up and down, flip positions [1:] so
            # it lands at the first take position consistently.
            if idown == 2:
                ordered = np.concatenate([ordered[:1], ordered[1:][::-1]])
                idown = int(np.where(ordered == down_edge)[0][0])
            # Interior edges between up and down (exclusive). Take ALL of them
            # (identifyEdgesFun_v2.m:108-121, `for iEdge=2:totalNumEdges-1`); the
            # elem/edge flagging below prevents double-merge, so no every-other skip.
            interior = ordered[1:idown]
            for eid in interior:
                eid_i = int(eid)
                if edge_used[eid_i] or eid_i in b_edge_set:
                    continue
                if flagged_mask[eid_i]:
                    continue  # never merge across a fold seam (QuADMesh #31)
                pair = edge2elem[eid_i]
                if pair[0] < 0 or pair[1] < 0:
                    continue
                if elem_used[int(pair[0])] or elem_used[int(pair[1])]:
                    continue
                edge_used[eid_i] = True
                elem_used[int(pair[0])] = True
                elem_used[int(pair[1])] = True
                removed.append(eid_i)

            up_edge = down_edge

    return LayerEdgeSelection(
        sub_mesh=sub_mesh,
        elem_ids_global=elem_ids,
        boundary_edge_ids=b_edges,
        boundary_vert_ids_global=np.unique(b_e2v.ravel()),
        removed_edge_ids=np.asarray(removed, dtype=int),
        paths=rotated_paths,
        flagged_edge_ids=flagged_edge_ids,
        flagged_vert_pairs=flagged_pairs,
    )


def _find_boundary_edge(
    b_edges: np.ndarray, b_e2v: np.ndarray, u: int, v: int
) -> int:
    """Return boundary edge ID joining verts ``u`` and ``v``. ``-1`` if none."""
    if b_edges.size == 0:
        return -1
    hits = np.where(
        ((b_e2v[:, 0] == u) & (b_e2v[:, 1] == v))
        | ((b_e2v[:, 0] == v) & (b_e2v[:, 1] == u))
    )[0]
    if hits.size:
        return int(b_edges[hits[0]])
    # Fall-back: edge with one endpoint matching (handles pinch verts).
    one = np.where((b_e2v[:, 0] == u) | (b_e2v[:, 1] == u))[0]
    return int(b_edges[one[0]]) if one.size else -1
