# QuADMesh introspection — 2026-05-31

## Issues addressed

### #61 — DomI sync
- Updated `.domi-pin` SHA from `c832cf7` (2026-05-30) to `e0bba05` (current DomI HEAD as of 2026-05-31).
- Committed: `chore: sync DomI@e0bba05e9ec495bde2790738ad93b17d0e33c20f`

### #55 — Skeletonization rename spec
- Created `specs/055-skeletonization-rename/spec.md` documenting: motivation (layers ≠ skeleton ≠ medial axis), acceptance criteria, rename touchpoints with a file-by-file migration table, skeleton implementation plan (distance-transform thinning, future session), skeleton-vs-layers comparison harness plan.
- Applied all safe docstring/comment renames in:
  - `src/quadmesh/_layer_state.py` — "skeletonization layers" → "layer decomposition"
  - `src/quadmesh/mesh_structure.py` — docstring + `NotImplementedError` message updated to reference `#55` / new spec
  - `src/quadmesh/tri2quad.py` — six "skeleton layers" occurrences renamed to "layer decomposition"
  - `src/quadmesh/validation/validator.py` — added clarifying comment that `_skeletonize` is CHILmesh's API (do not rename)
  - `tests/test_layer_state.py` — module docstring updated
- Committed: `docs: add spec for skeletonization rename (#55)`
- Note: `kind="skeleton"` remains `NotImplementedError` — skeleton definition is still being scoped by operator. The spec documents what image-style skeleton would require and the open question (pixel resolution vs h(x,y)).

### Pre-existing test failures fixed
- `test_tri_removal.py::test_route_dispatches_edge_bisection_when_interior` — `_split_opposing_tri` called `_ccw_tri` with a buffered midpoint index that exceeded `domain.points` bounds (point not yet flushed). Fixed by passing `WorkingMesh` to `_split_opposing_tri` so it can extend the points array with buffered extras before calling `_ccw_tri`.
- `test_tri_removal_faithful.py::test_working_mesh_add_point` — test asserted `work.points.shape[0] == 4` after `add_point`, but `add_point` buffers to `_extra_pts` by design (flush-on-demand). Fixed test to match actual API semantics.
- Both failures were pre-existing (not introduced by this session).

## Pains / hard stops

- Spec 004 (`specs/004-unified-mesh-structure/spec.md`) already covered most of #55's functional API (`compute_mesh_structure`, medial axis, skeleton placeholder). The new spec 055 complements it by covering the rename sweep and the still-open skeleton research scope — it does not duplicate 004.
- `validator.py` uses `hasattr(mesh, "_skeletonize")` which calls CHILmesh's internal layer-computation method. Verified this is CHILmesh's own API and should NOT be renamed on our side. Added a comment to make this clear for future sessions.
- Issue #46 (onion domain) skipped — requires a `.14` mesh file from ADMESH-Domains, which depends on an external cross-repo issue (domattioli/ADMESH-Domains#93). Not actionable here.
- Issue #20 (label triage) skipped — requires operator decisions on each label row (promote / keep / migrate). Not autonomous code work.
- Issues #9, #17, #18, #21, #26, #28, #38 are all `status: brainstorming` or `request: research` — no code shipping warranted.
- `git push` failed (HTTP 400 / auth); pushed via `mcp__github__push_files`.

## Skipped (with reason)

| Issue | Reason |
|---|---|
| #46 — onion domain | Depends on external ADMESH-Domains issue for .14 mesh file; not available |
| #20 — label triage | Requires operator decisions per table row; not autonomous |
| #9 — quadmeshing algorithms survey | `status: brainstorming`, research-only |
| #17, #18, #26, #28, #38 | `status: brainstorming`, research-only |
| #21 — size function drift | `status: ready` but investigative/research — no code target defined |
