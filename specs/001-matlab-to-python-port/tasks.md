# Tasks: Port MATLAB QuADMESH+ to Python

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Branch**: `claude/affectionate-heisenberg-prShD`

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
- [-] T4.6 Aggressive-path tests — deferred to v0.2 (default path keeps leftover tris as padded tris).

## T5 — Tri2Quad sweep (`tri2quad.py`)

- [x] T5.1 `tri2quad_routine(domain, can_remove_edges, parent=None)`.
- [x] T5.2 Layer-by-layer driver.
- [x] T5.3 Final assembly: quads + padded tris → CHILmesh.
- [x] T5.4 Smoke tests (3 tests on Test_Case_1: no-crash, ≥50% quads, no zero-area).

## T6 — Post-process operators

- [x] T6.1 `doublet_collapse`.
- [x] T6.2 `quad_vertex_merge`.
- [x] T6.3 `cleanup_boundary_quads` (collapse mode only).
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
- **Total: 18 tests, all green, runtime ~5s.**

## T9 — Docs + mapping

- [x] T9.1 `python/MAPPING.md`.
- [x] T9.2 README with Quick Start + CLI + Status + Spec.
- [x] T9.3 Caveman top-level docstrings per module.

## T10 — CHILmesh future-work issues

- [ ] T10.1 File issue: `chilmesh.mutations.MutableMesh.merge_elements` is a stub.
- [ ] T10.2 File issue: `chilmesh.ccw_edges_around_vert` — public helper.
- [ ] T10.3 File issue: `chilmesh.CHILmesh(...)` with `compute_layers=False` skips adjacency building too; add a `compute_adjacencies=True` flag.

## T11 — Deferred to v0.2

- [-] Edge-insertion case-2 retriangulation of iLayer-1 (spec Q2).
- [-] CleanupBoundaryQuads "shift" mode (spec Q4).
- [-] GUI / interactive plot progress (out of scope).
- [-] ADMESH_Library port (out of scope).
- [-] Aggressive leftover-tri routing in default path.

## T12 — Ship

- [ ] T12.1 Commit + push to `claude/affectionate-heisenberg-prShD`.
- [ ] T12.2 Open draft PR.
- [ ] T12.3 Session handoff (`docs/sessions/`).
- [ ] T12.4 Introspect.
