"""Build the 4-stage CHILmesh pipeline snapshots used by pipeline_annulus_scene.py.

Runs the legacy 4-row README pipeline on the annulus fixture and dumps the
resulting (vertex_positions, connectivity, quality stats) tuple per stage to
JSON so the Manim scene can render without re-running the pipeline.

Stages:
  Row 1: Raw annulus (Delaunay input)
  Row 2: ADMESH truss warm-start  (chilmesh.optimize_with_admesh_truss)
  Row 3: FEM smoother             (CHILmesh.smooth_mesh(method='fem'))
  Row 4: Right-iso smoother stub  (sort tri angles -> {45,45,90}; nudge verts)

Delaunay re-triangulation runs after every stage that moves vertices freely,
filtering simplices to the annular domain (0.30 < |centroid| < 1.00). Without
this step the ADMESH truss output carries ~137 negative-area triangles since
distmesh2d is a fresh-generation method, not an in-place optimizer.

Output: /tmp/readme_pipeline.json (or path passed as first argument).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import Delaunay

from chilmesh import CHILmesh, examples, optimize_with_admesh_truss


# --- annulus signed-distance + size grading for the truss ---------------
def annulus_sdf(p):
    return np.maximum(np.linalg.norm(p, axis=1) - 1.0, 0.3 - np.linalg.norm(p, axis=1))


H_MIN = 0.05
H_MAX = 0.18
GRADING_HALF_WIDTH = 0.35


def annulus_size_fn(p):
    d = np.abs(annulus_sdf(p))
    t = np.clip(d / GRADING_HALF_WIDTH, 0.0, 1.0)
    return H_MIN + (H_MAX - H_MIN) * t


# --- Delaunay re-triangulation restricted to the annulus ----------------
def retriangulate(points_xy: np.ndarray) -> np.ndarray:
    tri = Delaunay(points_xy)
    cents = points_xy[tri.simplices].mean(axis=1)
    r = np.linalg.norm(cents, axis=1)
    keep = (r > 0.30 + 1e-6) & (r < 1.0 - 1e-6)
    return tri.simplices[keep]


# --- right-iso heuristic (admesh.quad_prep stand-in) --------------------
def _tri_angles(p, a, b, c):
    ab = p[b] - p[a]; ac = p[c] - p[a]
    ba = -ab; bc = p[c] - p[b]
    ca = -ac; cb = -bc

    def ang(u, v):
        n = float(np.linalg.norm(u) * np.linalg.norm(v))
        if n < 1e-12:
            return 0.0
        return math.acos(max(-1.0, min(1.0, float(np.dot(u, v)) / n)))

    return ang(ab, ac), ang(ba, bc), ang(ca, cb)


def right_iso_smoother(mesh: CHILmesh, n_iter: int = 20, omega: float = 0.05) -> CHILmesh:
    """Iteratively push triangle angles toward the {45, 45, 90} target.

    Stub fallback for ADMESH's quad_prep.smooth_for_quadrangulation. For each
    triangle, sort its angles ascending and assign {45, 45, 90} to the sorted
    slots; for each interior vertex of that triangle, move it away from the
    opposite-edge midpoint when its angle exceeds the target, toward it when
    below. Sign convention: distance to opposite-edge midpoint and vertex
    angle are inversely related.
    """
    pts = mesh.points[:, :2].copy()
    b_verts = set(np.unique(mesh.edge2vert(mesh.boundary_edges()).flatten()).tolist())
    conn = mesh.connectivity_list

    for _ in range(n_iter):
        delta = np.zeros_like(pts)
        weight = np.zeros(mesh.n_verts)
        for row in conn:
            a, b, c = int(row[0]), int(row[1]), int(row[2])
            ang = np.array(_tri_angles(pts, a, b, c))
            order = np.argsort(ang)
            assigned = np.zeros(3)
            assigned[order[0]] = math.pi / 4
            assigned[order[1]] = math.pi / 4
            assigned[order[2]] = math.pi / 2
            verts = [a, b, c]
            for vi, vid in enumerate(verts):
                if vid in b_verts:
                    continue
                dev = ang[vi] - assigned[vi]  # positive => angle too large
                others = [verts[(vi + 1) % 3], verts[(vi + 2) % 3]]
                center = (pts[others[0]] + pts[others[1]]) / 2.0
                d = center - pts[vid]
                dn = float(np.linalg.norm(d))
                if dn > 1e-9:
                    delta[vid] += -(dev / math.pi) * d
                    weight[vid] += abs(dev) / math.pi
        msk = weight > 1e-9
        pts[msk] += omega * delta[msk] / weight[msk, None]

    new_pts = mesh.points.copy()
    new_pts[:, :2] = pts
    mesh.change_points(new_pts[:, :2], acknowledge_change=True)
    return mesh


# --- iso-deviation metric: mean L2 distance of sorted angles from {45,45,90}
def iso_dev_stat(mesh: CHILmesh) -> float:
    pts = mesh.points[:, :2]
    devs = []
    for row in mesh.connectivity_list:
        a, b, c = int(row[0]), int(row[1]), int(row[2])
        ang = np.array(_tri_angles(pts, a, b, c)) * 180.0 / math.pi
        ang_sorted = np.sort(ang)
        devs.append(float(np.linalg.norm(ang_sorted - np.array([45, 45, 90]))))
    return float(np.mean(devs))


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/readme_pipeline.json")

    # Row 1: raw annulus
    row1 = examples.annulus()

    # Row 2: ADMESH truss warm-start + Delaunay repair
    row2_raw = optimize_with_admesh_truss(
        row1, annulus_sdf, size_fn=annulus_size_fn, h0=H_MIN, seed=0,
        niter=500, deltat=0.02, Fscale=0.5, dptol=1e-3,
        enforce_non_degradation=False,
    )
    row2 = CHILmesh(connectivity=retriangulate(row2_raw.points[:, :2]),
                    points=row2_raw.points)

    # Row 3: FEM smoother (Balendran) + Delaunay repair
    row3 = row2.copy()
    row3.smooth_mesh(method="fem", acknowledge_change=True)
    row3 = CHILmesh(connectivity=retriangulate(row3.points[:, :2]),
                    points=row3.points)

    # Row 4: right-iso stub + Delaunay repair
    row4 = right_iso_smoother(row3.copy())
    row4 = CHILmesh(connectivity=retriangulate(row4.points[:, :2]),
                    points=row4.points)

    rows = []
    for stage, name, algo, mesh in [
        ("Row 1", "Raw annulus",             "Delaunay input",                          row1),
        ("Row 2", "ADMESH truss warm-start", "spring relaxation vs SDF + re-Delaunay",  row2),
        ("Row 3", "FEM smoother",            "Balendran direct + re-Delaunay",          row3),
        ("Row 4", "Right-iso smoother",      "angles -> {45,45,90} + re-Delaunay",      row4),
    ]:
        q = mesh.elem_quality()[0]
        rows.append({
            "stage": stage,
            "name": name,
            "algo": algo,
            "points": mesh.points[:, :2].tolist(),
            "elements": mesh.connectivity_list.tolist(),
            "q_med": float(np.median(q)),
            "iso_dev": iso_dev_stat(mesh),
        })
        print(f"{stage} {name:30s}: n_elems={mesh.n_elems}  "
              f"med Q={np.median(q):.4f}  iso-dev={iso_dev_stat(mesh):.2f}")

    out_path.write_text(json.dumps({"rows": rows}))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
