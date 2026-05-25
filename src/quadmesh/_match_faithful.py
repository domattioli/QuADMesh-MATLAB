"""Interior-layer heuristics for faithful QuADMESH+ pairing.

Ports Chapter 4.1 of Mattioli (2017): eligible-neighbour counting, IE-before-OE
ordering, T1 (fewest-eligible tiebreaker) and T2 (ladder) selection, and the
intra-before-inter-layer / innermost-outward sweep order.

These functions are called by ``tri2quad._faithful_per_layer`` and replace the
naïve first-come-first-served pass with the thesis-specified heuristics.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import numpy as np


# ── adjacency helpers ─────────────────────────────────────────────────────────

def _build_tri_adjacency(
    conn: np.ndarray,
) -> Dict[int, List[int]]:
    """Return {tri_idx: [neighbour_tri_idxs]} for a (N,3) connectivity array."""
    edge2tris: Dict[Tuple[int, int], List[int]] = {}
    for i, row in enumerate(conn):
        a, b, c = int(row[0]), int(row[1]), int(row[2])
        for e in (tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((a, c)))):
            edge2tris.setdefault(e, []).append(i)  # type: ignore[arg-type]
    adj: Dict[int, List[int]] = {i: [] for i in range(len(conn))}
    for tris in edge2tris.values():
        if len(tris) == 2:
            adj[tris[0]].append(tris[1])
            adj[tris[1]].append(tris[0])
    return adj


def _eligible_neighbours(
    tri_idx: int,
    adj: Dict[int, List[int]],
    consumed: Set[int],
    flagged_pairs: Set[FrozenSet[int]],
) -> List[int]:
    """Live, unflagged neighbours of tri_idx that can still be merged."""
    return [
        nb for nb in adj.get(tri_idx, [])
        if nb not in consumed
        and frozenset([tri_idx, nb]) not in flagged_pairs
    ]


# ── T1 selection: fewest-eligible + tiebreakers (thesis p64) ─────────────────

def _t1_select(
    candidates: List[int],
    adj: Dict[int, List[int]],
    consumed: Set[int],
    flagged_pairs: Set[FrozenSet[int]],
    conn: np.ndarray,
    pts: np.ndarray,
) -> Optional[Tuple[int, int]]:
    """T1: select the pairable tri with the fewest eligible neighbours.

    Among all candidate tri indices, find the one with the minimum eligible-
    neighbour count. Then from its neighbours, select the one that forms the
    best-quality quad. Returns (tri_a, tri_b) or None if no pair found.
    """
    best_a: Optional[int] = None
    best_count = 10**9
    for ti in candidates:
        if ti in consumed:
            continue
        nb = _eligible_neighbours(ti, adj, consumed, flagged_pairs)
        if not nb:
            continue
        if len(nb) < best_count:
            best_count = len(nb)
            best_a = ti

    if best_a is None:
        return None

    # Among best_a's neighbours pick the one yielding highest quad quality.
    nbs = _eligible_neighbours(best_a, adj, consumed, flagged_pairs)
    if not nbs:
        return None

    best_nb: Optional[int] = None
    best_q = -1.0
    for nb in nbs:
        q = _quad_quality_pair(conn, pts, best_a, nb)
        if q > best_q:
            best_q = q
            best_nb = nb

    if best_nb is None:
        return None
    return (best_a, best_nb)


# ── T2 selection: ladder (thesis p65-66) ─────────────────────────────────────

def _t2_ladder(
    start: int,
    adj: Dict[int, List[int]],
    consumed: Set[int],
    flagged_pairs: Set[FrozenSet[int]],
    max_len: int = 20,
) -> List[Tuple[int, int]]:
    """T2: walk a ladder of pairs starting from ``start``.

    Follows a greedy alternating path: pair start↔n1, then n1's first available
    neighbour ↔ n2, etc. Returns a list of (a, b) pairs. Stops when no
    continuation exists or max_len reached.
    """
    pairs: List[Tuple[int, int]] = []
    visited: Set[int] = set()
    current = start
    for _ in range(max_len):
        if current in consumed or current in visited:
            break
        visited.add(current)
        nbs = [
            nb for nb in _eligible_neighbours(current, adj, consumed, flagged_pairs)
            if nb not in visited
        ]
        if not nbs:
            break
        partner = nbs[0]
        pairs.append((current, partner))
        visited.add(partner)
        # Advance: first available neighbour of partner not already seen.
        next_nbs = [
            nb for nb in _eligible_neighbours(partner, adj, consumed, flagged_pairs)
            if nb not in visited
        ]
        if not next_nbs:
            break
        current = next_nbs[0]
    return pairs


# ── IE-before-OE ordering (thesis Ch 4.1) ────────────────────────────────────

def order_ie_before_oe(
    layer_elem_ids: np.ndarray,
    ie_ids: np.ndarray,
    oe_ids: np.ndarray,
) -> np.ndarray:
    """Return elem indices in IE-first, OE-second order within a layer.

    Preserves relative order within each group. Elements outside IE ∪ OE
    are appended last (should not occur in a well-formed layer).
    """
    ie_set = set(int(e) for e in ie_ids)
    oe_set = set(int(e) for e in oe_ids)
    ie_ordered = [int(e) for e in layer_elem_ids if int(e) in ie_set]
    oe_ordered = [int(e) for e in layer_elem_ids if int(e) in oe_set]
    rest = [int(e) for e in layer_elem_ids if int(e) not in ie_set and int(e) not in oe_set]
    return np.array(ie_ordered + oe_ordered + rest, dtype=int)


# ── Main per-layer heuristic sweep ───────────────────────────────────────────

def match_layer_heuristic(
    layer_conn: np.ndarray,
    layer_global_ids: np.ndarray,
    ie_global_ids: np.ndarray,
    oe_global_ids: np.ndarray,
    pts: np.ndarray,
    flagged_pairs: Optional[Set[FrozenSet[int]]] = None,
    already_consumed: Optional[Set[int]] = None,
    use_t2_ladder: bool = True,
) -> Tuple[List[Tuple[int, int]], Set[int]]:
    """Apply T1+T2 heuristics to pair tris within a single layer.

    Args:
        layer_conn: (N, 3) local connectivity for this layer's elements.
        layer_global_ids: (N,) global element IDs corresponding to layer_conn rows.
        ie_global_ids: global IDs of IE elements in this layer.
        oe_global_ids: global IDs of OE elements in this layer.
        pts: full point array (global indexing).
        flagged_pairs: frozenset pairs that must not be merged (fold seams).
        already_consumed: global IDs already merged in prior layers.
        use_t2_ladder: if True, extend T1 selections with the T2 ladder walk.

    Returns:
        (pairs, newly_consumed) where pairs are (local_a, local_b) indices into
        layer_conn, and newly_consumed are the global IDs used.
    """
    if flagged_pairs is None:
        flagged_pairs = set()
    if already_consumed is None:
        already_consumed = set()

    n = len(layer_conn)
    global_to_local = {int(g): i for i, g in enumerate(layer_global_ids)}

    # Map already_consumed → local indices to mark.
    local_consumed: Set[int] = set()
    for gid in already_consumed:
        if gid in global_to_local:
            local_consumed.add(global_to_local[gid])

    # Build adjacency on local indices.
    adj = _build_tri_adjacency(layer_conn)

    # Convert flagged_pairs (global IDs) to local.
    local_flagged: Set[FrozenSet[int]] = set()
    for fp in flagged_pairs:
        lst = list(fp)
        if len(lst) == 2:
            la = global_to_local.get(lst[0], -1)
            lb = global_to_local.get(lst[1], -1)
            if la >= 0 and lb >= 0:
                local_flagged.add(frozenset([la, lb]))

    # IE-before-OE ordering for candidate set.
    ie_local = np.array([global_to_local[g] for g in ie_global_ids if g in global_to_local], dtype=int)
    oe_local = np.array([global_to_local[g] for g in oe_global_ids if g in global_to_local], dtype=int)
    all_local = order_ie_before_oe(
        np.arange(n, dtype=int), ie_local, oe_local
    )

    pairs: List[Tuple[int, int]] = []
    consumed = set(local_consumed)

    # First pass: T1 (fewest-eligible) sweeping IE then OE.
    for ti in all_local:
        if ti in consumed:
            continue
        nb = _eligible_neighbours(ti, adj, consumed, local_flagged)
        if not nb:
            continue
        result = _t1_select([ti], adj, consumed, local_flagged, layer_conn, pts)
        if result is None:
            continue
        a, b = result

        if use_t2_ladder:
            ladder = _t2_ladder(b, adj, consumed | {a}, local_flagged)
            pairs.append((a, b))
            consumed.add(a)
            consumed.add(b)
            for la, lb in ladder:
                if la not in consumed and lb not in consumed:
                    pairs.append((la, lb))
                    consumed.add(la)
                    consumed.add(lb)
        else:
            pairs.append((a, b))
            consumed.add(a)
            consumed.add(b)

    newly_consumed: Set[int] = set()
    for la, lb in pairs:
        newly_consumed.add(int(layer_global_ids[la]))
        newly_consumed.add(int(layer_global_ids[lb]))

    return pairs, newly_consumed


# ── quality helper (internal) ────────────────────────────────────────────────

def _quad_quality_pair(
    conn: np.ndarray, pts: np.ndarray, ia: int, ib: int
) -> float:
    """Shape quality [0,1] of quad formed by merging local tris ia, ib."""
    si = set(int(v) for v in conn[ia, :3])
    sj = set(int(v) for v in conn[ib, :3])
    sh = si & sj
    if len(sh) != 2:
        return 0.0
    a_v, b_v = tuple(sh)
    o1 = next(v for v in si if v not in sh)
    o2 = next(v for v in sj if v not in sh)
    verts = [o1, a_v, o2, b_v]
    if any(v >= len(pts) for v in verts):
        return 0.0
    p = pts[verts, :2]
    worst = 0.0
    for i in range(4):
        aa = p[(i - 1) % 4] - p[i]
        bb = p[(i + 1) % 4] - p[i]
        na, nb = float(np.hypot(*aa)), float(np.hypot(*bb))
        if na < 1e-12 or nb < 1e-12:
            return 0.0
        cos = float(np.clip(np.dot(aa, bb) / (na * nb), -1.0, 1.0))
        worst = max(worst, abs(np.degrees(np.arccos(cos)) - 90.0))
    return max(0.0, 1.0 - worst / 90.0)
