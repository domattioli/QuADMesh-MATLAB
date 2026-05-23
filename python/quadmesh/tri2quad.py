"""Tri-to-quad routine.

Pairs adjacent triangles into quadrilaterals. The pairing is computed by a
**global triangle-adjacency matching biased to saturate interior triangles**:
every triangle whose three edges are all interior (a "interior triangle") is
guaranteed to be matched, so it is merged into a quad rather than left behind.
Because an odd triangle count forces at least one unmatched triangle, the bias
steers that residue onto the domain boundary, where a leftover triangle is
acceptable.

This guarantees **zero interior residual triangles** after matching (verified
across the canonical fixtures). Only adjacent tri *pairs* are merged — no new
points are inserted — so the matched output is conforming by construction.

The leftover boundary triangles are then eliminated by ``_remove_boundary_tris``
(a port of the MATLAB QuADMESH+ ``removeTrianglesFun`` on-mesh-boundary path:
edge removal for single-boundary-edge tris, truncation otherwise), making the
final result **quad-pure** by default. Pass ``remove_boundary_tris=False`` to
keep the quad-*dominant* matched output (padded boundary tris).
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from chilmesh import CHILmesh


def _tri_edges(tri) -> List[Tuple[int, int]]:
    a, b, c = int(tri[0]), int(tri[1]), int(tri[2])
    return [tuple(sorted(e)) for e in ((a, b), (b, c), (c, a))]


def _boundary_edge_set(tris: np.ndarray) -> Set[Tuple[int, int]]:
    """Edges incident to exactly one triangle = domain boundary edges."""
    count: Dict[Tuple[int, int], int] = {}
    for tri in tris:
        for e in _tri_edges(tri):
            count[e] = count.get(e, 0) + 1
    return {e for e, c in count.items() if c == 1}


def _segments_cross(a, b, c, d) -> bool:
    """True iff open segments ab and cd properly intersect (strict crossing)."""
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    d1, d2 = cross(c, d, a), cross(c, d, b)
    d3, d4 = cross(a, b, c), cross(a, b, d)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def _quad_ok(p: np.ndarray) -> bool:
    """Quad ``p`` (4, 2) is simple (no bowtie), CCW, and non-degenerate."""
    if _segments_cross(p[0], p[1], p[2], p[3]):
        return False
    if _segments_cross(p[1], p[2], p[3], p[0]):
        return False
    area2 = float(
        np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
    )
    return area2 > 1e-12


def _match_tris_to_quads(
    tris: np.ndarray, points: np.ndarray
) -> Tuple[List[Tuple[int, int, int, int]], List[int]]:
    """Pair adjacent triangles into quads, saturating interior triangles.

    Args:
        tris: ``(N, 3)`` triangle connectivity.
        points: ``(M, >=2)`` coordinates (for CCW orientation of quads).

    Returns:
        ``(quads, leftover_idx)`` — list of CCW 4-tuples and the indices of
        triangles left unmatched (guaranteed to be boundary triangles unless
        the adjacency graph cannot saturate the interior set).
    """
    n = len(tris)
    bset = _boundary_edge_set(tris)

    # Triangle adjacency: two tris adjacent iff they share an edge.
    edge_to_tris: Dict[Tuple[int, int], List[int]] = {}
    for i, tri in enumerate(tris):
        for e in _tri_edges(tri):
            edge_to_tris.setdefault(e, []).append(i)
    adj: List[Set[int]] = [set() for _ in range(n)]
    for lst in edge_to_tris.values():
        if len(lst) == 2:
            a, b = lst
            adj[a].add(b)
            adj[b].add(a)

    interior: Set[int] = {
        i for i, tri in enumerate(tris)
        if not any(e in bset for e in _tri_edges(tri))
    }

    matched: Dict[int, int] = {}
    used: Set[int] = set()

    def prio(i: int) -> int:
        return 0 if i in interior else 1

    def augment(start: int) -> bool:
        """Alternating-path search to match a stranded interior tri by
        rerouting an existing match (frees a boundary residue instead)."""
        prev: Dict[int, Optional[int]] = {start: None}
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for w in adj[u]:
                if w in prev:
                    continue
                if w not in used:  # free vertex → augment along path
                    path = [w, u]
                    x = u
                    while prev[x] is not None:
                        x = prev[x]
                        path.append(x)
                    for k in range(0, len(path) - 1, 2):
                        a, b = path[k], path[k + 1]
                        matched[a] = b
                        matched[b] = a
                        used.add(a)
                        used.add(b)
                    return True
                partner = matched.get(w)
                if partner is not None and partner not in prev:
                    prev[w] = u
                    prev[partner] = w
                    queue.append(partner)
        return False

    # Greedy match, interior triangles first, most-constrained (fewest free
    # neighbors) first, via a lazy heap. Near-linear: each match only updates
    # the matched pair's neighbors, avoiding an O(n^2) full rescan per pick.
    free_deg = [len(adj[i]) for i in range(n)]
    heap: List[Tuple[int, int, int]] = [(prio(i), free_deg[i], i) for i in range(n)]
    heapq.heapify(heap)

    while heap:
        _, d, i = heapq.heappop(heap)
        if i in used:
            continue
        if d != free_deg[i]:  # stale entry → reinsert at current degree
            heapq.heappush(heap, (prio(i), free_deg[i], i))
            continue
        cand = [j for j in adj[i] if j not in used]
        if not cand:
            continue
        j = min(cand, key=lambda y: (prio(y), free_deg[y]))
        matched[i] = j
        matched[j] = i
        used.add(i)
        used.add(j)
        # Matching i,j removes them as free neighbors of their own neighbors.
        for x in (i, j):
            for nb in adj[x]:
                if nb not in used:
                    free_deg[nb] -= 1
                    heapq.heappush(heap, (prio(nb), free_deg[nb], nb))

    # Fixup: any interior triangle still unmatched → reroute via augmenting path.
    for i in list(interior):
        if i not in used:
            augment(i)

    quads: List[Tuple[int, int, int, int]] = []
    seen: Set[Tuple[int, int]] = set()
    P = points[:, :2]
    for i, j in matched.items():
        key = (min(i, j), max(i, j))
        if key in seen:
            continue
        seen.add(key)
        shared = set(int(v) for v in tris[i]) & set(int(v) for v in tris[j])
        if len(shared) != 2:
            continue
        a, b = tuple(shared)
        o1 = next(int(v) for v in tris[i] if int(v) not in shared)
        o2 = next(int(v) for v in tris[j] if int(v) not in shared)
        quad = [o1, a, o2, b]
        p = P[quad]
        area2 = np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
        if area2 < 0:
            quad = [o1, b, o2, a]
        quads.append(tuple(quad))

    leftover = [i for i in range(n) if i not in used]
    return quads, leftover


def _remove_boundary_tris(
    quads: List[Tuple[int, int, int, int]],
    leftover_idx: List[int],
    tris: np.ndarray,
    points: np.ndarray,
    bset: Set[Tuple[int, int]],
    can_remove_edges: bool,
) -> Tuple[List[Tuple[int, int, int, int]], np.ndarray]:
    """Eliminate leftover boundary triangles so the output is quad-pure.

    Port of MATLAB ``removeTrianglesFun`` for the on-mesh-boundary case — the
    only case interior-saturating matching can leave (every leftover tri has
    >=1 domain-boundary edge). Routing per leftover tri:

    * ``n_bdy == 1`` and ``can_remove_edges`` → **edge removal** (squeeze):
      collapse the boundary edge by merging its two verts to their midpoint.
      The tri's two interior edges fuse, so the quads flanking them share an
      edge and the tri vanishes. Conforming by construction.
    * otherwise (``n_bdy >= 2``, or ``n_bdy == 1`` with ``can_remove_edges``
      False) → **drop** the tri (MATLAB ``edgeInsertion`` case-3 truncation).

    A squeeze is skipped (the tri dropped instead) if merging would collapse a
    quad — i.e. some quad already contains both edge endpoints.

    Returns ``(quads, points)`` with zero residual triangles.
    """
    if not leftover_idx:
        return quads, points

    quad_arr = (
        np.asarray(quads, dtype=int).reshape(-1, 4)
        if quads
        else np.empty((0, 4), dtype=int)
    )
    pts = points.copy()

    inc: Dict[int, List[Tuple[int, int]]] = {}
    for r in range(quad_arr.shape[0]):
        for c in range(4):
            inc.setdefault(int(quad_arr[r, c]), []).append((r, c))

    parent: Dict[int, int] = {}

    def find(v: int) -> int:
        while v in parent:
            v = parent[v]
        return v

    for ti in leftover_idx:
        tri = tris[ti]
        bdy = [e for e in _tri_edges(tri) if e in bset]
        if len(bdy) != 1 or not can_remove_edges:
            continue  # drop (n_bdy >= 2, or edges not removable)
        va, vb = (find(bdy[0][0]), find(bdy[0][1]))
        if va == vb:
            continue

        # Moving va to the edge midpoint and rewriting vb->va affects every
        # quad incident to either vert. Reject the squeeze (drop the tri) if it
        # would collapse, flip, or self-intersect (bowtie) any of them.
        new_va = 0.5 * (pts[va] + pts[vb])
        affected = {r for r, _ in inc.get(va, ())} | {r for r, _ in inc.get(vb, ())}
        ok = True
        for r in affected:
            row = [va if int(v) == vb else int(v) for v in quad_arr[r]]
            if len(set(row)) != 4:
                ok = False
                break
            poly = np.array(
                [new_va[:2] if v == va else pts[v][:2] for v in row], dtype=float
            )
            if not _quad_ok(poly):
                ok = False
                break
        if not ok:
            continue  # unsafe squeeze -> drop tri instead

        pts[va] = new_va
        parent[vb] = va
        for (r, c) in inc.get(vb, ()):
            quad_arr[r, c] = va
            inc.setdefault(va, []).append((r, c))
        inc[vb] = []

    return [tuple(int(v) for v in row) for row in quad_arr], pts


def _faithful_layer_sweep(
    domain: CHILmesh, tris: np.ndarray
) -> Tuple[List[Tuple[int, int, int, int]], List[int]]:
    """Per-layer every-other-edge sweep (port of the Tri2QuadRoutine layer loop).

    Runs ``identify_edges_in_layer`` (the every-other-edge primitive) over each
    skeleton layer innermost→outward and merges the flagged tri pairs into quads.

    PARTIAL faithful path (M2 in progress): this is the bare sweep primitive
    *without* the Chapter-4 heuristics (IE-before-OE, T1/T2 tiebreakers) or the
    inter-layer matching, so its pairing rate is lower than the fast matching
    path — more leftover boundary tris remain. Tracked: faithful-port-tasks T016-T019.
    """
    from .identify_edges import identify_edges_in_layer
    from ._topology import merge_tri_pairs

    quads: List[Tuple[int, int, int, int]] = []
    merged: Set[int] = set()
    for layer in range(domain.n_layers):
        sel = identify_edges_in_layer(domain, layer)
        red = sel.removed_edge_ids
        if red.size == 0:
            continue
        e2e = sel.sub_mesh.adjacencies["Edge2Elem"]
        pairs = e2e[red]
        pairs = pairs[(pairs[:, 0] >= 0) & (pairs[:, 1] >= 0)]
        if pairs.size == 0:
            continue
        for row in np.asarray(merge_tri_pairs(sel.sub_mesh, pairs)).reshape(-1, 4):
            quads.append(tuple(int(v) for v in row))
        gids = np.asarray(sel.elem_ids_global, dtype=int)
        for a, b in pairs:
            merged.add(int(gids[a]))
            merged.add(int(gids[b]))
    leftover = [i for i in range(len(tris)) if i not in merged]
    return quads, leftover


def tri2quad_routine(
    domain: CHILmesh,
    can_remove_edges: bool = True,
    parent: Optional[CHILmesh] = None,
    aggressive: bool = False,
    remove_boundary_tris: bool = True,
    method: str = "matching",
) -> CHILmesh:
    """Convert ``domain`` (triangular) into a quad CHILmesh.

    Adjacent triangles are paired into quadrilaterals via interior-saturating
    matching, guaranteeing zero interior residual triangles. The leftover
    boundary triangles are then eliminated (``removeTrianglesFun`` port) so the
    result is **quad-pure**: ``n_bdy == 1`` tris are squeezed out via edge
    removal, ``n_bdy >= 2`` tris are truncated.

    Args:
        domain: Triangular CHILmesh to convert.
        can_remove_edges: Allow boundary-edge collapse (squeeze) for ``n_bdy``
            == 1 leftover tris. If False, those tris are dropped instead.
        parent: Original parent mesh; only used to inherit ``grid_name``.
        aggressive: Reserved; currently unused.
        remove_boundary_tris: Eliminate leftover boundary triangles for a
            quad-pure result (default). Set False to emit them as padded rows
            (quad-dominant — the prior matching-only behaviour).
        method: ``"matching"`` (default) = fast global interior-saturating
            matching. ``"faithful"`` = the thesis per-layer every-other-edge
            sweep (partial — bare primitive, no Ch 4 heuristics yet; see
            faithful-port-plan.md). Default stays ``"matching"`` until the
            faithful path passes parity (spec FR-002a).

    Returns:
        A new CHILmesh of quads (quad-pure by default), or quads plus residual
        boundary triangles (padded) when ``remove_boundary_tris`` is False.
    """
    if parent is None:
        parent = domain

    points = domain.points.copy()
    tris = np.asarray(domain.connectivity_list)[:, :3].astype(int)

    if method == "faithful":
        quads, leftover_idx = _faithful_layer_sweep(domain, tris)
    elif method == "matching":
        quads, leftover_idx = _match_tris_to_quads(tris, points)
    else:
        raise ValueError(f"unknown method {method!r} (use 'matching' or 'faithful')")

    if remove_boundary_tris and leftover_idx:
        bset = _boundary_edge_set(tris)
        quads, points = _remove_boundary_tris(
            quads, leftover_idx, tris, points, bset, can_remove_edges
        )
        leftover_idx = []

    quads_arr = (
        np.asarray(quads, dtype=int).reshape(-1, 4)
        if quads
        else np.empty((0, 4), dtype=int)
    )
    surviving_tris = tris[leftover_idx] if leftover_idx else np.empty((0, 3), dtype=int)

    if quads_arr.size == 0 and surviving_tris.size == 0:
        raise RuntimeError("tri2quad produced empty mesh")

    if quads_arr.size > 0 and surviving_tris.size > 0:
        tris_padded = np.hstack([surviving_tris, surviving_tris[:, [2]]])
        conn_out = np.vstack([quads_arr, tris_padded])
    elif quads_arr.size > 0:
        conn_out = quads_arr
    else:
        conn_out = np.hstack([surviving_tris, surviving_tris[:, [2]]])

    used = np.unique(conn_out.ravel())
    remap = -np.ones(points.shape[0], dtype=int)
    remap[used] = np.arange(used.size)
    conn_out = remap[conn_out]
    pts_out = points[used]

    return CHILmesh(conn_out, pts_out, grid_name=getattr(parent, "grid_name", None))
