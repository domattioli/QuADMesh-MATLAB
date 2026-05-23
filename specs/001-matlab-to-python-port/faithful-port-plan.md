# Faithful QuADMESH+ Python Port — Implementation Plan

**Status:** plan only (no impl). Supersedes the scattered notes in `plan.md` /
`tasks.md` / `case-2-design.md` for the *faithfulness* effort specifically.
**Author:** session 2026-05-23 (post quad-pure + bowtie-safe boundary work).
**Owns:** issue #25 (faithful `removeTrianglesFun` port). Related: #26 (field-guided pairing).

> **Cross-referenced against the source thesis** — Mattioli, *QuADMESH+: A
> Quadrangular ADvanced Mesh Generator* (M.S., Ohio State), `docs/Mattioli_Thesis.pdf`
> (committed at dd3ff03). Section 0 records the corrections this forced.

---

## 0. Thesis cross-reference — corrections to the rest of this plan

Reading the thesis (Ch 3 "Building an Indirect Method", Ch 4 "Matching
Algorithms", Ch 5 "Post-Processing By Layer", + figures) overturns the central
premise the rest of this doc was written on. **Where Sections 1–11 below
disagree with this section, this section wins.**

### CR-1 (CRITICAL) — the faithful method is heuristic MATCHING, not every-other-edge
The thesis abstract (p3) and Ch 4 define QuADMESH+ as *"a heuristic
decision-making algorithm for matching two triangular elements together."* It is
a **layered, two-stage, priority-driven triangle matching**, worked **innermost
layer → outward to the boundary**. My earlier framing — "matching = the
unfaithful shortcut, `identifyEdgesFun_v2` every-other-edge = the faithful
method" — is **backwards**. Consequences:
- The current Python interior-saturating matching is a *crude approximation* of
  the thesis algorithm (interior-first ≈ IE-before-OE; most-constrained ≈
  fewest-eligible-neighbors). It is **directionally faithful**, not a divergent hack.
- The shipped MATLAB `identifyEdgesFun_v2` (every-other-edge along a path) is a
  *simpler realization* than the Ch 4 heuristic. **Open reconciliation:** is the
  repo MATLAB a production simplification of the thesis, or a different vintage?
  The thesis is the authoritative spec; the MATLAB is one implementation of it.
  Verify per-layer behavior against both.

### CR-2 — three operations are missing from this plan entirely
The thesis relies on recombination ops this plan never mentioned:
- **Edge Swap** (Fig 3.2, p39) — two tris sharing **one vertex** → reconnect the
  diagonal so they share an **edge** → mergeable into a quad. From Remacle et al.
- **Vertex Duplication** (Fig 3.3, p39) — duplicate a shared vertex to split a
  tri fan so tris pair off.
- **Edge Flip / "walking"** (Fig 3.6 p40, Fig 4.4 p69) — flip edges along a
  walkable path to *move* an isolated triangle toward a partner until they share
  an edge, then merge (Fig 3.6c). Used in the boundary layer to fix walkability.

### CR-3 — matching is TWO stages with OPPOSITE priorities
- **Interior layers (Ch 4.1):** match **IE_L before OE_L** (only IE_L can become
  isolated; OE_L can still match inter-layer with L−1). Exhaust all intra-layer
  matchings before any inter-layer L↔L−1. T1 selection = fewest eligible
  neighbors first; explicit T1/T2 tiebreaker ladders (p64–66).
- **Boundary layer (Ch 4.2):** **OE_L before IE_L** (opposite!) — try to leave the
  last unmatched tri as an IE_L, which is removable cleanly by *adding* a
  boundary point. Pre-process: **edge-flip** the leftover RE_L + a neighbor to
  improve walkability before matching.

### CR-4 — boundary-tri op preference is INVERTED in the current code
Thesis (p70): *"a more appealing outcome of manipulating a mesh boundary involves
the addition of a point rather than the removal of one — added resolution is
better than diminished resolution."* Preference order:
1. **Edge insertion / add boundary point** (Fig 3.4) — IE_L tri → quad. **Preferred.**
2. Edge swap / vertex duplication — if two tris share a vertex.
3. Edge collapse / removal (Fig 3.5) — OE_L fallback only.

The current `_remove_boundary_tris` does **squeeze (collapse) + drop** — i.e. the
*least* preferred ops, never the preferred point-insertion. This is the prime
suspect for our low quality (0.739 vs thesis greedy 0.8095).

### CR-5 — isolated-tri handling = intentional pairing + edge-swap fixup
Thesis (p66): when a tri unintentionally isolates, *intentionally* isolate
another unmatched tri that **shares a vertex** with it (form a "pair"), then after
the whole matching completes, apply an **edge-swap recombination** to the pair.
Current code uses an augmenting-path fixup instead — correct for zero-interior,
but not the thesis mechanism.

### CR-6 — quad-pure is NOT always achievable, and that's by design
Perfect matching (Edmonds' Blossom, Remacle) yields fully-quad meshes *only when a
perfect matching exists* — it often doesn't (odd # of boundary vertices, Fig 3.7),
and Blossom is too slow for large meshes (p42). QuADMESH+ deliberately chooses
heuristic matching + boundary point-insertion, **accepting ≤1 residual tri** in
the typical case. So our "always quad-pure" guarantee is *more aggressive than the
thesis*; faithful behavior is "minimize residual, add a point to clear the last
IE_L," not "force zero at any cost." Keep our quad-pure result as a *feature*, but
do not treat residual-tri as failure when reproducing thesis numbers.

### CR-7 — post-processing is applied BY LAYER
Ch 5.2: Doublet Collapse + Quad Vertex Merge are applied **per layer with
prioritization** (QVM creates quad strips; 5-quad sets can overlap, so ordering
matters). Current `post_process_routine` applies them globally. Faithful = layered.

### CR-8 — quality reference points (from the thesis)
- Greedy approach: 2417 tris → 1087 quads + 255 residual tris, **0.8095** mean
  quality after smoothing (p38). Original triangular mesh: 0.913.
- Our current matching+squeeze: **0.739**. Below even the Greedy baseline → our
  pairing heuristic is cruder than thesis Greedy *and* our boundary collapse hurts.
  Target after a faithful port: ≥ 0.81.

### Net effect on the plan below
- Section 1's "same pairing algorithm: every-other-edge" → **wrong**; replace with
  the Ch 4 two-stage heuristic matching.
- The biggest faithfulness lever is **not** "wire the every-other-edge sweep"; it is
  (a) implement the Ch 4 T1/T2 heuristic matching, (b) add edge-swap / edge-flip /
  vertex-duplication, (c) flip the boundary-tri op preference to point-insertion.
- The existing Python matching is a viable *starting point* to evolve toward the
  thesis heuristic, rather than something to discard for the every-other-edge sweep.

---

## 1. What "faithful" means (definition of done)

A faithful port reproduces the MATLAB QuADMESH+ pipeline (`02_QuADMESH_Library/00_Main/Main.m`)
**algorithmically**, not merely producing *some* valid quad mesh:

1. **Same pipeline shape:** `createQuadDomain → Tri2QuadRoutine (layer sweep) → PostProcessRoutine`.
2. **Same pairing algorithm:** the Ch 4 **two-stage layered heuristic matching**
   (interior layers IE-before-OE; boundary layer OE-before-IE), worked
   innermost→outward, with the documented T1/T2 tiebreaker ladders — *plus* the
   recombination ops Edge Swap, Vertex Duplication, Edge Flip (see CR-1, CR-2,
   CR-3). (NB: the shipped MATLAB realizes the per-layer step as `identifyEdgesFun_v2`
   every-other-edge; reconcile against the thesis heuristic — CR-1.)
3. **Same leftover-tri handling:** boundary tris cleared with **point-insertion
   preferred** (add boundary point → quad), edge-swap/vertex-duplication when two
   tris share a vertex, and edge-collapse only as fallback (CR-4) — *not* the
   squeeze/drop the current code uses. Accept the thesis's ≤1-residual behavior
   (CR-6); our zero-residual result is a bonus, not the parity criterion.
4. **Verified parity:** output element count, quad fraction, and mean quality
   match MATLAB ground truth within a tight tolerance (target ±2% count, ±0.02
   quality) on the canonical fixtures, **not** pinned to our own Python output.

Acceptance gate (all must hold on Test_Case_1/2/3, Block_O, + WNAT 98k for perf):
- [ ] quad-pure (0 residual tris), 0 bowties, conforming (max edge-share 2), 0 flipped/degenerate.
- [ ] mean quality ≥ MATLAB baseline (expected ~0.79+, vs current matching 0.739).
- [ ] per-layer `removed_edge_ids` deterministically reproduce the documented
      every-other-edge selection (algorithmic parity, layer by layer).
- [ ] parity tests assert against **captured MATLAB ground truth**, not Python regression baselines.

---

## 2. Current-state audit (honest)

Two tri2quad codepaths exist. The **live** one is a shortcut; the **faithful**
one is built but unwired.

| MATLAB | Python | Wired into live path? | Faithfulness |
|---|---|---|---|
| `createQuadDomain.m` | `create_quad_domain.py` | yes (pipeline) | OK |
| `Tri2QuadRoutine.m` (layer sweep) | `tri2quad.tri2quad_routine` | **live = matching, NOT the sweep** | **divergent** |
| `identifyEdgesFun_v2.m` | `identify_edges.identify_edges_in_layer` | **no — only `test_identify_edges.py` calls it** | built, unit-tested, unverified vs MATLAB |
| `mergeTrianglesFun` | `_topology.merge_tri_pair(s)` | no (only `repair.py` + tests) | built |
| `removeTrianglesFun.m` | `_tri_removal.route_leftover_tri` | **no — only `test_tri_removal.py`** | partial |
| `edgeRemoval.m` | `_tri_removal.edge_removal` | (live uses a *separate* squeeze in `tri2quad._remove_boundary_tris`) | done (two impls!) |
| `edgeBisection.m` | `_tri_removal.edge_bisection` | no | partial (no opposite-tri split) |
| `edgeInsertion.m` | `_tri_removal.edge_insertion` | no | partial (no iLayer-1 retri; case-3 = drop) |
| `PostProcessRoutine.m` | `post_process.post_process_routine` | yes | faithful to MATLAB's *active* steps |
| `DoubletCollapse` / `QuadVertexMerge_v2` / `CleanupBoundaryQuads_v2` / `RemoveUnusedVertices` / `FEMSmooth`+`MCSmooth` | respective modules | yes | OK |

**Live tri2quad today** = interior-saturating matching (`_match_tris_to_quads`)
+ boundary-tri squeeze/drop (`_remove_boundary_tris`, bowtie-safe as of `a46adf0`).
Quad-pure, conforming, 0 bowties — but **different topology and lower quality**
than MATLAB, and the leftover handling is the simplified on-boundary subset
(squeeze/drop), not the full insertion/retri.

**Key consequence for effort:** the faithful port is mostly a **wire-and-complete**
job (the hard parsing/skeleton/path code already exists and is unit-tested),
plus a **verification harness** that did not previously exist. It is *not* a
greenfield rewrite.

---

## 3. Gap analysis

| ID | Gap | Why it breaks faithfulness | Severity |
|---|---|---|---|
| **G1** | Pairing heuristic is crude vs thesis Ch 4 (no IE/OE priority, no T1/T2 tiebreakers, single-stage not interior+boundary) | Different quad topology; quality 0.739 vs thesis 0.81+ (CR-1, CR-3) | high |
| **G1b** | **Edge Swap / Vertex Duplication / Edge Flip not implemented** | Core QuADMESH+ ops for isolated/remaining tris + walkability absent (CR-2, CR-5) | high |
| **G1c** | Boundary-tri op preference inverted (squeeze/drop, not point-insertion) | Lowers quality; non-faithful boundary topology (CR-4) | high |
| **G2** | `removeTrianglesFun` insertion ops + iLayer-1 retri unported | Boundary/interior leftover tris handled by squeeze/drop, not MATLAB insertion | high |
| **G3** | No mutable `LayerState` + adjacency rebuild mid-sweep | Insertion ops mutate layer membership + connectivity; sweep needs live topology | high (blocks G2) |
| **G4** | No MATLAB ground-truth parity | "Faithful" is unverifiable; baselines are our own output | high |
| **G5** | `MAPPING.md` stale | Says `Tri2QuadRoutine.m` "done" though live path is matching | low (doc) |
| **G6** | chilmesh API gaps (#132 `merge_elements`, #138 `submesh`) | Some MATLAB ops want them; `rebuild_adjacencies` now exists | medium |
| **G7** | Two `edgeRemoval` impls (live `_remove_boundary_tris` vs `_tri_removal.edge_removal`) | Duplication; must converge on one when sweep goes live | low |

---

## 4. Target architecture

Faithful `tri2quad_routine` (mirrors `Tri2QuadRoutine.m` lines 18–56):

```
def tri2quad_routine(domain, can_remove_edges=True, parent=None, *, method="faithful"):
    # method="matching" keeps the current fast path (fallback / large meshes).
    if method == "matching":
        return _matching_path(...)            # existing live code, unchanged

    work = WorkingMesh(points=domain.points.copy(), quads=[])
    layer_state = LayerState.from_mesh(domain)        # mutable OE/IE/OV/IV
    for iLayer in range(domain.n_layers - 1, -1, -1): # outward → inward
        sel = identify_edges_in_layer(domain, iLayer)            # G1 (exists)
        pairs = sel.sub_mesh.edge2elem(sel.removed_edge_ids)
        work.quads += merge_tri_pairs(sel.sub_mesh, pairs)       # (exists)
        remaining = elems_of_layer(iLayer) - paired_elems
        for tri in remaining:                                    # G2
            route_leftover_tri(domain, work, tri, iLayer, layer_state,
                               on_mesh_boundary=(iLayer == 0 and domain.n_layers == parent.n_layers),
                               can_remove_edges=can_remove_edges)
        if layer_state_mutated:                                  # G3
            domain.rebuild_adjacencies()        # chilmesh public API (present)
    return _assemble_chilmesh(work, domain, parent)
```

Data structures:
- **`LayerState`** (dataclass): `OE/IE/OV/IV: list[np.ndarray]`. `from_mesh()` snapshot;
  mutated by insertion ops (per `edgeBisection.m:80–90`, `edgeInsertion.m:209–235`).
- **`WorkingMesh`** (already in `_tri_removal.py`): points + quad list accumulator.
- **Adjacency rebuild:** prefer `domain.invalidate_adjacencies()` + lazy rebuild
  (chilmesh exposes both `invalidate_adjacencies` and `rebuild_adjacencies`);
  fall back to `CHILmesh(conn, pts)` reconstruction only if cache proves wrong.

Invariant guards (carry over from the matching path, run after each layer):
`_quad_ok` (no bowtie / flip / degenerate), conformity (max edge-share ≤ 2),
zero-interior — fail fast in debug mode.

---

## 5. Workstreams (dependency-ordered)

### Phase 0 — Verification harness FIRST (unblocks G4; do before touching algo)
Without ground truth, "faithful" is unfalsifiable. Build the oracle before the engine.

- **0.1 Probe the `.mat` fixtures.** `scipy.io.loadmat` on
  `03_CHILMesh_Test_Cases/02_.m_Files/*.mat` + `Block_O` companion. If any holds
  the *final* quad `ConnectivityList`/`Points` (or the CHILmesh struct), that is
  direct ground truth. (MAPPING claims Block_O `.mat` is opaque — re-test with
  `squeeze_me`/`struct_as_record=False`; if v7.3, try `h5py`.)
- **0.2 If `.mat` insufficient → Octave path.** Attempt running the MATLAB under
  GNU Octave with a headless driver (`plotProgress=false`). The `CHILmesh` class
  is custom + heavy; budget this as *spike, may fail*. If it runs, dump per-stage
  golden files (after createQuadDomain, after each layer of Tri2QuadRoutine, after
  PostProcess): connectivity, points, `removedEdgeIDs`, quality.
- **0.3 If neither → algorithmic oracle.** Define parity against the *documented
  rule* (every-other-edge per sorted path) by hand-deriving expected
  `removed_edge_ids` on the smallest fixtures (`simple_test_case`,
  `structuredMesh1`) and checking by inspection + golden JSON committed to
  `tests/golden/`.
- **0.4 Harness module** `tests/_parity_oracle.py`: load golden, compare
  per-stage with tolerances; pretty diff on mismatch.

**Acceptance:** at least one ground-truth source per canonical fixture, committed under `tests/golden/`.
**Risk:** Octave incompatibility (high). Mitigation: 0.1 and 0.3 are independent fallbacks.

> **Re-prioritized per Section 0:** the faithful pairing is the Ch 4 heuristic
> matching + recombination ops, not merely the every-other-edge sweep. Phases 1–3
> below are reframed accordingly. The existing `identify_edges_in_layer` is a
> reference for the per-layer mechanics, not the whole algorithm.

### Phase 1 — Ch 4 heuristic matching engine (G1) + validate vs ground truth
Build/evolve the two-stage matching to match the thesis, not just port one function.

- 1.0 Decide: evolve the current `_match_tris_to_quads` toward the Ch 4 heuristic,
  vs. drive it from `identify_edges_in_layer`. Recommend **evolve** — the current
  matching already has interior-first + most-constrained, the seeds of IE-first +
  fewest-eligible-neighbors.
- 1.1 Implement **interior-layer matching** (Ch 4.1): per-layer, IE-before-OE,
  eligible-neighbor counting with flagged-edge handling, T1 selection
  (fewest-eligible → tiebreakers p64) + T2 selection (tiebreaker ladder p65–66),
  intra-layer-before-inter-layer, innermost→outward.
- 1.2 Implement **boundary-layer matching** (Ch 4.2): OE-before-IE; walkability
  edge-flip pre-pass on RE_L.
- 1.3 Validate per-layer matched pairs (as vertex-pair sets) vs Phase-0 golden.

- 1.1 Drive `identify_edges_in_layer` per layer on each fixture; compare
  `removed_edge_ids` (as vertex-pair sets, index-independent) to Phase-0 golden.
- 1.2 Fix divergences. Likely suspects (from reading `identifyEdgesFun_v2.m` vs
  the Python): path-rotation corner selection (`identify_edges.py:94–103`),
  up/down-edge seeding (`_find_boundary_edge` fallback), the `idown == 2` flip
  (`identifyEdgesFun_v2.m:86–88`), and even/odd phase of "every other".
- 1.3 Determinism: MATLAB iterates in index order; Python uses `set()` in places
  (`elem_ids.tolist()` membership). Replace order-sensitive sets with stable
  ordering so tie-breaks match MATLAB.

**Acceptance:** per-layer `removed_edge_ids` match golden on all fixtures (or
documented, justified deviations with equal/better quality).

### Phase 2 — Recombination ops + merge/assemble (G1b)
- 2.1 Implement the three missing ops (CR-2): **Edge Swap** (vertex-adjacent tris
  → edge-adjacent), **Vertex Duplication**, **Edge Flip** (+ the "walk along a
  path" driver, Fig 3.6). Unit-test each on minimal meshes.
- 2.2 Wire isolated-tri handling per CR-5: intentional vertex-pairing + post-match
  edge-swap fixup (compare against the current augmenting-path approach; keep
  whichever holds invariants with higher quality).
- 2.3 `method="faithful"` branch of `tri2quad_routine`: matching (Phase 1) →
  ops → `merge_tri_pairs` → accumulate; assemble CHILmesh (mirror
  `Tri2QuadRoutine.m:52–56`). Milestone: quad-dominant with *correct pairing*;
  expect quality recovery toward 0.81.

**Acceptance:** faithful-path quad fraction + mean quality ≥ matching path; 0 interior tris.

### Phase 3 — Boundary-tri clearing, faithful preference order (G1c + G2 + G3)
The big one. Flip the op preference + complete the sub-ops + thread mutable state.

- 3.0 **Reverse the boundary-tri preference (CR-4):** prefer **edge insertion /
  add-boundary-point** (Fig 3.4) for IE_L tris → quad; edge-swap/vertex-dup when a
  vertex is shared; edge-collapse (current squeeze) only as OE_L fallback. This
  alone should lift quality materially. Keep the bowtie-safe `_quad_ok` guard.

- 3.1 **`LayerState`** dataclass + `from_mesh` + mutation helpers.
- 3.2 **`edge_bisection` case 2** — opposite-tri split (`edgeBisection.m:47–96`):
  bisect interior layer-boundary edge, Delaunay-retriangulate the iLayer-1 tri
  into two, update `OE/IE/OV/IV`. Needs a 2-point Delaunay (trivial) + the
  degenerate-tri guard (`edgeBisection.m:56–72`).
- 3.3 **`edge_insertion` case 1/2/3** (`edgeInsertion.m`):
  - case 1/2: split lone boundary vert, build quad, **retriangulate iLayer-1**
    (the `case-2-design.md` walk: gather tris touching `tbVert`, build vert seq,
    fan from `np`/`tbVert`). This is the hardest single piece.
  - case 3 (n_bdy 2–3): MATLAB truncates (drops). Keep as drop — already faithful.
- 3.4 **`edge_removal`** — converge the two impls (G7): make the sweep use
  `_tri_removal.edge_removal`; keep `_remove_boundary_tris`'s bowtie guard
  (`_quad_ok`) as a shared safety check.
- 3.5 **Adjacency rebuild** after layer mutation (G3) via `rebuild_adjacencies`.
- 3.6 Wire `route_leftover_tri` into the Phase-2 sweep.

**Acceptance:** faithful path quad-pure (0 tris) on all fixtures; conforming; 0
bowties; mean quality ≥ Phase-2.
**Risk:** iLayer-1 retri correctness + adjacency staleness (high). Mitigation:
extensive sub-mesh unit tests (already scaffolded in `test_tri_removal.py`);
debug-mode invariant asserts after each op; rebuild-from-scratch fallback.

### Phase 4 — Perf hardening
- 4.1 Profile WNAT 98k on the faithful path. Adjacency rebuild per insertion is
  the likely hotspot (MATLAB itself calls this "really inefficient").
- 4.2 Batch rebuilds (once per layer, not per op) or use incremental adjacency
  updates. Budget: ≤ ~2× the matching path (matching = 6.2s).
- 4.3 Keep `method="matching"` as the documented fast path for huge meshes.

### Phase 5 — Post-process parity audit
- 5.1 Confirm `post_process_routine` matches `PostProcessRoutine.m` step order +
  loop conditions (it does today; re-verify against golden after-postprocess).
- 5.2 Confirm the two MATLAB-disabled steps (valence-3 "unnamed func", valence-6
  "ControlVA", commented at `PostProcessRoutine.m:78–88`) stay **unported**
  (porting them would be *unfaithful* — MATLAB doesn't run them).

### Phase 6 — Parity tests + docs reconcile (G4, G5)
- 6.1 Rewrite `test_parity.py` to assert against Phase-0 golden with tight tols.
- 6.2 Keep `test_no_interior_tris.py` (zero-interior, quad-pure, bowtie) as
  invariants on the faithful path.
- 6.3 Update `MAPPING.md`: real statuses (`Tri2QuadRoutine` faithful; edge ops done).
- 6.4 Update module docstrings; retire/clearly-mark the matching path as "fast alt".

---

## 6. Verification strategy (detail)

Per-stage golden comparison (the spine of faithfulness):

| Stage | Compare | Tolerance |
|---|---|---|
| after `createQuadDomain` | n_layers, OE/IE/OV/IV sizes | exact |
| per layer (`identifyEdgesFun_v2`) | `removed_edge_ids` as vertex-pair set | exact (or justified) |
| after `Tri2QuadRoutine` | n_elems, quad_frac, connectivity hash, mean quality | ±2% / ±0.02 |
| after `PostProcessRoutine` | n_elems, quad_frac, mean quality | ±2% / ±0.02 |

Index-independence: compare topology as **sorted vertex-pair / vertex-quad sets**
(MATLAB and Python will not share element/edge ordering). Geometry compared by
nearest-point matching with an epsilon.

Always-on invariants (cheap, every fixture, both paths): zero interior tris,
zero bowtie (`_segments_cross`), conforming (max edge-share ≤ 2), no flipped/
degenerate (`_quad_ok`).

---

## 7. Risks & mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No runnable MATLAB/Octave for ground truth | high | high | Phase-0 triple fallback (.mat probe / Octave spike / hand-derived golden on small fixtures) |
| iLayer-1 retri (`edgeInsertion` case 2) wrong | high | high | smallest-fixture unit tests; debug invariant asserts; rebuild-from-scratch fallback |
| Adjacency cache staleness mid-sweep | medium | high | `rebuild_adjacencies` per layer; verify with `_validate_adjacencies` |
| Determinism/tie-break divergence vs MATLAB | medium | medium | stable ordering; accept justified deviations if quality ≥ |
| Perf regression on 98k | medium | medium | per-layer (not per-op) rebuild; keep matching fast path |
| chilmesh API churn (#132/#138) | low | medium | most needs already covered by present APIs; file precise asks only if a wall is hit |
| Floating-point in Delaunay retri | low | low | epsilon-guarded; snap to existing verts where possible |

---

## 8. chilmesh asks (consolidated, file only if hit)

- Present + sufficient: `paths_on_outer_vertices`, `ccw_edges_around_vert`,
  `layers`, `invalidate_adjacencies`, `rebuild_adjacencies`, `_validate_adjacencies`.
- Possibly needed: #132 `merge_elements` (or keep doing it in `_topology`), #138
  `submesh` (we currently build `CHILmesh(sub_conn, pts, compute_layers=False)`
  by hand — works, keep). A small 2-point Delaunay helper (or use `scipy.spatial`).

---

## 9. Milestones & rough effort

| Milestone | Contents | Gate | Effort |
|---|---|---|---|
| **M1 — Oracle** | Phase 0 | golden committed | S–L (Octave risk) |
| **M2 — Faithful pairing live** | Phases 1–2 | quad-dominant, quality ≥ matching, per-layer parity | M |
| **M3 — Quad-pure faithful** | Phase 3 (+4) | quad-pure, 0 bowtie, quality ≥ M2, perf ≤ 2× | L |
| **M4 — Verified + documented** | Phases 5–6 | parity green vs MATLAB, MAPPING accurate | S |

Sequencing rule: **M1 before M2** (don't build the engine without the oracle).
M2 is shippable on its own (correct pairing, quad-dominant) if M3 stalls.

---

## 10. Open decisions (resolve before/at M1)

1. **Ground-truth source** — `.mat` probe vs Octave vs hand-derived golden? (Phase 0 picks.)
2. **Keep matching path?** Recommend **yes**, behind `method="matching"`, as the
   fast path for very large meshes and a cross-check oracle (two independent
   algorithms agreeing on invariants is strong evidence).
3. **Field-guided pairing (#26)** — orthogonal; could *replace* the every-other-edge
   heuristic for higher quality, but that would be *better-than-MATLAB*, not
   *faithful*. Keep separate; do not conflate with this plan.
4. **ADMESH library** (`01_ADMESH_Library/`) — out of scope.

---

## 11. Safety / rollback

- The faithful path is **additive** (`method="faithful"`); the matching path stays
  the default until M3 passes its gate, then default flips. No regression to the
  current quad-pure/bowtie-free guarantees at any point.
- Every phase keeps the always-on invariants green. A phase that can't hold them
  does not merge.
- Commit per phase; each phase independently revertable.
