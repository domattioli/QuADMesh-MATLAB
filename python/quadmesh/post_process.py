"""Post-process orchestrator. Port of MATLAB PostProcessRoutine.m + twoPartSmoother.m.

MAT twoPartSmoother applied MCSmooth to boundary layers (1-3) and FEMSmooth to interior
elements in alternation.  We approximate by applying angle + FEM smooth to the full mesh
in alternation (chilmesh sub-domain smooth not yet supported).

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


def two_part_smoother(mesh: CHILmesh, n_iter: int = 50) -> CHILmesh:
    """Interleaved angle + FEM smoother. Port of MATLAB twoPartSmoother.m.

    Each pass: angle smooth then FEM smooth over full mesh.
    MATLAB split across boundary/interior sub-meshes; deferred to v0.3
    pending chilmesh sub-domain smooth support.

    Args:
        mesh: CHILmesh to smooth.
        n_iter: Number of alternating passes.
    """
    for _ in range(n_iter):
        try:
            mesh.smooth_mesh(method="angle", acknowledge_change=True)
        except Exception:
            break
        try:
            mesh.smooth_mesh(method="fem", acknowledge_change=True)
        except Exception:
            break
    return mesh


def post_process_routine(
    mesh: CHILmesh,
    can_remove_edges: bool = True,
    n_smooth_iter: int = 50,
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
