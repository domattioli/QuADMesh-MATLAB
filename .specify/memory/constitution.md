# QuADMESH+ Constitution

Project: Python port of MATLAB QuADMESH+ tri→quad mesh generator.

## Core Principles

### I. Faithful Port

Algorithmic behaviour matches MATLAB source on canonical test cases (Test_Case_1, Block_O, Mixed_Test). Deviations require justification in commit + spec.

### II. Depend On chilmesh, No Reinvention

Mesh primitives (CHILmesh class, layers, boundary, adjacencies, paths_on_outer_vertices, MutableMesh, smoothers) come from `chilmesh`. Quadmesh adds only tri→quad logic. Touch a wheel, document the new spoke in the spec.

### III. Test-First Per Module

Each MATLAB routine ports with a paired pytest. Tests load real .14 fixtures from `03_CHILMesh_Test_Cases/01_.14_Files`. Acceptance: quad mesh produced; element-quality stats sane; no orphan verts; no zero-area elems.

### IV. Layered Implementation

Bottom-up dependency order. Leaf helpers (CCW edges, merge pair) first. Then identify_edges + tri-removal sub-ops. Then tri2quad sweep. Then post-process (doublet, QVM, boundary cleanup). Smoothing reuses chilmesh.

### V. Index 0-Based Throughout

MATLAB uses 1-based; Python port stays 0-based, matching chilmesh. Sentinel for "no neighbour" in edge2elem = -1 (chilmesh convention).

### VI. Caveman Docs

Docstrings + READMEs terse. Drop articles + filler. Fragments OK. Algorithmic invariants explicit.

## Scope

In scope:
- `00_Main/Main.m` → CLI + `run_pipeline`.
- `01_Create_Quad_Domain/` → polygon-mask subset selector (no GUI).
- `02_Tri2Quad_Routine/` → core sweep.
- `03_Layer_Paths/` → already in chilmesh.layer_paths.
- `04_Remove_Triangles/` → edge_insertion / bisection / removal.
- `05_Post-Process_Routine/`.
- `06_Cleanup_Boundary_Quads/` → CleanupBoundaryQuads_v2 only.
- `07_Doublet_Collapse/`.
- `08_Quad_Vertex_Merge/` → v2 only.
- `10_Remove_Unused_Vertices/`.
- `11_FEM_Smoothing/` → wrap chilmesh `direct_smoother` + `angle_based_smoother`.

Out of scope:
- `01_ADMESH_Library/` — distinct project; not ported here.
- `99_In_Progress/` — drafts.
- `.asv` autosave files.
- MATLAB UI calls (uigetdir, listdlg, questdlg, drawSubdomain interactive draw).
- `04_CHIL_Supporting_Functions/saveMesh.m` legacy file IO (chilmesh handles fort.14).

## Dependencies

- `chilmesh >= 0.4.0` (the Python port of CHILmesh.m).
- `numpy >= 1.24`, `scipy >= 1.10`, optional `matplotlib >= 3.6`.

## Quality Gates

- `pytest` green on Test_Case_1, Test_Case_2, Block_O.
- Output quad mesh: all elems CCW, no zero-area, vert count ≤ tri count + boundary buffer.
- README/CHILmesh future-work items filed as issues on `domattioli/CHILmesh`.

## Governance

Spec lives in `specs/<NNN>-<short-name>/`. Spec drives implementation; deviations land in `spec.md` clarifications first.

**Version**: 0.1.0 | **Ratified**: 2026-05-20 | **Last Amended**: 2026-05-20
