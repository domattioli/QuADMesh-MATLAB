# Session 009 — LayerState working copy for faithful sweep (T012, #25)

**Date:** 2026-05-27
**Branch:** `daily-issue-fixing`
**PR:** [#47](https://github.com/domattioli/QuADMESH/pull/47) (rolling, draft) — head `c57e9fa`
**Model:** claude-opus-4-7

## What changed

Ported the missing **T012** prerequisite for the M3 faithful-path tasks: a mutable
per-layer OE/IE/OV/IV working copy. The faithful sweep mutates layer membership as
it clears leftover tris, but CHILmesh reads `mesh.layers` once and never re-derives
it — the sweep needs its own copy.

| File | Change |
|---|---|
| `src/quadmesh/_layer_state.py` | New `LayerState` dataclass. `from_mesh(domain)` deep-copy snapshot; `add` (idempotent union) / `remove` / `members` / `contains`. Mirrors MATLAB `Domain.Layers.{OE,IE,OV,IV}` (`edgeBisection.m:80-96`, `edgeInsertion.m:209-214`). Internal module — not added to public package surface. |
| `tests/test_layer_state.py` | New: from_mesh snapshot vs `test_case_1`, deep-copy independence, add/remove/members/contains, MATLAB replace pattern, bad-kind/bad-index guards (10 tests). |
| `specs/001-matlab-to-python-port/faithful-port-tasks.md` | T012 marked `[x]`. |

Commit `c57e9fa`.

## Verification

`pytest tests/`: **97 passed** (10 new). Baseline was 87; no regressions. Gate
provisioned via `scripts/dev_setup.sh` (#48) — one command, worked clean.

## Deferred (M3 — keeps #25 OPEN)

- **T026** — `edge_insertion` case-2 iLayer-1 retriangulation (`case-2-design.md` fan walk). Now unblocked by LayerState.
- **T028** — wire LayerState bookkeeping into `edge_bisection`/`edge_insertion`; per-layer adjacency rebuild (`CHILmesh(conn,pts)` rebuild for v0.5).
- **T029** — wire `route_leftover_tri` into the live M2 sweep boundary stage.

`tests/test_no_interior_tris.py::test_tri2quad_faithful_path` stays expected-WIP until T026/T028/T029 land.

## Files to review on resume

- `src/quadmesh/_layer_state.py` — the new API.
- `src/quadmesh/_tri_removal.py` — `edge_insertion` (~166, simplified port T026 replaces), `route_leftover_tri` (~215, unwired router).
- `specs/001-matlab-to-python-port/case-2-design.md` — T026 retri design + the state-threading the wiring needs.

## What comes next

1. T026/T028/T029 to make `method="faithful"` quad-pure (closes #25).
2. #46 onion hero domain — blocked on ADMESH-Domains#93 `.14` generation + the faithful path above.

## Environment note

DomI contract plugins not installed at container start (marketplace add failed in
`instructions_on_start.sh`, #114) → ran `/introspect` + `.domi-pin` check inline
from the staged DomI clone. `.domi-pin` sha `3b12f77` matches DomI main HEAD — no
drift. settings.json already carries the DomI block, so next container start should
load the plugins.

## chilmesh issues status

No new chilmesh issues this session. T028's adjacency-rebuild need may warrant a
low-priority `rebuild_adjacencies()` ask later (currently the v0.5 plan rebuilds
`CHILmesh(conn,pts)` per mutation — see `case-2-design.md` "Open chilmesh ask").
