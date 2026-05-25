# SpecKit Workflow: QuADMESH+ Layers Approach & WNAT Domain Audit

**Date:** 2026-05-25  
**Sources:** `docs/Mattioli_Thesis.pdf`, `matlab/quadmesh/02_Tri2Quad_Routine/`, `matlab/quadmesh/03_Layer_Paths/PathsOnOV.m`, `src/quadmesh/tri2quad.py`, `src/quadmesh/identify_edges.py`, `specs/001-matlab-to-python-port/`  
**Focus:** Full speckit walkthrough (Specify → Clarify → Plan → Tasks → Analyze) for the thesis QuadMesh+ layers approach, MATLAB cross-reference, and Python port audit on the WNAT domain.

---

## STAGE 1 — SPECIFY

### What is the QuADMESH+ Layers Approach?

The thesis defines QuADMESH+ as a **layered, two-stage, indirect quad meshing algorithm**. Its structure:

```
Input tri mesh
  └─ createQuadDomain         (select subset to convert; compute mesh layers)
       └─ Tri2QuadRoutine     (layer sweep, innermost → outward)
            └─ for each layer iLayer (n_layers downto 1):
                 ├─ identifyEdgesFun_v2   (every-other-edge sweep on OV path)
                 ├─ mergeTrianglesFun     (merge tri pairs across flagged edges)
                 └─ removeTrianglesFun   (handle leftover tris per topology case)
       └─ PostProcessRoutine  (doublet collapse, QVM, boundary cleanup, smoothing)
Output quad mesh
```

#### The Layer Structure

A **mesh layer** is a ring of triangles between two concentric isocontours of the mesh skeleton:
- **OE_L** — "outer elements" of layer L (ring closest to the mesh boundary)
- **IE_L** — "inner elements" (ring closer to the skeleton core)
- **OV_L** — outer vertices (the outer isocontour node ring)
- **IV_L** — inner vertices (the inner isocontour node ring)

Layers are numbered outward: layer 1 = innermost (near skeleton), layer n_layers = boundary layer.

The MATLAB sweep processes **outward → inward**: `for iLayer = Domain.nLayers:-1:1`.

#### The Every-Other-Edge Sweep (identifyEdgesFun_v2)

For each layer, `identifyEdgesFun_v2` (→ Python `identify_edges_in_layer`) does:

1. Build sub-mesh from `OE_L ∪ IE_L` elements
2. Compute outer-vertex paths via `PathsOnOV` (→ `paths_on_outer_vertices`)
3. Rotate each path to start at a "corner" vertex (one with only 1 attached layer element)
4. Walk each path vertex-by-vertex; at each vertex `v`:
   - `up_edge` = the OV boundary edge from the previous vertex to `v`
   - `down_edge` = the OV boundary edge from `v` to the next vertex
   - Sort all edges around `v` CCW from `up_edge` to `down_edge`
   - Take **every other** interior edge (not up/down boundary edges) for removal
   - Skip already-used edges or elements
5. The removed edges = the **merge diagonals** for tri-pair merging

The critical MATLAB detail at `identifyEdgesFun_v2.m:86–88`:
```matlab
idownEdgeID = find(sortedEdgeIDs == downEdgeID);
if idownEdgeID == 2
    sortedEdgeIDs = [sortedEdgeIDs(1), fliplr(sortedEdgeIDs(2:end))];
end
```
This **reverses** the interior edge ordering when `idownEdgeID == 2` (only one interior edge between up and down). The Python port does not implement this flip.

#### The Ch 4 Two-Stage Priority Heuristics

These govern which pairs are formed when the strip branches, has odd counts, or risks isolation:

**Interior layers (Ch 4.1) — IE_L before OE_L:**
- Match IE elements first; they can become isolated (no OE neighbor available)
- OE elements can still match inter-layer with the next layer's OV
- T1 selection: fewest eligible neighbors first
- T2 tiebreaker: multiple eligible neighbors → pick the one forming the best-shaped quad
- Intra-layer before inter-layer (L ↔ L−1)

**Boundary layer (Ch 4.2) — OE_L before IE_L (reversed):**
- Match OE first so the last unmatched tri is an IE_L
- An IE_L leftover can be cleanly cleared by adding a boundary point (no boundary shrinkage)
- Pre-process: edge-flip the RE_L (remaining edge layer) + neighbor to improve walkability

#### The Ch 4 Leftover-Tri Operations

Priority order per thesis p70 ("added resolution is better than diminished"):

1. **Edge insertion / add-boundary-point** — IE_L tri → split into quad by inserting a new point. PREFERRED.
2. **Edge swap** (Fig 3.2) — two tris sharing one vertex → reconnect diagonal → edge-adjacent → merge.
3. **Vertex duplication** (Fig 3.3) — duplicate shared vertex to pair off fan tris.
4. **Edge flip + walk** (Fig 3.6, 4.4) — flip a diagonal, walk isolated tri toward a partner.
5. **Edge collapse / removal** (Fig 3.5) — boundary edge collapse. LEAST PREFERRED, OE_L fallback only.

#### PathsOnOV — The Outer Vertex Path Builder

`PathsOnOV.m` builds one or more closed-loop paths along the outer vertices (OV_L) of a layer. It:

1. Builds a sub-mesh from the layer's OE+IE elements
2. Filters boundary edges to those with both endpoints in OV_L
3. Constructs an adjacency matrix over local OV indices
4. Walks greedily, starting at junction nodes (degree > 2) when present
5. Handles multi-path layers (islands, fjords): when lone boundary edges remain after path 1, starts path 2 from unvisited neighbors of junctions in path 1
6. `pathRewind.m` handles dead ends: backtracks to the nearest junction with an untried branch
7. Loop guard: `if loopcounter > 1e5: break` — prints "Error: a path cannot be closed"

---

## STAGE 2 — CLARIFY

### Q1: What does "faithful" mean for the port?

**Answer:** A faithful port must implement **both levels** of the QuADMESH+ algorithm together:
- The per-layer **every-other-edge sweep** (`identifyEdgesFun_v2`) as the pairing primitive
- The **Ch 4 heuristics** (IE/OE ordering, T1/T2 tiebreakers, intra-before-inter-layer) governing the sweep
- Plus the **recombination ops** (edge swap, vertex dup, edge flip)

The current Python `method="matching"` is a *different, coarser* algorithm — not faithful. The `method="faithful"` path is partially wired but incomplete (missing Ch 4 heuristics, recombination ops, and boundary-tri preference inversion).

### Q2: What does WNAT refer to?

**Answer:** Four WNAT fixtures exist in `tests/fixtures/meshes/`:
- `WNAT_53K_Nodes.14` (5.7MB, ~53k nodes) — **marked `*Error*` in MATLAB Main.m**
- `WNAT_Hagen.14` (5.7MB, same SHA as 53K — identical file)
- `WNAT_Onur.14` (16MB, ~130k+ nodes) — largest fixture
- `WNAT_Test.14` (1.2MB, ~10k nodes) — smaller test variant

The "WNAT domain" is the Western North Atlantic — complex coastal geometry with many islands, peninsulas, fjords. MATLAB itself crashes on the 53K mesh (*Error* comment in Main.m) suggesting path-closure failure in PathsOnOV.

### Q3: What is the MATLAB error on WNAT_53K?

**Answer:** The MATLAB comment `% *Error*.` next to `WNAT_53K_Nodes.14` (line 33 of Main.m) indicates MATLAB itself fails. Based on PathsOnOV structure, the most likely cause is: the `loopcounter > 1e5` loop guard trips — a layer path cannot be closed, printed as "Error: a path cannot be closed." This propagates as an unhandled error crash.

### Q4: Does the Python port implement the `idownEdgeID == 2` flip?

**Answer:** No. `identify_edges.py` at line ~163 does:
```python
idown = int(np.where(ordered == down_edge)[0][0])
if idown <= 1:
    up_edge = down_edge
    continue
interior = ordered[1:idown]
for j, eid in enumerate(interior):
    if j % 2 == 1:
        continue
```
The MATLAB does `if idownEdgeID == 2: sortedEdgeIDs = [s(1), fliplr(s(2:end))]` before the loop. The Python skips entirely when `idown <= 1` but never reverses the interior order when `idown == 2`. This changes which edges get flagged for layers where vertices have exactly one interior edge between up and down.

### Q5: Does the Python port compute `get_vertex_elements` correctly at scale?

**Answer:** In `identify_edges_in_layer` (line ~130):
```python
counts = np.array(
    [len(set(domain.get_vertex_elements(int(v))) & set(elem_ids.tolist()))
     for v in verts], dtype=int)
```
`elem_ids.tolist()` is called once per outer vertex — O(|OV_L| × |layer_elem_ids|). For WNAT with 53k nodes and many large layers, this is an O(n²) bottleneck.

---

## STAGE 3 — PLAN

### Implementation Plan for Faithful QuADMESH+ Layers

**Goal:** Complete the faithful Python port of the thesis algorithm so `method="faithful"` reproduces MATLAB QuADMESH+ output on all canonical fixtures including WNAT.

**Architecture target** (mirrors `Tri2QuadRoutine.m`):

```python
def tri2quad_routine(domain, can_remove_edges=True, parent=None, method="faithful"):
    if method == "matching":
        return _matching_path(...)  # existing fast fallback

    work = WorkingMesh(points=domain.points.copy(), quads=[])
    layer_state = LayerState.from_mesh(domain)  # snapshot OE/IE/OV/IV

    for iLayer in range(domain.n_layers, 0, -1):  # outward → inward (MATLAB: nLayers downto 1)
        sel = identify_edges_in_layer(domain, iLayer - 1)  # every-other-edge sweep
        pairs = get_pairs_from_removed_edges(sel)           # sub_mesh.edge2elem
        work.quads += merge_tri_pairs(sel, pairs)           # _topology.merge_tri_pairs
        remaining = get_remaining_elems(sel, pairs)
        for tri in remaining:
            route_leftover_tri_faithful(domain, work, tri, iLayer,
                                         on_mesh_boundary=...,
                                         can_remove_edges=can_remove_edges,
                                         layer_state=layer_state)
        if layer_state.mutated:
            domain.rebuild_adjacencies()
            layer_state.sync(domain)

    return _assemble_chilmesh(work, domain, parent)
```

**Five-phase plan:**

| Phase | Goal | Blocks |
|---|---|---|
| P0 | Build verification oracle (golden fixtures) | All |
| P1 | Fix identify_edges per MATLAB: `idown==2` flip, stable ordering, corner rotation | P2 |
| P2 | Wire `identify_edges_in_layer` into `method="faithful"` main loop with `merge_tri_pairs` | P3 |
| P3 | Add recombination ops (edge swap, vertex dup, edge flip) + flip boundary-tri preference | SC-003 |
| P4 | Performance hardening for WNAT scale | Production |

---

## STAGE 4 — TASKS

### T001 — Fix the every-other-edge skip in `identify_edges_in_layer`

**File:** `src/quadmesh/identify_edges.py`  
**Location:** ~line 163 (the interior edge loop)

**MATLAB behavior** — `identifyEdgesFun_v2.m:108–121`:
```matlab
for iEdge = 2:totalNumEdges-1   % ALL interior positions, no skip
    if sortedEdgeIDs(iEdge) == 0          % skip if flagged used
        continue
    end
    iEdgeElemIDs = edge2Elems(sortedEdgeIDs(iEdge),:);
    if any(iEdgeElemIDs == 0)             % skip if elems flagged
        continue
    end
    removedEdgeIDs(i_removedEdgeIDs) = sortedEdgeIDs(iEdge);
    vert2Edges(ismember(vert2Edges, removedEdgeIDs(1:i_removedEdgeIDs))) = 0;
    i_removedEdgeIDs = i_removedEdgeIDs + 1;
    edge2Elems(ismember(edge2Elems, iEdgeElemIDs)) = 0;
end
```

No `iEdge % 2 == 0` check. Every interior edge not already used is taken. The "every-other" name in the thesis refers to the alternating up/interior/down rhythm as the path advances vertex-by-vertex — NOT to skipping edges within a single vertex's fan.

**Fix needed:**
```python
# Current (wrong — skips half the interior edges):
for j, eid in enumerate(interior):
    if j % 2 == 1:
        continue

# Correct (take ALL interior edges; flagging prevents double-use):
for eid in interior:
    eid_i = int(eid)
    if edge_used[eid_i] or eid_i in b_edge_set or flagged_mask[eid_i]:
        continue
    pair = edge2elem[eid_i]
    if pair[0] < 0 or pair[1] < 0:
        continue
    if elem_used[int(pair[0])] or elem_used[int(pair[1])]:
        continue
    edge_used[eid_i] = True
    elem_used[int(pair[0])] = True
    elem_used[int(pair[1])] = True
    removed.append(eid_i)
```

**Acceptance:** `removed_edge_ids` on `simple_test_case.14` matches hand-derived golden.

---

### T002 — Apply `idown==2` reversal

**File:** `src/quadmesh/identify_edges.py`  
**Location:** after computing `idown`, before the interior loop

MATLAB `identifyEdgesFun_v2.m:86–88`:
```matlab
idownEdgeID = find(sortedEdgeIDs == downEdgeID);
if idownEdgeID == 2
    sortedEdgeIDs = [sortedEdgeIDs(1), fliplr(sortedEdgeIDs(2:end))];
end
```
When `idownEdgeID == 2`, MATLAB reverses from position 2 onward so the single interior edge between up and down is consistently at position 2 (first to be taken). The loop then picks it up on `iEdge=2`. Python does not implement this flip.

**Fix:**
```python
idown = int(np.where(ordered == down_edge)[0][0])
if idown <= 1:
    up_edge = down_edge
    continue
# Apply MATLAB idown==2 reversal: flip interior ordering when single interior edge
if idown == 2:
    # Reverse positions [1:] of ordered so position 1 stays as is
    ordered = np.concatenate([ordered[:1], ordered[1:][::-1]])
    idown = int(np.where(ordered == down_edge)[0][0])
interior = ordered[1:idown]
```

---

### T003 — Fix O(n²) corner-rotation in `identify_edges_in_layer`

**File:** `src/quadmesh/identify_edges.py`  
**Location:** ~line 124 (corner rotation block)

**Performance fix** — replace O(n²) set intersection per vertex with a precomputed elem-set:

```python
# Current O(|OV| × |layer_elems|) — re-creates set(elem_ids.tolist()) per vertex:
counts = np.array(
    [len(set(domain.get_vertex_elements(int(v))) & set(elem_ids.tolist()))
     for v in verts], dtype=int)

# Fast O(|OV| + |layer_elems|) — compute elem_id_set once:
elem_id_set = set(int(e) for e in elem_ids)
counts = np.array(
    [sum(1 for e in domain.get_vertex_elements(int(v)) if e in elem_id_set)
     for v in verts], dtype=int)
```

At WNAT scale (~53k nodes, layers with thousands of elements), reduces from O(|OV| × |layer|) to O(|OV| + |layer|).

---

### T004 — Wire `identify_edges_in_layer` into `method="faithful"` main loop

**File:** `src/quadmesh/tri2quad.py`  
**Location:** `tri2quad_routine`, the `method == "faithful"` branch

Current state: `method="faithful"` calls `_sweep_pairs(domain)` → returns `(seed_pairs, flagged)` → feeds global `_match_tris_to_quads`. The MATLAB per-layer sequential structure (identify → merge → route → rebuild) is not implemented.

The MATLAB `Tri2QuadRoutine.m` critical structure:
```matlab
newMesh = struct('Points', Domain.Points, 'ConnectivityList', []);
for iLayer = Domain.nLayers:-1:1
    [Domain, subDomain, ElemIDs, ~, bEdgeIDs, bVertIDs, removedEdgeIDs] = ...
        identifyEdgesFun_v2(Domain, iLayer);
    pairElemIDs = subDomain.edge2Elem(removedEdgeIDs(removedEdgeIDs > 0));
    newMesh.ConnectivityList = [newMesh.ConnectivityList; ...
        mergeTrianglesFun(subDomain, pairElemIDs)];
    remainingElemIDs = ElemIDs(~ismember(ElemIDs, ElemIDs(pairElemIDs)));
    [Domain, newMesh] = removeTrianglesFun(CM, Domain, subDomain, newMesh, ...);
    newMesh.Points = Domain.Points;
end
```

**Required Python equivalent:**
```python
work = WorkingMesh(points=domain.points.copy(), quads=[])
for iLayer in range(domain.n_layers, 0, -1):
    layer_idx = iLayer - 1  # 0-based Python layer index
    sel = identify_edges_in_layer(domain, layer_idx)
    if sel.sub_mesh is None or sel.removed_edge_ids.size == 0:
        continue

    # Get elem pairs from removed edges (sub-mesh Edge2Elem)
    e2e = sel.sub_mesh.adjacencies["Edge2Elem"]
    glob = sel.elem_ids_global
    paired_local: Set[int] = set()
    for eid in sel.removed_edge_ids:
        row = e2e[int(eid)]
        a, b = int(row[0]), int(row[1])
        if a < 0 or b < 0:
            continue
        quad = merge_tri_pair(sel.sub_mesh, a, b)  # _topology
        if quad is not None:
            work.add_quad(remap_to_global(quad, glob))
            paired_local.add(a)
            paired_local.add(b)

    # Route remaining (unmatched) triangles
    remaining_global = [glob[i] for i in range(len(glob)) if i not in paired_local]
    for tri_id in remaining_global:
        route_leftover_tri(domain, work, tri_id, layer_idx, ...)

    if layer_state.mutated:
        domain.rebuild_adjacencies()
        layer_state.sync(domain)
```

---

### T005 — Implement edge swap, vertex duplication, edge flip (CR-2)

**File:** `src/quadmesh/_tri_removal.py`

Three operations from thesis Ch 3 required for faithful leftover-tri clearing:

**Edge Swap (Fig 3.2):** Two tris sharing vertex `s` with one quad between them in a tri-quad-tri fan → swap interior edges so the tris become edge-adjacent → merge into a quad. Currently implemented as `_edge_swap_tri_pairs` in `tri2quad.py` (post-hoc only); needs to be callable from `route_leftover_tri` during the per-layer sweep.

**Vertex Duplication (Fig 3.3):** Duplicate a shared vertex `s` to split a fan of tris so each tri gets its own copy → tris pair off into quads. Not implemented anywhere.

**Edge Flip + walk (Fig 3.6, 4.4):** Flip the diagonal of a quad adjacent to an isolated tri → tri moves one step. Chain flips until the isolated tri reaches a partner, then merge. Not implemented. Used in the boundary layer to improve walkability before matching.

---

### T006 — Flip boundary-tri op preference (CR-4)

**File:** `src/quadmesh/_tri_removal.py`, `route_leftover_tri`

Current preference: edge_removal (squeeze) → edge_bisection → drop  
Thesis preference (p70): **edge_insertion (add point) → edge_swap → edge_removal (last resort)**

Specific changes:
- `n_bdy == 0, on_mesh_boundary == True` (IE_L leftover): `edge_insertion` case 1 should do full MATLAB fan retriangulation of iLayer-1, not the current 1/3-heuristic
- `n_bdy == 1, can_remove_edges` (OE_L leftover): try edge swap first (if vertex-sharing partner exists), then edge removal as fallback

---

### T007 — Add `LayerState` dataclass for mutable layer tracking

**File:** `src/quadmesh/tri2quad.py` or `src/quadmesh/_tri_removal.py`

```python
@dataclass
class LayerState:
    oe: List[np.ndarray]  # per-layer outer elements
    ie: List[np.ndarray]  # per-layer inner elements
    ov: List[np.ndarray]  # per-layer outer vertices
    iv: List[np.ndarray]  # per-layer inner vertices
    mutated: bool = False

    @classmethod
    def from_mesh(cls, domain: CHILmesh) -> 'LayerState':
        layers = domain.layers
        nl = domain.n_layers
        return cls(
            oe=[np.asarray(layers["OE"][i]) for i in range(nl)],
            ie=[np.asarray(layers["IE"][i]) for i in range(nl)],
            ov=[np.asarray(layers["OV"][i]) for i in range(nl)],
            iv=[np.asarray(layers["IV"][i]) for i in range(nl)],
        )

    def sync(self, domain: CHILmesh) -> None:
        layers = domain.layers
        nl = domain.n_layers
        for i in range(nl):
            self.oe[i] = np.asarray(layers["OE"][i])
            self.ie[i] = np.asarray(layers["IE"][i])
        self.mutated = False
```

Insertion ops mutate layer membership; `LayerState` tracks mutations so `rebuild_adjacencies()` is called once per layer, not once per op.

---

### T008 — Build verification oracle (Phase 0)

**File:** `tests/golden/` (new directory)

Procedure:
1. Probe `.mat` files in `03_CHILMesh_Test_Cases/02_.m_Files/` with `scipy.io.loadmat`; if v7.3 use `h5py`
2. Attempt GNU Octave headless run with `plotProgress=false` (high risk — CHILmesh class is custom)
3. Fallback: hand-derive golden `removed_edge_ids` on `structuredMesh1.14` by manual path tracing

Golden format — JSON per fixture per stage:
```json
{
  "fixture": "structuredMesh1.14",
  "n_layers": 3,
  "layer_0": {"removed_edge_vertex_pairs": [[1,2],[3,4]], "n_quads": 12},
  "after_tri2quad": {"n_elems": 48, "quad_frac": 1.0, "mean_quality": 0.81}
}
```

---

### T009 — Fix `_point_insert_tri_pairs` for WNAT concave regions

**File:** `src/quadmesh/tri2quad.py`  
**Location:** `_point_insert_tri_pairs`

Current: centroid + 4×4 grid scan (17 candidates total). For concave WNAT bays, the centroid and grid may all fall outside the concave pentagon.

**Fix:** Expanded candidate set:
```python
# Add pentagon diagonal midpoints (5 more candidates)
mids = [(LP[i] + LP[(i+2)%5]) / 2 for i in range(5)]
cand += mids

# Add inward-offset candidates along edge normals
for i in range(5):
    edge_mid = (LP[i] + LP[(i+1)%5]) / 2
    inward = centroid - edge_mid
    inward_norm = inward / (np.linalg.norm(inward) + 1e-12)
    for t in [0.1, 0.2, 0.3, 0.4]:
        cand.append(edge_mid + t * inward_norm * np.linalg.norm(LP.max(0) - LP.min(0)))
```

---

## STAGE 5 — ANALYZE: Python Port Audit on WNAT Domain

### Overview

WNAT (`WNAT_53K_Nodes.14`, `WNAT_Hagen.14`, `WNAT_Onur.14`, `WNAT_Test.14`) is the Western North Atlantic coastal mesh — large (5–16MB), topologically complex (many islands, fjords, peninsulas), and explicitly marked `*Error*` in MATLAB Main.m for the 53K variant.

The Python port (`method="matching"`, the current default) avoids layer-path computation and may complete where MATLAB fails. But multiple bugs and performance issues still affect WNAT at scale.

---

### WNAT Bug 1 (CRITICAL): Every-other-edge sweep takes wrong edges

**File:** `src/quadmesh/identify_edges.py` lines ~155–175  
**Severity:** CRITICAL — wrong algorithm, produces wrong quad topology on all meshes

**Root cause:** The Python port applies `j % 2 == 1: continue` inside the interior edge loop, taking every **other** interior edge between up and down. MATLAB's `identifyEdgesFun_v2.m` loop `for iEdge = 2:totalNumEdges-1` takes **all** interior edges between up and down positions. The flagging of used elements (`edge2Elems(...) = 0`) prevents double-merging — no skip needed.

**Evidence from MATLAB source** (`identifyEdgesFun_v2.m:108–121`):
```matlab
for iEdge = 2:totalNumEdges-1   % ALL interior positions
    if sortedEdgeIDs(iEdge) == 0
        continue                 % skip ONLY if flagged used
    end
    iEdgeElemIDs = edge2Elems(sortedEdgeIDs(iEdge),:);
    if any(iEdgeElemIDs == 0)
        continue                 % skip ONLY if elems flagged
    end
    removedEdgeIDs(i_removedEdgeIDs) = sortedEdgeIDs(iEdge);
    % flag edges and elems used
```
No `iEdge % 2 == 0` guard. Every interior edge not already consumed is taken.

**Impact on WNAT:** WNAT has high-valence vertices (coastal geometry → many incident edges per vertex). For a vertex with 5 interior edges between up and down, MATLAB takes all 5; Python takes only edges at indices 0, 2, 4 (~50% fewer). This leaves far more leftover tris per layer, overwhelming the incomplete `route_leftover_tri` path.

**Fix:**
```python
# In identify_edges.py, replace:
for j, eid in enumerate(interior):
    if j % 2 == 1:
        continue
    # ... rest of loop

# With:
for eid in interior:  # take ALL, flagging prevents double-use
    eid_i = int(eid)
    if edge_used[eid_i] or eid_i in b_edge_set or flagged_mask[eid_i]:
        continue
    pair = edge2elem[eid_i]
    if pair[0] < 0 or pair[1] < 0:
        continue
    if elem_used[int(pair[0])] or elem_used[int(pair[1])]:
        continue
    edge_used[eid_i] = True
    elem_used[int(pair[0])] = True
    elem_used[int(pair[1])] = True
    removed.append(eid_i)
```

---

### WNAT Bug 2 (CRITICAL): `method="faithful"` is a hybrid, not the MATLAB algorithm

**File:** `src/quadmesh/tri2quad.py` lines ~404–423  
**Severity:** CRITICAL — `method="faithful"` does NOT implement MATLAB's per-layer sweep

**Root cause:** The `method="faithful"` branch calls `_sweep_pairs(domain)` → returns `(seed_pairs, flagged)` → passes to global `_match_tris_to_quads`. This means:
1. Seed pairs guide the global interior-saturating matcher
2. The augmenting-path fixup then overrides many seeds to guarantee interior saturation
3. `route_leftover_tri` is **never called** — `_remove_boundary_tris` handles residuals

MATLAB does: per-layer `identifyEdgesFun_v2` → per-layer `mergeTrianglesFun` → per-layer `removeTrianglesFun` → points update. The per-layer sequential merge+route cycle is entirely absent from the Python `method="faithful"` path.

**Impact on WNAT:** `method="faithful"` on WNAT behaves identically to `method="matching"` (plus a priority hint). Quality stays at ~0.739 vs thesis 0.81+.

**Fix:** Implement the true per-layer loop (T004).

---

### WNAT Bug 3 (HIGH): O(n²) per-vertex set intersection in `identify_edges_in_layer`

**File:** `src/quadmesh/identify_edges.py` lines ~124–131  
**Severity:** HIGH performance

```python
counts = np.array(
    [len(set(domain.get_vertex_elements(int(v))) & set(elem_ids.tolist()))
     for v in verts], dtype=int)
```

`set(elem_ids.tolist())` is re-created for every outer vertex — O(|OV_L| × |layer_elems|). For a WNAT layer with 500 OV and 1000 elements: 500k operations × n_layers.

**Fix:** T003 — pre-compute `elem_id_set = set(int(e) for e in elem_ids)` once per layer call.

---

### WNAT Bug 4 (HIGH): Full points array copied per layer sub-mesh

**File:** `src/quadmesh/identify_edges.py` line ~75  
**Severity:** HIGH memory

```python
sub_mesh = CHILmesh(
    sub_conn,
    domain.points.copy(),  # copies ALL 53k points, not just layer's ~500
    ...
)
```

For WNAT: 53k nodes × 3D × float64 = ~1.3MB per copy × 50+ layers = 65MB+ in copies. More critically, CHILmesh adjacency tables over 53k points are far larger than needed for a layer-local sub-mesh.

**Fix:** Slice to layer vertices only before constructing sub-mesh:
```python
used_verts = np.unique(sub_conn.ravel())
local_pts = domain.points[used_verts]
remap = np.full(domain.points.shape[0], -1, dtype=int)
remap[used_verts] = np.arange(used_verts.size)
local_conn = remap[sub_conn]
sub_mesh = CHILmesh(local_conn, local_pts, compute_layers=False, compute_adjacencies=True)
# Downstream index translation: local → global via used_verts[local_id]
```

---

### WNAT Bug 5 (HIGH): PathsOnOV loop guard causes silent truncation

**File:** `matlab/quadmesh/03_Layer_Paths/PathsOnOV.m` (+ chilmesh `paths_on_outer_vertices`)  
**Severity:** HIGH — root cause of MATLAB's `*Error*` on WNAT_53K

**Root cause:** PathsOnOV.m's `while true` loop has `if loopcounter > 1e5: break` with a `disp` (not an exception). For WNAT's complex topology (non-Eulerian outer vertex graph in some layers → path cannot close), MATLAB bails silently after 100k iterations. The returned partial path causes wrong edge selection in subsequent identifyEdgesFun_v2 → eventual crash.

**Python impact:** The `_sweep_pairs` function wraps all per-layer work in `try/except Exception: seed, forbidden = None, None`. If chilmesh's `paths_on_outer_vertices` raises on WNAT, the faithful path silently degrades to pure greedy. If it silently truncates (returns partial path), `identify_edges_in_layer` uses a wrong path → wrong removed_edge_ids.

**Fix:**
1. Audit chilmesh `paths_on_outer_vertices` for loop guard behavior and partial-path returns
2. Add pre-validation: check each layer's OV adjacency graph for Euler path existence before path construction
3. For WNAT specifically: log a warning when path construction fails for a layer; skip that layer (continue with next)

---

### WNAT Bug 6 (MEDIUM): `_edge_swap_tri_pairs` O(n²) rebuild per iteration

**File:** `src/quadmesh/tri2quad.py` lines ~268–332  
**Severity:** MEDIUM performance

```python
def candidates():
    v2e: Dict[int, Set[int]] = {}
    for ei, e in enumerate(elems):  # O(n_elems) rebuild each call
        for v in set(e):
            v2e.setdefault(v, set()).add(ei)
```

For `method="matching"` on WNAT, the matching path leaves very few leftover tris — this is called on a tiny array. For the correct `method="faithful"` per-layer sweep (T004), each layer may have O(n_layer) leftovers, calling this once per layer × 50+ layers on WNAT.

**Fix:** Incremental v2e update: after each swap removes elems `{i, j, q}` and adds `{q1, q2}`, update v2e in O(elem_size) rather than rebuilding.

---

### WNAT Bug 7 (MEDIUM): Squeeze distorts WNAT coastline boundary

**File:** `src/quadmesh/tri2quad.py` lines ~196–260 (`_remove_boundary_tris`)  
**Severity:** MEDIUM correctness — violates thesis priority order for WNAT coastal applications

The matching path leaves boundary tris and squeezes (`n_bdy==1` tris): collapses two coastal vertices to their midpoint. For WNAT:
- Squeeze moves coastline vertices inward → domain shrinks
- Multiplied across thousands of WNAT boundary tris → significant coastline distortion
- `_quad_ok` prevents bowties but NOT boundary shrinkage
- Coastline fidelity is critical for hydrodynamic models (ADCIRC, etc.)

Thesis p70: prefers adding a point (preserving boundary) over removing one.

**Fix:** For `method="matching"` on WNAT, set `minimize_boundary_change=True` as default. This drops residual boundary tris rather than squeezing them — quad-dominant output but coastline intact. Full fix: implement edge_insertion case 1 (T006).

---

### WNAT Bug 8 (MEDIUM): `_point_insert_tri_pairs` fails in concave WNAT bays

**File:** `src/quadmesh/tri2quad.py` lines ~343–407  
**Severity:** MEDIUM correctness — leaves residual tris in WNAT concave regions

For WNAT fjords and bays, a pentagon formed by a lone tri + neighboring quad may be highly concave. The current 17-candidate scan (centroid + 4×4 grid) has low probability of finding a valid interior point inside a concave WNAT pentagon. `_quad_ok` rejects all invalid placements → tri left as residual → quad-dominant, not quad-pure.

**Fix:** T009 — expanded candidate set including pentagon diagonal midpoints + inward-normal offsets.

---

### WNAT Bug 9 (LOW): No progress feedback or timeout at WNAT scale

**File:** `src/quadmesh/tri2quad.py`  
**Severity:** LOW — WNAT runs may appear to hang with no output

For `WNAT_Onur.14` (~130k nodes), `_match_tris_to_quads` + heap is O(n log n) but the `augment` BFS is O(n) per interior unmatched tri. No progress logging, no timeout, no cancellation.

**Fix:** Optional `progress_callback(layer_idx, n_layers, n_quads_so_far)` parameter; per-layer log in faithful loop; BFS depth cap (e.g., 10k nodes).

---

### WNAT Bug 10 (LOW): No awareness of WNAT_53K known failure

**File:** `src/quadmesh/pipeline.py`  
**Severity:** LOW informational

MATLAB Main.m marks `WNAT_53K_Nodes.14` as `*Error*`. Python pipeline runs until OOM or hang with no informative message.

**Fix:** Pre-flight check — if `create_quad_domain` returns a mesh with `n_layers < 1`, raise `ValueError("mesh layers could not be computed")`. Log a warning for meshes with `n_elems > 50000` about expected runtime and known WNAT topology issues.

---

### Summary Table — WNAT Audit

| ID | Severity | Component | Bug | Fix Task |
|---|---|---|---|---|
| W1 | CRITICAL | `identify_edges.py:163` | Python skips j%2==1; MATLAB takes ALL interior edges | T001 |
| W2 | CRITICAL | `tri2quad.py:405-423` | `method="faithful"` is hybrid seeded matcher, not MATLAB per-layer loop | T004 |
| W3 | HIGH | `identify_edges.py:124` | O(n²) set intersection per vertex in corner rotation | T003 |
| W4 | HIGH | `identify_edges.py:75` | Full domain.points copied per layer sub-mesh (~1.3MB × n_layers) | T004 |
| W5 | HIGH | chilmesh `paths_on_outer_vertices` | Loop guard truncates WNAT paths; root cause of MATLAB *Error* | T008 |
| W6 | MEDIUM | `tri2quad.py:268` | `_edge_swap_tri_pairs` O(n²) v2e rebuild per fixpoint iteration | T005 |
| W7 | MEDIUM | `tri2quad.py:196` | Squeeze distorts WNAT coastline; inverts thesis op preference | T006 |
| W8 | MEDIUM | `tri2quad.py:343` | Centroid/grid fails for concave WNAT bay pentagons | T009 |
| W9 | LOW | `tri2quad.py` | No progress/timeout for WNAT-scale runs | — |
| W10 | LOW | `pipeline.py` | No warning for known WNAT_53K failure mode | — |

### Critical Path to WNAT Correctness

**For `method="matching"` on WNAT today:** W1/W3/W4 don't apply (no layer-path code runs). W7 and W8 are the active bugs. WNAT with `method="matching"` should complete but with coastline distortion (W7) and potential residual tris near concave bays (W8).

**For `method="faithful"` on WNAT today:** All W1–W10 active. W1 is most impactful — wrong topology on every layer. W2 means no per-layer routing. W3+W4 cause slowness. W5 may cause path truncation.

**Fix priority order:**
1. **W1** — fix every-other-edge bug (`j%2==1` removal). Fundamental to correct topology.
2. **W5** — ensure path completeness for WNAT multi-island topology.
3. **W3+W4** — performance: pre-compute elem_id_set; slice sub-mesh points.
4. **W2** — implement true faithful per-layer loop (T004). Unlocks quality recovery.
5. **W7** — for production coastline fidelity: prefer point-insertion over squeeze.

---

## Cross-Reference: MATLAB vs Python

| MATLAB Function | Python Equivalent | Status | Key Divergence |
|---|---|---|---|
| `Main.m` | `pipeline.run_pipeline` | ✅ wired | GUI removed; `method="matching"` default |
| `createQuadDomain.m` | `create_quad_domain.py` | ✅ OK | Polygon strategy only (GUI strategies dropped) |
| `PathsOnOV.m` | `chilmesh.paths_on_outer_vertices` | ⚠️ delegated | chilmesh may not handle WNAT multi-path topology (W5) |
| `identifyEdgesFun_v2.m` | `identify_edges.identify_edges_in_layer` | ❌ WRONG | Every-other-edge bug W1; `idown==2` flip missing T002 |
| `mergeTrianglesFun.m` | `_topology.merge_tri_pairs` | ⚠️ built, not wired | Only called from `repair.py` and tests |
| `removeTrianglesFun.m` | `_tri_removal.route_leftover_tri` | ⚠️ partial, not wired | Preference inverted (T006); `edge_insertion` case 2 incomplete |
| `Tri2QuadRoutine.m` (main loop) | **NOT implemented** | ❌ MISSING | `method="faithful"` is hybrid; true per-layer loop absent (W2/T004) |
| `PostProcessRoutine.m` | `post_process.post_process_routine` | ✅ faithful | Post-process by layer (CR-7) not done but non-critical |
| `DoubletCollapse.m` | `doublet_collapse.doublet_collapse` | ✅ OK | — |
| `QuadVertexMerge_v2.m` | `quad_vertex_merge.quad_vertex_merge` | ✅ OK | — |
| `CleanupBoundaryQuads_v2.m` | `cleanup_boundary_quads.cleanup_boundary_quads` | ✅ OK | — |
| `RemoveUnusedVertices.m` | `remove_unused.remove_unused` | ✅ OK | — |
| Edge Swap (Fig 3.2) | `_edge_swap_tri_pairs` | ⚠️ post-hoc only | Not wired into per-layer `route_leftover_tri` |
| Vertex Duplication (Fig 3.3) | ❌ NOT IMPLEMENTED | MISSING | CR-2 gap |
| Edge Flip + walk (Fig 3.6, 4.4) | ❌ NOT IMPLEMENTED | MISSING | CR-2 gap |

---

## Appendix: MATLAB identifyEdgesFun_v2 vs Python identify_edges_in_layer — Line-by-Line

| Aspect | MATLAB (`identifyEdgesFun_v2.m`) | Python (`identify_edges.py`) | Diverges? |
|---|---|---|---|
| Sub-mesh construction | `CHILmesh(CL(ElemIDs,:), Points)` | `CHILmesh(sub_conn, domain.points.copy(), ...)` | Minor — Python copies full points (W4) |
| OV path source | `PathsOnOV(iLayer, Domain)` — local impl | `paths_on_outer_vertices(domain, layer_idx)` — chilmesh | Delegated (W5) |
| Corner rotation | `find(vert2Elem size == 1)` on OV verts | `counts == 1` with O(n²) set intersection | Same logic, wrong perf (W3) |
| Boundary edge filter | `sum(ismember(bVertIDs, VertIDs), 2) == 0` removes IV edges | `keep_mask` with OV_set check | Same logic |
| CCW edge sort | `CCWEdgesAroundVertsFun` → precomputed `vert2Edges` matrix | `ccw_edges_around_vert` called per-vertex | Functionally same |
| up/down edge seeding | `bEdgeIDs(ismember(..., pathVertIDs(1:2)) == 2)` with 1-match fallback | `_find_boundary_edge(b_edges, b_e2v, cur_v, nxt_v)` | Same intent |
| `idown == 2` reversal | `fliplr(sortedEdgeIDs(2:end))` applied before loop | **NOT IMPLEMENTED** | **BUG (T002)** |
| Interior edge loop | `for iEdge = 2:totalNumEdges-1` — **ALL** interior edges | `for j, eid in enumerate(interior): if j%2==1: continue` — HALF | **CRITICAL BUG (W1)** |
| Elem flagging after take | `edge2Elems(ismember(...)) = 0` | `elem_used[...] = True` | Same logic |
| Edge flagging after take | `vert2Edges(ismember(...)) = 0` | `edge_used[...] = True` | Same logic |
| Return value | `removedEdgeIDs, bEdgeIDs, bVertIDs, subDomain, ElemIDs` | `LayerEdgeSelection` dataclass | Python is richer |
