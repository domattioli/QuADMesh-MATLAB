"""Mutable working copy of CHILmesh layer decomposition (T012).

The faithful tri2quad sweep mutates per-layer element/vertex membership as it
clears leftover triangles: ``edge_bisection`` and ``edge_insertion`` move tris
between a layer's outer/inner edge sets and register inserted midpoints as new
verts (MATLAB ``edgeBisection.m:80-96``, ``edgeInsertion.m:209-214``). CHILmesh
reads ``mesh.layers`` once at sweep start and never re-derives it, so the sweep
needs its own mutable copy.

``LayerState`` mirrors MATLAB ``Domain.Layers.{OE,IE,OV,IV}``:

- ``OE[i]`` / ``IE[i]`` — element indices on layer ``i``'s outer / inner edge.
- ``OV[i]`` / ``IV[i]`` — vertex indices on layer ``i``'s outer / inner boundary.

Membership within a layer/kind is a **set** (order not significant); ``add`` is
idempotent, matching MATLAB's remove-then-append net effect. ``bEdgeIDs`` is not
tracked — the faithful sweep does not mutate it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Union

import numpy as np

_ELEM_KINDS = ("OE", "IE")
_VERT_KINDS = ("OV", "IV")
_KINDS = _ELEM_KINDS + _VERT_KINDS

IdLike = Union[int, np.integer, Iterable[int], np.ndarray]


def _as_id_array(ids: IdLike) -> np.ndarray:
    return np.asarray(ids, dtype=int).ravel()


@dataclass
class LayerState:
    """Per-layer outer/inner edge-element and vertex sets, mutable in place."""

    OE: List[np.ndarray]
    IE: List[np.ndarray]
    OV: List[np.ndarray]
    IV: List[np.ndarray]

    @classmethod
    def from_mesh(cls, domain) -> "LayerState":
        """Snapshot ``domain.layers`` into an independent mutable copy.

        The arrays are deep-copied, so mutating the returned ``LayerState`` never
        touches ``domain.layers``.
        """
        layers = domain.layers

        def snap(key: str) -> List[np.ndarray]:
            return [_as_id_array(a).copy() for a in layers[key]]

        return cls(OE=snap("OE"), IE=snap("IE"), OV=snap("OV"), IV=snap("IV"))

    @property
    def n_layers(self) -> int:
        return len(self.OE)

    def _bucket(self, kind: str) -> List[np.ndarray]:
        if kind not in _KINDS:
            raise KeyError(f"unknown layer kind {kind!r}; expected one of {_KINDS}")
        return getattr(self, kind)

    def _check_layer(self, kind: str, layer_idx: int) -> List[np.ndarray]:
        bucket = self._bucket(kind)
        if layer_idx < 0 or layer_idx >= len(bucket):
            raise IndexError(
                f"layer index {layer_idx} out of range [0, {len(bucket)}) for {kind}"
            )
        return bucket

    def members(self, kind: str, layer_idx: int) -> np.ndarray:
        """Return the (sorted) id set for ``kind`` on layer ``layer_idx``."""
        return self._check_layer(kind, layer_idx)[layer_idx]

    def contains(self, kind: str, layer_idx: int, elem_id: int) -> bool:
        return bool(np.isin(int(elem_id), self.members(kind, layer_idx)))

    def add(self, kind: str, layer_idx: int, ids: IdLike) -> None:
        """Add ``ids`` to ``kind`` on layer ``layer_idx`` (idempotent union)."""
        bucket = self._check_layer(kind, layer_idx)
        merged = np.concatenate([bucket[layer_idx], _as_id_array(ids)])
        bucket[layer_idx] = np.unique(merged)

    def remove(self, kind: str, layer_idx: int, ids: IdLike) -> None:
        """Remove ``ids`` from ``kind`` on layer ``layer_idx`` (no error if absent)."""
        bucket = self._check_layer(kind, layer_idx)
        drop = _as_id_array(ids)
        current = bucket[layer_idx]
        bucket[layer_idx] = current[~np.isin(current, drop)]
