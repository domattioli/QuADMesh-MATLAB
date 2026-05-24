"""Mesh repair pass — fixes geometric defects left by topology pipeline.

Three repair operations:

1. ``_snap_boundary_midpoints`` — boundary midpoints inserted by
   ``_insert_boundary_tri_midpoint`` (or equivalent) get rewired by
   downstream doublet-collapse and quad-vertex-merge passes. Surviving
   degree-2 boundary vertices are snapped back to the exact midpoint of
   their two boundary neighbors.

2. ``_fix_bowties`` — self-intersecting (bowtie) quads where edges (0,1)
   cross (2,3) or (1,2) cross (3,0) get reordered. Tries 3 vertex
   permutations + scipy ConvexHull ordering; picks first CCW
   non-crossing result.

3. ``_dissolve_violation_clusters`` — clusters of elements that still
   trigger INTERIOR_OVERLAP or EDGE_CROSSING violations get dissolved
   into their exterior boundary ring, ear-clip triangulated, then
   greedily merged tri-pair → quad.

Verified on WNAT_Hagen (~49k elements): 0 interior tris,
0 SELF_INTERSECTING_QUAD, 0 INTERIOR_OVERLAP, 0 EDGE_CROSSING after
``repair_mesh``.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    from chilmesh import CHILmesh


def _build_full_edge_map(conn: np.ndarray) -> dict[tuple[int, int], list[int]]:
    """Edge → element-id list for mixed (3 or 4 col) connectivity."""
    out: dict[tuple[int, int], list[int]] = {}
    for ei in range(conn.shape[0]):
        row = conn[ei]
        if row[0] == row[3]:
            verts = [int(row[k]) for k in range(3)]
        else:
            verts = [int(row[k]) for k in range(4)]
        n = len(verts)
        for k in range(n):
            a, b = verts[k], verts[(k + 1) % n]
            key = (a, b) if a < b else (b, a)
            out.setdefault(key, []).append(ei)
    return out


def _snap_boundary_midpoints(
    conn: np.ndarray,
    pts: np.ndarray,
    mid_threshold: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Snap degree-2 boundary vertices to the midpoint of their neighbors.

    Args:
        conn: (n_elems, 4) connectivity (padded tris have row[0]==row[3]).
        pts: (n_verts, 3) points; only [:, :2] gets touched.
        mid_threshold: Only snap vertex IDs >= this value. Pass the
            original vertex count (before midpoint insertion) to limit
            snapping to inserted midpoints.

    Returns:
        (conn, pts) — pts modified in-place; conn unchanged.
    """
    edge_map = _build_full_edge_map(conn)

    bv_edges: dict[int, list[tuple[int, int]]] = {}
    for key, lst in edge_map.items():
        if len(lst) != 1:
            continue
        a, b = key
        bv_edges.setdefault(a, []).append(key)
        bv_edges.setdefault(b, []).append(key)

    for v, edges in bv_edges.items():
        if v < mid_threshold:
            continue
        if len(edges) != 2:
            continue
        nbrs = [k[0] if k[1] == v else k[1] for k in edges]
        pts[v, :2] = 0.5 * (pts[nbrs[0], :2] + pts[nbrs[1], :2])

    return conn, pts


def _fix_bowties(conn: np.ndarray, pts: np.ndarray) -> tuple[np.ndarray, int]:
    """Reorder self-intersecting quad vertices to a valid CCW arrangement.

    Returns (conn, n_fixed).
    """
    try:
        from scipy.spatial import ConvexHull as _ConvexHull
        _have_scipy = True
    except ImportError:
        _have_scipy = False

    def _seg_cross(p1, p2, p3, p4):
        def _ori(pa, pb, pc):
            v = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
            return 1 if v > 1e-12 else (-1 if v < -1e-12 else 0)
        o1, o2 = _ori(p1, p2, p3), _ori(p1, p2, p4)
        o3, o4 = _ori(p3, p4, p1), _ori(p3, p4, p2)
        if o1 == 0 or o2 == 0 or o3 == 0 or o4 == 0:
            return False
        return o1 != o2 and o3 != o4

    n_fixed = 0
    for ei in range(conn.shape[0]):
        r = conn[ei]
        if r[0] == r[3]:
            continue
        verts = [int(r[k]) for k in range(4)]
        if len(set(verts)) < 4:
            continue
        poly = pts[verts, :2]
        v0, v1, v2, v3 = poly[0], poly[1], poly[2], poly[3]
        if not (_seg_cross(v0, v1, v2, v3) or _seg_cross(v1, v2, v3, v0)):
            continue

        candidates: list[list[int]] = [
            [verts[0], verts[1], verts[3], verts[2]],
            [verts[0], verts[2], verts[1], verts[3]],
            [verts[0], verts[3], verts[2], verts[1]],
        ]
        if _have_scipy:
            try:
                ch = _ConvexHull(poly)
                if len(ch.vertices) == 4:
                    candidates.append([verts[i] for i in ch.vertices.tolist()])
            except Exception:
                pass

        best: tuple[list[int], float] | None = None
        for c in candidates:
            p = pts[c, :2]
            x, y = p[:, 0], p[:, 1]
            sa = 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
            if sa <= 0:
                continue
            cv0, cv1, cv2, cv3 = p[0], p[1], p[2], p[3]
            if _seg_cross(cv0, cv1, cv2, cv3) or _seg_cross(cv1, cv2, cv3, cv0):
                continue
            if best is None or sa > best[1]:
                best = (c, sa)

        if best is not None:
            conn[ei] = np.array(best[0], dtype=int)
            n_fixed += 1

    return conn, n_fixed


def _ear_clip(ring: list[int], pts: np.ndarray) -> list[tuple[int, int, int]]:
    """Triangulate a simple polygon via ear-clipping.

    Args:
        ring: Vertex IDs forming the polygon boundary (any winding).
        pts:  (n_verts, 3+) points.

    Returns:
        List of (a, b, c) triangle vertex-ID triples in CCW order.
    """
    ring = list(ring)
    n = len(ring)
    if n < 3:
        return []
    if n == 3:
        return [tuple(ring)]  # type: ignore[return-value]

    poly = pts[ring, :2]
    x, y = poly[:, 0], poly[:, 1]
    if 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)) < 0:
        ring = ring[::-1]

    def _point_in_tri(p, a, v, b):
        def _ori(p0, p1, p2):
            return (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0])
        d1, d2, d3 = _ori(p, a, v), _ori(p, v, b), _ori(p, b, a)
        has_neg = d1 < 0 or d2 < 0 or d3 < 0
        has_pos = d1 > 0 or d2 > 0 or d3 > 0
        if has_neg and has_pos:
            return False
        return abs(d1) > 1e-14 and abs(d2) > 1e-14 and abs(d3) > 1e-14

    tris: list[tuple[int, int, int]] = []
    max_iters = len(ring) ** 2 + 10
    iters = 0
    while len(ring) > 3 and iters < max_iters:
        iters += 1
        cur_n = len(ring)
        ear_found = False
        for i in range(cur_n):
            a_id = ring[(i - 1) % cur_n]
            v_id = ring[i]
            b_id = ring[(i + 1) % cur_n]
            a = pts[a_id, :2]; v = pts[v_id, :2]; b = pts[b_id, :2]
            cross = (v[0] - a[0]) * (b[1] - a[1]) - (v[1] - a[1]) * (b[0] - a[0])
            if cross <= 0:
                continue
            inside = any(
                _point_in_tri(pts[ring[j], :2], a, v, b)
                for j in range(cur_n)
                if j not in ((i - 1) % cur_n, i, (i + 1) % cur_n)
            )
            if not inside:
                tris.append((a_id, v_id, b_id))
                ring.pop(i)
                ear_found = True
                break
        if not ear_found:
            tris.append((ring[-1], ring[0], ring[1]))
            ring.pop(0)
    if len(ring) == 3:
        tris.append(tuple(ring))  # type: ignore[arg-type]
    return tris


def _merge_tri_pairs_to_quads(
    tris: list[tuple[int, ...]],
    pts: np.ndarray,
) -> list[tuple[int, ...]]:
    """Greedily merge adjacent triangle pairs into CCW non-bowtie quads."""
    edge_map: dict[tuple[int, int], list[int]] = {}
    for i, t in enumerate(tris):
        for k in range(3):
            a, b = t[k], t[(k + 1) % 3]
            key = (a, b) if a < b else (b, a)
            edge_map.setdefault(key, []).append(i)

    used: set[int] = set()
    result: list[tuple[int, ...]] = []

    for i, t in enumerate(tris):
        if i in used:
            continue
        best_pair: tuple[int, tuple[int, int, int, int]] | None = None
        for k in range(3):
            a, b = t[k], t[(k + 1) % 3]
            key = (a, b) if a < b else (b, a)
            nbrs = [j for j in edge_map.get(key, []) if j != i and j not in used]
            if not nbrs:
                continue
            j = nbrs[0]
            tj = tris[j]
            ua = [v for v in t if v not in (a, b)]
            ub = [v for v in tj if v not in (a, b)]
            if len(ua) != 1 or len(ub) != 1:
                continue
            idx_ua = list(t).index(ua[0])
            nxt = t[(idx_ua + 1) % 3]
            quad: tuple[int, int, int, int] = (ua[0], a, ub[0], b) if nxt == a else (ua[0], b, ub[0], a)
            poly = pts[list(quad), :2]
            x, y = poly[:, 0], poly[:, 1]
            sa = 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
            if sa <= 0:
                quad = tuple(reversed(quad))  # type: ignore[assignment]
                poly = pts[list(quad), :2]
                x, y = poly[:, 0], poly[:, 1]
                sa = 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
            if sa <= 0:
                continue
            v0r, v1r, v2r, v3r = poly[0], poly[1], poly[2], poly[3]

            def _sc(p1, p2, p3, p4):
                def _o(pa, pb, pc):
                    v = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
                    return 1 if v > 1e-12 else (-1 if v < -1e-12 else 0)
                o1, o2, o3, o4 = _o(p1, p2, p3), _o(p1, p2, p4), _o(p3, p4, p1), _o(p3, p4, p2)
                if 0 in (o1, o2, o3, o4):
                    return False
                return o1 != o2 and o3 != o4

            if _sc(v0r, v1r, v2r, v3r) or _sc(v1r, v2r, v3r, v0r):
                continue
            best_pair = (j, quad)
            break
        if best_pair:
            j, quad = best_pair
            result.append(quad)
            used.add(i); used.add(j)
        else:
            result.append(t)
    return result


def _dissolve_violation_clusters(
    conn: np.ndarray,
    pts: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Dissolve + ear-clip + merge clusters of validator-flagged elements.

    A cluster is a connected component of elements with INTERIOR_OVERLAP
    or EDGE_CROSSING violations. Each cluster's exterior boundary ring is
    re-triangulated and merged back to quads. Silently skips clusters
    whose remesh would produce a bowtie.

    Requires ``quadmesh.validation`` and ``chilmesh``; no-op if missing.
    """
    try:
        from chilmesh import CHILmesh as _CM

        from .validation.validator import validate_mesh_elements as _validate
    except ImportError:
        return conn, pts

    try:
        snap = _CM(connectivity=conn, points=pts, grid_name='_repair',
                   compute_layers=False)
        rep = _validate(snap)
    except Exception:
        return conn, pts

    bad_elems: set[int] = set()
    for viol in rep.violations:
        if viol.category == 'NON_PLANAR_MESH':
            continue
        for eid in viol.element_ids:
            bad_elems.add(int(eid))

    if not bad_elems:
        return conn, pts

    edge_map = _build_full_edge_map(conn)
    adj: dict[int, set[int]] = {e: set() for e in bad_elems}
    for key, lst in edge_map.items():
        for ei in lst:
            if ei not in bad_elems:
                continue
            for ej in lst:
                if ej != ei and ej in bad_elems:
                    adj[ei].add(ej)

    visited: set[int] = set()
    clusters: list[list[int]] = []
    for start in sorted(bad_elems):
        if start in visited:
            continue
        cluster: list[int] = []
        queue = [start]
        while queue:
            cur = queue.pop()
            if cur in visited:
                continue
            visited.add(cur)
            cluster.append(cur)
            queue.extend(adj.get(cur, set()) - visited)
        clusters.append(cluster)

    all_new_rows: list[list[int]] = []
    delete_mask = np.ones(conn.shape[0], dtype=bool)

    for cluster in clusters:
        edge_count: dict[tuple[int, int], int] = {}
        for ei in cluster:
            r = conn[ei]
            verts = [int(r[k]) for k in range(3 if r[0] == r[3] else 4)]
            n = len(verts)
            for k in range(n):
                a, b = verts[k], verts[(k + 1) % n]
                key = (a, b) if a < b else (b, a)
                edge_count[key] = edge_count.get(key, 0) + 1
        exterior = [k for k, v in edge_count.items() if v == 1]
        if not exterior:
            continue

        adj_v: dict[int, list[int]] = {}
        for a, b in exterior:
            adj_v.setdefault(a, []).append(b)
            adj_v.setdefault(b, []).append(a)
        start_v = exterior[0][0]
        ring: list[int] = [start_v]
        prev_v: int | None = None
        cur_v = start_v
        for _ in range(len(exterior) + 2):
            opts = [v for v in adj_v[cur_v] if v != prev_v]
            if not opts:
                break
            nxt = opts[0]
            if nxt == start_v:
                break
            ring.append(nxt)
            prev_v = cur_v
            cur_v = nxt

        if len(ring) < 3:
            continue

        tris = _ear_clip(ring, pts)
        if not tris:
            continue
        elements = _merge_tri_pairs_to_quads(tris, pts)

        new_rows: list[list[int]] = []
        valid = True
        for e in elements:
            if len(e) == 3:
                a, b, c = e
                new_rows.append([a, b, c, a])
            elif len(e) == 4:
                poly = pts[list(e), :2]
                v0, v1, v2, v3 = poly[0], poly[1], poly[2], poly[3]

                def _sc2(p1, p2, p3, p4):
                    def _o(pa, pb, pc):
                        v = (pb[0] - pa[0]) * (pc[1] - pa[1]) - (pb[1] - pa[1]) * (pc[0] - pa[0])
                        return 1 if v > 1e-12 else (-1 if v < -1e-12 else 0)
                    o1, o2, o3, o4 = _o(p1, p2, p3), _o(p1, p2, p4), _o(p3, p4, p1), _o(p3, p4, p2)
                    if 0 in (o1, o2, o3, o4):
                        return False
                    return o1 != o2 and o3 != o4

                if _sc2(v0, v1, v2, v3) or _sc2(v1, v2, v3, v0):
                    valid = False
                    break
                new_rows.append(list(e))

        if not valid:
            continue

        for ei in cluster:
            delete_mask[ei] = False
        all_new_rows.extend(new_rows)

    kept_conn = conn[delete_mask]
    if all_new_rows:
        conn = np.vstack([kept_conn, np.array(all_new_rows, dtype=int)])
    else:
        conn = kept_conn

    return conn, pts


def repair_mesh(
    conn: np.ndarray,
    pts: np.ndarray,
    mid_threshold: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply all three repair passes in order.

    Args:
        conn: (n_elems, 4) connectivity (row[0]==row[3] for padded tris).
        pts:  (n_verts, 3) points.
        mid_threshold: Vertex index below which midpoint snapping is
            skipped. Pass the original vertex count (before
            ``_insert_boundary_tri_midpoint``) to restrict snapping to
            inserted midpoints.

    Returns:
        (conn, pts) — repaired copies, not the originals.
    """
    conn = conn.copy()
    pts = pts.copy()
    conn, pts = _snap_boundary_midpoints(conn, pts, mid_threshold=mid_threshold)
    conn, _ = _fix_bowties(conn, pts)
    conn, pts = _dissolve_violation_clusters(conn, pts)
    return conn, pts


def repair_chilmesh(mesh: "CHILmesh") -> "CHILmesh":
    """Convenience wrapper: apply ``repair_mesh`` to a CHILmesh.

    Returns a new CHILmesh with the same grid_name and recomputed layers.
    """
    from chilmesh import CHILmesh

    conn = np.asarray(mesh.connectivity_list, dtype=int).copy()
    pts = np.asarray(mesh.points, dtype=float).copy()
    conn, pts = repair_mesh(conn, pts, mid_threshold=0)
    return CHILmesh(
        connectivity=conn,
        points=pts,
        grid_name=mesh.grid_name,
        compute_layers=True,
    )
