"""Lightweight (matplotlib-only) renderer for the README pipeline demo GIF.

Produces ``videos/tri2quad_pipeline_annulus.gif`` without manim/ffmpeg/LaTeX —
useful in headless/CI containers where the manim toolchain is unavailable. The
manim script (``tri2quad_pipeline_annulus.py``) remains the higher-fidelity
generator when that toolchain is present.

Stages (matching the manim scene):
    1. Triangulated annulus input.
    2. Layer decomposition (elements colored by layer index).
    3. Tri2Quad result — faithful path, quad-pure (zero residual triangles).
    4. Post-processed quad mesh (smoothed).
    5. Quality summary.

Run:
    python videos/scripts/render_pipeline_gif.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.spatial import Delaunay

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.collections import PolyCollection

from chilmesh import CHILmesh
from quadmesh import tri2quad
from quadmesh.pipeline import run_pipeline

RINGS = [1.00, 0.87, 0.72, 0.58, 0.45, 0.32]
NODES_PER_RING = [18, 16, 14, 12, 10, 9]
LAYER_COLORS = ["#FF8C00", "#9370DB", "#20B2AA", "#4682B4", "#DAA520"]
OUT = Path(__file__).resolve().parents[1] / "tri2quad_pipeline_annulus.gif"


def build_annulus():
    pts = []
    for k, (r, n) in enumerate(zip(RINGS, NODES_PER_RING)):
        offset = (k % 2) * np.pi / n
        th = np.linspace(0, 2 * np.pi, n, endpoint=False) + offset
        pts.append(np.column_stack([r * np.cos(th), r * np.sin(th)]))
    pts = np.vstack(pts)
    tri = Delaunay(pts)
    centroids = pts[tri.simplices].mean(axis=1)
    keep = np.linalg.norm(centroids, axis=1) > RINGS[-1] * 1.06
    return pts, tri.simplices[keep]


def _polys(pts, conn):
    out = []
    for row in conn:
        vs = list(dict.fromkeys(int(x) for x in row))
        out.append(pts[vs, :2])
    return out


def compute_stages():
    pts, simps = build_annulus()
    m_tri = CHILmesh(simps, pts, grid_name="annulus")
    elem_layer = np.zeros(m_tri.n_elems, dtype=int)
    for k in range(len(m_tri.Layers["OE"])):
        for e in list(m_tri.Layers["OE"][k]) + list(m_tri.Layers["IE"][k]):
            elem_layer[e] = k
    m_quad = tri2quad(m_tri, method="faithful")
    m_post = run_pipeline(m_tri, method="faithful", n_smooth_iter=12)
    q_pre = m_quad.elem_quality()[0]
    q_post = m_post.elem_quality()[0]
    return {
        "tri_pts": np.asarray(pts)[:, :2],
        "tri_conn": np.asarray(simps),
        "tri_layer": elem_layer,
        "n_layers": len(m_tri.Layers["OE"]),
        "quad_pts": np.asarray(m_quad.points)[:, :2],
        "quad_conn": np.asarray(m_quad.connectivity_list),
        "post_pts": np.asarray(m_post.points)[:, :2],
        "post_conn": np.asarray(m_post.connectivity_list),
        "q_pre_mean": float(q_pre.mean()),
        "q_post_mean": float(q_post.mean()),
        "q_pre_min": float(q_pre.min()),
        "q_post_min": float(q_post.min()),
    }


def render(S, out=OUT, hold=18, fps=12):
    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#111111")
    ax.set_xlim(-1.25, 1.25)
    ax.set_ylim(-1.25, 1.35)
    ax.set_aspect("equal")
    ax.axis("off")

    tri_polys = _polys(S["tri_pts"], S["tri_conn"])
    quad_polys = _polys(S["quad_pts"], S["quad_conn"])
    post_polys = _polys(S["post_pts"], S["post_conn"])
    n_tri_resid = sum(1 for p in quad_polys if len(p) == 3)

    stages = [
        ("input", f"Input: {len(tri_polys)} triangles, {S['n_layers']} layers"),
        ("layers", f"Layer decomposition ({S['n_layers']} layers)"),
        ("quads", f"Tri2Quad (faithful): {len(quad_polys)} quads, "
                  f"{n_tri_resid} residual triangles"),
        ("post", "Post-process: collapse + merge + smoothing"),
        ("final", f"Mean skew {S['q_pre_mean']:.3f} -> {S['q_post_mean']:.3f}   "
                  f"min {S['q_pre_min']:.3f} -> {S['q_post_min']:.3f}"),
    ]
    frames = [(name, cap, j) for (name, cap) in stages for j in range(hold)]

    coll = PolyCollection([], edgecolors="white", linewidths=0.7)
    ax.add_collection(coll)
    title = ax.text(0, 1.27, "", ha="center", va="center", color="white",
                    fontsize=11, fontweight="bold")

    def draw(frame):
        name, cap, j = frame
        if name == "input":
            coll.set_verts(tri_polys)
            coll.set_facecolor("#3a6ea5")
            coll.set_alpha(0.55)
        elif name == "layers":
            coll.set_verts(tri_polys)
            coll.set_facecolor(
                [LAYER_COLORS[S["tri_layer"][i] % len(LAYER_COLORS)]
                 for i in range(len(tri_polys))]
            )
            coll.set_alpha(0.7)
        elif name == "quads":
            coll.set_verts(quad_polys)
            coll.set_facecolor("#2e8b57")
            coll.set_alpha(0.7)
        elif name == "post":
            # ease between raw-quad and post-process positions
            t = (j + 1) / hold
            if len(quad_polys) == len(post_polys):
                verts = [(1 - t) * a + t * b if a.shape == b.shape else b
                         for a, b in zip(quad_polys, post_polys)]
            else:
                verts = post_polys
            coll.set_verts(verts)
            coll.set_facecolor("#2e8b57")
            coll.set_alpha(0.7)
        else:  # final
            coll.set_verts(post_polys)
            coll.set_facecolor("#3cb371")
            coll.set_alpha(0.8)
        title.set_text(cap)
        return coll, title

    anim = FuncAnimation(fig, draw, frames=frames, blit=False)
    anim.save(out, writer=PillowWriter(fps=fps))
    plt.close(fig)
    return n_tri_resid


if __name__ == "__main__":
    S = compute_stages()
    resid = render(S)
    print(f"wrote {OUT}  ({len(S['quad_conn'])} quads, {resid} residual tris)")
