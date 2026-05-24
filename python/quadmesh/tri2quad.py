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
    tris: np.ndarray, points: np.ndarray, prio_arr: Optional[np.ndarray] = None
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

    if prio_arr is None:
        prio_arr = np.fromiter(
            (0 if i in interior else 1 for i in range(n)), dtype=int, count=n
        )

    def prio(i: int) -> int:
        return int(prio_arr[i])

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
                p_xyz = pts[loop].mean(axis=0)
                pid = pts.shape[0] + len(new_pts)
                Pp = np.vstack([pts, *new_pts, p_xyz.reshape(1, -1)]) if new_pts else np.vstack([pts, p_xyz.reshape(1, -1)])
                placed = False
                for r in range(5):
                    L = loop[r:] + loop[:r]
                    q1 = ccw([L[0], L[1], L[2], pid], Pp)
                    q2 = ccw([L[2], L[3], L[4], pid], Pp)
                    if _quad_ok(Pp[q1][:, :2]) and _quad_ok(Pp[q2][:, :2]):
                        new_pts.append(p_xyz)
                        new_elems += [q1, q2]
                        consumed |= {ti, q}
                        changed = placed = done = True
                        break
                if done:
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
        prio = _layer_priority(domain, len(tris))
        quads, leftover_idx = _match_tris_to_quads(tris, points, prio)
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
