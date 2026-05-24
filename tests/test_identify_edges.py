"""Tests for identify_edges_in_layer."""

from __future__ import annotations

import numpy as np

from quadmesh.identify_edges import identify_edges_in_layer


def test_layer0_selection_nonempty(test_case_1):
    """Outermost layer of Test_Case_1: at least some edges should be selected."""
    sel = identify_edges_in_layer(test_case_1, 0)
    assert sel.sub_mesh is not None
    assert sel.elem_ids_global.size > 0
    assert sel.boundary_edge_ids.size > 0
    # Removed edges should be non-zero count for a typical layer.
    assert sel.removed_edge_ids.size > 0


def test_selected_edges_yield_disjoint_pairs(test_case_1):
    """Each selected edge maps to an elem pair; pairs are mutually exclusive."""
    sel = identify_edges_in_layer(test_case_1, 0)
    edge2elem = sel.sub_mesh.adjacencies["Edge2Elem"]
    used_elems = set()
    for eid in sel.removed_edge_ids:
        a, b = edge2elem[int(eid)]
        assert int(a) not in used_elems
        assert int(b) not in used_elems
        used_elems.add(int(a))
        used_elems.add(int(b))


def test_sweep_all_layers_no_crash(test_case_1):
    """Every layer's selection runs without raising."""
    for k in range(test_case_1.n_layers):
        sel = identify_edges_in_layer(test_case_1, k)
        assert sel.sub_mesh is not None or sel.elem_ids_global.size == 0
