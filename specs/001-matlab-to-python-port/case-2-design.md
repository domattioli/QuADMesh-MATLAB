# Edge-Insertion Case 2 — iLayer-1 Retriangulation Design

**Status**: design only. v0.4 scope = doc + no impl.
**Blocked by**: chilmesh#138 (`CHILmesh.submesh`) is *not* needed; the work
is internal to ``tri2quad`` state.

## What MATLAB does

`02_QuADMESH_Library/04_Remove_Triangles/edgeInsertion.m` case 2:

1. Tri on layer-interior bdy, n_bdy=0. Pick one bdy-vert `tbVert`.
2. Insert new vert `np` at 1/3 along an interior edge from `tbVert`.
3. Split tri → quad `[tbVert, V2, V3, np]`. Append to `newMesh`.
4. **Retriangulate iLayer-1 around `tbVert`**:
   - Gather all OE+IE tris of iLayer-1 that touch `tbVert`.
   - Build local boundary vert seq (CCW walk of edges that *don't* touch `tbVert`).
   - Bisect seq at midpoint `switchVertID`. First half → tris fan from `np`.
     Second half → tris fan from `tbVert`. One extra tri = `[tbVert, np, vertSeq[switch+1]]`.
   - Overwrite old iLayer-1 tris with rt tris. Append remainder.
   - Update `Layers.OE{iLayer-1}`, `Layers.IE{iLayer-1}`, `Layers.OV{iLayer}`,
     `Layers.IV{iLayer-1}` per `iOE` mask.
   - Update `Domain.nEdges`, `nElems`, `nVerts`. Call `buildAdjacencies`.

Net effect: iLayer-1 absorbs `np` without leaving a hole. The layer-sweep
loop then continues on iLayer-1 with topology already legal.

## What Python skips

`python/quadmesh/_tri_removal.py::edge_insertion`:

- Inserts `np`. Emits quad. Zeros consumed tri row. Done.
- iLayer-1 retri: not run. Old iLayer-1 tris remain with stale topology.
- This is OK *only* because:
  - `tri2quad_routine` does not currently invoke `edge_insertion` from the
    main sweep (the `aggressive=True` flag is wired through but the
    leftover-tri loop is dead code — see `tri2quad.py:53-89`).
  - Sub-ops are unit-tested in isolation (tests/test_tri_removal.py) where
    no follow-up layer sweep happens.

So today: design parity bug is dormant. It activates the moment we wire
`route_leftover_tri` into `tri2quad_routine`.

## What state the wiring needs

To run case-2 retri inside the sweep, `tri2quad_routine` must thread:

1. **Mutable layer membership**. MATLAB rewrites
   `Domain.Layers.{OE,IE,OV,IV}[iLayer-1]`. chilmesh exposes `mesh.layers`
   as a dict but `Domain` is read once at sweep start, never re-derived.
   → Need `LayerState` working copy (just the 4 lists, dict-of-lists).
2. **Mutable Domain connectivity**. Currently we zero rows in
   `domain.connectivity_list` and `domain.points` is mutated/appended in
   place — fine for additive ops, breaks if we need to overwrite tris
   (which iLayer-1 retri does). chilmesh stores `connectivity_list` as a
   property backed by an ndarray; in-place mutation works but the
   adjacency cache (`mesh.adjacencies`) goes stale.
3. **Adjacency rebuild trigger**. MATLAB calls `Domain.buildAdjacencies`
   after retri. chilmesh has no public equivalent (the cache is built
   lazily on first access). Options:
   - File chilmesh issue for a public `invalidate_adjacencies()` /
     `rebuild_adjacencies()` API. (low priority; one-line wrapper for the
     consumer; the cache is `mesh._adjacencies`)
   - Build a fresh `CHILmesh(conn, pts)` each time retri fires. Slow but
     correct. Acceptable for the v0.5 first-cut.

## Recommended Python shape

```python
@dataclass
class LayerState:
    OE: list[np.ndarray]   # outer-edge elems per layer
    IE: list[np.ndarray]   # inner-edge elems per layer
    OV: list[np.ndarray]   # outer verts per layer
    IV: list[np.ndarray]   # inner verts per layer

def tri2quad_routine(domain, can_remove_edges=True, parent=None, aggressive=False):
    layer_state = LayerState.from_mesh(domain)  # snapshot
    work = WorkingMesh(...)

    for iLayer in range(domain.n_layers - 1, -1, -1):
        sel = identify_edges_in_layer(domain, iLayer)
        ...
        if aggressive:
            for leftover in remaining_elems:
                route_leftover_tri(
                    domain, work, leftover, iLayer,
                    on_mesh_boundary=(iLayer == 0 and domain.n_layers == parent.n_layers),
                    can_remove_edges=can_remove_edges,
                    sub_b_edge_set=..., sub_b_vert_set=...,
                    layer_state=layer_state,        # NEW
                    on_case2_retri=_retri_lm1,      # NEW callback
                )
        # rebuild domain adjacency if layer_state was mutated this iteration.
```

`_retri_lm1(domain, work, layer_state, iLayer, tbVert, np_id)` does the
MATLAB walk: gather iLayer-1 tris touching `tbVert`, build vert seq, fan,
overwrite, rebuild adjacencies.

## Why deferred

- iLayer-1 retri is the only mutation that needs adjacency invalidation
  in the middle of the layer sweep. Every other sub-op is additive.
- Skipping it costs ≤ few percent leftover tris on Test_Case_1 (current
  output is 100% quads; parity baseline holds without it). High effort,
  low yield until we have aggressive routing wired up.
- Right scope: ship as v0.5 alongside chilmesh#132 (`merge_elements`) and
  the aggressive-path wiring in `tri2quad_routine`. Single PR pays for the
  whole state-tracking refactor.

## Acceptance for the v0.5 impl

1. New tests in `tests/test_tri_removal.py`:
   - `edge_insertion(case=2)` followed by manual `_retri_lm1` invocation
     produces a legal sub-mesh (no overlapping tris; iLayer-1 boundary
     verts intact except for `tbVert` and `np`).
   - Aggressive end-to-end run on Test_Case_1 finishes with elem count
     within 5% of conservative-mode baseline.
2. `MAPPING.md`: `edgeInsertion.m` → status "done" instead of "partial".

## Open chilmesh ask

If `mesh._adjacencies` cache invalidation becomes a hot path, file low
priority chilmesh issue for a public `rebuild_adjacencies()` helper.
Workaround for v0.5: rebuild `CHILmesh(conn, pts)` per retri call.
