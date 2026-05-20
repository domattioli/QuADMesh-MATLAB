"""Post-process orchestrator. Port of MATLAB PostProcessRoutine.m.

Pipeline (MATLAB order):
    repeat until no quads removed (cap: max_outer_iter):
        repeat until no quads removed (cap: max_inner_iter):
            doublet_collapse → quad_vertex_merge
        cleanup_boundary_quads (collapse mode)
    remove_unused_vertices
    FEM smooth → angle-based smooth (chilmesh wraps these)
"""

from __future__ import annotations

from chilmesh import CHILmesh

from .cleanup_boundary_quads import cleanup_boundary_quads
from .doublet_collapse import doublet_collapse
from .quad_vertex_merge import quad_vertex_merge
from .remove_unused import remove_unused_vertices


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
        n_smooth_iter: Iterations for angle-based smoother.
        max_outer_iter: Outer loop cap (cleanup + inner loop).
        max_inner_iter: Inner loop cap (doublet + QVM).

    Returns:
        Smoothed CHILmesh.
    """
    outer = 0
    n_elems_prev = mesh.n_elems
    while outer < max_outer_iter:
        outer += 1
        # Inner loop: doublet + QVM until stable.
        inner = 0
        while inner < max_inner_iter:
            inner += 1
            n_before = mesh.n_elems
            mesh = doublet_collapse(mesh)
            mesh = quad_vertex_merge(mesh)
            if mesh.n_elems >= n_before:
                break

        # Boundary cleanup if pure quad mesh.
        if getattr(mesh, "type", None) != "Mixed-Element":
            mesh = cleanup_boundary_quads(mesh, can_remove_edges=can_remove_edges)

        if mesh.n_elems >= n_elems_prev:
            break
        n_elems_prev = mesh.n_elems

    mesh = remove_unused_vertices(mesh)

    # Smoothing — delegate to chilmesh.
    try:
        mesh.smooth_mesh(method="fem", acknowledge_change=True)
    except Exception:  # pragma: no cover — fall back to angle-based smoother
        pass
    try:
        mesh.smooth_mesh(method="angle", acknowledge_change=True)
    except Exception:  # pragma: no cover
        pass

    return mesh
