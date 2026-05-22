# Feature Specification: Port MATLAB QuADMESH+ to Python

**Feature Branch**: `001-matlab-to-python-port`
**Created**: 2026-05-20
**Status**: Draft
**Input**: User description: "Port MATLAB QuADMESH+ routine to Python. Use chilmesh Python package as dependency. Cross-reference, do not reinvent."

## User Scenarios & Testing

### User Story 1 — Convert tri mesh to quad mesh from Python (Priority: P1)

User has tri mesh in `fort.14` format. Calls `quadmesh.tri2quad(mesh)`. Gets a CHILmesh of quads back. No MATLAB, no GUI.

**Why P1**: Core deliverable. Without this, the port has no value.

**Independent Test**: Load `Test_Case_1.14` via chilmesh; pass to `quadmesh.tri2quad`. Output mesh: ≥80% quads by elem count; no orphan verts; all elems CCW; signed area >0.

**Acceptance**:
1. **Given** Test_Case_1 tri mesh (~2400 tris, 7 layers), **when** `tri2quad(mesh)` runs, **then** output is CHILmesh, mostly quads, finite n_elems > 0, n_verts > 0, no all-zero connectivity rows.
2. **Given** Block_O tri mesh, **when** pipeline runs, **then** output mesh has ≥75% quads.
3. **Given** a tri mesh with mixed-element padding, **when** pipeline runs, **then** padding is preserved or properly converted.

---

### User Story 2 — Post-process improves quality (Priority: P1)

After tri2quad, user calls `quadmesh.post_process(mesh)` and sees mean quality improve. Doublet collapse + QVM + boundary cleanup + smoothing run in sequence.

**Why P1**: Raw tri2quad output has degenerate quads. Post-process is required for usable mesh.

**Independent Test**: Run `tri2quad` then `post_process` on Test_Case_1. Verify mean skew quality ≥ raw output's mean, no concave quads remain.

**Acceptance**:
1. **Given** raw quad mesh from tri2quad, **when** post_process runs, **then** valence-2 internal verts are removed (doublet collapse).
2. **Given** raw quad mesh, **when** QVM runs, **then** any quad whose diagonal verts are both valence-3 is removed and neighbours rewired.
3. **Given** post-processed mesh, **when** quality computed, **then** mean quality > 0.4 (typical: 0.6–0.8 for canonical fixtures).

---

### User Story 3 — Polygon-based domain selection (Priority: P2)

User wants to convert only a subset of triangles (e.g., the interior, not the boundary). Provides one or more polygons; vertices inside the polygon flag triangles for conversion.

**Why P2**: MATLAB Main allows three strategies (all / distance-to-shoreline / polygon). Polygon is the only programmatic one we port; rest are GUI-bound.

**Independent Test**: Pass an `(N,2)` polygon to `create_quad_domain(mesh, polygon)`. Returns reduced mesh of only flagged tris.

**Acceptance**:
1. **Given** a polygon containing 50% of mesh verts, **when** `create_quad_domain(mesh, polygon)` runs, **then** returned domain has ≤50% the elements of input.
2. **Given** `polygon=None`, **when** function runs, **then** returns full mesh (all-elements strategy).

---

### User Story 4 — CLI driver (Priority: P3)

User runs `quadmesh path/to/mesh.14 -o out.14 --post-process` from shell. Reads fort.14, runs pipeline, writes fort.14.

**Why P3**: Convenience; library API covers most use cases.

**Independent Test**: `quadmesh Test_Case_1.14 -o /tmp/out.14`. Output is loadable by `CHILmesh.read_from_fort14`.

**Acceptance**:
1. **Given** valid input path, **when** CLI runs, **then** output file exists and is loadable.

---

### Edge Cases

- Mesh with internal holes (donut topology): layers seed from both boundaries; tri2quad should handle multiple closed paths per layer.
- Pinch points (degree-3 boundary verts on outer ring): path decomposition handles multigraph; tri2quad should not crash.
- Single-layer mesh: `n_layers == 1`; sweep runs one iteration; all tris are on mesh boundary.
- Mixed-element input (padding col): preserve padding semantics through pipeline.
- Mesh too small to converge: graceful exit, return best-effort result with warning.
- Domain partially overlapping mesh boundary: tris removed from outside the domain in input must not appear in output.

## Requirements

### Functional Requirements

- **FR-001**: `tri2quad(mesh, can_remove_edges=bool, parent=None)` MUST return a CHILmesh.
- **FR-002**: Tri-pair merging MUST be performed via the algorithm in `identifyEdgesFun_v2`: per layer, walk outer-vertex paths, flag every-other interior edge, merge tris sharing each flagged edge.
- **FR-003**: Outer-vertex paths MUST come from `chilmesh.layer_paths.paths_on_outer_vertices` — no re-implementation.
- **FR-004**: Leftover tris (one of the pair already merged, or odd-out) MUST be routed by their boundary-edge count: 0 → edge_insertion; 1 → edge_bisection or edge_removal; 2–3 → edge_insertion or edge_removal.
- **FR-005**: Output CHILmesh MUST have CCW elements and no zero-area elements.
- **FR-006**: `post_process(mesh, can_remove_edges, n_smooth_iter)` MUST run, in order: doublet_collapse → quad_vertex_merge → cleanup_boundary_quads → remove_unused_vertices → smoothing.
- **FR-007**: Smoothing MUST delegate to `chilmesh.CHILmesh.smooth_mesh('fem'|'angle')` — no re-implementation of FEM stiffness assembly.
- **FR-008**: `doublet_collapse(mesh)` MUST remove every interior valence-2 vertex whose two adjacent elems are quads, merging the pair into a single quad.
- **FR-009**: `quad_vertex_merge(mesh)` MUST remove every quad whose diagonal vertices are both valence-3, rewiring adjacent quads.
- **FR-010**: `cleanup_boundary_quads(mesh, can_remove_edges)` MUST identify boundary quads with two adjacent boundary edges and either collapse them (if `can_remove_edges`) or shift the interior vertex.
- **FR-011**: `remove_unused_vertices(mesh)` MUST drop verts with valence 0 and renumber connectivity.
- **FR-012**: `create_quad_domain(mesh, polygon=None)` MUST flag tris by their vertices' inclusion in `polygon` (None → all tris).
- **FR-013**: `run_pipeline(mesh, polygon=None, can_remove_edges=True, n_smooth_iter=50)` MUST chain create_quad_domain → tri2quad → post_process and return the final quad CHILmesh.
- **FR-014**: All indexing MUST be 0-based. `-1` sentinel for "no neighbour" in edge2elem matches chilmesh convention.
- **FR-015**: CLI `quadmesh INPUT.14 -o OUT.14 [--no-post-process] [--polygon poly.csv]` MUST drive the pipeline end-to-end.

### Key Entities

- **Tri Domain**: input CHILmesh, triangular or padded mixed.
- **WorkingMesh**: scratch state during tri2quad — accumulated quad rows + points list.
- **LayerEdgeSelection**: per-layer output of `identify_edges` — sub-mesh, removed edge IDs, paths, boundary edges/verts.
- **Quad Mesh**: output CHILmesh, mostly quads, optionally some residual padded tris.

## Success Criteria

- **SC-001**: `tri2quad(Test_Case_1)` produces a CHILmesh with ≥80% quad elements; zero zero-area elems; zero orphan verts.
- **SC-002**: `tri2quad(Block_O)` produces a CHILmesh with ≥75% quad elements.
- **SC-003**: `post_process(tri2quad(Test_Case_1))` mean skew quality ≥ 0.5; max angle ≤ 175°.
- **SC-004**: `pytest` green on all 4 user stories' acceptance tests (smoke + property tests).
- **SC-005**: `quadmesh --help` shows usage. `quadmesh Test_Case_1.14 -o /tmp/out.14` writes a fort.14 that re-loads cleanly.
- **SC-006**: No re-implementation of: PathsOnOV, FEM smoother, angle-based smoother, mesh layer computation, boundary edge detection, edge2vert/edge2elem/elem2edge. All sourced from chilmesh.

## Clarifications

**Q1** (Equivalence vs MATLAB): MATLAB binary not available in CI. Verify via property tests + visual inspection on canonical fixtures. Element counts may differ by a few %; topology validity is the hard requirement.

**Q2** (Edge-insertion case-2 retriangulation): MATLAB performs a re-triangulation of iLayer-1 to absorb the new vertex. Port deferred to a v0.2 follow-up; v0.1 inserts the vertex into the outgoing quad and lets later layers absorb it as a regular vert.

**Q3** (Mesh size scaling): Block_O (~2400 elems) is the largest canonical fixture. Performance not a v0.1 hard requirement, but pipeline should complete in <60s on Block_O.

**Q4** (CleanupBoundaryQuads modes): MATLAB has two modes (collapse vs shift). v0.1 implements collapse (when `can_remove_edges=True`) only; shift mode is a v0.2 follow-up.

## Assumptions

- chilmesh `>=0.4.0` is installed and provides: `read_from_fort14`, `write_to_fort14`, `layers`, `boundary_edges`, `boundary_node_indices`, `edge2vert`, `edge2elem`, `elem2edge`, `get_vertex_edges`, `get_vertex_elements`, `n_layers`, `connectivity_list`, `points`, `paths_on_outer_vertices`, `smooth_mesh`, `interior_angles`, `elem_quality`, `copy`.
- Test .14 fixtures live in `03_CHILMesh_Test_Cases/01_.14_Files/`.
- MATLAB UI (uigetdir, listdlg, drawSubdomain) is replaced by function arguments; no GUI parity required.
- "Interactive plot progress" replaced by optional logging/return-trace; matplotlib plots are convenience, not core.
- Post-process loop convergence (MATLAB has nested `while quadsStillBeingRemoved`) is bounded by an iteration cap (default 10) plus the natural convergence check.
