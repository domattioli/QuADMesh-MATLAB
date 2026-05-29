"""Unified entrypoint for mesh structure definitions (QuADMesh issue #55).

This module provides a single selectable entrypoint distinguishing three
related-but-distinct mesh structures:

- **layers** (currently implemented): outer/inner edge & vertex sets per
  skeletonization layer, computed by CHILmesh and read from ``domain.layers``.
  See ``LayerState`` in ``_layer_state.py`` for the mutable per-layer working
  copy the faithful sweep uses.

- **skeleton** (not yet implemented): image-style skeleton / medial-axis,
  fundamentally distinct from chilmesh layer decomposition. Reserved for future
  research; see specs/004-unified-mesh-structure/spec.md.

- **medial_axis** (not yet implemented): related to skeleton; also reserved for
  future research per specs/004-unified-mesh-structure/spec.md.

Issue ref: domattioli/QuADMesh#55
Spec ref: specs/004-unified-mesh-structure/spec.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ._layer_state import LayerState

VALID_KINDS = ("layers", "skeleton", "medial_axis")


@dataclass
class MeshStructure:
    """Selectable mesh structure with kind, layer count, and optional layer state."""

    kind: str
    n_layers: int
    layers: Optional[LayerState] = None


def compute_mesh_structure(domain, kind: str = "layers") -> MeshStructure:
    """Compute a mesh structure snapshot from a CHILmesh domain.

    Args:
        domain: A CHILmesh instance with layers attribute.
        kind: One of "layers", "skeleton", or "medial_axis". Defaults to "layers".

    Returns:
        A MeshStructure dataclass with the selected kind, layer count, and
        (for layers mode) a deep-copied LayerState snapshot.

    Raises:
        ValueError: If kind is not in VALID_KINDS.
        NotImplementedError: If kind is "skeleton" or "medial_axis"
            (not yet implemented).
    """
    if kind not in VALID_KINDS:
        raise ValueError(
            f"unknown kind {kind!r}; expected one of {VALID_KINDS}"
        )

    if kind == "layers":
        ls = LayerState.from_mesh(domain)
        n = getattr(domain, "n_layers", None)
        if n is None:
            n = ls.n_layers
        return MeshStructure(kind="layers", n_layers=int(n), layers=ls)

    if kind == "skeleton":
        raise NotImplementedError(
            "kind='skeleton' not yet implemented — image-style skeleton/"
            "medial-axis is distinct from chilmesh layers; tracked by "
            "QuADMesh #55 / specs/004-unified-mesh-structure/spec.md"
        )

    if kind == "medial_axis":
        raise NotImplementedError(
            "kind='medial_axis' not yet implemented — see QuADMesh #55 / "
            "specs/004-unified-mesh-structure/spec.md"
        )
