# Parallelization Strategy Options Memo — QuADMESH+

Tracks issue #38. Background brainstorm / decomposition memo. **No implementation in
this deliverable** — options + a recommended first target with rough effort/payoff.

Grounded in the current `src/quadmesh/` tree as of `daily-maintenance@166feb5`. File:line
citations are to that revision.

---

## TL;DR

- The **layer sweep is serial by construction** and cannot be cheaply parallelized in
  place (`_faithful_sweep.py:37-45`).
- **Within-layer matching is a greedy, order-dependent walk** — also a poor parallel
  target.
- The **clean win is the batch axis**: `run_pipeline()` (`pipeline.py:14`) is a
  self-contained per-mesh function with no global state, trivially fanned out across
  many meshes via `multiprocessing.Pool`.
- **Second win is vectorizing the measurement stages** (quality/validation), which are
  per-element and data-parallel.
- **Determinism is a prerequisite, not an afterthought.** The issue notes a known
  run-to-run nondeterminism bug; any parallel scheme must not worsen it. See §6.

Recommended first target: **batch-level multiprocessing at the driver** (lowest effort,
highest payoff, zero algorithm change). Fix determinism first so batch runs reproduce.

---

## 1. Layer sweep — serial by construction

`sweep_layers` (`_faithful_sweep.py:14`) runs:

```
while iter_count < max_iters:          # :37
    layers = _derive_layers(domain)    # :38  re-derive ALL layers from current state
    outer  = _outermost_triangular_layer(layers)
    if outer is None: break            # all-quad → done
    remove_triangles_from_layer(domain, outer)  # :42  mutates domain IN PLACE
    iter_count += 1
```

Each iteration **re-derives the full layer set** (`:38` → `_derive_layers` →
`domain.skeleton_layers()`, `:50-52`) and consumes the current outermost triangular ring
by mutating the domain in place (`:42`). Iteration `k+1` sees the topology iteration `k`
produced, so iterations form a strict serial chain.

**Is the dependency fundamental, or only adjacent?** The *MATLAB contract* couples only
adjacent rings (removing ring `r` re-triangulates the next inner ring). But the *current
Python implementation* re-derives **all** layers every pass (`:38`), which forecloses any
non-adjacent concurrency: there is no per-ring dependency graph to schedule against.

- **Option 1a (hard).** Replace whole-domain re-derivation with an incremental
  layer-dependency graph, then schedule non-adjacent rings concurrently (red/black
  wavefront). High effort, high risk, touches the algorithm's correctness core.
  Not recommended until the faithful path is stable (it is still WIP per PR #59).
- **Verdict.** Leave the sweep serial. Parallelism belongs *around* it, not *inside* it.

## 2. Connected components / submeshes

No connected-component or region decomposition exists in `src/quadmesh/`. The only
"regioning" notion is the concentric skeleton **layers** (`_faithful_sweep.py:50-52`,
delegating to the chilmesh domain's `skeleton_layers()`). A disconnected domain could in
principle tri2quad each component independently, but:

- The component split would need to live **upstream in chilmesh** (where the domain data
  structure and adjacency live), not here.
- Payoff depends entirely on how often real inputs are multi-component — unknown; most
  fixtures are single-component.

**Verdict.** Possible but blocked on upstream chilmesh adjacency work. File a low-priority
CHILmesh issue if/when multi-component inputs become common (per the quadmesh profile's
"open low-priority issues against CHILmesh for needed downstream API changes" rule).

## 3. Embarrassingly-parallel stages (vectorize before you fan out)

The pipeline composes three stages sequentially (`pipeline.py:25-27`):
`tri_to_quad` → `post_process` → `compute_quality`.

- **Measurement is data-parallel.** `compute_quality` (`quality_report.py`, uses
  `np.unique` at `:44`) computes a per-element metric — each element is independent.
  This is the cleanest candidate for **numpy vectorization** (preferred) or thread/process
  fan-out.
- **Validation predicates are per-element** (orientation/containment in
  `validation/predicates.py`) — also data-parallel, also better served by vectorization
  than by process pools (GIL + per-call overhead dominate small ops).
- **Mutation stages are greedy-sequential.** `post_process` (and its constituents
  `quad_vertex_merge`, `doublet_collapse`, `cleanup_boundary_quads`) mutate shared
  topology one operation at a time; a candidate's validity depends on prior operations.
  These are **not** safe to parallelize without a conflict/locking scheme that would cost
  more than it saves.

**Verdict.** Vectorize the *measurement* stages with numpy first; do not attempt to
parallelize the greedy *mutation* stages.

## 4. Within-layer matching

The tri-pair matcher (`identify_edges.py`, faithful variant `_match_faithful.py`) is a
**greedy path-walk**: it walks ordered path vertices and picks merge edges, each pick
constraining the next. Per-layer work is roughly O(vertices in layer) — small for inner
rings. Because the walk is order-dependent, splitting one layer's matching across workers
would change results and risk conflicting merges.

**Verdict.** Not a parallel target. Any cross-layer concurrency is blocked by §1.

## 5. Batch axis / driver — the recommended first target

`run_pipeline(domain, *, smooth=True, collect_quality=True)` (`pipeline.py:14`) is a
clean, self-contained per-mesh entrypoint: it takes one domain, returns one
`PipelineResult` (`pipeline.py:21`), and holds **no module-level mutable state**. The CLI
(`cli.py`) wraps it for a single input path.

This makes **driver-level multiprocessing across many independent meshes** the
lowest-effort, highest-payoff axis:

```python
# illustrative — NOT shipped in this memo
from multiprocessing import Pool
results = Pool().map(run_pipeline, domains)   # one mesh per worker, no shared state
```

Zero algorithm change. Sidesteps the serial sweep (§1), the missing component split (§2),
and the order-dependent matcher (§4). Natural fit for test-fixture sweeps and the
cross-domain CI experiment referenced in sibling issues (#18, #21).

**Caveat:** numpy releases the GIL inside array ops, so a *thread* pool helps the
vectorized measurement stages (§3); but for whole-pipeline fan-out use **processes**
(the greedy mutation stages are pure-Python and GIL-bound). Each mesh is independent, so
process overhead amortizes well.

## 6. Determinism — prerequisite for any parallel batch

The issue states a known run-to-run nondeterminism bug. **No code comment annotates it**
(grep for `determin|fixme|todo|random|seed` across `src/quadmesh/` returns nothing — the
bug is real per the issue, but undocumented in-tree).

Candidate roots — the matcher/repair accumulate into Python `set()`s whose iteration
order is not guaranteed stable for non-hashable-ordered contents:

- `_match_faithful.py:54`, `_match_faithful.py:88` — `pairs = set()`
- `identify_edges.py:140` — `seen = set()`
- `repair.py:71`, `cli.py:201` — `pairs = set()`

**I did not confirm which of these actually drives a nondeterministic merge order** —
that needs a dedicated repro (run the same fixture N times, diff connectivity). Flagged as
the first place to look.

**Why it matters for parallelism:** parallel batch runs are only useful if each mesh's
result is reproducible. Determinism must be fixed (replace order-sensitive `set` iteration
with sorted/ordered structures) **before** the batch fan-out lands, or parallel runs will
produce noise that's indistinguishable from real diffs.

## 7. Tooling

- **numpy** is used throughout (`pipeline.py:7`, `_faithful_sweep.py:8`, etc.); core data
  is numpy arrays. Vectorization is the natural first lever.
- **No** `multiprocessing`, `numba`, `cython`, `joblib`, or `concurrent.futures` anywhere
  in `src/quadmesh/` (grep confirms). No parallel infra exists yet.
- `pyproject.toml` deps are minimal (numpy, scipy, chilmesh) — adding `multiprocessing`
  (stdlib) costs nothing; `numba`/`cython` would add a build/runtime dependency and
  should be deferred until a profile proves a hot loop needs it.

---

## Recommended order of implementation

| # | Target | Effort | Payoff | Blocker |
|---|---|---|---|---|
| 1 | **Determinism fix** (sorted sets in matcher/repair) | low | unblocks everything | repro needed first |
| 2 | **Batch-level multiprocessing** at the driver (`run_pipeline` fan-out) | low | high (fixture sweeps, CI) | needs #1 for reproducibility |
| 3 | **numpy-vectorize measurement** stages (`compute_quality`, validation predicates) | medium | medium (per-mesh speedup) | none |
| 4 | Connected-component split | medium | unknown (input-dependent) | upstream chilmesh adjacency |
| 5 | Wavefront/red-black layer sweep | high | medium | algorithm-core risk; faithful path still WIP |

**First target: #2 (batch multiprocessing), gated on #1 (determinism).** Smallest blast
radius, no algorithm change, immediate win for fixture sweeps and the cross-domain CI
experiment.

## Out of scope (per the issue)

No implementation, no benchmark harness — this memo is the decomposition + recommended
first target only.

## Open questions for the operator

1. Determinism: confirm a repro (same fixture × N runs → connectivity diff) so we can
   pin which `set()` (§6) is the culprit before parallel work begins.
2. Multi-component inputs: how common are disconnected domains in practice? Decides
   whether §2 (component split) is worth an upstream chilmesh request.
3. `numba`/`cython` appetite: acceptable to add a build dependency later if a hot loop
   justifies it, or stay pure-numpy?

---

_Deliverable for issue #38 (research / options memo)._
