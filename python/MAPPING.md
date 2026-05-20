# MATLAB → Python File Map

Tracks port status. v0.1 ships green tests for entries marked ✓.

| MATLAB source (`02_QuADMESH_Library/`) | Python module (`quadmesh/`) | Status |
|---|---|---|
| `00_Main/Main.m` | `cli.py` + `pipeline.run_pipeline` | ✓ |
| `01_Create_Quad_Domain/createQuadDomain.m` | `create_quad_domain.create_quad_domain` | ✓ polygon mode |
| `01_Create_Quad_Domain/drawSubdomain.m` | — | ✗ GUI, not ported |
| `02_Tri2Quad_Routine/Tri2QuadRoutine.m` | `tri2quad.tri2quad_routine` | ✓ |
| `02_Tri2Quad_Routine/identifyEdgesFun.m` | — | ✗ superseded by v2 |
| `02_Tri2Quad_Routine/identifyEdgesFun_v2.m` | `identify_edges.identify_edges_in_layer` | ✓ |
| `02_Tri2Quad_Routine/mergeTrianglesFun.m` | `_topology.merge_tri_pairs` | ✓ |
| `02_Tri2Quad_Routine/CCWEdgesAroundVertsFun.m` | `_topology.ccw_edges_around_vert` | ✓ |
| `02_Tri2Quad_Routine/plotQuadProgress.m` | — | ✗ plotting helper, not ported |
| `03_Layer_Paths/PathsOnOV.m` | `chilmesh.layer_paths.paths_on_outer_vertices` | ✓ via chilmesh |
| `03_Layer_Paths/pathRewind.m` | inline in `identify_edges` | ✓ |
| `04_Remove_Triangles/removeTrianglesFun.m` | `_tri_removal.route_leftover_tri` | ⚠ defined; opt-in via `aggressive=True`; leftover-tris stay as padded tris by default |
| `04_Remove_Triangles/edgeInsertion.m` | `_tri_removal.edge_insertion` | ⚠ case 1/2 partial; iLayer-1 retriangulation deferred |
| `04_Remove_Triangles/edgeBisection.m` | `_tri_removal.edge_bisection` | ⚠ case 2 partial |
| `04_Remove_Triangles/edgeRemoval.m` | `_tri_removal.edge_removal` | ✓ |
| `05_Post-Process_Routine/PostProcessRoutine.m` | `post_process.post_process_routine` | ✓ |
| `05_Post-Process_Routine/plotQualityProgress.m` | — | ✗ plotting helper |
| `06_Cleanup_Boundary_Quads/CleanupBoundaryQuads_v2.m` | `cleanup_boundary_quads.cleanup_boundary_quads` | ⚠ collapse mode only; shift mode v0.2 |
| `06_Cleanup_Boundary_Quads/TruncateBoundaryQuads.m` | — | ✗ legacy, superseded |
| `07_Doublet_Collapse/DoubletCollapse.m` | `doublet_collapse.doublet_collapse` | ✓ |
| `08_Quad_Vertex_Merge/QuadVertexMerge.m` | — | ✗ legacy, superseded |
| `08_Quad_Vertex_Merge/QuadVertexMerge_v2.m` | `quad_vertex_merge.quad_vertex_merge` | ✓ |
| `10_Remove_Unused_Vertices/RemoveUnusedVertices.m` | `remove_unused.remove_unused_vertices` | ✓ |
| `11_FEM_Smoothing/FEMSmooth.m` | wrapped via `chilmesh.CHILmesh.smooth_mesh('fem')` | ✓ via chilmesh |
| `11_FEM_Smoothing/MCSmooth.m` | wrapped via `chilmesh.CHILmesh.smooth_mesh('angle')` | ✓ via chilmesh |
| `11_FEM_Smoothing/twoPartSmoother.m` | — | ✗ hybrid; deferred |
| `11_FEM_Smoothing/extdom_edges2.m` | wrapped via `chilmesh.boundary_edges()` | ✓ via chilmesh |
| `99_In_Progress/*` | — | ✗ drafts, out of scope |

## Status legend

- ✓ ported, tested.
- ⚠ ported, behaviour matches MATLAB on canonical fixtures but some rare paths are simplified.
- ✗ not ported (out of scope per constitution).

## chilmesh symbols reused

| Used by quadmesh | Source |
|---|---|
| `CHILmesh` class | `chilmesh.CHILmesh` |
| `read_from_fort14` / `write_to_fort14` | classmethod / method on `CHILmesh` |
| `boundary_edges` / `boundary_node_indices` | mesh method |
| `edge2vert` / `edge2elem` / `elem2edge` | mesh method |
| `get_vertex_edges` / `get_vertex_elements` | mesh method |
| `adjacencies` (Edge2Vert, Edge2Elem, Vert2Edge) | mesh property |
| `layers` (OE/IE/OV/IV/bEdgeIDs) | mesh property |
| `n_elems` / `n_verts` / `n_edges` / `n_layers` | mesh property |
| `connectivity_list` / `points` | mesh property |
| `paths_on_outer_vertices` | `chilmesh.layer_paths` |
| `smooth_mesh` (fem + angle) | mesh method |
| `signed_area` / `elem_quality` / `interior_angles` | mesh method |
| `copy` / `_ensure_ccw_orientation` (implicit via `__init__`) | mesh method |

## Deferred items (v0.2)

1. Aggressive leftover-tri routing (edge insertion / bisection with proper layer-state mutation).
2. `CleanupBoundaryQuads` shift mode (move corner vert when `can_remove_edges=False`).
3. `twoPartSmoother` hybrid smoothing.
4. ADMESH library port (whole `01_ADMESH_Library/` tree).
5. MATLAB-faithful element-count match on canonical fixtures (current Python diverges by a few %).
