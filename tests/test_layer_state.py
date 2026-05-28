"""LayerState tests (T012).

Covers the mutable per-layer OE/IE/OV/IV working copy the faithful sweep needs
to track membership changes from edge_bisection / edge_insertion without
re-deriving CHILmesh skeletonization.
"""

from __future__ import annotations

import numpy as np
import pytest

from quadmesh._layer_state import LayerState


@pytest.fixture
def hand_state() -> LayerState:
    """Two-layer hand-built state (ids arbitrary, sets per layer)."""
    return LayerState(
        OE=[np.array([0, 1, 2]), np.array([10, 11])],
        IE=[np.array([3, 4]), np.array([12])],
        OV=[np.array([100, 101]), np.array([110])],
        IV=[np.array([102]), np.array([111, 112])],
    )


def test_from_mesh_snapshots_all_layers(test_case_1):
    ls = LayerState.from_mesh(test_case_1)
    layers = test_case_1.layers
    n = test_case_1.n_layers

    assert ls.n_layers == n
    for kind in ("OE", "IE", "OV", "IV"):
        got = getattr(ls, kind)
        assert len(got) == n
        for i in range(n):
            np.testing.assert_array_equal(
                np.sort(got[i]), np.sort(np.asarray(layers[kind][i], dtype=int).ravel())
            )


def test_from_mesh_is_deep_copy(test_case_1):
    """Mutating the snapshot must not touch the source mesh's layers."""
    ls = LayerState.from_mesh(test_case_1)
    before = np.asarray(test_case_1.layers["OE"][0], dtype=int).ravel().copy()

    ls.add("OE", 0, 999999)
    ls.remove("OE", 0, before[:1] if before.size else [])

    after = np.asarray(test_case_1.layers["OE"][0], dtype=int).ravel()
    np.testing.assert_array_equal(np.sort(after), np.sort(before))


def test_members_and_contains(hand_state):
    np.testing.assert_array_equal(hand_state.members("OE", 0), np.array([0, 1, 2]))
    assert hand_state.contains("IE", 1, 12)
    assert not hand_state.contains("IE", 1, 4)


def test_add_is_idempotent_union(hand_state):
    hand_state.add("OE", 1, [11, 13])  # 11 already present
    np.testing.assert_array_equal(hand_state.members("OE", 1), np.array([10, 11, 13]))
    hand_state.add("OE", 1, 13)  # adding an existing id is a no-op
    np.testing.assert_array_equal(hand_state.members("OE", 1), np.array([10, 11, 13]))


def test_add_accepts_scalar(hand_state):
    hand_state.add("IV", 0, 200)
    np.testing.assert_array_equal(hand_state.members("IV", 0), np.array([102, 200]))


def test_remove(hand_state):
    hand_state.remove("OE", 0, [1])
    np.testing.assert_array_equal(hand_state.members("OE", 0), np.array([0, 2]))


def test_remove_absent_id_is_noop(hand_state):
    hand_state.remove("OE", 0, [777])
    np.testing.assert_array_equal(hand_state.members("OE", 0), np.array([0, 1, 2]))


def test_matlab_replace_pattern(hand_state):
    """edgeInsertion.m:209-210 pattern: drop old iLayer-1 OE tris, append new."""
    hand_state.remove("OE", 0, [1, 2])
    hand_state.add("OE", 0, [5, 6])
    np.testing.assert_array_equal(hand_state.members("OE", 0), np.array([0, 5, 6]))


def test_bad_kind_raises(hand_state):
    with pytest.raises(KeyError):
        hand_state.members("ZZ", 0)


def test_bad_layer_index_raises(hand_state):
    with pytest.raises(IndexError):
        hand_state.members("OE", 5)
    with pytest.raises(IndexError):
        hand_state.add("OE", -1, 0)
