# Session 008 — faithful per-layer tri2quad sweep (WIP) + demo layer-sequence fix

**Date:** 2026-05-24
**Branch:** `faithful-tri2quad-sweep` (cut from `daily-issue-fixing`)
**PR:** [#37](https://github.com/domattioli/QuADMESH/pull/37) (draft) — head `b2fe8ab`
**Model:** claude-opus-4-7

## What changed

Two threads this session.

### 1. Demo fix (landed on `daily-issue-fixing`, commits `3f04f17`, `c010ae4`)

`videos/scripts/tri2quad_pipeline_annulus.py`:
- `_to_quads`: simultaneous cross-fade → **layer-by-layer sequential conversion** (innermost first, mirrors QuADMESH+ sweep). Assign each quad to a layer by centroid radius; for each layer fade out its tris then fade in its quads. Stops tri-diagonal bleed-through that read as overlapping quads + gaps.
- `_smooth_post`: simultaneous cross-fade → sequential `FadeOut(old)` then `FadeIn(new)` (element count changes on post-process, so 1:1 transform stranded surplus).

### 2. Faithful sweep rebuild (WIP, on `faithful-tri2quad-sweep`, commit `b2fe8ab`)

Root cause of the demo's *real* overlaps (not manim): `method="faithful"`'s `_point_insert_tri_pairs` is **parity-impossible** — a lone-tri + neighbour-quad pentagon (5 verts + 1 interior pt → 2 quads needs 8 = 5 + 2k → k=1.5). Always gaps or overlaps.

Decided (user): full faithful port of MATLAB `Tri2QuadRoutine` as a real per-layer sweep.

| File | Change |
|---|---|
| `src/quadmesh/_faithful_sweep.py` | **NEW** (653 lines). Innermost→outward sweep, mutates a working `CHILmesh` Domain in place so each `edgeBisection` splits the next layer outward while still triangular. `identify_edges_in_layer` → `_merge_layer` (interior-saturating, seeded by flagged pairs) → `_route_remaining` (`_edge_bisection_case2` / `_edge_insertion` Remacle Fig 9 / edge_removal). Finalization: residual pair-merge + edge-swap + `_global_saturate` fallback. |
| `src/quadmesh/tri2quad.py` | `method=="faithful"` (~L764) now calls `faithful_sweep`, replacing global-match + `_point_insert_tri_pairs`. |

## Status: NOT yet faithful

Annulus fixture (validation script in §"validation") still produces **interior residual tris + shapely-overlapping quads**. Faithfulness invariant (zero interior tris) NOT met. Honest WIP.

## Diagnosis captured (next-session leads)

Two distinct defects, both reproduced this session:

1. **`_global_saturate` strands interior tris via its own seeds.** It splits every quad → 2 tris and seeds each pair to reform its quad before matching. Those seeds lock all quads, so a stranded interior tri has no free neighbour and the augmenting path finds no terminus. Measured on annulus residual (96 quads + 23 interior tris → 215 tris): **with seeds → 1 interior leftover; without seeds → 0 interior leftover** (merged 100, leftover 11, all boundary). **Fix:** surgical re-tile — split only the quads adjacent to each stranded interior-tri connected component, then `_match_tris_to_quads` seedless on that local patch; leave all other quads untouched. (Global seedless loses layer/quad alignment, so scope it.)

2. **`_edge_insertion` emits overlapping quads.** Places `B' = 0.5*B + 0.5*centroid` inside the tri and validates only per-quad via `_quad_ok` — never checks the new quad's union against the side quads it rewrites. **Fix:** correct CCW side-selection (walk CCW edges around `tbVertID`, everything up to `tElemID` gets `npID`) per MATLAB `edgeInsertion` + a union/overlap check before accepting.

Note: the sweep's own per-layer output (66 quads / 7 interior) and the pre-finalization snapshot (96 quads / 23 interior) differ run-to-run in the debug harness — investigate determinism too (likely layer-set iteration order / dict ordering in `_merge_layer`).

## Validation script (annulus ground truth)

Run `PYTHONPATH=src python`:
```python
import numpy as np
from scipy.spatial import Delaunay
from chilmesh import CHILmesh
from quadmesh import tri2quad
from shapely.geometry import Polygon as SPoly
RINGS=[1.00,0.87,0.72,0.58,0.45,0.32]; NPR=[18,16,14,12,10,9]
def build():
    pts=[]
    for k,(r,n) in enumerate(zip(RINGS,NPR)):
        off=(k%2)*np.pi/n; th=np.linspace(0,2*np.pi,n,endpoint=False)+off
        pts.append(np.column_stack([r*np.cos(th),r*np.sin(th)]))
    pts=np.vstack(pts); tri=Delaunay(pts); c=pts[tri.simplices].mean(axis=1)
    return pts,tri.simplices[np.linalg.norm(c,axis=1)>RINGS[-1]*1.06]
pts,simps=build(); m=CHILmesh(simps,pts,grid_name="annulus")
q=tri2quad(m,method="faithful"); cl=np.asarray(q.connectivity_list); P=q.points[:,:2]
def nz(r):
    v=[int(x) for x in r]; u=list(dict.fromkeys(v)); return tuple(u) if len(u)==3 else tuple(v)
els=[nz(r) for r in cl]
def edges(e):
    n=len(e); return [tuple(sorted((e[i],e[(i+1)%n]))) for i in range(n)]
cnt={}
for e in els:
    for ed in edges(e): cnt[ed]=cnt.get(ed,0)+1
bset={e for e,c in cnt.items() if c==1}
ntri=sum(1 for e in els if len(e)==3)
nint=sum(1 for e in els if len(e)==3 and not any(ed in bset for ed in edges(e)))
polys=[SPoly(P[list(e)]) for e in els]
ov=sum(1 for i in range(len(polys)) for j in range(i+1,len(polys)) if polys[i].intersects(polys[j]) and polys[i].intersection(polys[j]).area>1e-7)
print(f"elems={len(els)} tris={ntri} INTERIOR_tris={nint} overlaps={ov}")
# Target: INTERIOR_tris=0 overlaps=0 tris=0
```
Last result this session: `elems=73 tris=7 INTERIOR_tris=7 overlaps=21`.

## What comes next

1. Fix `_global_saturate` (surgical local re-tile, seedless) → 0 interior tris.
2. Fix `_edge_insertion` (CCW side-selection + union check) → 0 overlaps.
3. Investigate run-to-run nondeterminism in `_merge_layer`.
4. `pytest -q` green incl. `tests/test_no_interior_tris.py`; re-render demo on faithful path; flip PR #37 out of draft.
5. Then consider making `faithful` the default + relax `test_tri2quad_faithful_path` only if a few residual *boundary* tris legitimately remain (documented).

## Files to review on resume

- `src/quadmesh/_faithful_sweep.py` — `_global_saturate` (~L489), `_edge_insertion` (~L198), `faithful_sweep` (~L362), `_merge_layer` (~L554).
- `src/quadmesh/tri2quad.py` — `method=="faithful"` branch (~L764), `_match_tris_to_quads` (~L96, augmenting fixup ~L250).
- MATLAB refs (authoritative): `matlab/quadmesh/02_Tri2Quad_Routine/Tri2QuadRoutine.m`, `matlab/quadmesh/04_Remove_Triangles/{removeTrianglesFun,edgeBisection,edgeInsertion,edgeRemoval}.m`.

## Open issues

- **#25** faithful `removeTrianglesFun` port — this PR is the implementation; still WIP.
- **#31/#32/#33** — unchanged from session-007.

## chilmesh issues status

No new chilmesh issues this session.

## Environment / process notes

- Branch policy deviation: work is on `faithful-tri2quad-sweep`, NOT `daily-issue-fixing` (CLAUDE.md default). Explicit user instruction ("put the rebuild on its own branch") overrides the default. Draft PR #37 targets `daily-issue-fixing`.
- Build subagent (`Build faithful tri2quad layer sweep`) hit its own session token limit mid-task; output committed as WIP for review rather than discarded.
