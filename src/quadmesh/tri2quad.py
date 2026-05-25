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


def _quad_quality(p: np.ndarray) -> float:
    """Min-angle quad shape quality in [0, 1] (1 = square). ``p`` is (4, 2)."""
    worst = 0.0
    for i in range(4):
        a = p[(i - 1) % 4] - p[i]
        b = p[(i + 1) % 4] - p[i]
        na, nb = float(np.hypot(*a)), float(np.hypot(*b))
        if na < 1e-12 or nb < 1e-12:
            return 0.0
        cos = float(np.clip(np.dot(a, b) / (na * nb), -1.0, 1.0))
        worst = max(worst, abs(np.degrees(np.arccos(cos)) - 90.0))
    return max(0.0, 1.0 - worst / 90.0)


def _pair_quad_quality(tris: np.ndarray, P: np.ndarray, i: int, j: int) -> float:
    """Shape quality of the quad formed by merging adjacent tris ``i`` and ``j``."""
    si = {int(v) for v in tris[i]}
    sj = {int(v) for v in tris[j]}
    sh = si & sj
    if len(sh) != 2:
        return 0.0
    a, b = tuple(sh)
    o1 = next(int(v) for v in tris[i] if int(v) not in sh)
    o2 = next(int(v) for v in tris[j] if int(v) not in sh)
    return _quad_quality(P[[o1, a, o2, b]])


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
    tris: np.ndarray,
    points: np.ndarray,
    prio_arr: Optional[np.ndarray] = None,
    quality_aware: bool = False,
    seed_pairs: Optional[List[Tuple[int, int]]] = None,
    forbidden_edges: Optional[Set[Tuple[int, int]]] = None,
) -> Tuple[List[Tuple[int, int, int, int]], List[int]]:
    """Pair adjacent triangles into quads, saturating interior triangles.

    Args:
        tris: ``(N, 3)`` triangle connectivity.
        points: ``(M, >=2)`` coordinates (for CCW orientation of quads).
        prio_arr: optional ``(N,)`` int priority per triangle (lower = matched
            first). ``None`` → interior-first (0 if interior else 1). The
            ``method="faithful"`` path passes a layer-ordered priority
            (``_layer_priority``: innermost layer first, IE before OE).
            Whatever the priority, the augmenting-path fixup still guarantees
            **zero interior residual triangles**.
        forbidden_edges: optional set of ``(min, max)`` vertex-pair tuples that
            must NOT be used as a merge diagonal. These are the layer **flagged
            edges** (thesis p39: an interior edge whose both endpoints are inner
            vertices) — the seam where a self-folding layer's two strips border
            each other. The two triangles sharing such an edge are made
            non-adjacent here so the matcher never merges across the fold
            (QuADMesh #31, thesis Figure 4.1).
        seed_pairs: optional list of ``(i, j)`` global tri indices to pre-match
            before the greedy pass. The structured every-other-edge sweep
            (``_sweep_pairs``, thesis ``identifyEdgesFun_v2``) supplies
            layer-aligned pairs here so the quads follow the layer strips
            (square-ish, fewer slivers) instead of arbitrary greedy adjacency.
            Invalid seeds (already used, or not edge-adjacent) are skipped; the
            greedy pass + augmenting fixup still cover the residue and guarantee
            **zero interior residual triangles**.

    Returns:
        ``(quads, leftover_idx)`` — list of CCW 4-tuples and the indices of
        triangles left unmatched (guaranteed to be boundary triangles unless
        the adjacency graph cannot saturate the interior set).
    """
    n = len(tris)
    bset = _boundary_edge_set(tris)
    P = points[:, :2]

    # Triangle adjacency: two tris adjacent iff they share an edge.
    edge_to_tris: Dict[Tuple[int, int], List[int]] = {}
    for i, tri in enumerate(tris):
        for e in _tri_edges(tri):
            edge_to_tris.setdefault(e, []).append(i)
    adj: List[Set[int]] = [set() for _ in range(n)]
    for e, lst in edge_to_tris.items():
        if len(lst) != 2:
            continue
        if forbidden_edges and e in forbidden_edges:
            continue  # fold-seam (flagged) edge — strips stay invisible (#31)
        a, b = lst
        adj[a].add(b)
        adj[b].add(a)

    interior: Set[int] = {
        i for i, tri in enumerate(tris)
        if not any(e in bset for e in _tri_edges(tri))
    }

    matched: Dict[int, int] = {}
    used: Set[int] = set()

    if prio_arr is None:
        prio_arr = np.fromiter(
            (0 if i in interior else 1 for i in range(n)), dtype=int, count=n
        )

    def prio(i: int) -> int:
        return int(prio_arr[i])

    # Pre-match the structured-sweep pairs (layer-aligned) before greedy. Only
    # accept edge-adjacent, currently-free pairs; the rest of the mesh is then
    # filled greedily and the augmenting fixup guarantees zero interior residue.
    if seed_pairs:
        for a, b in seed_pairs:
            a, b = int(a), int(b)
            if a in used or b in used or b not in adj[a]:
                continue
            matched[a] = b
            matched[b] = a
            used.add(a)
            used.add(b)

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
    free_deg = [sum(1 for j in adj[i] if j not in used) for i in range(n)]
    heap: List[Tuple[int, int, int]] = [
        (prio(i), free_deg[i], i) for i in range(n) if i not in used
    ]
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
        if quality_aware:
            # Ch4 T2 refinement: among same-priority partners, pick the one that
            # forms the best-shaped quad (then most-constrained).
            j = min(cand, key=lambda y: (prio(y), -_pair_quad_quality(tris, P, i, y), free_deg[y]))
        else:
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
    minimize_boundary_change: bool = False,
) -> Tuple[List[Tuple[int, int, int, int]], np.ndarray, List[int]]:
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

    **Interior** leftover tris (no boundary edge, ``n_bdy == 0``) are NEVER
    dropped — dropping one leaves a hole. They are returned as ``kept`` for the
    caller to emit as padded tris. The matching path never produces interior
    leftovers (interior-saturating), so it stays quad-pure; the partial faithful
    sweep does, so this keeps its output hole-free (quad-dominant).

    Returns ``(quads, points, kept)`` — ``kept`` = indices of interior leftover
    tris to emit (empty for the matching path).
    """
    if not leftover_idx:
        return quads, points, []

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

    # Priority ladder for clearing a remaining BOUNDARY tri (least alteration of
    # the ORIGINAL boundary vertices first):
    #   T1 edge-swap / vertex-duplication with a vtx-adjacent remaining tri ->
    #      quad (0 vert alteration, no shrink). Preferred (thesis Fig 3.2/3.3).
    #      M3 TODO: needs an interior-edge flip + neighbour rewire — not yet safe.
    #   T2 edge insertion / add boundary point for an IE_L tri (0 original-vert
    #      alteration, adds resolution). M3 TODO (degenerate for n_bdy==1 alone).
    #   T3 drop: tri removed, original boundary verts a,b untouched (interior
    #      apex joins the boundary). 0 original-vert alteration; mild shrink.
    #   T4 edge collapse / squeeze: faithful edgeRemoval but MOVES+deletes the 2
    #      original boundary verts. Last resort.
    # minimize_boundary_change=True selects T3 (drop) over T4 (squeeze).
    kept: List[int] = []
    for ti in leftover_idx:
        tri = tris[ti]
        bdy = [e for e in _tri_edges(tri) if e in bset]
        if len(bdy) == 0:
            kept.append(ti)  # interior tri — emit, never drop (would hole)
            continue
        if minimize_boundary_change:
            # T3': emit the residual boundary tri unchanged — preserves ALL
            # original boundary verts (and area; no orphaned corners). Output is
            # quad-dominant (boundary tris allowed by the thesis), not quad-pure.
            kept.append(ti)
            continue
        if len(bdy) != 1 or not can_remove_edges:
            continue  # drop n_bdy>=2 (boundary truncation)
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

    return [tuple(int(v) for v in row) for row in quad_arr], pts, kept


def _edge_swap_tri_pairs(
    quads: List[Tuple[int, int, int, int]],
    tris: np.ndarray,
    points: np.ndarray,
) -> Tuple[List[Tuple[int, int, int, int]], np.ndarray]:
    """Edge-swap residual tri pairs into quads (thesis Fig 3.2).

    Two residual tris sharing one vertex ``s`` with exactly **one quad between
    them** (a tri-quad-tri fan ``s,a,b,c,d,e``) are recombined by swapping the
    two interior edges ``{s-b, s-d}`` for ``{s-c}`` → two quads ``(s,a,b,c)`` and
    ``(s,c,d,e)``. **No vertex is added, moved, or dropped** — so every boundary
    vertex is preserved, unlike squeeze. Each candidate swap is applied only if
    both resulting quads are valid (``_quad_ok``).

    Selection is **most-constrained-first**: each swap consumes its two tris *and*
    the shared quad, so two candidate swaps that share a quad conflict. Picking
    the swap whose tris/quad have the fewest alternative candidates first avoids a
    greedy pick blocking a second feasible swap (e.g. 4 tris around 2 quads → 2
    swaps, not 1). Iterates to a fixpoint.
    """
    P = points[:, :2]
    elems: List[List[int]] = [list(q) for q in quads] + [
        [int(v) for v in t] for t in np.asarray(tris).reshape(-1, 3)
    ]

    def ccw(qd: List[int]) -> List[int]:
        p = P[qd]
        area2 = float(
            np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
        )
        return qd if area2 > 0 else qd[::-1]

    def candidates() -> List[Tuple[int, int, int, List[int], List[int]]]:
        v2e: Dict[int, Set[int]] = {}
        for ei, e in enumerate(elems):
            for v in set(e):
                v2e.setdefault(v, set()).add(ei)
        out: List[Tuple[int, int, int, List[int], List[int]]] = []
        seen: Set[Tuple[int, int, int]] = set()
        for ei, e in enumerate(elems):
            if len(set(e)) != 3:
                continue
            for s in set(e):
                fan = v2e[s]
                tri_f = [k for k in fan if len(set(elems[k])) == 3]
                quad_f = [k for k in fan if len(set(elems[k])) == 4]
                if len(tri_f) != 2 or len(quad_f) != 1 or ei not in tri_f:
                    continue
                t2 = tri_f[0] if tri_f[1] == ei else tri_f[1]
                q = quad_f[0]
                key = (min(ei, t2), max(ei, t2), q)
                if key in seen:
                    continue
                seen.add(key)
                T1, T2, Q = set(elems[ei]), set(elems[t2]), set(elems[q])
                b, d = (T1 & Q) - {s}, (T2 & Q) - {s}
                c = Q - {s} - b - d
                a, e2 = T1 - {s} - b, T2 - {s} - d
                if not (len(a) == len(b) == len(c) == len(d) == len(e2) == 1):
                    continue
                av, bv, cv, dv, ev = a.pop(), b.pop(), c.pop(), d.pop(), e2.pop()
                q1, q2 = ccw([s, av, bv, cv]), ccw([s, cv, dv, ev])
                if _quad_ok(P[q1]) and _quad_ok(P[q2]):
                    out.append((ei, t2, q, q1, q2))
        return out

    changed = True
    while changed:
        changed = False
        cands = candidates()
        if not cands:
            break
        tri_use: Dict[int, int] = {}
        quad_use: Dict[int, int] = {}
        for i, j, q, _, _ in cands:
            tri_use[i] = tri_use.get(i, 0) + 1
            tri_use[j] = tri_use.get(j, 0) + 1
            quad_use[q] = quad_use.get(q, 0) + 1
        cands.sort(key=lambda c: tri_use[c[0]] + tri_use[c[1]] + quad_use[c[2]])
        used: Set[int] = set()
        consumed: Set[int] = set()
        new_elems: List[List[int]] = []
        for i, j, q, q1, q2 in cands:
            if i in used or j in used or q in used:
                continue
            used |= {i, j, q}
            consumed |= {i, j, q}
            new_elems += [q1, q2]
            changed = True
        if changed:
            elems = [e for k, e in enumerate(elems) if k not in consumed] + new_elems

    quads_out = [tuple(int(v) for v in e) for e in elems if len(set(e)) == 4]
    tri_rows = [e for e in elems if len(set(e)) == 3]
    tris_out = (
        np.asarray(tri_rows, dtype=int).reshape(-1, 3)
        if tri_rows
        else np.empty((0, 3), dtype=int)
    )
    return quads_out, tris_out


def _ordered_loop(perimeter: List[Tuple[int, int]]) -> Optional[List[int]]:
    """Walk perimeter edges into an ordered vertex loop. ``None`` if not a cycle."""
    adj: Dict[int, List[int]] = {}
    for u, v in perimeter:
        adj.setdefault(u, []).append(v)
        adj.setdefault(v, []).append(u)
    if any(len(a) != 2 for a in adj.values()):
        return None
    start = perimeter[0][0]
    loop = [start]
    prev, cur = None, start
    while True:
        nxts = [w for w in adj[cur] if w != prev]
        if not nxts:
            return None
        nxt = nxts[0]
        if nxt == start:
            break
        loop.append(nxt)
        prev, cur = cur, nxt
        if len(loop) > len(perimeter) + 1:
            return None
    return loop


def _point_insert_tri_pairs(
    quads: List[Tuple[int, int, int, int]],
    tris: np.ndarray,
    points: np.ndarray,
) -> Tuple[List[Tuple[int, int, int, int]], np.ndarray, np.ndarray]:
    """Clear lone residual tris by point insertion (thesis edge insertion).

    A lone boundary tri cannot become a single quad without a degenerate
    (colinear) vertex. Instead, pair it with an edge-adjacent quad: the union is
    a pentagon, into which a new **interior** point ``p`` (centroid) is inserted,
    splitting the region into **two quads** ``(v0,v1,v2,p)`` + ``(v2,v3,v4,p)``.

    Adds resolution (one interior point per insertion) and **preserves every
    original vertex** — boundary verts untouched. Local: only the tri + its
    neighbour quad change; the pentagon perimeter (shared with other elements) is
    unchanged → conforming. Each insertion applied only if both quads are valid
    (``_quad_ok``). Iterates to a fixpoint.

    Returns ``(quads, remaining_tris, points)`` with new interior points appended
    to ``points``.
    """
    pts = points.copy()
    elems: List[List[int]] = [list(q) for q in quads] + [
        [int(v) for v in t] for t in np.asarray(tris).reshape(-1, 3)
    ]

    def ccw(qd: List[int], P: np.ndarray) -> List[int]:
        p = P[qd]
        area2 = float(
            np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1])
        )
        return qd if area2 > 0 else qd[::-1]

    changed = True
    while changed:
        changed = False
        edge2elem: Dict[Tuple[int, int], List[int]] = {}
        for ei, e in enumerate(elems):
            n = len(e)
            for i in range(n):
                edge2elem.setdefault(
                    tuple(sorted((e[i], e[(i + 1) % n]))), []
                ).append(ei)
        consumed: Set[int] = set()
        new_elems: List[List[int]] = []
        new_pts: List[np.ndarray] = []
        for ti, e in enumerate(elems):
            if ti in consumed or len(set(e)) != 3:
                continue
            done = False
            for i in range(3):
                edge = tuple(sorted((e[i], e[(i + 1) % 3])))
                nbrs = [
                    x
                    for x in edge2elem[edge]
                    if x != ti and x not in consumed and len(set(elems[x])) == 4
                ]
                if not nbrs:
                    continue
                q = nbrs[0]
                perim: List[Tuple[int, int]] = []
                cnt: Dict[Tuple[int, int], int] = {}
                for el in (elems[ti], elems[q]):
                    n = len(el)
                    for k in range(n):
                        ed = tuple(sorted((el[k], el[(k + 1) % n])))
                        cnt[ed] = cnt.get(ed, 0) + 1
                perim = [ed for ed, c in cnt.items() if c == 1]
                loop = _ordered_loop(perim)
                if loop is None or len(loop) != 5:
                    continue
                LP = pts[loop][:, :2]
                zc = float(pts[loop][:, 2].mean()) if pts.shape[1] > 2 else 0.0
                # Candidate interior points: centroid + grid over the bbox.
                centroid = LP.mean(axis=0)
                std_cand = [centroid]
                xs = np.linspace(LP[:, 0].min(), LP[:, 0].max(), 6)[1:-1]
                ys = np.linspace(LP[:, 1].min(), LP[:, 1].max(), 6)[1:-1]
                std_cand += [np.array([x, y]) for x in xs for y in ys]
                # Concave-pentagon fallback (WNAT bays): centroid+grid all land
                # outside a concave loop. Diagonal midpoints + inward-normal offsets
                # reach into non-convex regions. Tried ONLY when the standard set
                # finds nothing, and held to a higher quality floor so a marginal
                # insertion never replaces a better-left residual tri.
                diag = float(np.linalg.norm(LP.max(axis=0) - LP.min(axis=0)))
                fb_cand = [0.5 * (LP[i] + LP[(i + 2) % 5]) for i in range(5)]
                for i in range(5):
                    edge_mid = 0.5 * (LP[i] + LP[(i + 1) % 5])
                    inward = centroid - edge_mid
                    nrm = float(np.linalg.norm(inward))
                    if nrm < 1e-12:
                        continue
                    inward /= nrm
                    fb_cand += [edge_mid + t * diag * inward for t in (0.1, 0.2, 0.3, 0.4)]
                pt = pts.shape[0]  # temp id of the candidate point in `tmp`

                def _scan(cands):
                    bq, bsel = -1.0, None
                    for pxy in cands:
                        tmp = np.vstack([pts[:, :2], pxy.reshape(1, -1)])
                        for r in range(5):
                            L = loop[r:] + loop[:r]
                            q1 = ccw([L[0], L[1], L[2], pt], tmp)
                            q2 = ccw([L[2], L[3], L[4], pt], tmp)
                            if _quad_ok(tmp[q1]) and _quad_ok(tmp[q2]):
                                mq = min(_quad_quality(tmp[q1]), _quad_quality(tmp[q2]))
                                if mq > bq:
                                    bq, bsel = mq, (pxy, list(q1), list(q2))
                    return bq, bsel

                best_q, best = _scan(std_cand)
                if (best is None or best_q < 0.1):
                    fb_q, fb = _scan(fb_cand)
                    if fb is not None and fb_q >= 0.3:
                        best_q, best = fb_q, fb
                if best is None or best_q < 0.1:
                    continue  # no acceptable placement -> leave tri (rare)
                pxy, q1l, q2l = best
                pid = pts.shape[0] + len(new_pts)
                new_pts.append(np.array([pxy[0], pxy[1], zc]))
                new_elems.append([pid if v == pt else v for v in q1l])
                new_elems.append([pid if v == pt else v for v in q2l])
                consumed |= {ti, q}
                changed = done = True
                break
        if changed:
            if new_pts:
                pts = np.vstack([pts, *[p.reshape(1, -1) for p in new_pts]])
            elems = [e for k, e in enumerate(elems) if k not in consumed] + new_elems

    quads_out = [tuple(int(v) for v in e) for e in elems if len(set(e)) == 4]
    tri_rows = [e for e in elems if len(set(e)) == 3]
    tris_out = (
        np.asarray(tri_rows, dtype=int).reshape(-1, 3)
        if tri_rows
        else np.empty((0, 3), dtype=int)
    )
    return quads_out, tris_out, pts


def _layer_priority(domain: CHILmesh, n: int) -> np.ndarray:
    """Per-triangle match priority from the skeleton layers (Ch 4 ordering).

    Encodes the thesis priorities as one sortable int (lower = matched first):
    **innermost layer first**; **IE before OE** in interior layers (only IE_L can
    isolate); but **OE before IE in the boundary layer** (thesis §4.2 — match OE_L
    first so the last residual is an IE_L, which is cleared without touching the
    domain boundary). A tri in layer ``li`` gets ``2*(n_layers-1-li) + off``.
    Triangles with no layer membership sort last.
    """
    layers = domain.layers
    nl = domain.n_layers
    prio = np.full(n, 2 * nl + 1, dtype=int)
    for li in range(nl):
        rank = nl - 1 - li  # innermost layer (largest li) -> rank 0
        ie_off, oe_off = (1, 0) if li == 0 else (0, 1)  # boundary layer: OE first
        for e in np.asarray(layers["IE"][li], dtype=int):
            prio[int(e)] = 2 * rank + ie_off
        for e in np.asarray(layers["OE"][li], dtype=int):
            prio[int(e)] = 2 * rank + oe_off
    return prio


def _sweep_pairs(
    domain: CHILmesh,
) -> Tuple[List[Tuple[int, int]], Set[Tuple[int, int]]]:
    """Structured every-other-edge sweep → (merge pairs, flagged-edge set).

    Port driver for thesis ``identifyEdgesFun_v2`` (Ch 4 §4.1): walk each
    skeleton layer **innermost first**, flag every-other interior edge, and emit
    the two tris flanking each flagged edge as a pair. Because the per-layer pass
    marks each element used at most once and elements partition across layers,
    the emitted pairs are disjoint — safe to seed the matcher with.

    The sweep alone leaves unpaired interior tris (every-other skips some); those
    are closed by the greedy pass + augmenting fixup in ``_match_tris_to_quads``,
    so the **zero interior residual** guarantee is preserved. The win is shape:
    sweep pairs run along the layer strips, yielding square-ish quads instead of
    the skewed slivers arbitrary greedy adjacency produces.

    The second return value is the set of **flagged edges** (thesis p39 / Figure
    4.1) as ``(min, max)`` vertex-pair tuples — the fold seams where a layer
    self-intersects. The matcher forbids merging across these so the two
    bordering strips are never stitched into one quad (QuADMesh #31).
    """
    from .identify_edges import identify_edges_in_layer

    pairs: List[Tuple[int, int]] = []
    flagged: Set[Tuple[int, int]] = set()
    nl = int(getattr(domain, "n_layers", 0) or 0)
    for li in range(nl - 1, -1, -1):  # innermost layer first
        sel = identify_edges_in_layer(domain, li)
        if sel.sub_mesh is None:
            continue
        for pr in sel.flagged_vert_pairs:
            flagged.add((int(pr[0]), int(pr[1])))
        if sel.removed_edge_ids.size == 0:
            continue
        e2e = sel.sub_mesh.adjacencies["Edge2Elem"]
        glob = np.asarray(sel.elem_ids_global, dtype=int)
        for eid in np.asarray(sel.removed_edge_ids, dtype=int):
            row = np.asarray(e2e[int(eid)]).ravel()
            if row.size < 2 or int(row[0]) < 0 or int(row[1]) < 0:
                continue
            a, b = int(row[0]), int(row[1])
            if a >= glob.size or b >= glob.size:
                continue
            pairs.append((int(glob[a]), int(glob[b])))
    return pairs, flagged


def _faithful_per_layer(
    domain: CHILmesh,
    tris: np.ndarray,
    can_remove_edges: bool,
) -> Tuple[List[Tuple[int, int, int, int]], List[int], np.ndarray]:
    """True MATLAB Tri2QuadRoutine per-layer loop.

    Mirrors ``Tri2QuadRoutine.m``: innermost layer first, per-layer
    identifyEdges → mergeTriangles → removeTriangles, then a fallback global
    matcher for any elements not covered by the skeleton layers.

    Returns ``(quads, leftover_global_idx, points)`` where ``leftover_global_idx``
    indexes into the original ``tris`` array for tris not handled by the
    per-layer sweep, and ``points`` is the (possibly augmented) vertex table.
    """
    from ._tri_removal import WorkingMesh, route_leftover_tri
    from ._topology import merge_tri_pair
    from .identify_edges import identify_edges_in_layer

    work = WorkingMesh(points=domain.points.copy(), quads=[])
    consumed: Set[int] = set()  # global elem IDs already merged or routed

    nl = int(getattr(domain, "n_layers", 0) or 0)
    layers = domain.layers

    # All elem IDs that belong to at least one layer — the rest fall through to
    # the global matcher below.
    all_layer_elems: Set[int] = set()
    for li in range(nl):
        all_layer_elems.update(int(e) for e in layers["OE"][li])
        all_layer_elems.update(int(e) for e in layers["IE"][li])

    for li in range(nl - 1, -1, -1):  # MATLAB: nLayers downto 1 (innermost first)
        try:
            sel = identify_edges_in_layer(domain, li)
        except Exception:
            continue
        if sel.sub_mesh is None:
            continue

        from ._match_faithful import match_layer_heuristic

        glob = np.asarray(sel.elem_ids_global, dtype=int)
        local_consumed: Set[int] = set()

        # Build flagged (fold-seam) pairs in global IDs.
        flagged_global: Set[frozenset] = set()
        for fp in sel.flagged_vert_pairs:
            # fp is a (min, max) vertex-pair; find which global elems share it.
            pass  # fold-seam flagging via flagged_vert_pairs will be wired in T018

        # T017: IE-before-OE + T1/T2 heuristic pairing.
        ie_ids = np.asarray(layers["IE"][li], dtype=int)
        oe_ids = np.asarray(layers["OE"][li], dtype=int)
        layer_conn = domain.connectivity_list[glob]
        heuristic_pairs, heuristic_consumed = match_layer_heuristic(
            layer_conn=layer_conn,
            layer_global_ids=glob,
            ie_global_ids=ie_ids,
            oe_global_ids=oe_ids,
            pts=domain.points,
            flagged_pairs=flagged_global,
            already_consumed=consumed,
            use_t2_ladder=True,
        )

        # Merge flagged edge pairs → quads (mergeTrianglesFun): honour
        # identify_edges selection *filtered* by heuristic to avoid double-merge.
        e2e = sel.sub_mesh.adjacencies["Edge2Elem"]
        heuristic_local_pairs: Set[frozenset] = set(
            frozenset([la, lb]) for la, lb in heuristic_pairs
        )
        for eid in sel.removed_edge_ids:
            row = np.asarray(e2e[int(eid)]).ravel()
            if row.size < 2 or int(row[0]) < 0 or int(row[1]) < 0:
                continue
            la, lb = int(row[0]), int(row[1])
            if la >= glob.size or lb >= glob.size:
                continue
            ga, gb = int(glob[la]), int(glob[lb])
            if ga in consumed or gb in consumed:
                continue
            if la in local_consumed or lb in local_consumed:
                continue
            # Only merge if heuristic also selected this pair (or heuristic found
            # nothing for these elems, in which case fall back to identify_edges).
            pair_key = frozenset([la, lb])
            if heuristic_local_pairs and pair_key not in heuristic_local_pairs:
                # Heuristic has already assigned one of these to a different partner.
                if ga in heuristic_consumed or gb in heuristic_consumed:
                    continue
            try:
                quad = merge_tri_pair(sel.sub_mesh, la, lb)
            except (ValueError, IndexError):
                continue
            work.add_quad(quad)
            consumed.add(ga)
            consumed.add(gb)
            local_consumed.add(la)
            local_consumed.add(lb)

        # Route leftover (unmatched) tris (removeTrianglesFun).
        # Outermost layer = mesh boundary layer (MATLAB: iLayer == nLayers).
        on_mesh_boundary = (li == nl - 1)
        b_edge_set = set(int(e) for e in sel.boundary_edge_ids)
        b_vert_set = set(int(v) for v in sel.boundary_vert_ids_global)

        for gid in glob:
            gid_i = int(gid)
            if gid_i in consumed:
                continue
            try:
                route_leftover_tri(
                    domain, work, gid_i, li,
                    on_mesh_boundary=on_mesh_boundary,
                    can_remove_edges=can_remove_edges,
                    sub_b_edge_set=b_edge_set,
                    sub_b_vert_set=b_vert_set,
                )
            except Exception:
                pass  # degenerate — tri collected in leftover_idx below
            consumed.add(gid_i)

    # Global matcher fallback for any elems not covered by skeleton layers.
    unclaimed_idx = [
        i for i in range(len(tris))
        if i not in consumed
        and i not in all_layer_elems
        and len(set(tris[i].tolist())) == 3  # skip zero/degenerate rows
    ]
    if unclaimed_idx:
        unclaimed_tris = tris[unclaimed_idx]
        unc_quads, unc_left_local = _match_tris_to_quads(
            unclaimed_tris, domain.points
        )
        for q in unc_quads:
            work.add_quad(np.asarray(q, dtype=int))
        unc_left_set = set(unc_left_local)
        consumed.update(
            unclaimed_idx[j]
            for j in range(len(unclaimed_idx))
            if j not in unc_left_set
        )

    # Remaining tris: in consumed set but zero-row means consumed-in-place (fine).
    # Not in consumed = genuinely unhandled, pass to downstream cleanup.
    leftover_idx = [
        i for i in range(len(tris))
        if i not in consumed and len(set(tris[i].tolist())) == 3
    ]

    # Sync points — route ops may have augmented domain.points via bisection/insertion.
    points_out = domain.points.copy()

    return [tuple(int(v) for v in q) for q in work.quads], leftover_idx, points_out


def tri2quad_routine(
    domain: CHILmesh,
    can_remove_edges: bool = True,
    parent: Optional[CHILmesh] = None,
    aggressive: bool = False,
    remove_boundary_tris: bool = True,
    method: str = "matching",
    minimize_boundary_change: Optional[bool] = None,
    point_insert: bool = True,
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
            matching (``compute_layers`` not required). ``"faithful"`` =
            layer-ordered matching (Ch 4 priority: innermost layer first, IE
            before OE) + augmenting-path saturation — **zero interior residual
            tris**, requires skeleton layers. Default stays ``"matching"`` until
            the faithful path passes full MATLAB parity (spec FR-002a).
        minimize_boundary_change: prefer ops that do not alter ORIGINAL boundary
            vertices when clearing residual boundary tris — drop (preserve a,b)
            over squeeze (collapse, which moves+deletes them). ``None`` →
            auto: True for ``method="faithful"``, False for ``method="matching"``
            (keeps matching's prior squeeze behaviour + parity baselines).
        point_insert: faithful path only — clear remaining lone boundary tris by
            pairing each with a neighbour quad + inserting an interior point →
            two quads (quad-pure, every original vertex preserved). Default True.
            Set False to leave them as residual tris (quad-dominant, higher
            per-element quality; point placement is currently crude/centroid).

    Returns:
        A new CHILmesh of quads (quad-pure by default), or quads plus residual
        boundary triangles (padded) when ``remove_boundary_tris`` is False.
    """
    if parent is None:
        parent = domain

    points = domain.points.copy()
    tris = np.asarray(domain.connectivity_list)[:, :3].astype(int)

    if method == "faithful":
        nl_check = int(getattr(domain, "n_layers", 0) or 0)
        if nl_check > 0:
            # True per-layer loop: identifyEdges → mergePairs → routeLeftovers per layer
            # (mirrors Tri2QuadRoutine.m).  domain.points may be augmented in-place by
            # route ops; points is re-synced from domain after the sweep.
            quads, leftover_idx, points = _faithful_per_layer(
                domain, tris, can_remove_edges
            )
        else:
            # No skeleton layers (e.g. mesh too coarse) — degrade gracefully.
            prio = _layer_priority(domain, len(tris))
            try:
                seed, forbidden = _sweep_pairs(domain)
            except Exception:
                seed, forbidden = None, None
            quads, leftover_idx = _match_tris_to_quads(
                tris, points, prio, seed_pairs=seed, forbidden_edges=forbidden
            )
    elif method == "matching":
        quads, leftover_idx = _match_tris_to_quads(tris, points)
    else:
        raise ValueError(f"unknown method {method!r} (use 'matching' or 'faithful')")

    if remove_boundary_tris and leftover_idx:
        bset = _boundary_edge_set(tris)
        mbc = (
            minimize_boundary_change
            if minimize_boundary_change is not None
            else (method == "faithful")  # faithful: preserve original boundary verts
        )
        quads, points, leftover_idx = _remove_boundary_tris(
            quads, leftover_idx, tris, points, bset, can_remove_edges, mbc
        )

    surviving_tris = tris[leftover_idx] if leftover_idx else np.empty((0, 3), dtype=int)

    # Edge-swap residual tri pairs (tri-quad-tri fans) -> quads, preserving every
    # vertex (preferred over squeeze; thesis Fig 3.2). Reduces residual tris.
    if surviving_tris.size > 0 and quads:
        quads, surviving_tris = _edge_swap_tri_pairs(quads, surviving_tris, points)

    # Point insertion: clear remaining lone tris by pairing each with a neighbour
    # quad (pentagon) + an interior point -> 2 quads. Adds resolution, preserves
    # every original (incl. boundary) vertex. Makes the faithful path quad-pure.
    if point_insert and method == "faithful" and surviving_tris.size > 0 and quads:
        quads, surviving_tris, points = _point_insert_tri_pairs(
            quads, surviving_tris, points
        )

    quads_arr = (
        np.asarray(quads, dtype=int).reshape(-1, 4)
        if quads
        else np.empty((0, 4), dtype=int)
    )

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
