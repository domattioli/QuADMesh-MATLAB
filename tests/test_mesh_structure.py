"""MeshStructure tests (issue #55).

Covers the unified entrypoint for mesh structure selection: layers (implemented),
medial_axis (implemented via Voronoi-of-boundary interior ridges),
skeleton (not yet implemented, raises NotImplementedError).
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


def test_invalid_kind_raises_valueerror(test_case_1):
    """Unknown kind raises ValueError with helpful message."""
    with pytest.raises(ValueError):
        compute_mesh_structure(test_case_1, kind="bogus")


def test_medial_axis_returns_graph(test_case_1):
    ms = compute_mesh_structure(test_case_1, kind="medial_axis")
    assert ms.kind == "medial_axis"
    assert ms.nodes is not None and ms.edges is not None
    assert ms.nodes.ndim == 2 and ms.nodes.shape[1] == 2
    assert ms.edges.ndim == 2 and ms.edges.shape[1] == 2
    assert ms.nodes.shape[0] > 0 and ms.edges.shape[0] > 0
    # edge indices reference valid nodes
    assert int(ms.edges.max()) < ms.nodes.shape[0]
    assert int(ms.edges.min()) >= 0


def test_medial_axis_nodes_within_bbox(test_case_1):
    P = np.asarray(test_case_1.points)[:, :2]
    ms = compute_mesh_structure(test_case_1, kind="medial_axis")
    assert (ms.nodes[:, 0] >= P[:, 0].min() - 1e-6).all()
    assert (ms.nodes[:, 0] <= P[:, 0].max() + 1e-6).all()
    assert (ms.nodes[:, 1] >= P[:, 1].min() - 1e-6).all()
    assert (ms.nodes[:, 1] <= P[:, 1].max() + 1e-6).all()


def test_medial_axis_deterministic(test_case_1):
    a = compute_mesh_structure(test_case_1, kind="medial_axis")
    b = compute_mesh_structure(test_case_1, kind="medial_axis")
    assert np.array_equal(a.nodes, b.nodes)
    assert np.array_equal(a.edges, b.edges)
