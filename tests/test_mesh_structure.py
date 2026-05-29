"""MeshStructure tests (issue #55).

Covers the unified entrypoint for mesh structure selection: layers (implemented),
skeleton & medial_axis (not yet implemented, raise NotImplementedError).
"""

from __future__ import annotations

import numpy as np
import pytest

from quadmesh.mesh_structure import compute_mesh_structure, MeshStructure


def test_layers_default_kind(test_case_1):
    """Default kind is 'layers'; result is MeshStructure instance."""
    ms = compute_mesh_structure(test_case_1)
    assert isinstance(ms, MeshStructure)
    assert ms.kind == "layers"


def test_layers_returns_layerstate(test_case_1):
    """Layers mode returns LayerState; counts match."""
    ms = compute_mesh_structure(test_case_1, kind="layers")
    assert ms.layers is not None
    assert ms.layers.n_layers == ms.n_layers
    assert ms.n_layers > 0
    assert len(ms.layers.OE) == ms.n_layers
    assert len(ms.layers.IE) == ms.n_layers
    assert len(ms.layers.OV) == ms.n_layers
    assert len(ms.layers.IV) == ms.n_layers


def test_layers_snapshot_is_independent(test_case_1):
    """LayerState is a deep copy; mutations don't touch domain.layers."""
    ms = compute_mesh_structure(test_case_1)
    before_len = len(test_case_1.layers["OE"][0])

    # Mutate the snapshot
    ms.layers.OE[0] = np.array([])

    # Original should be unchanged
    after_len = len(test_case_1.layers["OE"][0])
    assert after_len == before_len


def test_skeleton_not_implemented(test_case_1):
    """kind='skeleton' raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        compute_mesh_structure(test_case_1, kind="skeleton")


def test_medial_axis_not_implemented(test_case_1):
    """kind='medial_axis' raises NotImplementedError."""
    with pytest.raises(NotImplementedError):
        compute_mesh_structure(test_case_1, kind="medial_axis")


def test_invalid_kind_raises_valueerror(test_case_1):
    """Unknown kind raises ValueError with helpful message."""
    with pytest.raises(ValueError):
        compute_mesh_structure(test_case_1, kind="bogus")
