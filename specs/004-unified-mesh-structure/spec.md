# Feature Specification: Unified mesh-structure entrypoint (layers / skeleton / medial axis)

**Feature Branch**: `daily-maintenance`
**Created**: 2026-05-29 · **Last Amended**: 2026-05-30 (medial_axis implemented)
**Status**: Active (layers + medial_axis shipped; skeleton reserved-research)
**Input**: User description (QuADMesh #55): "medial axis, layers, and skeleton are all similar but different. i think skeleton for a mesh should be defined/derived in the same way it is for an image. we need to create a unifying function that computes all three of these and the user can designate which with an input. id also like to investigate the differences that the skeleton has in comparison to the layer when trying to identify tris to convert to quads."

## Context

Today the codebase conflates three terms. "Layers" and "skeleton" / "skeletonization" are used as synonyms in docstrings (`_layer_state.py:1`, `tri2quad.py:670`), and there is **no** medial-axis implementation. Layers themselves are not computed here at all — `chilmesh` computes them and QuADMesh only *reads* `domain.layers` (`OE`/`IE`/`OV`/`IV` keyed lists) and `chilmesh.layer_paths.paths_on_outer_vertices`.

The three concepts are genuinely distinct:

| Concept | Definition | Status |
|---|---|---|
| **layers** | chilmesh concentric outer/inner edge+vertex ring decomposition (skeletonization layers); drives the faithful tri2quad sweep | Implemented (chilmesh-backed; read-only here) |
| **skeleton** | image-style skeleton (e.g. thinning / distance-transform ridge of the rasterized domain) — operator's ask: "defined/derived in the same way it is for an image" | Not implemented — research (concept still being scoped by operator) |
| **medial axis** | locus of centers of maximal inscribed circles of the domain polygon (continuous, geometry-defined) | **Implemented** (2026-05-30) — interior Voronoi ridges of densified boundary samples; deterministic. `_medial_axis.py` |

## User Scenarios & Testing

### User Story 1 — Single selectable entrypoint (Priority: P1)

A caller wants one function to ask for a named mesh structure rather than reaching into `domain.layers` directly or guessing which private helper computes what.

**Why P1**: Removes the layers/skeleton conflation at the API boundary and gives a stable seam to add skeleton/medial_axis later without touching call sites.
**Independent Test**: `compute_mesh_structure(domain)` returns a `MeshStructure` whose `kind == "layers"` and whose `layers` is an independent (deep-copied) `LayerState` with `n_layers > 0`.
**Acceptance**:
1. **Given** a CHILmesh domain with precomputed layers, **when** `compute_mesh_structure(domain)` is called (default), **then** it returns `MeshStructure(kind="layers", n_layers=N, layers=<LayerState>)` with `N == domain.n_layers`.
2. **Given** the returned structure, **when** its `layers` snapshot is mutated, **then** `domain.layers` is unchanged (deep-copy guarantee inherited from `LayerState.from_mesh`).
3. **Given** an unknown `kind`, **when** the function is called, **then** it raises `ValueError` listing the valid kinds.

### User Story 2 — Medial axis as a graph (Priority: P2)

Medial axis is a precise, geometry-defined structure (unlike "skeleton", whose definition the operator is still scoping). It is computed deterministically and returned as a node/edge graph.

**Why P2**: Gives the operator a concrete medial-axis to compare against layers, without waiting on the still-open skeleton concept.
**Independent Test**: `compute_mesh_structure(domain, kind="medial_axis")` returns `MeshStructure(kind="medial_axis", nodes=(M,2), edges=(K,2))` with M,K > 0, all edge indices valid, all nodes interior to the domain, and identical output across repeated calls.
**Acceptance**:
1. **Given** a domain, **when** `kind="medial_axis"`, **then** a graph (`nodes`, `edges`) is returned; every node lies inside the domain polygon; two calls are bit-identical (deterministic).

### User Story 3 — Reserved-but-named skeleton mode (Priority: P3)

Skeleton is named, discoverable, and fails loudly rather than silently aliasing to "layers" or "medial_axis".

**Why P3**: The operator explicitly wants to *investigate* what a mesh "skeleton" should be ("i think ... defined/derived in the same way it is for an image"); silently returning another structure would hide that open question.
**Independent Test**: `compute_mesh_structure(domain, kind="skeleton")` raises `NotImplementedError` referencing this spec / #55.
**Acceptance**:
1. **Given** `kind="skeleton"`, **when** called, **then** `NotImplementedError` is raised with a message pointing at #55 / this spec.

## Requirements

### Functional Requirements
- **FR-001**: Provide `compute_mesh_structure(domain, kind="layers") -> MeshStructure` in `src/quadmesh/mesh_structure.py`, exported from `quadmesh`.
- **FR-002**: `kind` MUST be validated against `VALID_KINDS = ("layers", "skeleton", "medial_axis")`; invalid → `ValueError`.
- **FR-003**: `kind="layers"` MUST return a deep-copied `LayerState` (reuse `LayerState.from_mesh`) so callers cannot accidentally mutate `domain.layers`.
- **FR-004**: `kind="skeleton"` MUST raise `NotImplementedError` (no silent fallback to another kind).
- **FR-005**: The change is ADDITIVE — `MeshStructure` gains optional `nodes`/`edges` fields (default `None`); no existing field, behavior, or `compute_mesh_structure` signature changes.
- **FR-006**: `kind="medial_axis"` MUST return `MeshStructure` with `nodes (M,2) float64` and `edges (K,2) int64` populated from the interior Voronoi medial-axis graph. Computation MUST be deterministic and every returned node MUST be interior to the domain. Implemented in `_medial_axis.py` (`medial_axis_graph`). Defaults: boundary resample spacing = median boundary edge length; no branch pruning (`prune_tol=None`). Both are parameters for future tuning (the spec's open "branch-pruning tolerance" question).

### Non-Goals (this increment)
- Implementing skeleton computation (concept still being scoped by operator).
- Aggressive medial-axis branch pruning (raw interior Voronoi graph shipped; pruning param reserved).
- Changing how the faithful sweep consumes layers.

## Decomposition / follow-ups (research, decompose before building)

The operator's full ask is partly research. Remaining follow-ups (NOT filed automatically — surfaced for operator triage to avoid issue spam):

1. ~~**medial_axis(domain)**~~ — **DONE 2026-05-30**: Voronoi of densified boundary samples, interior ridges kept. Open question deferred: branch-pruning tolerance (`prune_tol` param exists, default off).
2. **skeleton(domain)** — define the image-style skeleton: rasterize domain at a chosen `h`, distance-transform + thinning, map ridge back to mesh coordinates. Open questions for operator: pixel resolution vs `h(x,y)`; what "skeleton" should mean for a mesh vs the now-shipped medial axis.
3. **skeleton-vs-layer (and now medial-axis-vs-layer) comparison harness** — the operator's investigative ask: on the canonical fixtures, quantify how structure-guided tri-selection differs from layer-guided selection in `identify_edges` (cross-ref `tri2quad.py:_layer_priority`). Possible prior art in `domattioli/madmeshing` ("not sure the work was saved").

## Validation
- `pytest tests/test_mesh_structure.py` (layers path + medial_axis graph/interior/determinism + skeleton NotImplementedError + ValueError) — 8 tests.
- Full `pytest tests/` stays green (additive change; faithful-sweep tests pre-existing slow/hang, unrelated).

## Cross-refs
- `src/quadmesh/_layer_state.py` — `LayerState` (the layers payload).
- `src/quadmesh/identify_edges.py` — layer consumption + `paths_on_outer_vertices`.
- QuADMesh #55 (this feature), #17/#18 (size-function-aware merge selection, downstream of structure choice).
