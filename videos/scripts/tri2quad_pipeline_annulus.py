"""
Manim animation of the CHILmesh -> QuADMESH+ pipeline on a triangulated annulus.

Stages animated:
    1. Triangulated annulus (input).
    2. Layer decomposition (color elements by layer index).
    3. Tri2Quad result (raw quadrilateral mesh from tri2quad_routine).
    4. Post-processed quad mesh (vertices smoothed by doublet collapse,
       quad-vertex merge, angle-based smoother, and FEM smoother).
    5. Quality summary.

Mirrors the end-to-end driver in `src/quadmesh/pipeline.py` which is the
Python port of QuADMESH-MATLAB's `matlab/quadmesh/00_Main/Main.m`.

Render:
    manim -ql --disable_caching videos/scripts/tri2quad_pipeline_annulus.py AnnulusPipelineScene
    manim -qm --disable_caching videos/scripts/tri2quad_pipeline_annulus.py AnnulusPipelineScene
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import Delaunay

from chilmesh import CHILmesh
from quadmesh import tri2quad
from quadmesh.pipeline import run_pipeline

from manim import (
    Scene, VGroup, Polygon, Line, Dot, Text,
    Create, FadeIn, FadeOut, Write, ReplacementTransform,
    UP, DOWN, LEFT, RIGHT, ORIGIN,
    WHITE, BLUE, RED, YELLOW, GREEN, GREY, ORANGE, PURPLE, TEAL, GOLD,
)


# ----------------------------- annulus geometry -----------------------------
RINGS = [1.00, 0.87, 0.72, 0.58, 0.45, 0.32]
NODES_PER_RING = [18, 16, 14, 12, 10, 9]


def build_annulus():
    """Build a triangulated annulus on concentric rings via Delaunay."""
    pts = []
    for k, (r, n) in enumerate(zip(RINGS, NODES_PER_RING)):
        offset = (k % 2) * np.pi / n        # stagger alternate rings
        th = np.linspace(0, 2 * np.pi, n, endpoint=False) + offset
        pts.append(np.column_stack([r * np.cos(th), r * np.sin(th)]))
    pts = np.vstack(pts)
    tri = Delaunay(pts)
    centroids = pts[tri.simplices].mean(axis=1)
    keep = np.linalg.norm(centroids, axis=1) > RINGS[-1] * 1.06
    return pts, tri.simplices[keep]


# ----------------------------- pipeline runner ------------------------------
def compute_stages():
    """Run the full pipeline once; snapshot each stage's state for Manim."""
    pts, simps = build_annulus()
    m_tri = CHILmesh(simps, pts, grid_name="annulus")

    # Per-element layer index for the tri mesh.
    elem_layer = np.zeros(m_tri.n_elems, dtype=int)
    for k in range(len(m_tri.Layers["OE"])):
        for e in list(m_tri.Layers["OE"][k]) + list(m_tri.Layers["IE"][k]):
            elem_layer[e] = k

    # Faithful path: layer-ordered sweep + interior saturation -> quad-pure
    # (zero interior tris, residual boundary tris cleared by point insertion).
    m_quad = tri2quad(m_tri, method="faithful")
    m_post = run_pipeline(m_tri, method="faithful", n_smooth_iter=12)

    q_pre = m_quad.elem_quality()[0]
    q_post = m_post.elem_quality()[0]

    return {
        "tri_pts": np.asarray(pts)[:, :2].copy(),
        "tri_conn": np.asarray(simps).copy(),
        "tri_layer": elem_layer,
        "n_layers": len(m_tri.Layers["OE"]),
        "quad_pts": np.asarray(m_quad.points)[:, :2].copy(),
        "quad_conn": np.asarray(m_quad.connectivity_list).copy(),
        "post_pts": np.asarray(m_post.points)[:, :2].copy(),
        "post_conn": np.asarray(m_post.connectivity_list).copy(),
        "q_pre_mean": float(q_pre.mean()),
        "q_post_mean": float(q_post.mean()),
        "q_pre_min": float(q_pre.min()),
        "q_post_min": float(q_post.min()),
    }


# ----------------------------- Manim styling --------------------------------
SCALE = 2.6
LAYER_COLORS = [ORANGE, PURPLE, TEAL, BLUE, GOLD]
TRI_FILL_OPACITY = 0.30
QUAD_FILL_OPACITY = 0.42
EDGE_COLOR = WHITE
EDGE_WIDTH = 1.3
SMOOTH_DURATION = 2.0


def to_canvas(p):
    return np.array([p[0] * SCALE, p[1] * SCALE, 0.0])


def make_polygon(pts_2d, conn_row, fill_color, fill_opacity):
    return Polygon(
        *[to_canvas(pts_2d[i]) for i in conn_row],
        stroke_width=EDGE_WIDTH,
        stroke_color=EDGE_COLOR,
        fill_color=fill_color,
        fill_opacity=fill_opacity,
    )


def quad_polygon_pts(pts_2d, conn_row):
    """Quad row may encode a tri as col0==col1; emit 3 or 4 verts accordingly."""
    a, b, c, d = conn_row
    if a == b:
        return [to_canvas(pts_2d[b]), to_canvas(pts_2d[c]), to_canvas(pts_2d[d])]
    return [
        to_canvas(pts_2d[a]),
        to_canvas(pts_2d[b]),
        to_canvas(pts_2d[c]),
        to_canvas(pts_2d[d]),
    ]


class AnnulusPipelineScene(Scene):
    def construct(self):
        S = compute_stages()
        self._title_card(S)
        tri_polys = self._draw_tris(S)
        self._show_layers(tri_polys, S)
        quad_polys = self._to_quads(tri_polys, S)
        self._smooth_post(quad_polys, S)
        self._final_card(S)

    # ------------------------------------------------------------- helpers
    def _title_card(self, S):
        title = Text(
            "QuADMESH+ Pipeline on a Triangulated Annulus",
            font_size=30,
        )
        sub = Text(
            "CHILmesh -> Tri2Quad -> Post-Process",
            font_size=20, color=GREY,
        ).next_to(title, DOWN, buff=0.25)
        self.play(Write(title), FadeIn(sub))
        self.wait(1.4)
        self.play(FadeOut(title), FadeOut(sub))

    def _draw_tris(self, S):
        caption = Text(
            f"Input: {len(S['tri_conn'])} triangles, "
            f"{len(S['tri_pts'])} vertices, "
            f"{S['n_layers']} layers",
            font_size=22,
        ).to_edge(UP, buff=0.30)
        self.play(Write(caption))

        tri_polys = [
            make_polygon(S["tri_pts"], row, BLUE, TRI_FILL_OPACITY)
            for row in S["tri_conn"]
        ]
        group = VGroup(*tri_polys)
        self.play(Create(group, lag_ratio=0.01), run_time=2.2)
        self.wait(0.8)
        self.play(FadeOut(caption))
        return tri_polys

    def _show_layers(self, tri_polys, S):
        caption = Text(
            f"Layer decomposition ({S['n_layers']} concentric layers)",
            font_size=22,
        ).to_edge(UP, buff=0.30)
        self.play(Write(caption))
        anims = []
        for ti, layer in enumerate(S["tri_layer"]):
            color = LAYER_COLORS[layer % len(LAYER_COLORS)]
            anims.append(tri_polys[ti].animate.set_fill(color, opacity=0.45))
        self.play(*anims, run_time=1.4)
        self.wait(1.5)
        # Reset back to neutral so the tri->quad transition reads clean.
        reset = [
            t.animate.set_fill(BLUE, opacity=TRI_FILL_OPACITY) for t in tri_polys
        ]
        self.play(*reset, run_time=0.6)
        self.play(FadeOut(caption))

    def _to_quads(self, tri_polys, S):
        caption = Text(
            f"Tri2Quad: pair triangles across every-other edge -> "
            f"{len(S['quad_conn'])} quads",
            font_size=20,
        ).to_edge(UP, buff=0.30)
        self.play(Write(caption))

        quad_polys = [
            Polygon(
                *quad_polygon_pts(S["quad_pts"], row),
                stroke_width=EDGE_WIDTH,
                stroke_color=EDGE_COLOR,
                fill_color=GREEN,
                fill_opacity=QUAD_FILL_OPACITY,
            )
            for row in S["quad_conn"]
        ]
        quad_group = VGroup(*quad_polys)
        tri_group = VGroup(*tri_polys)
        # Cross-fade.
        self.play(FadeOut(tri_group), FadeIn(quad_group), run_time=1.4)
        self.wait(1.0)
        self.play(FadeOut(caption))
        return quad_polys

    def _smooth_post(self, quad_polys, S):
        caption = Text(
            "Post-process: doublet collapse, quad-vertex merge, angle + FEM smoothing",
            font_size=18,
        ).to_edge(UP, buff=0.30)
        self.play(Write(caption))

        # Build new polygons at post-process vertex positions.
        new_polys = [
            Polygon(
                *quad_polygon_pts(S["post_pts"], row),
                stroke_width=EDGE_WIDTH,
                stroke_color=EDGE_COLOR,
                fill_color=GREEN,
                fill_opacity=QUAD_FILL_OPACITY,
            )
            for row in S["post_conn"]
        ]
        # Post-process changes the element COUNT (collapse + merge), so a 1:1
        # ReplacementTransform would strand the surplus raw quads on screen
        # (they overlap the post mesh). Cross-fade whole groups instead.
        old_group = VGroup(*quad_polys)
        new_group = VGroup(*new_polys)
        self.play(FadeOut(old_group), FadeIn(new_group), run_time=SMOOTH_DURATION)
        self.wait(1.0)
        self.play(FadeOut(caption))

    def _final_card(self, S):
        title = Text("Pipeline complete", font_size=28).to_edge(UP, buff=0.30)
        stats = Text(
            f"Quads: {len(S['quad_conn'])}    "
            f"Mean skew: {S['q_pre_mean']:.3f} -> {S['q_post_mean']:.3f}    "
            f"Min: {S['q_pre_min']:.3f} -> {S['q_post_min']:.3f}",
            font_size=18, color=GREY,
        ).next_to(title, DOWN, buff=0.20)
        self.play(Write(title), FadeIn(stats))
        self.wait(2.5)
