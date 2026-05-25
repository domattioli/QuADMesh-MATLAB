"""Post-process orchestrator. Port of MATLAB PostProcessRoutine.m + twoPartSmoother.m.

MAT twoPartSmoother for non-mixed meshes applied MCSmooth to boundary layers (1-3) and
FEMSmooth to interior elements.  For mixed-element meshes (typical output), MATLAB just
runs FEMSmoother once.  We match that behavior: n_iter passes of FEM by default.

Angle-based smooth is available as opt-in (method='angle-based') but is slow (~40s/pass
on 2417 elements in chilmesh 0.4); avoid in production until chilmesh vectorises it.

Pipeline:
    repeat until stable (max_outer_iter):
        repeat until stable (max_inner_iter):
            doublet_collapse -> quad_vertex_merge
        cleanup_boundary_quads
    remove_unused_vertices
    two_part_smoother
"""
from __future__ import annotations

from chilmesh import CHILmesh

from .cleanup_boundary_quads import cleanup_boundary_quads
from .doublet_collapse import doublet_collapse
from .quad_vertex_merge import quad_vertex_merge
from .remove_unused import remove_unused_vertices


def two_part_smoother(
    mesh: CHILmesh,
    n_iter: int = 3,
    method: str = "fem",
) -> CHILmesh:
    """Iterative mesh smoother. Port of MATLAB twoPartSmoother.m.

    MATLAB mixed-element path: single FEM pass. We generalise to n_iter passes.
    Default method is 'fem' (fast: ~0.3s/pass on 2417 elems).
    Use method='angle-based' for higher quality at ~40s/pass (chilmesh 0.4 is slow).

    The FEM stiffness matrix goes near-singular wherever tri2quad's boundary-tri
    squeeze (edge_removal) left a tight cluster of near-coincident vertices; the
    solve then flings that whole cluster many element-widths away, drawing
    long "spoke" edges across the domain. Guard: after each pass, revert any
    node whose displacement exceeds ``cap_factor`` × its local edge scale (median
    incident-edge length pre-pass) back to its prior position. Reverting the
    whole offending set simultaneously keeps neighbourhoods consistent (a lone
    bbox check left reverted nodes stranded beside un-reverted neighbours,
    re-creating the spoke). Independent of chilmesh boundary internals.

    Args:
        mesh: CHILmesh to smooth.
        n_iter: Number of smooth passes.
        method: 'fem' (default) or 'angle-based'.
    """
    import numpy as np

    cap_factor = 3.0  # max allowed move = cap_factor × local median edge length

    for _ in range(n_iter):
        prev = mesh.points[:, :2].copy()
        n = len(prev)

        # Local edge scale per node: median length of its incident edges.
        edge_sum = np.zeros(n)
        edge_cnt = np.zeros(n)
        for row in mesh.connectivity_list:
            v = [int(x) for x in row if int(x) >= 0]
            k = len(v)
            for j in range(k):
                a, b = v[j], v[(j + 1) % k]
                L = float(np.hypot(prev[a, 0] - prev[b, 0], prev[a, 1] - prev[b, 1]))
                edge_sum[a] += L
                edge_cnt[a] += 1
                edge_sum[b] += L
                edge_cnt[b] += 1
        scale = np.where(edge_cnt > 0, edge_sum / np.maximum(edge_cnt, 1), 0.0)

        try:
            mesh.smooth_mesh(method=method, acknowledge_change=True)
        except Exception:
            break

        cur = mesh.points[:, :2]
        m = min(len(prev), len(cur))
        disp = np.hypot(cur[:m, 0] - prev[:m, 0], cur[:m, 1] - prev[:m, 1])
        cap = cap_factor * scale[:m]
        # Cap of 0 (isolated node) → use global median edge as fallback.
        global_scale = float(np.median(scale[scale > 0])) if np.any(scale > 0) else 0.0
        cap = np.where(cap > 0, cap, cap_factor * global_scale)
        runaway = disp > cap
        if runaway.any():
            mesh.points[:m][runaway, :2] = prev[runaway]
    return mesh



def post_process_routine(
    mesh: CHILmesh,
    can_remove_edges: bool = True,
    n_smooth_iter: int = 3,
    max_outer_iter: int = 5,
    max_inner_iter: int = 5,
    repair: bool = False,
) -> CHILmesh:
    """Iteratively improve quad-mesh quality.

    Args:
        mesh: Quad (or mixed) CHILmesh from tri2quad.
        can_remove_edges: Allow boundary-quad collapse.
        n_smooth_iter: Passes for two_part_smoother.
        max_outer_iter: Outer loop cap.
        max_inner_iter: Inner loop cap (doublet + QVM).
        repair: Apply ``repair_chilmesh`` as a final pass — snap
            boundary midpoints, fix bowties, dissolve+remesh validator
            clusters. Off by default (element count + quality drift can
            break parity baselines); opt-in via ``repair=True`` or call
            ``repair_chilmesh`` directly after this routine.
    """
    outer = 0
    n_elems_prev = mesh.n_elems
    while outer < max_outer_iter:
        outer += 1
        inner = 0
        while inner < max_inner_iter:
            inner += 1
            n_before = mesh.n_elems
            mesh = doublet_collapse(mesh)
            mesh = quad_vertex_merge(mesh)
            if mesh.n_elems >= n_before:
                break

        if getattr(mesh, "type", None) != "Mixed-Element":
            mesh = cleanup_boundary_quads(mesh, can_remove_edges=can_remove_edges)

        if mesh.n_elems >= n_elems_prev:
            break
        n_elems_prev = mesh.n_elems

    mesh = remove_unused_vertices(mesh)
    mesh = two_part_smoother(mesh, n_iter=n_smooth_iter)

    # Smoother moves vertices without bowtie guard; fix any self-intersecting
    # quads it creates by reordering their vertices (no point added/deleted).
    from .repair import _fix_bowties
    import numpy as np
    _conn = np.asarray(mesh.connectivity_list).copy()
    _conn_fixed, _n_bt = _fix_bowties(_conn, mesh.points)
    if _n_bt:
        mesh = CHILmesh(
            _conn_fixed, mesh.points, grid_name=getattr(mesh, "grid_name", None)
        )

    if repair:
        from .repair import repair_chilmesh
        mesh = repair_chilmesh(mesh)

    return mesh
