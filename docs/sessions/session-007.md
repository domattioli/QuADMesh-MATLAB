# Session 007 — faithful tri2quad fold-seam (flagged-edge) guard (#31)

**Date:** 2026-05-24
**Branch:** `daily-issue-fixing`
**PR:** [#29](https://github.com/domattioli/QuADMESH/pull/29) (draft) — updated, head `b33e932`
**Model:** claude-opus-4-7

## What changed

Implemented thesis Figure 4.1 / §3.2.2 **flagged edges** so the faithful matcher never merges across a self-folding layer's two bordering strips (#31).

| File | Change |
|---|---|
| `python/quadmesh/identify_edges.py` | detect flagged edges = interior sub-mesh edges with **both endpoints inner vertices (IV)**; skip them in the sweep; return `flagged_edge_ids` + `flagged_vert_pairs` |
| `python/quadmesh/tri2quad.py` | `_match_tris_to_quads` gains `forbidden_edges` (drops those edges from tri-adjacency → strips "invisible"); `_sweep_pairs` now returns `(pairs, flagged_set)`; faithful path wires it in |
| `python/tests/test_flagged_edges.py` | new — fixture fold property (0 cross-fold quads) + forbidden-edge unit test |

Commit `b33e932`.

## Definition (thesis p39)

> A flagged edge is any edge within a mesh composed of two inner vertices.

In a layer that does NOT fold, the IV ring is a sub-mesh *boundary*; an interior IV–IV edge (shared by two layer tris) only arises where the layer self-intersects → it is exactly the seam between the two bordering strips. Forbidding the merge across it keeps the strips invisible to each other.

## Verification

Cross-fold quads (faithful matcher) eliminated, zero-interior preserved:

| fixture | flagged edges | cross-fold before | after |
|---|---|---|---|
| Test_Case_1 | 20 | 6 | 0 |
| Test_Case_2 | 35 | 14 | 0 |
| Test_Case_3 | 24 | 5 | 0 |
| Block_O | 47 | 12 | 0 |
| WNAT_Hagen | 234 | 70 | 0 |

Tests: **82 pass, 1 fail**. The fail (`test_parity::...[Test_Case_1.14]`, default `matching` pipeline mean 0.375 vs baseline 0.739) is **pre-existing** — verified failing at parent `f7a11b2`, on the `matching` path this change does not touch.

## Investigation — "why does the zip rule not lift quality?"

The fold-seam guard is a **topological-correctness** fix, not a quality lever. Evidence (WNAT_Hagen):

1. **Dilution.** 70 cross-fold quads / 49143 (0.14%) → median moves ~0.
2. **Rerouting is quality-neutral.** Forbidding 234 seams reroutes 3411 quads; removed-set med 0.534 vs replacement med 0.533. The rule changes *which* tris pair, not the tri shapes.
3. **Metric is blind.** Cross-fold quads are low-Q (med 0.406, min 0.070) but all pass `_quad_ok` (simple, CCW, +area). min-angle quality never penalized the fold-bridge defect, so removing it can't raise that metric.

FEM (single `direct_smoother` solve, no iterations) lifts both before/after equally: median 0.540 → ~0.658.

## Open issues

- **#31** — left OPEN; closes when PR #29 merges. Status comment posted.
- **#32** (filed this session) — matching-path parity regression: TC1 pipeline mean 0.375 vs 0.739, predates this session (verified at `f7a11b2`), suspect `a36ba04` bowtie/cleanup pass.
- **#33** (filed this session) — fold-aware validity metric to make the #31 defect class measurable in CI (quad covering domain void / area-vs-source-tri mismatch / seam-crossing), or recombination of freed seam tris.
- **#25** faithful `removeTrianglesFun` port; **#26** field-guided post-process — unchanged.

## What comes next

1. Review + merge PR #29.
2. Triage the matching-path parity regression (separate issue).
3. Decide on fold-aware metric vs recombination for the freed seam region.

## Files to review on resume

- `python/quadmesh/identify_edges.py` — flagged-edge block (~line 90) + sweep skip (~line 205).
- `python/quadmesh/tri2quad.py` — `_match_tris_to_quads` adj build (`forbidden_edges`), `_sweep_pairs` return.
- `python/tests/test_flagged_edges.py` — the fold contract.

## Environment note

Fresh container had **no** numpy/scipy/chilmesh in the test interpreter (uv-tool pytest is isolated). Built a venv from declared `pyproject` deps + editable `chilmesh`/`quadmesh` to run the gate: `uv venv python/.venv && uv pip install numpy scipy pytest -e /home/user/CHILmesh -e python`. (`.venv/` is gitignored.) `cryptography`'s rust binding was broken (`_cffi_backend`) — `pip install --force-reinstall cffi` fixed it for reading the thesis PDF via `pypdf`.

## chilmesh issues status

No new chilmesh issues this session.
