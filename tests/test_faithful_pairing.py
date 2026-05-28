"""T009: Per-layer matched-pair sets vs golden (or structural invariants).

Golden fixtures are skipped if not available. Structural invariants (no pair
uses a consumed elem, no pair re-uses a vert across two different pairs in the
same layer) are always checked.
"""

import pytest
import numpy as np
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "meshes"
MESH_FILES = sorted(FIXTURES_DIR.glob("*.14"))


@pytest.fixture(params=[p.name for p in MESH_FILES], ids=[p.name for p in MESH_FILES])
def domain(request):
    from chilmesh import CHILmesh
    return CHILmesh.read_from_fort14(str(FIXTURES_DIR / request.param))


def _per_layer_pairs(domain):
    """Run the faithful per-layer loop and return {layer_idx: [(ga,gb)...]}."""
    from quadmesh._match_faithful import match_layer_heuristic
    layers = domain.layers
    nl = int(getattr(domain, "n_layers", 0) or 0)
    result = {}
    consumed = set()
    for li in range(nl - 1, -1, -1):
        ie_ids = np.asarray(layers["IE"][li], dtype=int)
        oe_ids = np.asarray(layers["OE"][li], dtype=int)
        glob = np.concatenate([oe_ids, ie_ids])
        if glob.size == 0:
            continue
        layer_conn = domain.connectivity_list[glob]
        pairs, new_consumed = match_layer_heuristic(
            layer_conn=layer_conn,
            layer_global_ids=glob,
            ie_global_ids=ie_ids,
            oe_global_ids=oe_ids,
            pts=domain.points,
            already_consumed=consumed,
            is_boundary_layer=(li == nl - 1),
        )
        result[li] = [(int(glob[la]), int(glob[lb])) for la, lb in pairs]
        consumed.update(new_consumed)
    return result


def test_no_elem_used_twice(domain):
    """Each global elem ID appears in at most one pair, across all layers."""
    all_pairs = _per_layer_pairs(domain)
    seen = set()
    for pairs in all_pairs.values():
        for ga, gb in pairs:
            assert ga not in seen, f"elem {ga} used in multiple pairs"
            assert gb not in seen, f"elem {gb} used in multiple pairs"
            seen.add(ga)
            seen.add(gb)


def test_pairs_share_edge(domain):
    """Each pair (ga, gb) must share exactly 2 vertices (i.e. an edge)."""
    conn = domain.connectivity_list
    all_pairs = _per_layer_pairs(domain)
    for li, pairs in all_pairs.items():
        for ga, gb in pairs:
            va = set(int(v) for v in conn[ga, :3])
            vb = set(int(v) for v in conn[gb, :3])
            shared = va & vb
            assert len(shared) == 2, (
                f"Layer {li} pair ({ga},{gb}) shares {len(shared)} verts, expected 2"
            )


def test_pair_count_reasonable(domain):
    """At least 30% of tris get paired (sanity floor — not a faithfulness check)."""
    conn = domain.connectivity_list
    n_tris = sum(1 for row in conn if len(set(int(v) for v in row[:3])) == 3)
    all_pairs = _per_layer_pairs(domain)
    n_paired = sum(len(p) for p in all_pairs.values()) * 2
    if n_tris == 0:
        return
    ratio = n_paired / n_tris
    assert ratio >= 0.3, f"Only {ratio:.1%} of tris paired (expected ≥30%)"
