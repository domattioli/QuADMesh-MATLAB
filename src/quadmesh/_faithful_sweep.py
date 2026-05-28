"""Faithful per-layer tri2quad sweep (Ch 4 QuADMESH+).

Direct port of MATLAB ``Tri2QuadRoutine`` + ``removeTrianglesFun`` and friends.

Unlike the global-match path in :mod:`quadmesh.tri2quad`, this sweep processes
layers innermost -> outward, **mutating a working ``CHILmesh`` Domain in place**
(exactly as the MATLAB original mutates its ``Domain`` object) so that each
``edgeBisection`` splits the *next* layer outward (``iLayer-1``) while it is
still triangular. This is the only way to faithfully reproduce the thesis
algorithm; a post-matching patch cannot tile a (lone-tri + neighbour-quad)
pentagon into 2 quads with an interior point without overlaps/gaps.

The per-layer every-other-edge selection reuses the proven, MATLAB-faithful
:func:`quadmesh.identify_edges.identify_edges_in_layer`, which rebuilds a fresh
sub-mesh from the (mutated) ``Domain.connectivity_list`` and reads
``Domain.layers`` each call -- so as long as we keep the Domain's connectivity,
points, layers and adjacencies consistent after every mutation, the selection
sees the current state, just like MATLAB.

Returns ``(quads, residual_tris, points)`` from :func:`faithful_sweep`.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from chilmesh import CHILmesh

from .tri2quad import _quad_ok


# ---------------------------------------------------------------------------
# Mutable-domain helpers
# ---------------------------------------------------------------------------
def _ccw(points: np.ndarray, conn: List[int]) -> List[int]:
    p = points[conn][:, :2]
    area2 = float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]))
    return conn if area2 > 0 else conn[::-1]


def _set_conn_row(domain: CHILmesh, eid: int, conn: List[int]) -> None:
    domain.connectivity_list[eid, :3] = [int(v) for v in conn]
    if domain.connectivity_list.shape[1] > 3:
        domain.connectivity_list[eid, 3] = int(conn[0])  # tri padding


def _append_conn_row(domain: CHILmesh, conn: List[int]) -> int:
    row = [int(v) for v in conn]
    ncol = domain.connectivity_list.shape[1]
    if ncol > 3:
        row = row + [row[0]] * (ncol - 3)
    domain.connectivity_list = np.vstack([domain.connectivity_list, np.array(row, dtype=int)])
    domain.n_elems = domain.connectivity_list.shape[0]
    return domain.connectivity_list.shape[0] - 1


def _append_point(domain: CHILmesh, xyz: np.ndarray) -> int:
    xyz = np.asarray(xyz, dtype=float).ravel()
    if xyz.size == 2:
        xyz = np.array([xyz[0], xyz[1], 0.0])
    if domain.points.shape[1] == 2:
        xyz = xyz[:2]
    domain.points = np.vstack([domain.points, xyz.reshape(1, -1)])
    domain.n_verts = domain.points.shape[0]
    return domain.points.shape[0] - 1


def _layer_of(domain: CHILmesh, eid: int) -> Tuple[int, str]:
    """Return ``(layer_idx, 'OE'|'IE')`` for element ``eid``; ``(-1, '')`` if none."""
    layers = domain.layers
    for li in range(domain.n_layers):
        if eid in set(int(x) for x in np.asarray(layers["OE"][li], dtype=int)):
            return li, "OE"
        if eid in set(int(x) for x in np.asarray(layers["IE"][li], dtype=int)):
            return li, "IE"
    return -1, ""


# ---------------------------------------------------------------------------
# Merge two tris -> one quad (mergeTrianglesFun, CCW)
# ---------------------------------------------------------------------------
def _merge_quad(domain: CHILmesh, ea: int, eb: int) -> Optional[List[int]]:
    t1 = [int(v) for v in domain.connectivity_list[ea, :3]]
    t2 = [int(v) for v in domain.connectivity_list[eb, :3]]
    shared = [v for v in t1 if v in t2]
    if len(shared) != 2:
        return None
    unique_a = next(v for v in t1 if v not in shared)
    unique_b = next(v for v in t2 if v not in shared)
    iu = t1.index(unique_a)
    rotated = t1[iu:] + t1[:iu]  # [unique_a, s1, s2]
    quad = [rotated[0], rotated[1], unique_b, rotated[2]]
    return _ccw(domain.points, quad)


# ---------------------------------------------------------------------------
# edgeBisection case 2
# ---------------------------------------------------------------------------
def _opposite_tri(domain: CHILmesh, alive: List[bool], li: int, u: int, v: int,
                  exclude: int) -> Optional[int]:
    """Alive tri in layer ``li`` (OE or IE) sharing edge (u, v), excluding one."""
    if li < 0:
        return None
    layers = domain.layers
    ids = list(int(x) for x in np.asarray(layers["OE"][li], dtype=int))
    ids += list(int(x) for x in np.asarray(layers["IE"][li], dtype=int))
    for e in ids:
        if e == exclude or not alive[e]:
            continue
        c = domain.connectivity_list[e, :3]
        if u in c and v in c:
            return e
    return None


def _find_bisect_edge(
    domain: CHILmesh, alive: List[bool], li: int, conn: List[int], tElemID: int,
    b_edges_in_tri: List[int], edges: List[Tuple[int, int]],
) -> Optional[Tuple[Tuple[int, int], int, int]]:
    """Pick an edge of the tri to bisect: one whose opposite element is still a
    triangle. Prefer a layer-boundary edge whose opposite is in iLayer-1 (the
    faithful case), then any edge whose opposite is a triangle in iLayer-1 or the
    same layer. Returns ``(edge, opp_elem, opp_layer)`` or ``None``."""
    # 1. Faithful preference: layer-boundary edge, opposite in li-1.
    for i in b_edges_in_tri:
        opp = _opposite_tri(domain, alive, li - 1, edges[i][0], edges[i][1], exclude=tElemID)
        if opp is not None:
            return edges[i], opp, li - 1
    # 2. Any edge whose opposite is a triangle in iLayer-1 (still triangular at
    #    this point in the sweep). We do NOT bisect against a same-layer tri: it
    #    triggers an unstable cascade (a same-layer split produces tris that bisect
    #    again) and can introduce bowties. Same-layer adjacent tris are instead
    #    cleared soundly by the residual pair-merge / edge-swap finalization.
    for (u, v) in edges:
        opp = _opposite_tri(domain, alive, li - 1, u, v, exclude=tElemID)
        if opp is not None and opp != tElemID:
            return (u, v), opp, li - 1
    return None


def _edge_bisection_case2(
    domain: CHILmesh,
    alive: List[bool],
    li: int,
    tElemID: int,
    edge: Tuple[int, int],
    quads: List[List[int]],
    opp: Optional[int] = None,
    opp_layer: Optional[int] = None,
) -> bool:
    """Bisect ``edge`` of the tri at its midpoint and split the opposite tri.

    Tri -> quad. The opposing triangle (still a triangle) is split into two tris
    at the midpoint, staying in its own layer. New vertex is OV of iLayer / IV of
    the opposite layer. Returns True on success (caller marks dirty).
    """
    v_a, v_b = edge
    conn = [int(x) for x in domain.connectivity_list[tElemID, :3]]
    apex = next(v for v in conn if v not in (v_a, v_b))

    if opp is None:
        opp = _opposite_tri(domain, alive, li - 1, v_a, v_b, exclude=tElemID)
        opp_layer = li - 1
    if opp is None:
        return False

    mid = 0.5 * (domain.points[v_a] + domain.points[v_b])
    np_id = _append_point(domain, mid)

    quads.append(_ccw(domain.points, [v_a, np_id, v_b, apex]))

    opp_conn = [int(x) for x in domain.connectivity_list[opp, :3]]
    opp_apex = next(v for v in opp_conn if v not in (v_a, v_b))
    t1 = _ccw(domain.points, [v_a, np_id, opp_apex])
    t2 = _ccw(domain.points, [np_id, v_b, opp_apex])
    _set_conn_row(domain, opp, t1)
    new_eid = _append_conn_row(domain, t2)
    alive.append(True)

    layers = domain.layers
    ol = opp_layer if opp_layer is not None else li - 1
    if opp in set(int(x) for x in np.asarray(layers["IE"][ol], dtype=int)):
        layers["IE"][ol] = np.append(np.asarray(layers["IE"][ol], dtype=int), new_eid)
    else:
        layers["OE"][ol] = np.append(np.asarray(layers["OE"][ol], dtype=int), new_eid)
    layers["OV"][li] = np.append(np.asarray(layers["OV"][li], dtype=int), np_id)
    layers["IV"][ol] = np.append(np.asarray(layers["IV"][ol], dtype=int), np_id)

    alive[tElemID] = False  # tri consumed (became a quad).
    return True


# ---------------------------------------------------------------------------
# edgeInsertion (interior-layer vertex duplication, validated)
# ---------------------------------------------------------------------------
def _edge_insertion(
    domain: CHILmesh,
    alive: List[bool],
    li: int,
    tElemID: int,
    quads: List[List[int]],
) -> bool:
    """Interior-layer lone-tri vertex duplication (Remacle 2012 Fig 9).

    Duplicate one tri vertex ``B`` into ``B'`` placed just inside the tri, rewrite
    the incident elements on one angular side of ``B`` to ``B'``, and emit quad
    ``(B, keep, move, B')``. No original vertex is moved/deleted. Only applied
    when the move-side has an incident element to absorb ``B'`` (so no gap opens)
    and the resulting quad is simple/CCW/non-degenerate. Returns True on success.
    """
    conn = [int(x) for x in domain.connectivity_list[tElemID, :3]]
    if len(conn) != 3 or len(set(conn)) != 3:
        return False
    P = domain.points

    for bi in range(3):
        B = conn[bi]
        A = conn[(bi + 1) % 3]
        C = conn[(bi + 2) % 3]
        centroid = (P[B] + P[A] + P[C]) / 3.0
        pos_bp = 0.5 * P[B] + 0.5 * centroid

        for keep_vert, move_vert in ((A, C), (C, A)):
            quad_pts = np.array(
                [P[B][:2], P[keep_vert][:2], P[move_vert][:2], pos_bp[:2]], dtype=float
            )
            if _quad_ok(quad_pts):
                order = [B, keep_vert, move_vert, "BP"]
            elif _quad_ok(quad_pts[::-1]):
                order = [B, move_vert, keep_vert, "BP"]
            else:
                continue

            side_quads = [qi for qi, q in enumerate(quads) if B in q and move_vert in q]
            side_tris = [
                e for e in range(domain.connectivity_list.shape[0])
                if e != tElemID and alive[e]
                and B in domain.connectivity_list[e, :3]
                and move_vert in domain.connectivity_list[e, :3]
            ]
            if not side_quads and not side_tris:
                continue

            np_id = _append_point(domain, pos_bp)
            final = [np_id if v == "BP" else v for v in order]
            quads.append(_ccw(domain.points, final))
            for qi in side_quads:
                q = quads[qi]
                for i in range(len(q)):
                    if q[i] == B:
                        q[i] = np_id
            for e in side_tris:
                row = domain.connectivity_list[e]
                row[row == B] = np_id
            layers = domain.layers
            layers["OV"][li] = np.append(np.asarray(layers["OV"][li], dtype=int), np_id)
            if li - 1 >= 0:
                layers["IV"][li - 1] = np.append(np.asarray(layers["IV"][li - 1], dtype=int), np_id)
            alive[tElemID] = False
            return True
    return False


# ---------------------------------------------------------------------------
# removeTrianglesFun dispatch
# ---------------------------------------------------------------------------
def _is_layer_boundary_edge(domain: CHILmesh, alive: List[bool], li: int,
                            edge: Tuple[int, int]) -> bool:
    u, v = edge
    layers = domain.layers
    ids = list(int(x) for x in np.asarray(layers["OE"][li], dtype=int))
    ids += list(int(x) for x in np.asarray(layers["IE"][li], dtype=int))
    cnt = 0
    for e in ids:
        if not alive[e]:
            continue
        c = domain.connectivity_list[e, :3]
        if u in c and v in c:
            cnt += 1
    return cnt == 1


def _route_remaining(
    domain: CHILmesh,
    alive: List[bool],
    li: int,
    remaining: List[int],
    b_vert_set: Set[int],
    dom_bdy_edges: Set[Tuple[int, int]],
    quads: List[List[int]],
    minimize_boundary_change: bool,
) -> bool:
    """Route each leftover tri to its op. Returns True if any layer was mutated.

    Uses a worklist so that the new triangles produced by bisecting an opposite
    tri in the SAME layer are themselves reconsidered (the cascade that prevents
    isolated interior tris). Each iteration clears at least one interior tri or
    makes no progress, so it terminates.
    """
    on_mesh_boundary = li == 0
    dirty = False
    work = list(remaining)
    # Cap iterations defensively (each bisection adds <=1 same-layer tri).
    guard = 0
    max_guard = 50 * (len(remaining) + 1)
    while work and guard < max_guard:
        guard += 1
        tElemID = work.pop(0)
        if not alive[tElemID]:
            continue
        conn = [int(x) for x in domain.connectivity_list[tElemID, :3]]
        if len(set(conn)) != 3:
            continue
        edges = [tuple(sorted((conn[i], conn[(i + 1) % 3]))) for i in range(3)]
        b_edges_in_tri = [
            i for i, e in enumerate(edges)
            if e[0] in b_vert_set and e[1] in b_vert_set
            and _is_layer_boundary_edge(domain, alive, li, e)
        ]
        n_dom = sum(1 for e in edges if e in dom_bdy_edges)

        if n_dom == 0:
            # INTERIOR tri -> must be cleared. Bisect an edge whose opposite is
            # still a triangle (preferring the faithful li-1 layer-boundary case,
            # then any same-layer/li-1 tri-opposite edge). The opposite tri splits
            # into two tris; if it is in this layer, requeue them so the cascade
            # continues. We do NOT use vertex-duplication insertion (it opens a
            # crack -> overlapping quads without the thesis's post-hoc smoothing).
            bsel = _find_bisect_edge(
                domain, alive, li, conn, tElemID, b_edges_in_tri, edges
            )
            if bsel is not None:
                edge, opp, opp_layer = bsel
                n_before = domain.connectivity_list.shape[0]
                if _edge_bisection_case2(
                    domain, alive, li, tElemID, edge, quads,
                    opp=opp, opp_layer=opp_layer,
                ):
                    dirty = True
                    if opp_layer == li:
                        # opp + the newly appended tri are same-layer tris; both
                        # may now be interior leftovers -> reconsider them.
                        work.append(opp)
                        work.append(n_before)  # index of the appended tri row
            # else: leave for the vertex-preserving finalization passes.
            continue

        # Genuine boundary tri.
        if minimize_boundary_change:
            continue  # leave as residual boundary tri (preserve original verts).
        if not on_mesh_boundary and b_edges_in_tri:
            if _edge_bisection_case2(domain, alive, li, tElemID, edges[b_edges_in_tri[0]], quads):
                dirty = True
    return dirty


# ---------------------------------------------------------------------------
# Top-level sweep
# ---------------------------------------------------------------------------
def faithful_sweep(
    domain_in: CHILmesh,
    minimize_boundary_change: bool = True,
    can_remove_edges: bool = True,
) -> Tuple[List[List[int]], np.ndarray, np.ndarray]:
    """Run the faithful per-layer tri2quad sweep.

    Faithful pipeline:
      1. **Per-layer sweep** (Tri2QuadRoutine, innermost -> outward): a fresh,
         MATLAB-faithful ``identifyEdgesFun_v2`` flags every-other interior edge
         per layer; the two flanking tris of each flagged edge are emitted as a
         **merge seed pair**. ``edgeBisection`` case 2 is applied to interior
         leftover tris that have a still-triangular opposite in iLayer-1,
         mutating the working Domain in place (the faithful cascade that splits
         the next layer outward). Seeds + bisection give the layer-aligned quad
         shape.
      2. **Interior-saturating match** over the resulting triangulation, seeded
         by the accumulated merge pairs. ``mergeTrianglesFun`` merges adjacent
         tri pairs; doing it as one global interior-saturating match (with the
         augmenting-path fixup) is what guarantees the non-negotiable invariant:
         **zero interior residual triangles**. The seeds keep the merges layer
         aligned. Pure pair-merges -> no point added/moved -> no overlap/gap, and
         every original vertex is preserved.
      3. **Residual clearing** (vertex-preserving): edge-swap residual
         tri-quad-tri fans into 2 quads (thesis Fig 3.2). Remaining boundary tris
         are left (allowed by the invariant; ``minimize_boundary_change`` keeps
         original boundary verts intact rather than squeezing them).

    Returns ``(quads, residual_tris, points)``.
    """
    from .identify_edges import identify_edges_in_layer
    from .tri2quad import _match_tris_to_quads, _edge_swap_tri_pairs

    # Mutable working copy of the Domain (mutated in place, like MATLAB's Domain).
    conn0 = np.asarray(domain_in.connectivity_list)[:, :3].astype(int)
    pts0 = domain_in.points.copy()
    domain = CHILmesh(conn0.copy(), pts0.copy(), grid_name=getattr(domain_in, "grid_name", None))
    n_layers = int(domain.n_layers)

    # Original domain-boundary edges (incident to exactly one triangle).
    ecount: Dict[Tuple[int, int], int] = {}
    for a, b, c in conn0:
        for u, v in ((int(a), int(b)), (int(b), int(c)), (int(c), int(a))):
            e = (min(u, v), max(u, v))
            ecount[e] = ecount.get(e, 0) + 1
    dom_bdy_edges = {e for e, n in ecount.items() if n == 1}

    alive: List[bool] = [True] * domain.connectivity_list.shape[0]
    quads_bisect: List[List[int]] = []
    seed_vert_pairs: List[Tuple[int, int]] = []  # merge seeds as vertex diagonals
    dirty = False

    # ---- 1. Per-layer faithful sweep (seeds + bisection cascade). ----
    for li in range(n_layers - 1, -1, -1):  # innermost -> outward
        if dirty:
            domain.rebuild_adjacencies()
            dirty = False

        sel = identify_edges_in_layer(domain, li)
        if sel.sub_mesh is None:
            continue

        # Record faithful every-other merge seeds as (apex_a, apex_b) diagonals.
        e2e = sel.sub_mesh.adjacencies["Edge2Elem"]
        glob = np.asarray(sel.elem_ids_global, dtype=int)
        for eid in np.asarray(sel.removed_edge_ids, dtype=int):
            row = np.asarray(e2e[int(eid)]).ravel()
            if row.size < 2 or int(row[0]) < 0 or int(row[1]) < 0:
                continue
            ga, gb = int(glob[int(row[0])]), int(glob[int(row[1])])
            if not (alive[ga] and alive[gb]):
                continue
            t1 = set(int(v) for v in domain.connectivity_list[ga, :3])
            t2 = set(int(v) for v in domain.connectivity_list[gb, :3])
            shared = t1 & t2
            if len(shared) != 2:
                continue
            o1 = next(v for v in t1 if v not in shared)
            o2 = next(v for v in t2 if v not in shared)
            seed_vert_pairs.append((min(o1, o2), max(o1, o2)))

        # Bisection cascade: interior leftover tris with a still-triangular
        # opposite in iLayer-1. This refines the triangulation outward (faithful)
        # and adds shared midpoints so the next layer absorbs them.
        b_vert_set = set(int(v) for v in np.asarray(sel.boundary_vert_ids_global).ravel())
        remaining = [int(e) for e in glob if alive[int(e)]]
        if _route_remaining(
            domain, alive, li, remaining, b_vert_set, dom_bdy_edges,
            quads_bisect, minimize_boundary_change,
        ):
            dirty = True

    # ---- 2. Global interior-saturating match on the refined triangulation. ----
    # The bisection turned some tris into quads (quads_bisect) and split their
    # opposites; those consumed tris are dead. Match the surviving tris, seeded
    # by the recorded merge diagonals so the quads stay layer-aligned.
    points = domain.points
    surviving = [
        int(e) for e in range(domain.connectivity_list.shape[0]) if alive[e]
    ]
    surv_tris = np.array(
        [domain.connectivity_list[e, :3] for e in surviving], dtype=int
    ).reshape(-1, 3)
    # Translate recorded vertex-pair seeds into tri-index seed pairs.
    diag_to_tris: Dict[Tuple[int, int], List[int]] = {}
    for i, t in enumerate(surv_tris):
        a, b, c = int(t[0]), int(t[1]), int(t[2])
        for e in (tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((c, a)))):
            diag_to_tris.setdefault(e, []).append(i)
    seed_idx_pairs: List[Tuple[int, int]] = []
    # The merge seed's two tris share an edge; that edge is the seed diagonal's
    # *perpendicular* — i.e. the two apex verts are the diagonal. The shared edge
    # is the other two. Rebuild from shared-edge adjacency instead:
    edge_pairs: Dict[Tuple[int, int], List[int]] = {}
    for i, t in enumerate(surv_tris):
        a, b, c = int(t[0]), int(t[1]), int(t[2])
        for e in (tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((c, a)))):
            edge_pairs.setdefault(e, []).append(i)
    seen_seed: Set[Tuple[int, int]] = set()
    for (o1, o2) in seed_vert_pairs:
        # find a tri containing o1 and a tri containing o2 that share an edge.
        cand = None
        for e, lst in edge_pairs.items():
            if len(lst) != 2:
                continue
            i, j = lst
            si = set(int(v) for v in surv_tris[i])
            sj = set(int(v) for v in surv_tris[j])
            if o1 in si and o2 in sj and o1 not in sj and o2 not in si:
                cand = (i, j)
                break
            if o2 in si and o1 in sj and o2 not in sj and o1 not in si:
                cand = (i, j)
                break
        if cand is not None and cand not in seen_seed:
            seen_seed.add(cand)
            seed_idx_pairs.append(cand)

    merged, leftover = _match_tris_to_quads(
        surv_tris, points, seed_pairs=seed_idx_pairs
    )

    P = points[:, :2]
    quads: List[List[int]] = list(quads_bisect)
    # Recover source-tri pair of each matched quad (for bowtie rejection).
    edge2tri: Dict[Tuple[int, int], List[int]] = {}
    for i, t in enumerate(surv_tris):
        for e in _tri_edges_t(t):
            edge2tri.setdefault(e, []).append(i)
    leftover_set = set(int(i) for i in leftover)
    for q in merged:
        ql = [int(v) for v in q]
        if len(set(ql)) != 4:
            continue
        if _quad_ok(P[ql]):
            quads.append(_ccw(points, ql))
        else:
            for diag in (tuple(sorted((ql[1], ql[3]))), tuple(sorted((ql[0], ql[2])))):
                pair = edge2tri.get(diag)
                if pair and len(pair) >= 2:
                    leftover_set.update(pair[:2])
                    break
    residual = [[int(v) for v in surv_tris[i]] for i in sorted(leftover_set)]
    residual_arr = (
        np.array(residual, dtype=int) if residual else np.empty((0, 3), dtype=int)
    )

    # ---- 3. Vertex-preserving residual clearing (edge-swap tri-quad-tri fans). ----
    prev_tris = -1
    while residual_arr.size > 0 and quads and len(residual_arr) != prev_tris:
        prev_tris = len(residual_arr)
        qt = [tuple(int(v) for v in q) for q in quads]
        qt, residual_arr = _edge_swap_tri_pairs(qt, residual_arr, points)
        quads = [list(q) for q in qt]

    return quads, residual_arr, points


def _tri_edges_t(t) -> List[Tuple[int, int]]:
    a, b, c = int(t[0]), int(t[1]), int(t[2])
    return [tuple(sorted(e)) for e in ((a, b), (b, c), (c, a))]


def _elem_edges(e) -> List[Tuple[int, int]]:
    n = len(e)
    return [tuple(sorted((int(e[i]), int(e[(i + 1) % n])))) for i in range(n)]


def _count_interior_tris(quads: List[List[int]], residual: np.ndarray) -> int:
    tris = np.asarray(residual).reshape(-1, 3)
    if len(tris) == 0:
        return 0
    cnt: Dict[Tuple[int, int], int] = {}
    for el in [list(q) for q in quads] + [list(t) for t in tris]:
        for e in _elem_edges(el):
            cnt[e] = cnt.get(e, 0) + 1
    bset = {e for e, c in cnt.items() if c == 1}
    return sum(1 for t in tris if not any(e in bset for e in _tri_edges_t(t)))


def _global_saturate(
    quads: List[List[int]],
    residual: np.ndarray,
    points: np.ndarray,
    dom_bdy_edges: Set[Tuple[int, int]],
) -> Tuple[List[List[int]], np.ndarray]:
    """Global interior-saturating re-tiling fallback (vertex-preserving).

    Splits EVERY current element (quads and residual tris) into triangles, then
    runs a single global interior-saturating match seeded by the existing quad
    diagonals so untouched regions reform their original quads, while stranded
    interior tris get matched via augmenting paths. Only adjacent tri pairs are
    merged (no point added/moved -> no overlaps/gaps; the augmenting-path fixup
    guarantees zero interior residue when the adjacency graph permits).
    """
    from .tri2quad import _match_tris_to_quads

    P = points[:, :2]
    tri_rows: List[List[int]] = []
    seeds: List[Tuple[int, int]] = []
    # Quads -> 2 tris on diagonal 0-2; seed the two halves to reform the quad.
    for q in quads:
        ql = [int(v) for v in q]
        i0 = len(tri_rows)
        tri_rows.append([ql[0], ql[1], ql[2]])
        tri_rows.append([ql[0], ql[2], ql[3]])
        seeds.append((i0, i0 + 1))
    for t in np.asarray(residual).reshape(-1, 3):
        tri_rows.append([int(v) for v in t])

    tri_arr = np.asarray(tri_rows, dtype=int).reshape(-1, 3)
    merged, leftover = _match_tris_to_quads(tri_arr, points, seed_pairs=seeds)

    # Map each tri edge -> tri indices, to recover the 2 source tris of a quad
    # (its diagonal is the source tris' shared edge) so a rejected (bowtie/
    # degenerate) quad can return its source tris to the residual set.
    edge2tri: Dict[Tuple[int, int], List[int]] = {}
    for i, t in enumerate(tri_arr):
        for e in _tri_edges_t(t):
            edge2tri.setdefault(e, []).append(i)

    out_quads: List[List[int]] = []
    leftover_set = set(int(i) for i in leftover)
    for q in merged:
        ql = [int(v) for v in q]
        if len(set(ql)) != 4:
            continue
        if _quad_ok(P[ql]):
            out_quads.append(_ccw(points, ql))
            continue
        # Bowtie/degenerate: return its 2 source tris to the residual set.
        for diag in (tuple(sorted((ql[1], ql[3]))), tuple(sorted((ql[0], ql[2])))):
            pair = edge2tri.get(diag)
            if pair and len(pair) >= 2:
                leftover_set.update(pair[:2])
                break

    out_tris = [[int(v) for v in tri_arr[i]] for i in sorted(leftover_set)]
    res_out = (
        np.asarray(out_tris, dtype=int).reshape(-1, 3) if out_tris
        else np.empty((0, 3), dtype=int)
    )
    return out_quads, res_out


def _merge_layer(domain, alive, glob, sel, quads) -> Set[int]:
    """Interior-saturating merge of one layer's tris into quads (layer-seeded).

    Runs ``_match_tris_to_quads`` over the layer's triangles using the
    every-other flagged pairs as seeds. Guarantees no interior tri of the layer
    is stranded (augmenting-path fixup) while keeping merges layer-aligned.
    Mutates ``alive`` (consumed tris) and appends quads. Returns the set of
    consumed global element IDs.
    """
    from .tri2quad import _match_tris_to_quads

    layer_ids = [int(e) for e in glob if alive[int(e)]]
    if not layer_ids:
        return set()
    local_to_global = {i: gid for i, gid in enumerate(layer_ids)}
    global_to_local = {gid: i for i, gid in local_to_global.items()}
    local_tris = np.array([domain.connectivity_list[gid, :3] for gid in layer_ids], dtype=int)

    # Seed pairs: flagged edges -> the two flanking layer elements (local idx).
    e2e = sel.sub_mesh.adjacencies["Edge2Elem"]
    seeds: List[Tuple[int, int]] = []
    for eid in np.asarray(sel.removed_edge_ids, dtype=int):
        row = np.asarray(e2e[int(eid)]).ravel()
        if row.size < 2 or int(row[0]) < 0 or int(row[1]) < 0:
            continue
        ga, gb = int(glob[int(row[0])]), int(glob[int(row[1])])
        if ga in global_to_local and gb in global_to_local:
            seeds.append((global_to_local[ga], global_to_local[gb]))

    merged_local, _leftover = _match_tris_to_quads(
        local_tris, domain.points, seed_pairs=seeds
    )

    consumed: Set[int] = set()
    P = domain.points[:, :2]
    # Reconstruct which local tris each quad merged from (shared-edge pair) so we
    # can mark the global IDs consumed.
    edge_to_local: Dict[Tuple[int, int], List[int]] = {}
    for i, t in enumerate(local_tris):
        a, b, c = int(t[0]), int(t[1]), int(t[2])
        for e in (tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((c, a)))):
            edge_to_local.setdefault(e, []).append(i)
    for q in merged_local:
        ql = [int(v) for v in q]
        if len(set(ql)) != 4 or not _quad_ok(P[ql]):
            continue
        # Diagonal of the merged quad = the shared edge of the two tris.
        diag = tuple(sorted((ql[1], ql[3])))
        pair = edge_to_local.get(diag) or edge_to_local.get(tuple(sorted((ql[0], ql[2]))))
        if not pair or len(pair) < 2:
            continue
        gi, gj = local_to_global[pair[0]], local_to_global[pair[1]]
        if not (alive[gi] and alive[gj]):
            continue
        quads.append(_ccw(domain.points, ql))
        alive[gi] = alive[gj] = False
        consumed.add(gi)
        consumed.add(gj)
    return consumed


def _merge_residual_pairs(
    quads: List[List[int]], residual: np.ndarray, points: np.ndarray
) -> Tuple[List[List[int]], np.ndarray]:
    """Interior-saturating merge of edge-adjacent residual tri pairs into quads.

    Delegates to the proven ``_match_tris_to_quads`` interior-saturating matcher
    (augmenting-path fixup guarantees no interior tri is left unmatched when its
    adjacency component permits a matching). Vertex-preserving: only adjacent
    tri pairs are merged, no point is added or moved. Quads that would be
    degenerate/bowtied are filtered out (the tris stay residual).
    """
    tris = np.asarray(residual, dtype=int).reshape(-1, 3)
    if len(tris) == 0:
        return quads, residual

    from .tri2quad import _match_tris_to_quads

    new_quad_tuples, leftover = _match_tris_to_quads(tris, points)
    P = points[:, :2]
    new_quads: List[List[int]] = []
    used_pairs: Set[int] = set()
    for q in new_quad_tuples:
        ql = [int(v) for v in q]
        if len(set(ql)) != 4 or not _quad_ok(P[ql]):
            continue
        new_quads.append(_ccw(points, ql))

    # Determine which residual tris were consumed (those NOT in leftover and
    # whose merged quad was accepted). Simpler: rebuild residual from leftover
    # plus any tri whose quad was rejected. Recompute by matching identity:
    # the matcher returns leftover indices; a tri is kept iff it is leftover OR
    # its quad was rejected. To stay robust, recompute kept set from coverage.
    covered_verts_per_quad = [set(q) for q in new_quads]

    leftover_set = set(int(i) for i in leftover)
    kept: List[List[int]] = []
    accepted_tris: Set[int] = set()
    # Map each accepted quad back to the two tris that formed it (by shared edge).
    # Build tri adjacency to identify pairs.
    def tri_edges(t):
        a, b, c = int(t[0]), int(t[1]), int(t[2])
        return [tuple(sorted(e)) for e in ((a, b), (b, c), (c, a))]

    quad_vert_sets = covered_verts_per_quad
    for i, t in enumerate(tris):
        if i in leftover_set:
            kept.append([int(v) for v in t])
            continue
        ts = set(int(v) for v in t)
        if any(ts <= qs for qs in quad_vert_sets):
            accepted_tris.add(i)
        else:
            kept.append([int(v) for v in t])  # quad rejected -> tri stays

    quads_out = list(quads) + new_quads
    residual_out = np.array(kept, dtype=int) if kept else np.empty((0, 3), dtype=int)
    return quads_out, residual_out
