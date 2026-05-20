# Tasks: Port MATLAB QuADMESH+ to Python

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Branch**: `claude/awesome-goodall-cqPYK` (v0.2) / `claude/affectionate-heisenberg-prShD` (v0.1)

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
- [-] T4.6 Aggressive-path tests — deferred to v0.3.

## T5 — Tri2Quad sweep (`tri2quad.py`)

- [x] T5.1 `tri2quad_routine(domain, can_remove_edges, parent=None)`.
- [x] T5.2 Layer-by-layer driver.
- [x] T5.3 Final assembly: quads + padded tris → CHILmesh.
- [x] T5.4 Smoke tests (3 tests on Test_Case_1: no-crash, ≥50% quads, no zero-area).

## T6 — Post-process operators

- [x] T6.1 `doublet_collapse`.
- [x] T6.2 `quad_vertex_merge`.
- [x] T6.3 `cleanup_boundary_quads` (collapse mode).
- [x] T6.4 `remove_unused_vertices`.
- [x] T6.5 `post_process_routine` orchestrator with outer + inner iteration caps.
- [x] T6.6 Per-op smoke tests + end-to-end pipeline test.

## T7 — Pipeline + driver

- [x] T7.1 `create_quad_domain(mesh, polygon=None)`.
- [x] T7.2 `run_pipeline(mesh, polygon, can_remove_edges, n_smooth_iter)`.
- [x] T7.3 `cli.py` — argparse driver.

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

- [x] T11.1 `cleanup_boundary_quads(can_remove_edges=False)` shift mode — binary-search bisection to ≤90°. Python-only (MATLAB never implemented this).
- [x] T11.2 `two_part_smoother(mesh, n_iter)` — port of `twoPartSmoother.m`; full-mesh angle+FEM interleave (sub-domain split deferred T11.5).
- [x] T11.3 `post_process_routine` calls `two_part_smoother` instead of bare `smooth_mesh`.
- [x] T11.4 7 new tests in `test_cleanup_bq.py` — helpers, no-op, collapse+shift on real mesh. Total: 25 tests.
- [-] T11.5 Sub-domain (boundary vs interior) split in `two_part_smoother` — deferred to v0.3; needs `CHILmesh.submesh()` public API.
- [-] T11.6 Edge-insertion case-2 retriangulation of iLayer-1 (spec Q2) — deferred to v0.3.
- [-] T11.7 Aggressive leftover-tri routing in default path — deferred to v0.3 (blocked by chilmesh#132).

## T12 — v0.1 Ship

- [x] T12.1 Commit + push to `claude/affectionate-heisenberg-prShD`.
- [x] T12.2 Open draft PR → PR #2.

## T13 — v0.2 Ship

- [x] T13.1 Commit + push to `claude/awesome-goodall-cqPYK`.
- [x] T13.2 Open draft PR → PR #3.
- [x] T13.3 Session handoff (`docs/sessions/session-002.md`).
- [-] T13.4 Introspect — skill not available in current remote exec environment.

## v0.3 Deferred backlog

- sub-domain split in twoPartSmoother (needs CHILmesh.submesh)
- aggressive tri routing (needs chilmesh#132 merge_elements)
- edge-insertion case-2 retriangulation
- CleanupBoundaryQuads collapse topology alignment with MATLAB (snap side-verts vs snap corner)
