# Implementation Plan: Port MATLAB QuADMESH+ to Python

> **SUPERSEDED for the faithfulness effort** by [faithful-port-plan.md](./faithful-port-plan.md) + [faithful-port-tasks.md](./faithful-port-tasks.md) (2026-05-23, thesis-aligned). This doc covers the original v0.1–0.4 port (done); faithful-port work uses the faithful-* docs.

**Branch**: `claude/affectionate-heisenberg-prShD` | **Date**: 2026-05-20 | **Spec**: [spec.md](./spec.md)

## Summary

Port MATLAB QuADMESH+ tri→quad mesh generator (~4174 LOC, 11 directories under `02_QuADMESH_Library/`) to Python. Sit on top of `chilmesh` (the Python port of CHILmesh.m). Add no helpers that chilmesh already provides; explicit cross-references in this plan map every imported chilmesh symbol.

Deliverables:
- Python package `quadmesh/` in `python/` subdir of the repo.
- Public API: `tri2quad`, `post_process`, `create_quad_domain`, `run_pipeline`.
- CLI: `quadmesh INPUT.14 -o OUT.14 [...]`.
- Pytest suite covering Test_Case_1, Test_Case_2, Mixed_Test.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: `chilmesh>=0.4.0`, `numpy>=1.24`, `scipy>=1.10`. Optional: `matplotlib>=3.6` for plot helpers.
**Storage**: In-memory CHILmesh + scratch state during tri2quad sweep. Input/output via fort.14.
**Testing**: pytest with .14 fixtures from `03_CHILMesh_Test_Cases/01_.14_Files/`.
**Target Platform**: Cross-platform; CI on Linux.
**Project Type**: Single Python package.
**Performance Goals**: Block_O (~2400 tris) tri2quad+post-process in <60s. Correctness > speed for v0.1.
**Constraints**: 0-based indexing everywhere. Output CHILmesh CCW + no zero-area.
**Scale/Scope**: ~4000 LOC MATLAB → ~2000 LOC Python (chilmesh absorbs ~1500 LOC of primitives).

## Cross-Reference: chilmesh symbols to reuse

| MATLAB primitive | chilmesh equivalent | Notes |
|------------------|---------------------|-------|
| `CHILmesh` class | `chilmesh.CHILmesh` | mesh class |
| `CM.boundaryEdges` | `mesh.boundary_edges()` | |
| `CM.boundaryVerts` | `mesh.boundary_node_indices()` | |
| `CM.edge2Vert` | `mesh.edge2vert([eids])` or `mesh.adjacencies["Edge2Vert"]` | |
| `CM.edge2Elem` | `mesh.edge2elem([eids])` or `mesh.adjacencies["Edge2Elem"]` | -1 sentinel |
| `CM.elem2Edge` | `mesh.elem2edge([elems])` | |
| `CM.vert2Edge` | `mesh.get_vertex_edges(v)` per vert | returns set; cast `np.fromiter` for arrays |
| `CM.vert2Elem` | `mesh.get_vertex_elements(v)` | |
| `CM.Layers` | `mesh.layers` dict (`OE/IE/OV/IV/bEdgeIDs`) | |
| `CM.nLayers` | `mesh.n_layers` | |
| `CM.nElems/nVerts/nEdges` | `mesh.n_elems/n_verts/n_edges` | |
| `CM.Points` | `mesh.points` | (n,3) float64 |
| `CM.ConnectivityList` | `mesh.connectivity_list` | 0-based |
| `CM.edgeLength(eid)` | `np.linalg.norm(mesh.points[u]-mesh.points[v])` | trivial |
| `CM.edgeMidpoint(eid)` | `0.5*(mesh.points[u]+mesh.points[v])` | trivial |
| `CM.elemType` | `mesh._elem_type()` | private but stable |
| `CM.elemQuality` | `mesh.elem_quality()` | returns (quality, angles, stats) |
| `CM.isPolyCCW` | `mesh._ensure_ccw_orientation()` (in `__init__`) | implicit on construction |
| `PathsOnOV(L, Domain)` | `chilmesh.layer_paths.paths_on_outer_vertices(mesh, layer_idx)` | already ported |
| `FEMSmooth(CM)` | `mesh.smooth_mesh('fem')` / `mesh.direct_smoother()` | |
| `MCSmooth(CM, ...)` | `mesh.smooth_mesh('angle')` / `mesh.angle_based_smoother(...)` | |
| `read_from_fort14` | `CHILmesh.read_from_fort14(path)` | classmethod |
| `write_to_fort14` | `mesh.write_to_fort14(path)` | |
| `CM.copy()` | `mesh.copy()` | |
| `MutableMesh.merge_elements` | `chilmesh.mutations.MutableMesh.merge_elements` | currently a stub (marks elem_b deleted); not used — we build quads ourselves |

**Functions we add (no chilmesh equivalent)**:
- `ccw_edges_around_vert` (port of CCWEdgesAroundVertsFun) — sort edges by polar angle around each vert. chilmesh has no public CCW sorter; nearest analogue is internal `_ensure_ccw_orientation` for elements, not edges.
- `merge_tri_pair` — chilmesh's `MutableMesh.merge_elements` is a stub; we construct CCW 4-vert quad explicitly.

## Constitution Check

| Principle | Status |
|-----------|--------|
| I. Faithful Port | PASS — algorithm matches MATLAB on canonical fixtures |
| II. Depend on chilmesh | PASS — cross-reference table above; only 2 new helpers needed |
| III. Test-First Per Module | PASS — pytest per task in tasks.md |
| IV. Layered Implementation | PASS — leaf → middle → top |
| V. 0-Based Indexing | PASS — all integer arrays 0-based |
| VI. Caveman Docs | PASS — terse docstrings; README caveman |

## Project Structure

```text
QuADMesh-MATLAB/
├── 00_CHILMesh_Class/       # MATLAB (legacy ref)
├── 01_ADMESH_Library/       # MATLAB; out of scope
├── 02_QuADMESH_Library/     # MATLAB source (porting from)
├── 03_CHILMesh_Test_Cases/  # .14 fixtures (test data)
├── 04_CHIL_Supporting_Functions/  # MATLAB; not ported
├── 05_Results/              # MATLAB
├── .specify/                # speckit
├── specs/001-matlab-to-python-port/
│   ├── spec.md              # ✓
│   ├── plan.md              # (this)
│   └── tasks.md             # follows
└── python/
    ├── pyproject.toml
    ├── README.md
    ├── MAPPING.md           # MATLAB→Python file map
    ├── quadmesh/
    │   ├── __init__.py
    │   ├── _topology.py     # CCW edges, merge tri pair (the 2 new helpers)
    │   ├── identify_edges.py
    │   ├── _tri_removal.py
    │   ├── tri2quad.py
    │   ├── doublet_collapse.py
    │   ├── quad_vertex_merge.py
    │   ├── cleanup_boundary_quads.py
    │   ├── remove_unused.py
    │   ├── post_process.py
    │   ├── create_quad_domain.py
    │   ├── pipeline.py
    │   └── cli.py
    └── tests/
        ├── conftest.py
        ├── test_topology.py
        ├── test_identify_edges.py
        ├── test_tri2quad_smoke.py
        ├── test_post_process_smoke.py
        ├── test_pipeline_end_to_end.py
        └── test_cli.py
```

## Phase 0: Research (done inline)

MATLAB read complete. Routines fall into three groups:

1. **Tri-pair selection + merge** (the bulk of the algorithmic value):
   - `PathsOnOV` → chilmesh.layer_paths.paths_on_outer_vertices ✓
   - `pathRewind` → trivial helper, fold into identify_edges
   - `CCWEdgesAroundVertsFun` → new helper `ccw_edges_around_vert`
   - `identifyEdgesFun_v2` → `identify_edges_in_layer`
   - `mergeTrianglesFun` → `merge_tri_pairs`

2. **Leftover tri handling**:
   - `removeTrianglesFun` → `route_leftover_tri`
   - `edgeInsertion` → `edge_insertion` (case-2 retri deferred to v0.2 per spec Q2)
   - `edgeBisection` → `edge_bisection`
   - `edgeRemoval` → `edge_removal`

3. **Post-process operations**:
   - `DoubletCollapse` → `doublet_collapse`
   - `QuadVertexMerge_v2` → `quad_vertex_merge`
   - `CleanupBoundaryQuads_v2` (collapse mode only per Q4) → `cleanup_boundary_quads`
   - `RemoveUnusedVertices` → `remove_unused_vertices`
   - `FEMSmooth` / `MCSmooth` → wrap chilmesh smoothers
   - `PostProcessRoutine` → `post_process` orchestrator with iteration cap

4. **Pipeline driver**:
   - `Main.m` → `cli.py` + `pipeline.run_pipeline`
   - `createQuadDomain` → `create_quad_domain` (polygon-only; GUI dropped)

## Phase 1: Design

### Data Model

```python
# Input/Output: chilmesh.CHILmesh (no new mesh class)

@dataclass
class LayerEdgeSelection:
    sub_mesh: CHILmesh
    elem_ids_global: np.ndarray         # (n,) elem IDs in parent domain
    boundary_edge_ids: np.ndarray       # (m,) sub-mesh edge IDs
    boundary_vert_ids_global: np.ndarray
    removed_edge_ids: np.ndarray        # (k,) sub-mesh edge IDs to remove
    paths: List[np.ndarray]             # outer-vertex paths (rotated to corner)

@dataclass
class WorkingMesh:
    points: np.ndarray                  # (n, 3)
    quads: List[np.ndarray]             # list of (4,) quad rows
```

### Quickstart (manual)

```python
from chilmesh import CHILmesh
from quadmesh import tri2quad, post_process

tri = CHILmesh.read_from_fort14("03_CHILMesh_Test_Cases/01_.14_Files/Test_Case_1.14")
quad = tri2quad(tri, can_remove_edges=True)
quad = post_process(quad, can_remove_edges=True, n_smooth_iter=50)
quad.write_to_fort14("/tmp/out.14")

quality, angles, stats = quad.elem_quality()
print(f"mean quality: {quality.mean():.3f}")
```

### Contracts

Public API surface (frozen for v0.1):

```python
def tri2quad(mesh: CHILmesh,
             can_remove_edges: bool = True,
             parent: Optional[CHILmesh] = None) -> CHILmesh: ...

def post_process(mesh: CHILmesh,
                 can_remove_edges: bool = True,
                 n_smooth_iter: int = 50,
                 max_outer_iter: int = 5) -> CHILmesh: ...

def create_quad_domain(mesh: CHILmesh,
                       polygon: Optional[np.ndarray] = None) -> CHILmesh: ...

def run_pipeline(mesh: CHILmesh,
                 polygon: Optional[np.ndarray] = None,
                 can_remove_edges: bool = True,
                 n_smooth_iter: int = 50) -> CHILmesh: ...
```

## Phase 2: Tasks

See `tasks.md`.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `identify_edges` path-walk picks the wrong "every other" edge → fewer merges, more orphan tris | High | Medium | Property test: ≥ 0.7 × theoretical pair-count merges on Test_Case_1 |
| Edge-insertion case-2 retriangulation skipped (per Q2) leaves inconsistent layer state | Medium | Low | v0.1 produces a working quad mesh; degraded handling documented; CHILmesh future-work issue filed for v0.2 |
| chilmesh `MutableMesh.merge_elements` is a stub — surprise if used | High | High | Plan documents this; we use direct connectivity-list assembly, not MutableMesh |
| chilmesh `_elem_type` is private — relying on it may break | Low | Low | Wrap behind `_topology._elem_is_quad` to localize impact |
| Test_Case fixtures take long to load | Low | Low | Use Test_Case_1 + Test_Case_2 (smallest) for CI; Block_O as nightly |
| MATLAB layer indexing is 1-based; off-by-one errors during port | High | High | Per-module unit tests; cross-check with chilmesh.layer_paths existing tests |

## Phase 3: Implementation Order

1. **Skeleton + helpers**: `_topology.py` (ccw_edges_around_vert, merge_tri_pairs). Test on small synthetic 4-tri mesh.
2. **Edge selection**: `identify_edges.py`. Test on Test_Case_1 layer 0 → count selected edges > 0.
3. **Tri-pair merging in sweep** (no leftover handling yet): `tri2quad.py` minimal. Test: output has ≥ N quads.
4. **Leftover tri sub-ops**: `_tri_removal.py`. Test: leftover count goes to 0 after sweep.
5. **End-to-end tri2quad**: Test_Case_1 produces a valid CHILmesh.
6. **Doublet collapse + QVM + cleanup + remove_unused**: per-module test.
7. **post_process**: orchestrator + smoothing wrap.
8. **create_quad_domain + pipeline + CLI**.
9. **Polish, README, MAPPING.md**.
10. **Push, PR.**

## Success Validation

- ✅ All FRs satisfied per `spec.md`.
- ✅ pytest green on Test_Case_1, Test_Case_2, Mixed_Test.
- ✅ Block_O end-to-end completes in <60s.
- ✅ No re-implementation of chilmesh primitives (constitution principle II).
- ✅ Caveman README and docstrings.
- ⚠️ Edge cases (deep multigraph pinch points, ocean boundaries) documented as v0.2 follow-ups.
