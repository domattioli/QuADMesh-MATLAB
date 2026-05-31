"""LayerState tests (T012).

Covers the mutable per-layer OE/IE/OV/IV working copy the faithful sweep needs
to track membership changes from edge_bisection / edge_insertion without
re-deriving CHILmesh layer decomposition.
"""

from __future__ import annotations

import numpy as np
import pytest

from quadmesh._layer_state import LayerState


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _FakeDomain:
    """Minimal stand-in for CHILmesh with .layers and .n_layers."""

    def __init__(self, n_layers: int = 3):
        self.n_layers = n_layers
        self.layers = {
            "OE": [np.array([i * 10, i * 10 + 1]) for i in range(n_layers)],
            "IE": [np.array([i * 10 + 2]) for i in range(n_layers)],
            "OV": [np.array([i * 20]) for i in range(n_layers)],
            "IV": [np.array([i * 20 + 1]) for i in range(n_layers)],
        }


@pytest.fixture
def domain():
    return _FakeDomain(n_layers=3)


@pytest.fixture
def state(domain):
    return LayerState.from_mesh(domain)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_from_mesh_snapshots_all_layers(domain, state):
    """from_mesh copies all four kinds across all layers."""
    for kind in ("OE", "IE", "OV", "IV"):
        for li in range(domain.n_layers):
            np.testing.assert_array_equal(
                state.members(kind, li),
                np.unique(domain.layers[kind][li]),
            )


def test_from_mesh_is_deep_copy(domain, state):
    """Mutating the snapshot does not affect the original domain.layers."""
    original = domain.layers["OE"][0].copy()
    state.add("OE", 0, 999)
    np.testing.assert_array_equal(domain.layers["OE"][0], original)


def test_members_and_contains(state):
    """members() and contains() agree."""
    assert state.contains("OE", 0, 0)
    assert not state.contains("OE", 0, 999)


def test_add_is_idempotent_union(state):
    """add() is idempotent: re-adding an existing id does not duplicate it."""
    before = state.members("OE", 0).copy()
    state.add("OE", 0, before[0])
    np.testing.assert_array_equal(state.members("OE", 0), before)


def test_add_accepts_scalar(state):
    """add() works for a scalar id not already present."""
    state.add("IE", 1, 500)
    assert state.contains("IE", 1, 500)


def test_remove(state):
    """remove() drops the id and leaves the rest."""
    members_before = state.members("OE", 0).copy()
    target = members_before[0]
    state.remove("OE", 0, target)
    assert not state.contains("OE", 0, int(target))
    for v in members_before[1:]:
        assert state.contains("OE", 0, int(v))


def test_remove_absent_id_is_noop(state):
    """remove() does not error when the id is not present."""
    before = state.members("OE", 0).copy()
    state.remove("OE", 0, 99999)
    np.testing.assert_array_equal(state.members("OE", 0), before)


def test_matlab_replace_pattern(state):
    """MATLAB remove-then-append pattern: remove a, add a + new → idempotent on a."""
    state.remove("OE", 0, 0)
    state.add("OE", 0, [0, 777])
    assert state.contains("OE", 0, 0)
    assert state.contains("OE", 0, 777)


def test_bad_kind_raises(state):
    """Unknown kind raises KeyError."""
    with pytest.raises(KeyError):
        state.members("BAD", 0)


def test_bad_layer_index_raises(state):
    """Out-of-range layer index raises IndexError."""
    with pytest.raises(IndexError):
        state.members("OE", 999)
