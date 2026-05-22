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

    Args:
        mesh: CHILmesh to smooth.
        n_iter: Number of smooth passes.
        method: 'fem' (default) or 'angle-based'.
    """
    for _ in range(n_iter):
        try:
            mesh.smooth_mesh(method=method, acknowledge_change=True)
        except Exception:
            break
    return mesh


def post_process_routine(
    mesh: CHILmesh,
    can_remove_edges: bool = True,
    n_smooth_iter: int = 3,
    max_outer_iter: int = 5,
    max_inner_iter: int = 5,
) -> CHILmesh:
    """Iteratively improve quad-mesh quality.

    Args:
        mesh: Quad (or mixed) CHILmesh from tri2quad.
        can_remove_edges: Allow boundary-quad collapse.
        n_smooth_iter: Passes for two_part_smoother.
        max_outer_iter: Outer loop cap.
        max_inner_iter: Inner loop cap (doublet + QVM).
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
    return mesh
