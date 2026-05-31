# Feature Specification: Skeletonization Rename — Unify layers / skeleton / medial axis

**Feature Branch**: `daily-maintenance`
**Created**: 2026-05-31
**Status**: Spec (rename pass pending; `compute_mesh_structure` API already landed in spec 004)
**Input**: Issue #55: "medial axis, layers, and skeleton are all similar but different. i think skeleton for a mesh should be defined/derived in the same way it is for an image. we need to create a unifying function that computes all three of these and the user can designate which with an input."
**Cross-ref**: `specs/004-unified-mesh-structure/spec.md` (API already implemented; this spec covers the rename sweep and remaining research tasks)

---

## Motivation

The codebase uses "skeleton" and "skeletonization" as a loose alias for "layers" — the CHILmesh concentric ring decomposition. This conflation is inaccurate: a mesh skeleton in the image-processing sense (ridge of the distance transform / thinning) is a distinct concept from layering. The medial axis (locus of inscribed-circle centres) is a third concept. All three are similar but not the same, and mixing the terms makes it harder to reason about which structure the algorithm uses and why.

**Spec 004** already delivered:
- `compute_mesh_structure(domain, kind=)` — the unifying entrypoint.
- `kind="layers"` — returns a deep-copied `LayerState` (CHILmesh layers, innermost→outermost).
- `kind="medial_axis"` — returns a `MeshStructure` with interior Voronoi nodes/edges.
- `kind="skeleton"` — raises `NotImplementedError` (concept still being scoped).

This spec covers the remaining work: **purging the stale "skeletonization" terminology** from docstrings and internal helpers, and **scoping the skeleton research** so a future session can implement it correctly.

---

## Acceptance Criteria

1. **No false synonyms**: every reference to "skeletonization" or "skeleton" in QuADMesh source that *actually means layers* is renamed to "layers" or "layer decomposition".
2. **`_skeletonize` method handle in validator** — the `hasattr(mesh, "_skeletonize")` branch is either updated to `_compute_layers` (matching CHILmesh's real API) or removed if it is dead code.
3. **Docstring precision**: `_layer_state.py` module docstring uses "layer decomposition", not "skeletonization". `tri2quad.py` function docstring at line 670 uses "layer-priority" not "skeleton layers".
4. **`kind="skeleton"` error message** in `mesh_structure.py` references this spec (#55) so the operator knows where the open question lives.
5. **All existing tests pass** after the rename: `pytest tests/` green (no functional change — rename is documentation-level only for now).
6. **Skeleton scoping note** committed in this spec (see Research section below).

---

## Migration Path — Rename Touchpoints

All files requiring terminology fixes (as of 2026-05-31):

| File | Line(s) | Current text | Replacement |
|---|---|---|---|
| `src/quadmesh/_layer_state.py` | 1 | `"CHILmesh skeletonization layers"` | `"CHILmesh layer decomposition"` |
| `src/quadmesh/mesh_structure.py` | 7 | `"skeletonization layer"` | `"layer decomposition"` |
| `src/quadmesh/tri2quad.py` | 670, 698, 790, 879, 945, 978 | `"skeleton layers"` | `"layers"` or `"layer decomposition"` (context-dependent) |
| `src/quadmesh/validation/validator.py` | 118–133 | `_skeletonize` | audit: if CHILmesh uses `_compute_layers`, update; if dead code, remove |
| `tests/test_layer_state.py` | 5 | `"CHILmesh skeletonization"` | `"CHILmesh layer decomposition"` |
| `tests/test_mesh_structure.py` | 5 | `"skeleton (not yet implemented"` | keep — still accurate; update to reference #55 |

### Validator `_skeletonize` — required audit

The `validator.py` snippet at lines 118–133 checks `hasattr(mesh, "_skeletonize")` and calls `mesh._skeletonize()`. This is CHILmesh's internal method name. Before renaming, confirm the CHILmesh API:

```
python -c "import chilmesh; import inspect; print([m for m in dir(chilmesh.CHILmesh) if 'layer' in m.lower() or 'skelet' in m.lower()])"
```

If CHILmesh exposes `_skeletonize`, keep the name (it is their API, not ours to rename). If CHILmesh renamed it, update the call site. Either way, add a comment clarifying this calls into CHILmesh's layer-computation method.

---

## Research Section — Skeleton Definition (concept scoping)

The operator wants the image-style skeleton. Key distinctions:

| Concept | Definition | Input | Output |
|---|---|---|---|
| **Layers** | CHILmesh concentric ring decomposition (innermost to outermost edges + vertices) | CHILmesh mesh object | `LayerState` (OE/IE/OV/IV lists per ring) |
| **Medial axis** | Locus of centres of maximal inscribed circles; continuous geometry-defined structure | Domain polygon | Node/edge graph (interior Voronoi ridges of densified boundary) — **shipped** |
| **Skeleton (image-style)** | Ridge of the distance-transform of the rasterized domain; found by morphological thinning | Domain polygon + pixel resolution `h` | Set of 1-pixel-wide curves, mapped back to mesh coordinates |

### Skeleton implementation plan (future session)

1. Rasterize domain polygon at pixel size ≈ `median_edge_length / 4`.
2. Compute 2D Euclidean distance transform (`scipy.ndimage.distance_transform_edt`).
3. Apply morphological thinning (`skimage.morphology.skeletonize` on the binary domain mask).
4. Extract skeleton pixels, convert to `(x, y)` coordinates.
5. Return `MeshStructure(kind="skeleton", nodes=..., edges=...)` — same shape as `medial_axis`.

**Open question for operator**: should the skeleton resolution follow the mesh's local `h(x,y)` size function, or use a fixed pixel scale? Fixed scale is simpler; `h`-adaptive requires a varying-resolution rasterization.

### Skeleton-vs-layers comparison harness (future session)

The operator also wants to quantify differences between structure-guided and layer-guided tri selection in `identify_edges`. Plan:
1. Run `identify_edges` normally (layer-driven).
2. For the same domain, derive an ordering from the skeleton / medial axis (by projecting each triangle's centroid onto the nearest skeleton branch and sorting by distance from domain centre).
3. Compare: which tris are matched, in which order, and what is the resulting quad quality?

Prior art may exist in `domattioli/madmeshing` — check before implementing.

---

## Test Plan

| Test | File | Trigger |
|---|---|---|
| Docstring-only tests (none) | — | Rename is doc-only; no new functional tests needed |
| Existing: `test_mesh_structure.py::test_skeleton_not_implemented` | `tests/test_mesh_structure.py` | Must still pass after error message update |
| Existing: `test_layer_state.py` (all) | `tests/test_layer_state.py` | Must pass — no functional change |
| Future: `test_skeleton` | `tests/test_mesh_structure.py` | Add when `kind="skeleton"` is implemented |
| Future: `test_skeleton_vs_layers_comparison` | `tests/test_mesh_structure.py` | Add when comparison harness is built |

Run: `pytest tests/test_mesh_structure.py tests/test_layer_state.py -v`

---

## Success Criteria

- **SC-001**: `grep -rn "skeletonization" src/` returns no results that refer to "layers" (only legitimate references to CHILmesh's internal method name are allowed).
- **SC-002**: `pytest tests/` green.
- **SC-003**: `kind="skeleton"` error message references `#55` / this spec.
- **SC-004**: The `_skeletonize` validator branch is documented with a comment explaining it calls CHILmesh's layer-computation API.

## Assumptions

- CHILmesh's method `_skeletonize` is their canonical name for layer computation and should not be renamed here.
- The rename is docstring/comment level only for this increment — no functional behaviour changes.
- Skeleton implementation (image-style) is deferred pending operator input on pixel resolution strategy.
