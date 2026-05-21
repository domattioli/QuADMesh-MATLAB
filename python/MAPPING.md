# MATLAB -> Python Map

Port status. v0.4.

| MATLAB (`02_QuADMESH_Library/`) | Python (`quadmesh/`) | Status |
|---|---|---|
| `00_Main/Main.m` | `cli.py` + `pipeline.run_pipeline` | done |
| `01_Create_Quad_Domain/createQuadDomain.m` | `create_quad_domain` | done (polygon mode) |
| `01_Create_Quad_Domain/drawSubdomain.m` | - | skip (GUI) |
| `02_Tri2Quad_Routine/Tri2QuadRoutine.m` | `tri2quad.tri2quad_routine` | done |
| `02_Tri2Quad_Routine/identifyEdgesFun.m` | - | skip (superseded by v2) |
| `02_Tri2Quad_Routine/identifyEdgesFun_v2.m` | `identify_edges.identify_edges_in_layer` | done |
| `02_Tri2Quad_Routine/mergeTrianglesFun.m` | `_topology.merge_tri_pairs` | done |
| `02_Tri2Quad_Routine/CCWEdgesAroundVertsFun.m` | `_topology.ccw_edges_around_vert` | done |
| `02_Tri2Quad_Routine/plotQuadProgress.m` | - | skip (plot) |
| `03_Layer_Paths/PathsOnOV.m` | `chilmesh.layer_paths.paths_on_outer_vertices` | done via chilmesh |
| `03_Layer_Paths/pathRewind.m` | inline in `identify_edges` | done |
| `04_Remove_Triangles/removeTrianglesFun.m` | `_tri_removal.route_leftover_tri` | partial (conservative default; aggressive=True opt-in; bisection bug fixed) |
| `04_Remove_Triangles/edgeInsertion.m` | `_tri_removal.edge_insertion` | partial (cases 1/2 without iLayer-1 retriangulation; design doc lands v0.4 — `specs/001-matlab-to-python-port/case-2-design.md`) |
| `04_Remove_Triangles/edgeBisection.m` | `_tri_removal.edge_bisection` | partial (case 2) |
| `04_Remove_Triangles/edgeRemoval.m` | `_tri_removal.edge_removal` | done |
| `05_Post-Process_Routine/PostProcessRoutine.m` | `post_process.post_process_routine` | done |
| `05_Post-Process_Routine/plotQualityProgress.m` | `quality_report.compute_quality_stats` + `format_quality_report` | done (stats; plot skipped) |
| `06_Cleanup_Boundary_Quads/CleanupBoundaryQuads_v2.m` | `cleanup_boundary_quads` | done (collapse MATLAB-aligned: side verts -> corner; shift: Python-only) |
| `06_Cleanup_Boundary_Quads/TruncateBoundaryQuads.m` | - | skip (legacy) |
| `07_Doublet_Collapse/DoubletCollapse.m` | `doublet_collapse.doublet_collapse` | done |
| `08_Quad_Vertex_Merge/QuadVertexMerge.m` | - | skip (legacy) |
| `08_Quad_Vertex_Merge/QuadVertexMerge_v2.m` | `quad_vertex_merge.quad_vertex_merge` | done |
| `10_Remove_Unused_Vertices/RemoveUnusedVertices.m` | `remove_unused.remove_unused_vertices` | done |
| `11_FEM_Smoothing/FEMSmooth.m` | `post_process.two_part_smoother` | done |
| `11_FEM_Smoothing/MCSmooth.m` | `post_process.two_part_smoother` | done |
| `11_FEM_Smoothing/twoPartSmoother.m` | `post_process.two_part_smoother` | done v0.3 (bug fixed: angle-based method; default FEM; sub-domain deferred) |
| `11_FEM_Smoothing/extdom_edges2.m` | `chilmesh.boundary_edges()` | done via chilmesh |
| `99_In_Progress/*` | - | skip (drafts) |

## chilmesh reuse

| quadmesh uses | from |
|---|---|
| `CHILmesh` | `chilmesh.CHILmesh` |
| `read_from_fort14` / `write_to_fort14` | classmethod / method |
| `boundary_edges` / `boundary_node_indices` | mesh method |
| `edge2vert` / `edge2elem` / `elem2edge` | mesh method |
| `get_vertex_edges` / `get_vertex_elements` | mesh method |
| `adjacencies` (Edge2Vert, Edge2Elem, Vert2Edge) | property |
| `layers` (OE/IE/OV/IV/bEdgeIDs) | property |
| `n_elems` / `n_verts` / `n_edges` / `n_layers` | property |
| `connectivity_list` / `points` | property |
| `paths_on_outer_vertices` | `chilmesh.layer_paths` |
| `smooth_mesh(method)` | method |
| `signed_area` / `elem_quality` | method |

## collapse alignment note

MATLAB `subroutineCleanupBoundaryQuads`:
- corner = middleVertID, stays at its position.
- side1 = `verts[(ci-1)%4]`, side2 = `verts[(ci+1)%4]` -- both remapped to corner everywhere.
- Bad quad deleted. Two vertices removed per pass.

Prev Python (v0.1): moved corner to opposing, remapped opposing->corner. Different topology, one vertex removed.
Current Python (v0.2+): MATLAB-aligned.

## v0.3 bug fixes

- `two_part_smoother`: `method="angle"` -> `method="angle-based"` -- smoother was silently broken (ValueError caught by bare `except Exception`). Discovered angle-based is ~42s/pass; defaulted to FEM-only.

## v0.4 bug fixes

- `edge_insertion`: `domain.edge2vert(int(e)).astype(int).tolist()` returned `[[u,v]]` (shape `(1,2)`) which failed the `u, v = ...` unpack. Fixed to `.ravel().astype(int).tolist()`. Hidden until T4.6 aggressive-path tests landed.

## deferred v0.5

1. Aggressive tri routing -- `edgeInsertion` case 2 iLayer-1 retriangulation. v0.4 design doc lands in `specs/001-matlab-to-python-port/case-2-design.md`; implementation deferred to v0.5.
2. `two_part_smoother` sub-domain split -- needs `CHILmesh.submesh()` public API (chilmesh#138).
3. ADMESH library (`01_ADMESH_Library/`).
4. Aggressive leftover-tri routing -- blocked by chilmesh#132.
5. Element-count parity with MATLAB on canonical fixtures -- v0.4 framework lands with Python-baseline goldens; MATLAB golden capture deferred (requires MATLAB session).
6. Incremental layer-update API in chilmesh -- needed by case-2 retriangulation, see case-2-design.md "chilmesh API gaps". Filed as low-priority once design is reviewed.

## chilmesh gaps (low-priority issues filed)

- chilmesh#132: `MutableMesh.merge_elements` stub -- quadmesh aggressive path needs this.
- chilmesh#133: Public `ccw_edges_around_vert` helper -- remove duplication in `_topology.py`.
- chilmesh#134: `CHILmesh(compute_adjacencies=True)` independent of `compute_layers`.
- chilmesh#138: `CHILmesh.submesh(elem_ids)` public API -- needed for two_part_smoother sub-domain split (boundary vs interior layers).
- chilmesh#139: `angle_based_smoother` performance -- ~42s/pass on 2417-elem mesh; currently disabled as default. Port uses FEM smoother only.
