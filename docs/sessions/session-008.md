# Session 008 — faithful tri2quad case-2 opposite-tri split (#25)

**Date:** 2026-05-27
**Branch:** `daily-issue-fixing`
**PR:** [#47](https://github.com/domattioli/QuADMESH/pull/47) (rolling, draft) — head `0c955c5`
**Model:** claude-opus-4-7

## What changed

Ported MATLAB `edgeBisection.m:47-79` — the **opposite-tri split** #25 names as "currently missing in `_tri_removal.py`".

| File | Change |
|---|---|
| `src/quadmesh/_tri_removal.py` | New `_split_opposing_tri`: re-triangulates the iLayer-1 neighbour at the bisection midpoint (apex→midpoint split). New `_ccw_tri` helper. Wired into `route_leftover_tri` case-2 branch. **Also fixed** a latent infinite loop in `edge_bisection` (unbounded conn-rotation spun forever on a reverse-oriented `v_b→v_a` edge — exactly what case-2 triggers); replaced with a bounded, direction-robust slot. |
| `tests/test_tri_removal_faithful.py` | New (spec T023): opposite-tri split partitions the neighbour, mesh-boundary no-op, route-level wiring. |

Commit `0c955c5`.

## Key decision — no scipy dependency

MATLAB uses `delaunayTriangulation([opp_conn, np_id])` + a degenerate-tri guard. Because `np_id` is the midpoint of the edge **shared** between the bisected tri and its iLayer-1 neighbour, it lies *on* that neighbour's edge — so the only valid 2-tri split is apex→midpoint, which is exactly what the Delaunay yields once its collinear degenerate tri is dropped. Built directly; no scipy.

## Verification

`pytest tests/`: **87 passed** (3 new this session). Baseline (pre-change, tri_removal + no_interior subset) was 29 passed; full suite green with no regressions. session-007's pre-existing TC1 parity failure is already resolved (PR #47 / #32 fix).

## Deferred (M3 — keeps #25 OPEN)

The full quad-pure faithful path still needs:
- **T026** — `edge_insertion` case-2 iLayer-1 retriangulation (the `case-2-design.md` fan walk).
- **T028** — per-layer adjacency rebuild after mutation (`domain.rebuild_adjacencies()`), plus LayerState (OE/IE/OV/IV) bookkeeping that MATLAB updates in `edgeBisection.m:80-96`.
- **T029** — wire `route_leftover_tri` (the faithful router) into the live M2 sweep boundary stage; today it is only exercised by unit tests.

`tests/test_no_interior_tris.py::test_tri2quad_faithful_path` stays expected-WIP until T026/T028/T029 land.

## Files to review on resume

- `src/quadmesh/_tri_removal.py` — `_split_opposing_tri` (~line 108), `edge_bisection` slot fix (~line 89), `route_leftover_tri` case-2 branch (~line 240).
- `tests/test_tri_removal_faithful.py` — the case-2 contract.
- `specs/001-matlab-to-python-port/faithful-port-tasks.md` — T024-T030 remaining.

## What comes next

1. T026/T028/T029 to make `method="faithful"` quad-pure (closes #25).
2. #46 onion hero domain — blocked on ADMESH-Domains#93 `.14` generation + the faithful path above.
3. Smoother root-cause fix tracked in CHILmesh #174 (#35 advanced, kept open).

## Environment note

Fresh container test interpreter lacked numpy/scipy/chilmesh/pytest (recurring; see session-007). Built `uv venv .venv && uv pip install numpy scipy pytest -e /home/user/CHILmesh -e .` to run the gate (`.venv/` gitignored). Filed DomI #148 (`ensure-test-venv` skill request) to remove this per-session tax. DomI contract plugins were not installed at container start (marketplace add failed, #114) → ran `/introspect` + pin-check inline from the local DomI clone.

## chilmesh issues status

No new chilmesh issues this session (#174 already tracks the FEM-smoother root cause).
