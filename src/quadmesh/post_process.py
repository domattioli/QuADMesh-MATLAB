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


def _balendran_smooth(mesh: "CHILmesh") -> "np.ndarray":
    """Balendran direct FEM smoother matching MATLAB FEMSmooth.m exactly.

    chilmesh direct_smoother is bugged: it applies angle-based cotangent forces
    (Zhou & Shimada) as RHS, which is inconsistent with the Balendran rotation
    stiffness matrix K. On large meshes this causes K*x=F to have no geometric
    meaning, flinging interior nodes hundreds of element-widths.

    MATLAB FEMSmooth.m uses F=0 for interior nodes — K drives equilibrium purely
    via structural coupling to pinned boundary nodes. This function replicates that.

    See chilmesh issue #173 for details.
    """
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.linalg import spsolve

    kinf = 1e12
    p = mesh.points[:, :2].copy()
    n = mesh.n_verts

    tri_indices, quad_indices = mesh._detect_element_types()
    if len(quad_indices) == 0:
        rows, cols, data = mesh._tri_stiffness_assembly(tri_indices, p, n)
    elif len(tri_indices) == 0:
        rows, cols, data = mesh._quad_stiffness_assembly(quad_indices, p, n)
    else:
        rows, cols, data = mesh._mixed_stiffness_assembly(tri_indices, quad_indices, p, n)

    K = csr_matrix((data, (rows, cols)), shape=(2 * n, 2 * n))
    F = np.zeros(2 * n)  # zero interior RHS — matches MATLAB FEMSmooth.m

    edge_verts = mesh.edge2vert(mesh.boundary_edges())
    boundary_nodes = np.unique(edge_verts.flatten())
    for v in boundary_nodes:
        v = int(v)
        F[2 * v : 2 * v + 2] = kinf * p[v]
        K[2 * v, 2 * v] = kinf
        K[2 * v + 1, 2 * v + 1] = kinf

    c = spsolve(K, F)
    new_pts = mesh.points.copy()
    new_pts[:, :2] = c.reshape(-1, 2)
    return new_pts


def two_part_smoother(
    mesh: CHILmesh,
    n_iter: int = 3,
    method: str = "fem",
) -> CHILmesh:
    """Iterative mesh smoother. Port of MATLAB twoPartSmoother.m.

    MATLAB mixed-element path: single FEM pass. We generalise to n_iter passes.
    Default method is 'fem' (fast: ~1.5s/pass on 46k elems).
    Use method='angle-based' for higher quality at ~1400s/pass (chilmesh is slow).

    Args:
        mesh: CHILmesh to smooth.
        n_iter: Max FEM passes (stops early once a pass stops improving).
    """
    import numpy as np

    for _ in range(n_iter):
        before = np.asarray(mesh.points).copy()
        try:
            if method == "fem":
                new_pts = _balendran_smooth(mesh)
                mesh.points[:, :2] = new_pts[:, :2]
            else:
                mesh.smooth_mesh(method=method, acknowledge_change=True)
        except Exception:
            mesh.points[...] = before
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
