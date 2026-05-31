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


def truss_smoother(
    mesh: CHILmesh,
    fh=None,
    h0: float = None,
    n_iter: int = 200,
    deltat: float = 0.2,
    dptol: float = 1e-3,
) -> CHILmesh:
    """Spring-force mesh smoother via quad-to-4tri fan + frozen edge set.

    Splits each quad into 4 triangles sharing a centroid, extracts edge topology,
    then applies spring forces (distmesh2d-style) with frozen edges. Interior
    nodes move; boundary nodes pinned. Returns mesh with original quad vertices
    repositioned, centroids discarded.
    """
    import numpy as np

    p = mesh.points[:, :2].copy()
    n_orig = len(p)

    # Get quads from connectivity; build 4-tri fan per quad with centroid
    _conn = np.asarray(mesh.connectivity_list)
    quads = [elem for elem in _conn if len(elem) == 4]
    if not quads:
        return mesh  # No quads; return unchanged

    quads = np.asarray(quads)
    centroids = p[quads].mean(axis=1)  # (n_quads, 2)
    n_quads = len(quads)

    # Build p_ext: original points + centroids
    p_ext = np.vstack([p, centroids])

    # Compute h0 if not provided: median of quad edge lengths
    if h0 is None:
        quad_edges = np.concatenate([
            quads[:, [0, 1]], quads[:, [1, 2]],
            quads[:, [2, 3]], quads[:, [3, 0]]
        ])
        edge_vecs = p[quad_edges[:, 1]] - p[quad_edges[:, 0]]
        edge_lens = np.linalg.norm(edge_vecs, axis=1)
        h0 = np.median(edge_lens)

    # Extract edges from 4-tri fan: for each quad, add 8 edges
    # (4 perimeter + 4 centroid-to-corner)
    bar = []
    for i, quad in enumerate(quads):
        v0, v1, v2, v3 = quad
        c_idx = n_orig + i
        # Perimeter edges
        bar.extend([[v0, v1], [v1, v2], [v2, v3], [v3, v0]])
        # Centroid edges
        bar.extend([[c_idx, v0], [c_idx, v1], [c_idx, v2], [c_idx, v3]])

    bar = np.asarray(bar)

    # Get boundary nodes
    edge_verts = mesh.edge2vert(mesh.boundary_edges())
    boundary_nodes = np.unique(edge_verts.flatten()).astype(int)

    # Spring-force loop
    for iteration in range(n_iter):
        # Compute current edge vectors and lengths
        dL = p_ext[bar[:, 1]] - p_ext[bar[:, 0]]
        Lbar = np.linalg.norm(dL, axis=1)

        # Compute target lengths
        if fh is not None:
            midpoints = (p_ext[bar[:, 0]] + p_ext[bar[:, 1]]) / 2
            L0 = fh(midpoints)
        else:
            L0 = np.full_like(Lbar, h0)

        # Compute edge forces (bidirectional, no clipping)
        denom = np.maximum(Lbar, 1e-10)
        Fbar = (L0 - Lbar) / denom
        F_edge = Fbar[:, None] * dL / np.maximum(Lbar[:, None], 1e-10)

        # Accumulate forces per node
        F = np.zeros_like(p_ext)
        np.add.at(F, bar[:, 0], -F_edge)
        np.add.at(F, bar[:, 1], F_edge)

        # Zero boundary forces
        F[boundary_nodes] = 0

        # Update positions
        movement = deltat * F
        p_ext = p_ext + movement

        # Convergence check
        max_move = np.max(np.linalg.norm(movement, axis=1))
        if max_move / h0 < dptol:
            break

    # Extract original quad vertices; discard centroids
    new_p = mesh.points.copy()
    new_p[:n_orig, :2] = p_ext[:n_orig]

    mesh.points[:, :2] = new_p[:n_orig, :2]
    return mesh


def fem_smoother(
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

    mesh = remove_unused_vertices(mesh)

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
    truss_smooth: bool = False,
    truss_fh=None,
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
        truss_smooth: If True, apply truss_smoother before fem_smoother.
        truss_fh: Callable or None. Target edge length function for truss_smoother.
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

    if truss_smooth:
        mesh = truss_smoother(mesh, fh=truss_fh)

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
