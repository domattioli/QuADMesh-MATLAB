# Session Handoff — QuADMESH · daily-maintenance_ccd9e10 · 2026-05-31

**Task:** #28 — prototype 4-tri fan truss smoother for size-function-respecting quad smoothing.
**Phase:** research + prototype implementation.
**Progress:** prototype complete, stable, documented on #28 and PR #65. Key finding: truss smoother requires proper `fh(x,y)` to beat FEM; without it, it's structural stabilizer only.
**Branch:** daily-maintenance → PR #65 (draft, open)
**Duration:** ~2h
**Outcome:** working prototype, architectural finding documented, issue left open.

## Pre-flight

- branch_policy_conflict: no — daily-maintenance per CLAUDE.md
- mcp_scope_gap: no
- haiku_subagent_dispatch: yes — all code writes dispatched per CLAUDE.md rule

## What worked (top 3, with evidence)

1. **4-tri fan structural concept correct.** Quad braced by only 4 perimeter springs = 4-bar linkage (mechanism). Adding centroid splits → shear-rigid. Implemented cleanly, imports OK, 87 tests pass.
2. **Iterative debugging via live Block-O plots.** Each failure (global h0, bidirectional overshoot, inversion) diagnosed from quality metrics + signed-area counts before re-dispatching Haiku fix. Loop: run → measure → diagnose → dispatch → rerun, ~4 iterations total.
3. **Issue #28 comment + PR #65 comment** document findings verbatim with numbers. Future sessions won't re-derive.

## What didn't (top 3, with evidence)

1. **Global h0 = median catastrophic on variable-density mesh.** Block-O edge-length ratio 44×; uniform h0 → 460/2349 inverted quads. Required local-h0 per-node fix.
2. **Bidirectional springs → overshoot.** `Fbar = (L0 - Lbar) / Lbar` with `deltat=0.2` sends nodes across neighbors. Switched to repulsive-only: `max(L0 - Lbar, 0) / Lbar`. Should have started repulsive-only (distmesh convention).
3. **Inversion guard insufficient alone.** Guard catches first-time inversions within a step but not pre-existing ones from topo cleanup or cascading reverts. Repulsive-only forces make the guard largely redundant but it stays as a safety net.

## Architectural finding (critical)

Truss smoother needs `fh(x,y)` threaded from ADMESH through pipeline to deliver #28's hypothesis gain. Without it, FEM dominates and truss adds nothing to mean quality on uniform meshes. On variable-density meshes, best it can do is stabilize compressed zones before FEM runs. This is an ADMESH-to-QuADMESH API gap — no path to close it without pipeline changes.

## Open state

- PR #65 (draft): `truss_smoother` proto, needs `fh` integration before production
- Issue #28: not closed — next step is threading `fh(x,y)` through `run_pipeline`
- Issue #63 (QuADMESH): V=6 vs V=8 valence lattice mismatch — unrelated but same session context
- Pre-existing: `test_tri_removal.py::test_route_dispatches_edge_bisection_when_interior` IndexError still open

## Files touched this session

- `src/quadmesh/post_process.py` — `truss_smoother()` added (commits d37e1d5, ccd9e10)
- `src/quadmesh/pipeline.py` — `run_pipeline()` wired `truss_smooth`, `truss_fh` params

## Recurring frictions

1. Full `pytest tests/` times out (faithful-test hang) — same as prior sessions. Test-timeout markers still not applied.
2. CHILmesh constructor requires `np.ndarray` not list for connectivity — implicit contract, not documented.
3. Haiku agent reported "fix already applied" (centroid L0 fix) when it wasn't — agent read stale file state. Required manual verification of implementation before trusting subagent summary.
