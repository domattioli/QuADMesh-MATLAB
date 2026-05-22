# Design: edge_insertion case 2 — iLayer-1 retriangulation

**Branch**: `python-porting-project` (sessions 004+)
**Author**: session-004
**Status**: design only — implementation deferred (still v0.4 backlog)

## Background

`removeTrianglesFun` in MATLAB routes leftover tris in a layer sweep through
three sub-ops: `edgeRemoval`, `edgeBisection`, `edgeInsertion`.
`edgeInsertion` itself has three "cases":

| CASE | Trigger (from `removeTrianglesFun.m`) | What it does |
|------|---------------------------------------|--------------|
| 1    | `on_mesh_boundary == True`  && `n_bdy_edges == 0` && 1 vert in `bVertIDs` | Split tri by inserting a new edge at the one boundary vert. |
| 2    | `on_mesh_boundary == False` && `n_bdy_edges == 0` && 1 vert in `bVertIDs` | Same as case 1 **plus** retriangulate iLayer-1 around the new edge. |
| 3    | `on_mesh_boundary == True`  && `n_bdy_edges ∈ {2, 3}` | Split tri to form a decently-shaped quad rather than truncating. |

The current Python port (`_tri_removal.edge_insertion`) implements an
approximation of the "split tri into a quad" half of all three cases — it
picks an adjacent tri edge, places a 1/3-along-edge point, and forms a quad —
but does **not** perform the case-2 iLayer-1 retriangulation, nor does it
follow MATLAB's two-stationary-vert / moved-tbVert / adjacent-quad-rewrite
mechanics. Aggressive routing is opt-in (`aggressive=True`) and the deferred
case-2 work is the single biggest gap to MATLAB-faithful aggressive output.

## Why case 2 is the hard one

Cases 1 and 3 mutate only the current layer's elements + the local quad
neighborhood in `work.quads`. They leave iLayer-1 untouched.

Case 2 additionally:

1. Removes existing tris from `iLayer-1` that touch the boundary vert
   (`tbVertID`).
2. Fans new tris around `[tbVertID, npID]` to cover the just-evacuated
   neighborhood.
3. Updates `Domain.Layers.OE[iLayer-1]`, `IE[iLayer-1]`, `OV[iLayer]`,
   `IV[iLayer-1]` to reflect the new ownership.
4. Calls `Domain.buildAdjacencies` to rebuild Edge2Vert / Edge2Elem /
   Vert2Edge / Vert2Elem.

Steps 1–3 require **mutable per-layer state** that the current layer-by-layer
sweep in `tri2quad.tri2quad_routine` does not carry. The sweep currently:

- Iterates layers outermost → innermost (note: MATLAB sweep direction is the
  opposite of the bug-prone reading; verify in `Tri2QuadRoutine.m` if
  re-implementing).
- For each layer, calls `identify_edges_in_layer` once (read-only) and
  `merge_tri_pairs` once (writes to a `quads` accumulator, not to `domain`).
- Tracks `consumed_elems` as a single boolean array against the original
  `domain` indexing.

For case 2 to be MATLAB-faithful, the sweep needs to:

- **Mutate `domain` mid-sweep**: insert new vertex `npID`, rewrite
  connectivity rows in iLayer-1, push new connectivity rows, and rebuild
  adjacencies.
- **Mutate `domain.Layers`**: re-bucket iLayer-1 elements between OE/IE
  based on edge-count membership in `newBoundaryVerts`, and add `npID` to
  `OV[iLayer]` / `IV[iLayer-1]`.
- **Rewrite quads in `work`**: replace `tbVertID` with `npID` in the half of
  adjacent quads that share the iLayer-1 side ("newPTQuad").

## State to add

A minimal `LayerSweepState` carried through `tri2quad_routine`:

```python
@dataclass
class LayerSweepState:
    domain: CHILmesh           # mutated in place
    work: WorkingMesh          # mutated in place
    consumed_elems: np.ndarray # bool, parent-indexed
    layer_dirty: set[int]      # layer indices needing layer rebuild
```

Reasons:

- `domain` itself must already be mutable (we already poke `connectivity_list`
  and `points` in `edge_bisection`). The current sweep keeps `points` and
  `connectivity_list` as the source of truth.
- `layer_dirty` flags which layers had structural changes; we rebuild
  adjacencies + layers only once at sweep-end (or per-layer end), not per
  insertion. Avoids O(L) cost per insertion.

## Algorithm sketch

```
def edge_insertion_case_2(state: LayerSweepState, tri_elem_id: int,
                          layer_idx: int, t_bdy_vert: int) -> int:
    domain, work = state.domain, state.work

    # 1. Compute boundary edges of iLayer adjacent to t_bdy_vert.
    ccw_edges = ccw_edges_around_vert(domain, [t_bdy_vert])[0]
    adj_bdy_edges = _filter_layer_boundary_edges(domain, ccw_edges, layer_idx)

    # 2. Compute stationary vert IDs (other endpoints of adj_bdy_edges).
    stationary = _other_endpoints(domain, adj_bdy_edges, t_bdy_vert)
    assert len(stationary) == 2, "case-2 expects exactly 2 layer-bdy edges"

    # 3. Place new point npID 1/3 along adj_bdy_edges[0]; move t_bdy_vert
    #    1/3 along adj_bdy_edges[1] (MATLAB lines 60-68).
    new_p = (2 / 3) * domain.points[t_bdy_vert] + (1 / 3) * domain.points[stationary[0]]
    moved_t = (2 / 3) * domain.points[t_bdy_vert] + (1 / 3) * domain.points[stationary[1]]
    np_id = work.add_point(new_p)
    domain.points = np.vstack([domain.points, new_p[None, :]])
    domain.points[t_bdy_vert] = moved_t

    # 4. Identify adjacent quads in work that share t_bdy_vert. Bisect
    #    into newPTQuad (rewrite t_bdy_vert -> np_id) and oldPTQuad (keep).
    adj_q_ids = _find_quads_with_vert(work, t_bdy_vert)
    new_pt_quads = _select_new_side_quads(domain, work, adj_q_ids, ccw_edges, tri_elem_id)
    for qi in new_pt_quads:
        work.quads[qi][work.quads[qi] == t_bdy_vert] = np_id

    # 5. Build the new quad from tri (MATLAB lines 130-138).
    conn = domain.connectivity_list[tri_elem_id, :3].astype(int)
    v_old_pt = _vert_shared_with_old_quads(conn, work, adj_q_ids, new_pt_quads, t_bdy_vert)
    v3 = int([v for v in conn if v not in (t_bdy_vert, v_old_pt)][0])
    work.add_quad(np.array([t_bdy_vert, v_old_pt, v3, np_id]))
    domain.connectivity_list[tri_elem_id, :] = 0

    # 6. Case-2 SPECIFIC: retriangulate iLayer-1 around t_bdy_vert.
    if layer_idx > 0:
        _retriangulate_layer_minus_one(domain, layer_idx, t_bdy_vert, np_id,
                                       stationary)
        state.layer_dirty.add(layer_idx - 1)

    state.layer_dirty.add(layer_idx)
    return np_id
```

`_retriangulate_layer_minus_one` mirrors MATLAB lines 145-220:

```
def _retriangulate_layer_minus_one(domain, iLayer, t_vert, np_id, stationary):
    # 1. Find tris in OE[iLayer-1] ∪ IE[iLayer-1] adjacent to t_vert.
    layer_m1_elems = domain.layers["OE"][iLayer - 1] + domain.layers["IE"][iLayer - 1]
    tris_t = [e for e in layer_m1_elems
              if t_vert in domain.connectivity_list[e]]
    # 2. Collect their edge list, drop edges touching t_vert (we re-fan).
    fan_edges = _collect_edges(domain, tris_t)
    fan_edges = [e for e in fan_edges if t_vert not in e]
    # 3. Build CCW vert sequence around [np_id, t_vert] along fan boundary.
    vert_seq = _walk_boundary_sequence(np_id, t_vert, fan_edges,
                                       _layer_bdy_edges_for_stationary(stationary))
    # 4. Fan first half from np_id, second half from t_vert; the middle
    #    edge becomes [t_vert, np_id, vert_seq[mid+1]] (the IE-of-iLayer-1
    #    tri carrying the new edge).
    new_tris = _fan_triangulate(vert_seq, np_id, t_vert)
    # 5. Overwrite the |tris_t| oldest old tris in connectivity_list;
    #    append any remainder. Update layers.OE/IE/OV/IV per MATLAB lines
    #    200-216 (OE membership = exactly 1 vert from [np_id, t_vert,
    #    stationary], else IE).
    _overwrite_and_relayer(domain, tris_t, new_tris, np_id, t_vert, stationary, iLayer - 1)
```

## chilmesh API gaps

| MATLAB | Python equivalent today | Gap |
|--------|------------------------|-----|
| `Domain.Layers.OE/IE/OV/IV{i}` | `mesh.layers["OE"][i]` etc. | `.layers` may be read-only or recomputed on access — needs `domain.layers["OE"][i] = ...` to land in CHILmesh, not just a local list. |
| `Domain.buildAdjacencies` | `mesh._build_adjacencies()` | already private (filed as chilmesh#134). For case-2, we'd call once at sweep end. |
| `splitQuad(newMesh, qid)` | not in port | trivial (split quad into 2 tris) — implement inline. |
| Layer rebuilding after mutation | `CHILmesh.__init__(compute_layers=True)` on new mesh | rebuilding the whole mesh is expensive; per-layer incremental update is what MATLAB does, but is not exposed in chilmesh. **Already filed** as chilmesh#93 ("Phase 5: Incremental skeletonization for adaptive / dynamic meshes"). |
| `splitQuad`, `swapEdge`, `insertVertex` | not in port | bundled into chilmesh#94 ("Phase 5: Mesh mutation API"). chilmesh#132 (`merge_elements`) is the specific quadmesh-relevant subset already filed. |

If chilmesh doesn't expose mutable Layers and incremental updates (status:
gated by chilmesh#93 + chilmesh#94, both Phase 5), the case-2 implementation
can fall back to **end-of-sweep full rebuild**: collect all (`points`,
`connectivity_list`) deltas during the sweep, then construct a fresh
`CHILmesh(conn, pts, compute_layers=True)`. The cost is O(N log N) per sweep
instead of O(per-insertion); acceptable for the v0.4 target fixtures but
suboptimal for big meshes.

## Risks / open questions

1. **Sweep direction**: does `tri2quad_routine` walk innermost→outermost or
   outermost→innermost? Case 2 reaches into `iLayer-1`, so the direction
   matters — if we walk outermost→innermost, the touched iLayer-1 has not
   yet been processed (good). The current Python loop is
   `range(domain.n_layers - 1, -1, -1)` (outermost→innermost), which matches.
2. **Cascading retriangulation**: a case-2 insertion that retriangulates
   iLayer-1 may evict elements that the iLayer-1 pass would later try to
   pair via `identify_edges_in_layer`. Need to invalidate the iLayer-1 edge
   selection cache on `layer_dirty` and re-run `identify_edges_in_layer`
   when reaching it.
3. **`adj_q_ids` for the half-split**: MATLAB has `nadjQuadIDs == 2` and
   `else` branches. The 2-quad case is the "tri sits in a corner pocket
   between two existing quads" path; the else handles more complex layouts.
   Worth implementing the 2-quad path first and asserting the else branch as
   `NotImplementedError`.
4. **Test data**: building a 3-tri WorkingMesh that triggers case 2
   specifically (not on mesh boundary, no bdy edges, has a bdy vert) is
   awkward — the new T4.6 tests in `test_tri_removal.py` use 3-tri fans on
   the mesh boundary. Case 2 requires a 5+ tri fixture where the tri sits
   strictly inside the OV ring. **Add to test plan once `_retriangulate`
   helpers exist**.
5. **Quality regression check**: the v0.3 baselines in `test_parity.py` are
   captured with `aggressive=False`. Aggressive + case-2 may shift counts
   and quality. Re-baseline after implementation; consider a separate
   `BASELINES_AGGRESSIVE` table.

## Scope cut for v0.4

Implementation of case 2 retriangulation is large enough that it should be
its own session (v0.5 candidate). v0.4 closes this design doc + ships the
T4.6 tests + parity framework. The case-2 implementation lives downstream of:

- chilmesh exposing mutable / incremental layer API (filed if not present),
- a `LayerSweepState` refactor of `tri2quad_routine`,
- a 5+ tri unit-test fixture suite hand-built for the case-2 trigger.

## Acceptance criteria when implementation lands

- `tri2quad_routine(domain, aggressive=True)` produces no zero-area elems on
  Test_Case_1.14 + Block_O.14.
- Output elem count drops by `n_case2_invocations` vs the conservative path
  (each case-2 leaf-tri becomes a quad + retriangulates iLayer-1).
- All current T4.6 unit tests still pass.
- New tests: ≥3 case-2-specific topology assertions (npID added to layer
  OV[iLayer]; iLayer-1 fan tri count = expected; quad count + 1).
- Parity framework updated with aggressive baselines.
