"""
Manim illustration of the Tri2Quad layer routine from QuADMesh-MATLAB.

Renders a 6x6-vertex sample domain (50 triangles, three layers) and animates
the core algorithm from 02_QuADMESH_Library/02_Tri2Quad_Routine/Tri2QuadRoutine.m:

    For each layer (outward -> inward):
        1. Walk a CCW path along the layer's outer boundary vertices.
        2. At every other interior edge incident to the path vertex, flag
           the edge for removal (element-flagging ensures the adjacent
           triangle is skipped on the next vertex).
        3. Merge the two triangles sharing each flagged edge into a quad.

Render commands:
    manim -ql videos/scripts/tri2quad_6x6_grid.py Tri2QuadScene   # 480p preview
    manim -qm videos/scripts/tri2quad_6x6_grid.py Tri2QuadScene   # 720p
    manim -qh videos/scripts/tri2quad_6x6_grid.py Tri2QuadScene   # 1080p
"""

from manim import (
    Scene, VGroup, Polygon, Line, Dot, Text, Arrow,
    Create, FadeIn, FadeOut, Write, Indicate, ReplacementTransform,
    UP, DOWN, LEFT, RIGHT, ORIGIN,
    WHITE, BLUE, RED, YELLOW, GREEN, GREY, ORANGE, PURPLE, TEAL,
)
import numpy as np


# --- Sample domain: 6 cols x 6 rows of vertices (5x5 = 25 cells, 50 tris) ---
COLS, ROWS = 6, 6
SPACING = 0.80
ORIGIN_SHIFT = np.array([
    -(COLS - 1) * SPACING / 2.0,
    (ROWS - 1) * SPACING / 2.0,
    0.0,
])

def vid(i, j):
    return j * COLS + i

# Vertex coords. Manim is y-up; row j=0 placed at top by negating j.
VERTS = np.array(
    [
        [i * SPACING, -j * SPACING, 0.0]
        for j in range(ROWS)
        for i in range(COLS)
    ]
) + ORIGIN_SHIFT

# Each cell triangulated along its NW->SE diagonal.
TRIS = []
CELL2TRIS = {}          # (ci,cj) -> (lower_tri_idx, upper_tri_idx)
CELL2DIAG = {}          # (ci,cj) -> (vert_a, vert_d) endpoints of removed diagonal
CELL2QUAD = {}          # (ci,cj) -> CCW quad vertex coords [a, c, d, b]
for cj in range(ROWS - 1):
    for ci in range(COLS - 1):
        a = vid(ci, cj)              # top-left
        b = vid(ci + 1, cj)          # top-right
        c = vid(ci, cj + 1)          # bot-left
        d = vid(ci + 1, cj + 1)      # bot-right
        ti = len(TRIS)
        TRIS.append((a, c, d))       # lower-left tri
        TRIS.append((a, d, b))       # upper-right tri
        CELL2TRIS[(ci, cj)] = (ti, ti + 1)
        CELL2DIAG[(ci, cj)] = (a, d)
        CELL2QUAD[(ci, cj)] = [VERTS[a], VERTS[c], VERTS[d], VERTS[b]]


def boundary_loop(i0, i1, j0, j1):
    """CCW (math, y-up) loop of vertex IDs around rect [i0..i1] x [j0..j1]."""
    loop = []
    for j in range(j0, j1 + 1):           loop.append(vid(i0, j))     # left top->bot
    for i in range(i0 + 1, i1 + 1):       loop.append(vid(i, j1))     # bot L->R
    for j in range(j1 - 1, j0 - 1, -1):   loop.append(vid(i1, j))     # right bot->top
    for i in range(i1 - 1, i0, -1):       loop.append(vid(i, j0))     # top R->L
    return loop


def cells_in_layer(k):
    """Layer k (0-indexed): cells on the perimeter of the inner rectangle peeled k times."""
    return [
        (ci, cj)
        for cj in range(k, ROWS - 1 - k) for ci in range(k, COLS - 1 - k)
        if ci == k or ci == COLS - 2 - k or cj == k or cj == ROWS - 2 - k
    ]


def build_layers():
    layer_colors = [ORANGE, PURPLE, TEAL]
    layers = []
    k = 0
    while True:
        cells = cells_in_layer(k)
        if not cells:
            break
        layers.append({
            "name": f"Layer {k + 1}",
            "cells": cells,
            "loop": boundary_loop(k, COLS - 1 - k, k, ROWS - 1 - k),
            "color": layer_colors[k % len(layer_colors)],
        })
        k += 1
    return layers


def compute_merge_order(cells, loop_verts):
    """
    Walk the boundary path in order; at each vertex try to remove every
    incident diagonal whose two incident tris are not yet flagged.
    Mirrors the element-flagging behavior of identifyEdgesFun_v2.m.
    Returns list of (path_vertex_id, cell_coord) in traversal order.
    """
    diag_at = {}
    for cell in cells:
        a, d = CELL2DIAG[cell]
        diag_at.setdefault(a, []).append(cell)
        diag_at.setdefault(d, []).append(cell)
    flagged = set()
    order = []
    for v in loop_verts:
        for cell in diag_at.get(v, []):
            if cell in flagged:
                continue
            order.append((v, cell))
            flagged.add(cell)
    return order


LAYERS = build_layers()  # ordered outer (Layer 1) -> inner (Layer N)


# --- Style ---
TRI_FILL = BLUE
TRI_FILL_OPACITY = 0.22
EDGE_COLOR = WHITE
EDGE_WIDTH = 2.0
DIAG_HIGHLIGHT = RED
QUAD_FILL = GREEN
QUAD_FILL_OPACITY = 0.40
PATH_COLOR = YELLOW
VERT_COLOR = WHITE


class Tri2QuadScene(Scene):
    def construct(self):
        self._title_card()
        tri_polys, edge_lines, vert_dots = self._draw_mesh()
        self._show_layers(tri_polys)
        # MATLAB: for iLayer = Domain.nLayers:-1:1  (innermost -> outermost).
        for layer in reversed(LAYERS):
            self._process_layer(layer, tri_polys, edge_lines)
        self._final_card()

    # ---------------------------------------------------------------- helpers
    def _title_card(self):
        title = Text("Tri2Quad Routine: Layered Triangle Pairing", font_size=30)
        sub = Text(
            "QuADMesh-MATLAB / 02_Tri2Quad_Routine",
            font_size=20, color=GREY,
        ).next_to(title, DOWN, buff=0.25)
        self.play(Write(title), FadeIn(sub))
        self.wait(1.0)
        self.play(FadeOut(title), FadeOut(sub))

    def _draw_mesh(self):
        edge_keys = set()
        for tri in TRIS:
            a, b, c = tri
            for u, v in [(a, b), (b, c), (c, a)]:
                edge_keys.add(tuple(sorted((u, v))))
        edge_lines = {
            k: Line(VERTS[k[0]], VERTS[k[1]],
                    color=EDGE_COLOR, stroke_width=EDGE_WIDTH)
            for k in edge_keys
        }
        edges_group = VGroup(*edge_lines.values())
        # Triangles drawn with fill only; edge_lines provide strokes.
        tri_polys = [
            Polygon(
                VERTS[a], VERTS[b], VERTS[c],
                stroke_width=0,
                fill_color=TRI_FILL, fill_opacity=TRI_FILL_OPACITY,
            )
            for (a, b, c) in TRIS
        ]
        tri_group = VGroup(*tri_polys)
        vert_dots = VGroup(*[
            Dot(point=p, radius=0.045, color=VERT_COLOR) for p in VERTS
        ])

        caption = Text(
            f"Input: {len(TRIS)} triangles, {COLS * ROWS} vertices",
            font_size=22,
        ).to_edge(UP, buff=0.3)
        self.play(Write(caption))
        self.play(FadeIn(tri_group, lag_ratio=0.02), run_time=1.2)
        self.play(Create(edges_group), run_time=1.8)
        self.play(FadeIn(vert_dots, lag_ratio=0.01), run_time=0.7)
        self.wait(0.6)
        self.play(FadeOut(caption))
        return tri_polys, edge_lines, vert_dots

    def _show_layers(self, tri_polys):
        caption = Text(
            f"Layer decomposition: {len(LAYERS)} layers (Layer 1 = outermost)",
            font_size=22,
        ).to_edge(UP, buff=0.3)
        self.play(Write(caption))
        anims = []
        for layer in LAYERS:
            for cell in layer["cells"]:
                for ti in CELL2TRIS[cell]:
                    anims.append(
                        tri_polys[ti].animate.set_fill(layer["color"], opacity=0.42)
                    )
        self.play(*anims, run_time=1.0)
        self.wait(1.0)
        reset = [
            tri_polys[ti].animate.set_fill(TRI_FILL, opacity=TRI_FILL_OPACITY)
            for ti in range(len(tri_polys))
        ]
        self.play(*reset, run_time=0.6)
        self.play(FadeOut(caption))

    def _process_layer(self, layer, tri_polys, edge_lines):
        caption = Text(
            f"{layer['name']}: walk CCW path -> flag every-other edge -> merge",
            font_size=20,
        ).to_edge(UP, buff=0.3)
        self.play(Write(caption))

        loop = layer["loop"]
        # CCW arrows around this layer's boundary.
        arrows = VGroup()
        for k in range(len(loop)):
            p0 = VERTS[loop[k]]
            p1 = VERTS[loop[(k + 1) % len(loop)]]
            arrows.add(Arrow(
                start=p0, end=p1, buff=0.10, stroke_width=4,
                color=PATH_COLOR,
                max_tip_length_to_length_ratio=0.20,
            ))
        self.play(Create(arrows, lag_ratio=0.08), run_time=1.5)

        # Tint layer cells lightly with the layer color.
        anims = []
        for cell in layer["cells"]:
            for ti in CELL2TRIS[cell]:
                anims.append(
                    tri_polys[ti].animate.set_fill(layer["color"], opacity=0.35)
                )
        if anims:
            self.play(*anims, run_time=0.5)

        # Walk merges in path-traversal order.
        merges = compute_merge_order(layer["cells"], loop)
        cursor = Dot(point=VERTS[loop[0]], radius=0.11, color=RED)
        self.play(FadeIn(cursor))

        for (v, cell) in merges:
            self.play(cursor.animate.move_to(VERTS[v]), run_time=0.18)
            a, d = CELL2DIAG[cell]
            ekey = tuple(sorted((a, d)))
            diag = edge_lines[ekey]
            self.play(
                diag.animate.set_color(DIAG_HIGHLIGHT).set_stroke(width=5),
                run_time=0.15,
            )
            quad = Polygon(
                *CELL2QUAD[cell],
                stroke_width=0,
                fill_color=QUAD_FILL, fill_opacity=QUAD_FILL_OPACITY,
            )
            t_lower_idx, t_upper_idx = CELL2TRIS[cell]
            self.play(
                FadeOut(diag),
                ReplacementTransform(
                    VGroup(tri_polys[t_lower_idx], tri_polys[t_upper_idx]),
                    quad,
                ),
                run_time=0.35,
            )
            tri_polys[t_lower_idx] = quad
            tri_polys[t_upper_idx] = quad

        self.play(FadeOut(cursor), FadeOut(arrows))
        self.play(FadeOut(caption))
        self.wait(0.3)

    def _final_card(self):
        n_quads = sum(len(L["cells"]) for L in LAYERS)
        caption = Text(
            f"Result: {n_quads} quadrilaterals from {len(TRIS)} triangles",
            font_size=24,
        ).to_edge(UP, buff=0.3)
        self.play(Write(caption))
        self.wait(2.5)
