# Tri-to-Quad Matching — Graph Theory Description

This document describes the QuADMESH+ triangle-pairing algorithm using graph theory
lexicon. Source: [`src/quadmesh/tri2quad.py`](../src/quadmesh/tri2quad.py),
[`src/quadmesh/identify_edges.py`](../src/quadmesh/identify_edges.py),
[`src/quadmesh/_match_faithful.py`](../src/quadmesh/_match_faithful.py),
and Mattioli (2017) Chapters 3–4.

---

## 1. Triangle Adjacency Graph

Let **T** = {t₁, …, tₙ} be the triangles of the input triangulation. Define the
**triangle adjacency graph**:

> **G = (V, E)** where V = T and (tᵢ, tⱼ) ∈ E iff tᵢ and tⱼ share exactly one
> interior (non-boundary) edge.

Every merge of a triangle pair into a quad corresponds to selecting one edge of G.
The output quadmesh is determined by the matching M ⊆ E chosen.

---

## 2. The Matching Problem

The algorithm's primary invariant is **interior saturation**: every **interior
vertex** — a triangle tᵢ whose three edges are all interior (no edge on the domain
boundary) — must appear in the matching M.

> **Problem**: Find a matching M ⊆ E such that every interior vertex of G is
> M-saturated.

If |T| is odd, at least one triangle must be left unmatched; interior saturation
ensures that residual (unmatched) vertices are **boundary triangles** — those
incident to at least one domain boundary edge. This makes the residue geometrically
harmless.

---

## 3. Forbidden Edges (Fold Seams)

Each mesh layer Lᵢ partitions its triangles into:

- **IE(Lᵢ)** — inner elements: triangles whose free vertex lies on the inner
  boundary ring.
- **OE(Lᵢ)** — outer elements: triangles whose free vertex lies on the outer
  boundary ring.
- **OV(Lᵢ)** / **IV(Lᵢ)** — the outer / inner vertex sets.

When a layer **self-folds**, a seam appears: an interior edge of G whose both
endpoints are IV vertices of Lᵢ (an IV–IV edge). Merging across such a seam would
stitch the two bordering strips of the fold into a single quad, violating mesh
structure.

These edges are removed from E before matching:

> **G′ = (V, E \ F)** where F = {e ∈ E : both endpoints of e are IV vertices of
> some layer}.

The two triangles across a fold seam become **non-adjacent** in G′ and are invisible
to each other throughout matching. (Thesis §3.2.2 / Figure 4.1;
`identify_edges.py:flagged_mask`.)

---

## 4. Layer-Ordered Vertex Priority

Triangles are assigned a **vertex priority** in G′ encoding the Ch 4 sweep order:

| Condition | Priority (lower = matched first) |
|---|---|
| IE element, innermost layer | 0 |
| OE element, innermost layer | 1 |
| IE element, layer Lᵢ | 2·(nₗ−1−i) |
| OE element, layer Lᵢ | 2·(nₗ−1−i)+1 |
| Boundary layer — OE first | OE rank < IE rank (reversed) |
| No layer membership | ∞ |

**Interior layers (Ch 4.1): IE before OE.** IE vertices can become isolated (no
inter-layer escape); OE vertices can still match inter-layer with layer Lᵢ₋₁.

**Boundary layer (Ch 4.2): OE before IE.** Matching OE first guarantees that any
residual is an IE triangle, which can be cleared without altering the domain
boundary.

---

## 5. Structured Sweep — Seed Matching (identifyEdgesFun_v2)

For each layer Lᵢ, the algorithm walks the **outer-vertex path** — a Hamiltonian
path on OV(Lᵢ) ordered along the outer ring. At each path vertex v:

1. Collect all edges of G′ incident to v in **CCW order**, from the up-path
   boundary edge to the down-path boundary edge.
2. Flag all **interior** edges in this arc for removal (skipping forbidden and
   already-consumed ones).
3. Each flagged edge (tₐ, t_b) ∈ E′ adds the pair (tₐ, t_b) to a **seed set** S.

The seed set S is a partial matching M₀ ⊆ M — the **structured, layer-aligned**
initial matching. Because each element is consumed at most once per layer and
elements partition disjointly across layers, M₀ is a valid matching. The quads
formed by M₀ run along the layer strips, giving square-ish elements instead of the
skewed slivers that arbitrary greedy adjacency produces. (`identify_edges.py:
identify_edges_in_layer`; `tri2quad.py:_sweep_pairs`.)

---

## 6. Greedy Extension with Most-Constrained-Vertex Heuristic

After seeding M₀, the algorithm extends to a full matching via a
**priority-ordered greedy pass** on the residual graph G′ \ V(M₀):

- A **lazy min-heap** orders unmatched vertices by `(priority, free_degree)` —
  lowest free degree (most constrained) first within each priority class.
- For each vertex tᵢ popped, match tᵢ to the **most-constrained free neighbor**
  argmin_{j ∈ N(tᵢ)} `(priority(j), deg_free(j))`.

This is the **minimum-degree greedy** strategy: matching the vertex with fewest
remaining options first minimises blocking — analogous to the greedy maximum
independent set heuristic.

**T1 selection (thesis p64):** among all unmatched candidates, pick the vertex
with fewest eligible neighbors; then among its neighbors pick the one that forms
the highest-quality quad (shape quality as secondary tiebreaker).

**T2 ladder (thesis p65–66):** after selecting pair (tₐ, t_b) via T1, extend
greedily along an **alternating path** from t_b — follow t_b → t_c → t_d → … as
long as each next vertex is the first available free neighbor of the previous one.
The ladder emits a chain of pairs running in a strip across the layer.

(`tri2quad.py:_match_tris_to_quads`; `_match_faithful.py:_t1_select`,
`_t2_ladder`.)

---

## 7. Augmenting-Path Fixup (Interior Saturation Guarantee)

After the greedy pass, any interior vertex still unmatched is fixed via
**augmenting paths** (Berge's theorem):

> A matching M is maximum iff G contains no M-augmenting path.

The algorithm runs **BFS on alternating paths** from each stranded interior vertex
tᵢ: alternate between unmatched edges (free) and matched edges (occupied). Upon
reaching a free vertex t_f, the path P = tᵢ – … – t_f is an **augmenting path**;
M ⊕ P yields a larger matching that saturates tᵢ and displaces one boundary
triangle as the new residual.

This guarantees **zero interior residual triangles** regardless of the seed or
greedy outcome. (`tri2quad.py:augment`.)

---

## 8. Residual Triangle Recombination

After matching, surviving boundary triangles are cleared by **local graph rewriting
rules**:

| Operation | Graph description |
|---|---|
| **Edge swap** (Fig 3.2) | Tri–quad–tri fan around shared vertex s: swap edges {s–b, s–d} → {s–c} in the planar graph → two quads. No vertex inserted or deleted. |
| **Vertex duplication** (Fig 3.3) | Split a shared vertex into two to separate two strips — adds one vertex, splits one adjacency in the planar graph. |
| **Edge flip + walk** (Fig 3.6/4.4) | Flip an interior edge of G to create a new adjacency; makes an isolated triangle matchable. |
| **Steiner point insertion** | Pair a lone triangle with an adjacent quad to form a 5-gon; insert one interior point, splitting the region into two quads. Adds one vertex, preserves all original vertices. |
| **Edge collapse / squeeze** | Collapse a domain boundary edge (merge its two endpoints to their midpoint) — removes one vertex; used only when `can_remove_edges=True`. |

Each operator is applied **most-constrained-first**: the candidate whose constituent
tris / quads have the fewest alternative swap partners is selected first, preventing
one greedy pick from blocking a second feasible operation. (`tri2quad.py:
_edge_swap_tri_pairs`, `_point_insert_tri_pairs`, `_remove_boundary_tris`.)

---

## 9. Summary

```
Input triangulation T
        │
        ▼
Build G = (V=T, E=shared-interior-edges)      ← triangle adjacency graph
        │
        ▼
Remove forbidden edges F (IV–IV fold seams)   → G′ = G \ F
        │
        ▼
Assign vertex priority
  (layer rank, IE/OE, boundary-layer reversal)
        │
        ▼
Structured sweep (identifyEdgesFun_v2)         ← partial matching M₀ ⊆ G′
  • walk outer-vertex Hamiltonian path per layer (innermost first)
  • flag CCW-arc interior edges → seed pairs S = M₀
        │
        ▼
Priority-ordered greedy extension on G′ \ V(M₀)
  • min-heap by (priority, free-degree)
  • T1: fewest-eligible vertex first
  • T2: ladder walk (alternating-path strip extension)
        │
        ▼
Augmenting-path fixup (BFS) for all unmatched interior vertices
  → M is now interior-saturating
        │
        ▼
Local recombination (edge swap, point insert, edge collapse)
  → clears all residual boundary triangles
        │
        ▼
Output quad mesh Q
```

The algorithm is a **weighted, priority-seeded, interior-saturating maximum
matching** on the triangle adjacency graph, with seed pairs computed by a
structured sweep on layer Hamiltonian paths, and a Berge augmenting-path fixup
guaranteeing interior saturation.

---

*See also: [MAPPING.md](MAPPING.md) (MATLAB→Python function map),
[`docs/Mattioli_Thesis.pdf`](Mattioli_Thesis.pdf) (Ch 3–4 for full derivations).*
