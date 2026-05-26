"""T010: Faithful path → 0 interior tris, conforming, 0 bowtie/flip.

Supplements test_no_interior_tris.py with conforming + bowtie checks.
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


def _run_faithful(domain):
    from quadmesh.tri2quad import tri2quad_routine
    return tri2quad_routine(domain, can_remove_edges=False, method="faithful")


def _boundary_edges(conn):
    from collections import Counter
    cnt = Counter()
    for row in conn:
        verts = [int(v) for v in row if v >= 0]
        n = len(verts)
        for i in range(n):
            e = tuple(sorted([verts[i], verts[(i+1) % n]]))
            cnt[e] += 1
    return {e for e, c in cnt.items() if c == 1}


def _segments_cross(a, b, c, d):
    def cross2(o, p, q):
        return (p[0]-o[0])*(q[1]-o[1]) - (p[1]-o[1])*(q[0]-o[0])
    d1, d2 = cross2(c, d, a), cross2(c, d, b)
    d3, d4 = cross2(a, b, c), cross2(a, b, d)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def test_conforming(domain):
    """No edge shared by more than 2 elements (conforming mesh)."""
    result = _run_faithful(domain)
    conn = result.connectivity_list
    from collections import Counter
    cnt = Counter()
    for row in conn:
        verts = [int(v) for v in row if v >= 0]
        n = len(verts)
        for i in range(n):
            e = tuple(sorted([verts[i], verts[(i+1) % n]]))
            cnt[e] += 1
    violations = [(e, c) for e, c in cnt.items() if c > 2]
    assert not violations, f"Non-conforming edges: {violations[:5]}"


def test_no_bowtie_quads(domain):
    """No quad has crossing diagonals (bowtie)."""
    result = _run_faithful(domain)
    conn = result.connectivity_list
    pts = result.points[:, :2]
    bowties = []
    for i, row in enumerate(conn):
        if int(row[3]) < 0 or int(row[0]) == int(row[3]):
            continue  # tri row (padded or repeated-first-vertex form)
        a, b, c, d = int(row[0]), int(row[1]), int(row[2]), int(row[3])
        if _segments_cross(pts[a], pts[b], pts[c], pts[d]):
            bowties.append(i)
        if _segments_cross(pts[b], pts[c], pts[d], pts[a]):
            bowties.append(i)
    assert not bowties, f"{len(bowties)} bowtie quads found"


def test_zero_area_quads(domain):
    """No quad has near-zero area (degenerate)."""
    result = _run_faithful(domain)
    conn = result.connectivity_list
    pts = result.points[:, :2]
    degenerate = []
    for i, row in enumerate(conn):
        if int(row[3]) < 0 or int(row[0]) == int(row[3]):
            continue
        verts = [int(row[j]) for j in range(4)]
        p = pts[verts]
        area = abs(float(np.sum(
            p[:, 0] * np.roll(p[:, 1], -1) - np.roll(p[:, 0], -1) * p[:, 1]
        ))) / 2
        if area < 1e-10:
            degenerate.append(i)
    assert not degenerate, f"{len(degenerate)} degenerate quads"
