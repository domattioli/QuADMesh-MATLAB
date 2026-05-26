# Session 008 — python-optimized: 3× tri2quad speedup

**Date:** 2026-05-26
**Branch:** `python-optimized`
**PR:** [#45](https://github.com/domattioli/QuADMESH/pull/45) (draft) — head `87b48f4`
**Model:** claude-opus-4-7

## What changed

Speckit-style optimization pass on the faithful tri2quad path. Algorithm unchanged; replaced three O(n²) numpy patterns surfaced by cProfile on WNAT_Hagen.

| File | Change |
|---|---|
| `src/quadmesh/_tri_removal.py` | `WorkingMesh.add_point` no longer `np.vstack` per call — buffers coords in `_extra_pts` list, tracks `_n_pts` counter. New API: `n_pts` property, `get_extra_point(idx)`, `flush_points_to_domain(domain)`. Removed redundant `domain.points` vstack in `edge_bisection` + `edge_insertion` (new vertex coords never read back during sweep). |
| `src/quadmesh/tri2quad.py` | `_faithful_per_layer` calls `work.flush_points_to_domain(domain)` once before final `points_out` sync. |
| `src/quadmesh/identify_edges.py` | Vectorized `identify_edges_in_layer`: flagged-mask via numpy boolean indexing on `all_e2v`; corner-count rotation via `np.bincount` over layer conn (was per-vertex `get_vertex_elements()`); ov/iv membership via boolean mask arrays; `b_edge_set` → boolean array. Sub-mesh built from `domain.points` view (no `.copy()`). |
| `tests/test_tri_removal.py` | Updated 4 assertions to new WorkingMesh API (`n_pts`, `get_extra_point`, `flush_points_to_domain`). |

Commit `87b48f4`.

## Profile — root cause (cProfile, WNAT_Hagen, 53.6s baseline)

| Hotspot | calls | cum time | cause |
|---|---|---|---|
| `numpy.vstack` | 111,086 | 17.9s | per-point grow in `add_point` + 2 redundant `domain.points` vstacks |
| `CHILmesh.__init__` | 31 | 16.7s | per-layer sub-mesh build (`_build_adjacencies` 14s) |
| `identify_edges_in_layer` | 30 | 19.6s | sub-mesh + Python membership loops |
| `degree_remaining` (chilmesh) | 2.8M | 2.9s | path-walk in `layer_paths` — chilmesh-side, untouched |

## Verification

| | time | quads |
|---|---|---|
| before | 53.6s | — |
| after | **17.5s** | 76,954 |

**3.06× speedup.** Tests: **310/310 pass** (full suite, exit 0).

Estimate vs actual: pessimistic 18% / optimistic 38% predicted → **67% actual** (vectorized identify_edges saved more than modeled).

## Not done (further headroom)

- `CHILmesh.__init__` ×31 (~13.5s) still dominant — sub-mesh rebuilt per layer. Can't avoid without chilmesh API for sub-mesh-from-parent-adjacencies or reuse. `ccw_edges_around_vert` needs the sub-mesh object.
- `degree_remaining` 2.8M calls — chilmesh-internal path-walk; needs upstream fix.
- Compiled-language rewrite (C++/Rust via pybind11/PyO3) of `_faithful_per_layer`: est. another 3–8× (workload is pointer-chasing graph traversal). Numba = easiest next step, stays Python.

## What comes next

1. Review + merge PR #45.
2. Consider chilmesh issue: sub-mesh construction reusing parent adjacencies (would cut remaining ~13.5s).
3. Decide if compiled inner-loop worth it vs current 17.5s.

## Files to review on resume

- `src/quadmesh/_tri_removal.py` — `WorkingMesh` (buffered points), `edge_bisection`/`edge_insertion` (vstack removed).
- `src/quadmesh/identify_edges.py` — vectorized blocks (~line 97 flagged-mask, ~line 122 corner counts, ~line 148 keep_mask).
- `src/quadmesh/tri2quad.py` — `_faithful_per_layer` flush call (~line 866).

## chilmesh issues status

No new chilmesh issues filed. Candidate: sub-mesh-from-parent (reuse adjacencies) to kill per-layer `_build_adjacencies` cost.
