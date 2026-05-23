# Feature Specification: Port MATLAB QuADMESH+ to Python

**Feature Branch**: `001-matlab-to-python-port`
**Created**: 2026-05-20 · **Last Amended**: 2026-05-23 (thesis cross-ref; matching pivot; quad-pure; recombination ops — see Q5–Q7)
**Status**: Draft (faithful-port realignment in progress — `faithful-port-plan.md` / `faithful-port-tasks.md`)
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
- **FR-002**: Tri-pair merging MUST follow QuADMESH+ as defined in the thesis (`docs/Mattioli_Thesis.pdf`, Ch 4) — a **layered, two-stage heuristic matching**, worked innermost→outward. Its per-layer pairing primitive is the **every-other-edge sweep** of `identifyEdgesFun_v2` (walk outer-vertex paths, flag every-other interior edge, merge tris sharing each flagged edge); the sweep is **governed by the Ch 4 heuristics**: interior layers match IE_L before OE_L; the boundary layer matches OE_L first; T1/T2 selection by eligible-neighbor counts + the documented tiebreaker ladders; all intra-layer matchings precede inter-layer L↔L−1. The sweep and the heuristics are one method at two levels (NOT alternatives) — see Clarification Q5.
  - **FR-002a (interim)**: A coarse global interior-saturating matching MAY back `tri2quad(..., method="matching")` as a fast fallback for very large meshes, but the **faithful path (`method="faithful"`) is the target default**. The fallback is explicitly non-faithful and MUST NOT be the shipped default once the faithful path passes parity.
- **FR-003**: Outer-vertex paths MUST come from `chilmesh.layer_paths.paths_on_outer_vertices` — no re-implementation.
- **FR-004**: Leftover tris (one of the pair already merged, or odd-out) MUST be routed by boundary-edge count: 0 → edge_insertion; 1 → edge_bisection or edge_removal; 2–3 → edge_insertion or edge_removal. **Preference order MUST be: (1) add a boundary point / edge-insertion → quad (preferred — "added resolution is better than diminished", thesis p70); (2) edge-swap / vertex-duplication when two leftover tris share a vertex; (3) edge-collapse / removal only as a fallback.** Boundary-edge collapse (squeeze) is the *least*-preferred op, not the default.
- **FR-005**: Output CHILmesh MUST have CCW elements and no zero-area elements.
- **FR-006**: `post_process(mesh, can_remove_edges, n_smooth_iter)` MUST run, in order: doublet_collapse → quad_vertex_merge → cleanup_boundary_quads → remove_unused_vertices → smoothing.
- **FR-007**: Smoothing MUST delegate to `chilmesh.CHILmesh.smooth_mesh('fem'|'angle')` — no re-implementation of FEM stiffness assembly.
- **FR-008**: `doublet_collapse(mesh)` MUST remove every interior valence-2 vertex whose two adjacent elems are quads, merging the pair into a single quad.
- **FR-009**: `quad_vertex_merge(mesh)` MUST remove every quad whose diagonal vertices are both valence-3, rewiring adjacent quads.
- **FR-010**: `cleanup_boundary_quads(mesh, can_remove_edges)` MUST identify boundary quads with two adjacent boundary edges and either collapse them (if `can_remove_edges`) or shift the interior vertex.
- **FR-011**: `remove_unused_vertices(mesh)` MUST drop verts with valence 0 and renumber connectivity.
- **FR-012**: `create_quad_domain(mesh, polygon=None)` MUST flag tris by their vertices' inclusion in `polygon` (None → all tris).
- **FR-013**: `run_pipeline(mesh, polygon=None, can_remove_edges=True, n_smooth_iter=3)` MUST chain create_quad_domain → tri2quad → post_process and return the final quad CHILmesh. (`n_smooth_iter` default 3 = fast FEM; raise for higher quality — MATLAB Main used 100. Threading a `method=` selector — FR-002a — is deferred to the M2 faithful path.)
- **FR-014**: All indexing MUST be 0-based. `-1` sentinel for "no neighbour" in edge2elem matches chilmesh convention.
- **FR-015**: CLI `quadmesh INPUT.14 -o OUT.14 [--no-post-process] [--polygon poly.csv]` MUST drive the pipeline end-to-end.
- **FR-016**: `edge_swap` MUST recombine two triangles sharing **one vertex** into an edge-sharing pair (reconnect the diagonal) so they can merge into a quad (thesis Fig 3.2). Used for the isolated-tri "pair" fixup (Q5) and boundary remaining-tri removal.
- **FR-017**: `vertex_duplication` MUST split a triangle fan by duplicating a shared vertex so the tris pair off into quads (thesis Fig 3.3).
- **FR-018**: `edge_flip` MUST flip a shared diagonal, and a `walk_isolated_tri` driver MUST chain flips along a walkable path to move an isolated triangle adjacent to a partner, then merge (thesis Fig 3.6, 4.4). Used in the boundary layer to improve walkability before matching (thesis §4.2.1).

### Key Entities

- **Tri Domain**: input CHILmesh, triangular or padded mixed.
- **WorkingMesh**: scratch state during tri2quad — accumulated quad rows + points list.
- **LayerEdgeSelection**: per-layer output of `identify_edges` — sub-mesh, removed edge IDs, paths, boundary edges/verts.
- **Quad Mesh**: output CHILmesh, mostly quads, optionally some residual padded tris.
- **Terminology** (D1): "leftover tri" (spec) = "remaining / isolated triangle" (thesis) = "boundary tri" (code) — same concept: a triangle unmatched after pairing. Used interchangeably; prefer "leftover tri" in spec.

## Success Criteria

- **SC-001**: `tri2quad(Test_Case_1)` produces a **quad-pure** CHILmesh (zero residual triangles — interior *and* boundary); zero zero-area elems; zero orphan verts; zero self-intersecting (bowtie) quads; conforming (no edge in >2 elems). NB per Q6: the thesis heuristic may leave ≤1 boundary tri (cleared by point insertion); quad-pure is not guaranteed when no perfect matching exists (odd boundary-vertex count). The current implementation achieves zero on all canonical fixtures.
- **SC-002**: `tri2quad(Block_O)` produces a **quad-pure** CHILmesh (same guarantees as SC-001).
- **SC-003**: `post_process(tri2quad(Test_Case_1))` mean skew quality ≥ 0.5 (target after faithful port: ≥ 0.81, vs thesis greedy 0.8095); max angle ≤ 175°.
- **SC-004**: `pytest` green on all 4 user stories' acceptance tests (smoke + property tests).
- **SC-005**: `quadmesh --help` shows usage. `quadmesh Test_Case_1.14 -o /tmp/out.14` writes a fort.14 that re-loads cleanly.
- **SC-006**: No re-implementation of: PathsOnOV, FEM smoother, angle-based smoother, mesh layer computation, boundary edge detection, edge2vert/edge2elem/elem2edge. All sourced from chilmesh.
- **SC-007** (faithfulness parity): The `method="faithful"` pipeline MUST match MATLAB QuADMESH+ ground truth within **±2% element count and ±0.02 mean quality** on Test_Case_1/2/3 + Block_O, and per-layer matched pairs MUST reproduce the golden selection (as index-independent vertex-pair sets). Ground truth comes from a captured oracle — extracted `.mat`, an Octave run, or hand-derived golden on the smallest fixtures — committed under `python/tests/golden/` (see faithful-port-plan §0/Phase 0). Until an oracle exists, parity is provisional (property tests only, per Q1).

## Clarifications

**Q1** (Equivalence vs MATLAB): MATLAB binary not available in CI. Verify via property tests + visual inspection on canonical fixtures. Element counts may differ by a few %; topology validity is the hard requirement.

**Q2** (Edge-insertion case-2 retriangulation): MATLAB performs a re-triangulation of iLayer-1 to absorb the new vertex. Deferred (was "v0.2"); now tracked in `faithful-port-tasks.md` M3/T026.

**Q3** (Mesh size scaling): Block_O (~2400 elems) is the largest canonical fixture. Performance not a v0.1 hard requirement, but pipeline should complete in <60s on Block_O.

**Q4** (CleanupBoundaryQuads modes): MATLAB has two modes (collapse vs shift). Collapse (when `can_remove_edges=True`) implemented; shift mode deferred (was "v0.2"), tracked in `faithful-port-tasks.md`.

**Q5** (Matching pivot + thesis cross-reference, 2026-05-23): The shipped `tri2quad` deviated from FR-002's faithful sweep to a coarse global interior-saturating **matching** (zero interior tris, quad-dominant), then quad-pure via boundary squeeze/drop. Cross-referencing the source thesis (`docs/Mattioli_Thesis.pdf`, Ch 3–5) clarified that QuADMESH+ is fundamentally **heuristic matching realized as the every-other-edge layer sweep governed by the Ch 4 IE/OE + T1/T2 rules** — sweep and heuristics are the same method at two levels, not alternatives. Resolution: the every-other-edge sweep + Ch 4 heuristics is the faithful target (FR-002); the coarse matching is retained only as an explicit fast fallback (FR-002a). Full plan: `faithful-port-plan.md` (§0 records all corrections CR-1…CR-8); tasks: `faithful-port-tasks.md`.

**Q6** (Quad-pure goal + achievability, 2026-05-23): Residual *interior* triangles are a conversion **bug** (a properly-implemented tri2quad eliminates them) — pinned by `test_no_interior_tris.py`. Residual *boundary* tris are cleared to reach quad-pure output (SC-001/002). However, perfect (fully-quad) matching does not always exist — typically when the boundary has an odd vertex count (thesis Fig 3.7) — so the faithful algorithm may legitimately leave ≤1 boundary tri, cleared by **adding a boundary point** (FR-004 preference). Our always-zero result is more aggressive than the thesis and is treated as a bonus, not the parity criterion.

**Q7** (Missing recombination ops, 2026-05-23): The original spec omitted Edge Swap, Vertex Duplication, and Edge Flip — core QuADMESH+ operations for isolated/remaining triangles and boundary walkability (thesis Figs 3.2, 3.3, 3.6, 4.4). Added as FR-016/017/018.

## Assumptions

- chilmesh `>=0.4.0` is installed and provides: `read_from_fort14`, `write_to_fort14`, `layers`, `boundary_edges`, `boundary_node_indices`, `edge2vert`, `edge2elem`, `elem2edge`, `get_vertex_edges`, `get_vertex_elements`, `n_layers`, `connectivity_list`, `points`, `paths_on_outer_vertices`, `smooth_mesh`, `interior_angles`, `elem_quality`, `copy`.
- Test .14 fixtures live in `03_CHILMesh_Test_Cases/01_.14_Files/`.
- MATLAB UI (uigetdir, listdlg, drawSubdomain) is replaced by function arguments; no GUI parity required.
- "Interactive plot progress" replaced by optional logging/return-trace; matplotlib plots are convenience, not core.
- Post-process loop convergence (MATLAB has nested `while quadsStillBeingRemoved`) is bounded by an iteration cap (default 10) plus the natural convergence check.
