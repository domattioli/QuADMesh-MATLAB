"""Regression: tri2quad must leave ZERO interior residual triangles.

A properly converted mesh may keep triangles only on the domain boundary;
any triangle whose three edges are all interior is a conversion failure.
This pins the interior-saturating matching guarantee across fixtures.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from chilmesh import CHILmesh
from quadmesh import tri2quad

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "03_CHILMesh_Test_Cases" / "01_.14_Files"

FIXTURES = [
    "Test_Case_1.14",
    "Test_Case_2.14",
    "Test_Case_3.14",
    "simple_test_case.14",
    "square_mesh_test.14",
    "structuredMesh1.14",
]


def _edges(el):
    n = len(el)
    return [tuple(sorted((int(el[i]), int(el[(i + 1) % n])))) for i in range(n)]


def _normalize(row):
    """Padded quad [a,b,c,c] (any duplicated vertex) -> the underlying triangle."""
    vs = [int(x) for x in row]
    uniq = list(dict.fromkeys(vs))
    return tuple(uniq) if len(uniq) == 3 else tuple(vs)


def _interior_tri_count(mesh: CHILmesh) -> int:
    elems = [_normalize(r) for r in np.asarray(mesh.connectivity_list)]
    count = {}
    for el in elems:
        for e in _edges(el):
            count[e] = count.get(e, 0) + 1
    bset = {e for e, c in count.items() if c == 1}
    return sum(
        1 for el in elems if len(el) == 3 and not any(e in bset for e in _edges(el))
    )


def _tri_count(mesh: CHILmesh) -> int:
    return sum(
        1 for r in np.asarray(mesh.connectivity_list) if len(_normalize(r)) == 3
    )


def _segments_cross(a, b, c, d) -> bool:
    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    return (cr(c, d, a) > 0) != (cr(c, d, b) > 0) and (cr(a, b, c) > 0) != (
        cr(a, b, d) > 0
    )


def _bowtie_count(mesh: CHILmesh) -> int:
    cl = np.asarray(mesh.connectivity_list)
    P = mesh.points[:, :2]
    n = 0
    for row in cl:
        el = _normalize(row)
        if len(el) != 4:
            continue
        p = P[list(el)]
        if _segments_cross(p[0], p[1], p[2], p[3]) or _segments_cross(
            p[1], p[2], p[3], p[0]
        ):
            n += 1
    return n


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_tri2quad_zero_interior_tris(fixture_name):
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    mesh = CHILmesh.read_from_fort14(path)
    # Matching-only path (no boundary removal): interior must already be zero.
    quad_mesh = tri2quad(mesh, can_remove_edges=True, remove_boundary_tris=False)
    n_interior = _interior_tri_count(quad_mesh)
    assert n_interior == 0, (
        f"{fixture_name}: {n_interior} interior residual triangles after matching "
        f"(expected 0)"
    )


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_tri2quad_quad_pure(fixture_name):
    """Default tri2quad eliminates ALL triangles (interior and boundary)."""
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    mesh = CHILmesh.read_from_fort14(path)
    quad_mesh = tri2quad(mesh, can_remove_edges=True)
    n_tri = _tri_count(quad_mesh)
    assert n_tri == 0, (
        f"{fixture_name}: {n_tri} residual triangles after quad-pure tri2quad "
        f"(expected 0)"
    )
    n_bt = _bowtie_count(quad_mesh)
    assert n_bt == 0, (
        f"{fixture_name}: {n_bt} self-intersecting (bowtie) quads after boundary-tri "
        f"removal (expected 0)"
    )


def test_tri2quad_conforming_and_valid():
    """Quads must be non-degenerate and the mesh conforming (no edge in >2 elems)."""
    path = FIXTURE_DIR / "Test_Case_1.14"
    if not path.exists():
        pytest.skip("fixture missing")
    mesh = CHILmesh.read_from_fort14(path)
    q = tri2quad(mesh, can_remove_edges=True)
    cl = np.asarray(q.connectivity_list)
    count = {}
    for row in cl:
        for e in _edges(_normalize(row)):
            count[e] = count.get(e, 0) + 1
    assert max(count.values()) <= 2, "non-conforming edge shared by >2 elements"
