# Tasks: Port MATLAB QuADMESH+ to Python

> **SUPERSEDED for the faithfulness effort** by [faithful-port-tasks.md](./faithful-port-tasks.md) (2026-05-23). This tracks the original v0.1–0.4 port (T1–T15, done). New faithful-port tasks live in the faithful-* docs.

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Branch**: `claude/awesome-goodall-Tbur3` (v0.3) / `claude/awesome-goodall-cqPYK` (v0.2) / `claude/affectionate-heisenberg-prShD` (v0.1)

Status legend: `[ ]` todo · `[~]` in-progress · `[x]` done · `[-]` deferred.

## T1 — Bootstrap

- [x] T1.1 Create `python/` skeleton (pyproject.toml, README, package dir).
- [x] T1.2 Install chilmesh dependency, smoke test load Test_Case_1.
- [x] T1.3 Set up `.specify/` + spec + plan + tasks.

## T2 — Helpers (`_topology.py`)

- [x] T2.1 `ccw_edges_around_vert(mesh, vert_ids) -> List[ndarray]`.
- [x] T2.2 `merge_tri_pair(mesh, a, b) -> ndarray(4,)`.
- [x] T2.3 `merge_tri_pairs(mesh, pairs) -> ndarray(n,4)` batch.
- [x] T2.4 Unit tests (6 tests, all green).

## T3 — Edge selection (`identify_edges.py`)

- [x] T3.1 `identify_edges_in_layer(domain, layer_idx) -> LayerEdgeSelection`.
- [x] T3.2 Test on Test_Case_1 layer 0.
- [x] T3.3 Disjoint-pair property test.

## T4 — Tri-removal sub-ops (`_tri_removal.py`)

- [x] T4.1 `WorkingMesh` dataclass.
- [x] T4.2 `edge_removal`.
- [x] T4.3 `edge_bisection`.
- [x] T4.4 `edge_insertion`.
- [x] T4.5 `route_leftover_tri` (opt-in via `aggressive=True`).
- [x] T4.6 Aggressive-path tests -- done in v0.4 (21 tests; uncovered + fixed `edge_insertion` unpack bug, see T15.1).

## T5 — Tri2Quad sweep (`tri2quad.py`)

- [x] T5.1 `tri2quad_routine(domain, can_remove_edges, parent=None)`.
- [x] T5.2 Layer-by-layer driver.
- [x] T5.3 Final assembly: quads + padded tris -> CHILmesh.
- [x] T5.4 Smoke tests (3 tests on Test_Case_1: no-crash, >=50% quads, no zero-area).

## T6 — Post-process operators

- [x] T6.1 `doublet_collapse`.
- [x] T6.2 `quad_vertex_merge`.
- [x] T6.3 `cleanup_boundary_quads` (collapse + shift modes).
- [x] T6.4 `remove_unused_vertices`.
- [x] T6.5 `post_process_routine` orchestrator with outer + inner iteration caps.
- [x] T6.6 Per-op smoke tests + end-to-end pipeline test.

## T7 — Pipeline + driver

- [x] T7.1 `create_quad_domain(mesh, polygon=None)`.
- [x] T7.2 `run_pipeline(mesh, polygon, can_remove_edges, n_smooth_iter)`.
- [x] T7.3 `cli.py` -- argparse driver with `--n-smooth-iter` + `--max-outer-iter` + `--max-inner-iter` flags.

## T8 — Tests + fixtures

- [x] T8.1 `tests/conftest.py`.
- [x] T8.2 `test_topology.py` (6 tests).
- [x] T8.3 `test_identify_edges.py` (3 tests).
- [x] T8.4 `test_tri2quad_smoke.py` (3 tests).
- [x] T8.5 `test_pipeline.py` (5 tests; covers post-process + pipeline).
- [x] T8.6 `test_cli.py` (1 test, end-to-end CLI roundtrip).
- **Total v0.1: 18 tests, all green, runtime ~5s.**

## T9 — Docs + mapping

- [x] T9.1 `python/MAPPING.md`.
- [x] T9.2 README with Quick Start + CLI + Status + Spec.
- [x] T9.3 Caveman top-level docstrings per module.

## T10 — CHILmesh future-work issues

- [x] T10.1 Filed chilmesh#132: `MutableMesh.merge_elements` stub.
- [x] T10.2 Filed chilmesh#133: `ccw_edges_around_vert` public helper.
- [x] T10.3 Filed chilmesh#134: `compute_adjacencies=True` independent of `compute_layers`.

## T11 — v0.2 additions

- [x] T11.1 `cleanup_boundary_quads(can_remove_edges=False)` shift mode.
- [x] T11.2 `two_part_smoother(mesh, n_iter)` -- port of `twoPartSmoother.m`.
- [x] T11.3 `post_process_routine` calls `two_part_smoother`.
- [x] T11.4 7 new tests in `test_cleanup_bq.py`. Total: 25 tests.
- [-] T11.5 Sub-domain split in `two_part_smoother` -- deferred; needs `CHILmesh.submesh()`.
- [-] T11.6 Edge-insertion case-2 retriangulation of iLayer-1 -- deferred; requires stateful layer sweep redesign.

## T12 -- v0.1 Ship

- [x] T12.1 Commit + push to `claude/affectionate-heisenberg-prShD`.
- [x] T12.2 Open draft PR -> PR #2.

## T13 -- v0.2 Ship

- [x] T13.1 Commit + push to `claude/awesome-goodall-cqPYK`.
- [x] T13.2 Open draft PR -> PR #3.
- [x] T13.3 Session handoff (`docs/sessions/session-002.md`).
- [-] T13.4 Introspect -- skill not available in remote exec environment.

## T14 -- v0.3 (session 003 branch `claude/awesome-goodall-Tbur3`)

- [x] T14.1 Collapse alignment with MATLAB: side verts (ci+/-1)%4 merged into corner (not corner->opposing).
- [x] T14.2 Fix `route_leftover_tri` bug: `n_bdy==1 && !can_remove_edges` -> `edge_bisection` (was `edge_removal`).
- [x] T14.3 Bug fix: `two_part_smoother` -- `method="angle"` -> `method="angle-based"`; smoother was silently producing 0 iterations.
- [x] T14.4 `quality_report.py` -- `compute_quality_stats` + `format_quality_report` (port of MATLAB plotQualityProgress, no plot).
- [x] T14.5 CLI flags `--max-outer-iter` and `--max-inner-iter` in `cli.py`; quality stats printed after pipeline.
- [x] T14.6 `pipeline.py` threads `max_outer_iter` + `max_inner_iter` through to `post_process_routine`.
- [x] T14.7 5 new tests: `test_smoother.py` (2) + `test_quality.py` (3). Total: 35 tests.
- [x] T14.8 CHILmesh issues filed: chilmesh#138 (`submesh()` API), chilmesh#139 (angle_based_smoother perf ~42s/pass).
- [x] T14.9 Version bumped to 0.3.0.
- [-] T14.10 Aggressive leftover-tri routing -- blocked by chilmesh#132.
- [-] T14.11 Sub-domain smoother -- blocked by chilmesh#138 (`CHILmesh.submesh()`).

## T15 — v0.4 (session 004 branch `claude/gifted-ptolemy-uQk5F`)

- [x] T15.1 T4.6 done — `tests/test_tri_removal.py` (11 tests covering
      `edge_removal`, `edge_bisection`, `edge_insertion`, dispatcher).
- [x] T15.2 Bug fix in `edge_insertion`: `edge2vert(...).astype(...).tolist()`
      missed `.ravel()` — unpack failed on `(1,2)` shape. Caught by new tests.
      The aggressive path was previously dead code so this never surfaced.
- [x] T15.3 Element-count parity scaffold — `tests/test_parity.py` (6 tests,
      Test_Case_1 + Block_O). Regression baselines pinned to current Python
      output; MATLAB ground truth deferred (Block_O `.mat` is MATLAB-opaque).
- [x] T15.4 Case-2 design doc — `specs/001-matlab-to-python-port/case-2-design.md`.
      Identifies needed state (LayerState dataclass, callback hook,
      adjacency invalidation). Defers impl to v0.5 alongside chilmesh#132.
- [x] T15.5 Version bumped to 0.4.0. Total: 46 tests (35 → +11 sub-ops; +6 parity = +17).
- [-] T15.6 Sub-domain smoother — still blocked on chilmesh#138.
- [-] T15.7 Aggressive tri routing wiring — still blocked on chilmesh#132.

## v0.5 backlog

- Wire `route_leftover_tri` into `tri2quad_routine` (depends on chilmesh#132).
- Implement `edge_insertion` case-2 iLayer-1 retriangulation per `case-2-design.md`.
- Sub-domain smoother (depends on chilmesh#138).
- Angle-based smoother default-on (depends on chilmesh#139).
- Capture MATLAB ground-truth elem counts; tighten parity tolerances.
