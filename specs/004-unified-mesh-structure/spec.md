# Feature Specification: Unified mesh-structure entrypoint (layers / skeleton / medial axis)

**Feature Branch**: `daily-maintenance`
**Created**: 2026-05-29 · **Last Amended**: 2026-05-29 (initial draft)
**Status**: Active (layers mode shipped; skeleton + medial_axis reserved)
**Input**: User description (QuADMesh #55): "medial axis, layers, and skeleton are all similar but different. i think skeleton for a mesh should be defined/derived in the same way it is for an image. we need to create a unifying function that computes all three of these and the user can designate which with an input. id also like to investigate the differences that the skeleton has in comparison to the layer when trying to identify tris to convert to quads."

## Context

Today the codebase conflates three terms. "Layers" and "skeleton" / "skeletonization" are used as synonyms in docstrings (`_layer_state.py:1`, `tri2quad.py:670`), and there is **no** medial-axis implementation. Layers themselves are not computed here at all — `chilmesh` computes them and QuADMesh only *reads* `domain.layers` (`OE`/`IE`/`OV`/`IV` keyed lists) and `chilmesh.layer_paths.paths_on_outer_vertices`.

The three concepts are genuinely distinct:

| Concept | Definition | Status |
|---|---|---|
| **layers** | chilmesh concentric outer/inner edge+vertex ring decomposition (skeletonization layers); drives the faithful tri2quad sweep | Implemented (chilmesh-backed; read-only here) |
| **skeleton** | image-style skeleton (e.g. thinning / distance-transform ridge of the rasterized domain) — operator's ask: "defined/derived in the same way it is for an image" | Not implemented — research |
| **medial axis** | locus of centers of maximal inscribed circles of the domain polygon (continuous, geometry-defined) | Not implemented — research |

## User Scenarios & Testing

### User Story 1 — Single selectable entrypoint (Priority: P1)

A caller wants one function to ask for a named mesh structure rather than reaching into `domain.layers` directly or guessing which private helper computes what.

**Why P1**: Removes the layers/skeleton conflation at the API boundary and gives a stable seam to add skeleton/medial_axis later without touching call sites.
**Independent Test**: `compute_mesh_structure(domain)` returns a `MeshStructure` whose `kind == "layers"` and whose `layers` is an independent (deep-copied) `LayerState` with `n_layers > 0`.
**Acceptance**:
1. **Given** a CHILmesh domain with precomputed layers, **when** `compute_mesh_structure(domain)` is called (default), **then** it returns `MeshStructure(kind="layers", n_layers=N, layers=<LayerState>)` with `N == domain.n_layers`.
2. **Given** the returned structure, **when** its `layers` snapshot is mutated, **then** `domain.layers` is unchanged (deep-copy guarantee inherited from `LayerState.from_mesh`).
3. **Given** an unknown `kind`, **when** the function is called, **then** it raises `ValueError` listing the valid kinds.

### User Story 2 — Reserved-but-named research modes (Priority: P2)

Skeleton and medial axis are named, discoverable, and fail loudly rather than silently aliasing to "layers".

**Why P2**: Prevents a future caller assuming `kind="skeleton"` already differs from `kind="layers"`. The operator explicitly wants to *investigate the difference*; silently returning layers would hide it.
**Independent Test**: `compute_mesh_structure(domain, kind="skeleton")` and `kind="medial_axis"` each raise `NotImplementedError` referencing this spec / #55.
**Acceptance**:
1. **Given** `kind="skeleton"` or `kind="medial_axis"`, **when** called, **then** `NotImplementedError` is raised with a message pointing at #55 / this spec.

## Requirements

### Functional Requirements
- **FR-001**: Provide `compute_mesh_structure(domain, kind="layers") -> MeshStructure` in `src/quadmesh/mesh_structure.py`, exported from `quadmesh`.
- **FR-002**: `kind` MUST be validated against `VALID_KINDS = ("layers", "skeleton", "medial_axis")`; invalid → `ValueError`.
- **FR-003**: `kind="layers"` MUST return a deep-copied `LayerState` (reuse `LayerState.from_mesh`) so callers cannot accidentally mutate `domain.layers`.
- **FR-004**: `kind="skeleton"` and `kind="medial_axis"` MUST raise `NotImplementedError` (no silent fallback to layers).
- **FR-005**: The change is ADDITIVE — no existing module behavior or signature changes.

### Non-Goals (this increment)
- Implementing skeleton or medial-axis computation.
- Changing how the faithful sweep consumes layers.

## Decomposition / follow-ups (research, decompose before building)

The operator's full ask is partly research. Suggested follow-up issues (NOT filed automatically — surfaced for operator triage to avoid issue spam):

1. **skeleton(domain)** — define the image-style skeleton: rasterize domain at a chosen `h`, distance-transform + thinning, map ridge back to mesh coordinates. Open question: pixel resolution vs `h(x,y)`; determinism.
2. **medial_axis(domain)** — exact/approximate medial axis of the boundary PSLG (Voronoi of boundary samples, prune spurious branches). Open question: branch-pruning tolerance.
3. **skeleton-vs-layer comparison harness** — the operator's investigative ask: on the canonical fixtures, quantify how skeleton-guided tri-selection differs from layer-guided selection in `identify_edges` (cross-ref `tri2quad.py:_layer_priority`). Possible prior art in `domattioli/madmeshing` ("not sure the work was saved").

## Validation
- `pytest tests/test_mesh_structure.py` (layers path + both NotImplementedError modes + ValueError).
- Full `pytest tests/` stays green (additive change).

## Cross-refs
- `src/quadmesh/_layer_state.py` — `LayerState` (the layers payload).
- `src/quadmesh/identify_edges.py` — layer consumption + `paths_on_outer_vertices`.
- QuADMesh #55 (this feature), #17/#18 (size-function-aware merge selection, downstream of structure choice).
