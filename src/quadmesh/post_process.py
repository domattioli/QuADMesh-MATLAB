"""Post-process orchestrator. Port of MATLAB PostProcessRoutine.m.

Smoothing is a FEM direct solve, iterated n_iter passes (chilmesh
``smooth_mesh('fem')``). MATLAB's ``twoPartSmoother.m`` also ran MCSmooth on the
boundary layers, but that half was never ported — the Python path has always
been FEM-only — so the smoother is named for what it is: ``fem_smoother``.

Pipeline:
    repeat until stable (max_outer_iter):
        repeat until stable (max_inner_iter):
            doublet_collapse -> quad_vertex_merge
        cleanup_boundary_quads
    fem_smoother  (compacts unused verts, then n_iter FEM passes)
"""
from __future__ import annotations

from chilmesh import CHILmesh

from .cleanup_boundary_quads import cleanup_boundary_quads
from .doublet_collapse import doublet_collapse
from .quad_vertex_merge import quad_vertex_merge
from .remove_unused import remove_unused_vertices


def fem_smoother(mesh: CHILmesh, n_iter: int = 3) -> CHILmesh:
    """FEM direct-solve smoother: n_iter passes of chilmesh ``smooth_mesh('fem')``.

    Args:
        mesh: CHILmesh to smooth.
        n_iter: Number of FEM passes.
    """
    if n_iter <= 0:
        return mesh
    # Element-less vertices add zero rows to the stiffness matrix, making it
    # singular and spsolve return garbage; drop them so every caller is safe.
    mesh = remove_unused_vertices(mesh)
    for _ in range(n_iter):
        try:
            mesh.smooth_mesh(method="fem", acknowledge_change=True)
        except Exception:
            break
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
        n_smooth_iter: Passes for fem_smoother.
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

    mesh = fem_smoother(mesh, n_iter=n_smooth_iter)

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
