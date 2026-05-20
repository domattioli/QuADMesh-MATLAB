"""
Manim illustration of the Tri2Quad layer routine from QuADMesh-MATLAB.

Renders a small 4x3-vertex sample domain (12 triangles) and animates the
core algorithm from 02_QuADMESH_Library/02_Tri2Quad_Routine/Tri2QuadRoutine.m:

    For each layer (outward):
        1. Walk a path along the layer's outer boundary vertices.
        2. At every other interior edge, flag the edge for removal
           (element-flagging ensures adjacent triangles are skipped).
        3. Merge the two triangles sharing each flagged edge into a quad.

Render commands:
    manim -ql visualization/manim_tri2quad.py Tri2QuadScene   # 480p preview
    manim -qm visualization/manim_tri2quad.py Tri2QuadScene   # 720p
    manim -qh visualization/manim_tri2quad.py Tri2QuadScene   # 1080p
"""

from manim import (
    Scene, VGroup, Polygon, Line, Dot, Text, Arrow, Create, FadeIn, FadeOut,
    Transform, ReplacementTransform, Write, Indicate, AnimationGroup,
    UP, DOWN, LEFT, RIGHT, ORIGIN,
    WHITE, BLUE, RED, YELLOW, GREEN, GREY, ORANGE, BLACK,
)
import numpy as np


# --- Sample domain: 4 cols x 3 rows of vertices, NW->SE diagonals ---
COLS, ROWS = 4, 3
SPACING = 1.1
ORIGIN_SHIFT = np.array([-1.65, -0.5, 0.0])  # center grid roughly on canvas

# Vertex index helper.
def vid(i, j):
    return j * COLS + i

# Build vertex coordinates.
VERTS = np.array(
    [
        [i * SPACING, -j * SPACING, 0.0]
        for j in range(ROWS)
        for i in range(COLS)
    ]
) + ORIGIN_SHIFT

# Triangles: each grid cell (i,j) split by diagonal v(i,j)->v(i+1,j+1).
# Order chosen so each consecutive pair shares the diagonal we will remove.
TRIS = []                                       # list[(a,b,c)] vertex indices
MERGE_PAIRS = []                                # list[(tri_idx_a, tri_idx_b, shared_edge_endpoints)]
for j in range(ROWS - 1):
    for i in range(COLS - 1):
        a, b = vid(i, j), vid(i + 1, j)         # top-left, top-right
        c, d = vid(i, j + 1), vid(i + 1, j + 1) # bot-left, bot-right
        t_lower = (a, c, d)                     # left triangle (below diagonal)
        t_upper = (a, d, b)                     # right triangle (above diagonal)
        ti = len(TRIS)
        TRIS.append(t_lower)
        TRIS.append(t_upper)
        MERGE_PAIRS.append((ti, ti + 1, (a, d)))   # diagonal a<->d

# Outer boundary loop (CCW starting at v0).
def boundary_loop():
    loop = []
    for i in range(COLS):        loop.append(vid(i, 0))             # top L->R
    for j in range(1, ROWS):     loop.append(vid(COLS - 1, j))      # right T->B
    for i in range(COLS - 2, -1, -1): loop.append(vid(i, ROWS - 1)) # bot R->L
    for j in range(ROWS - 2, 0, -1):  loop.append(vid(0, j))        # left B->T
    return loop

BOUNDARY = boundary_loop()


# --- Style ---
TRI_FILL = BLUE
TRI_FILL_OPACITY = 0.25
EDGE_COLOR = WHITE
EDGE_WIDTH = 2.5
DIAG_HIGHLIGHT = RED
QUAD_FILL = GREEN
QUAD_FILL_OPACITY = 0.35
PATH_COLOR = YELLOW
VERT_COLOR = WHITE


class Tri2QuadScene(Scene):
    def construct(self):
        self._title_card()
        tri_polys, edge_lines, vert_dots = self._draw_mesh()
        self._label_layer(tri_polys)
        path_arrows = self._draw_boundary_path()
        self._merge_phase(tri_polys, edge_lines, path_arrows)
        self._final_card()

    # ---- Helpers ----
    def _title_card(self):
        title = Text("Tri2Quad Routine: Layered Triangle Pairing", font_size=32)
        sub = Text(
            "QuADMesh-MATLAB / 02_Tri2Quad_Routine",
            font_size=20, color=GREY,
        ).next_to(title, DOWN, buff=0.25)
        self.play(Write(title), FadeIn(sub))
        self.wait(1.2)
        self.play(FadeOut(title), FadeOut(sub))

    def _draw_mesh(self):
        # Vertices.
        vert_dots = VGroup(*[Dot(point=p, radius=0.05, color=VERT_COLOR) for p in VERTS])
        # Triangles.
        tri_polys = VGroup(*[
            Polygon(VERTS[a], VERTS[b], VERTS[c],
                    color=EDGE_COLOR, stroke_width=EDGE_WIDTH,
                    fill_color=TRI_FILL, fill_opacity=TRI_FILL_OPACITY)
            for (a, b, c) in TRIS
        ])
        # Edges drawn separately so we can highlight individual diagonals later.
        unique_edges = {}
        for (a, b, c) in TRIS:
            for (u, v) in [(a, b), (b, c), (c, a)]:
                key = tuple(sorted((u, v)))
                unique_edges.setdefault(key, key)
        edge_lines = {
            key: Line(VERTS[key[0]], VERTS[key[1]],
                      color=EDGE_COLOR, stroke_width=EDGE_WIDTH)
            for key in unique_edges
        }
        edges_group = VGroup(*edge_lines.values())

        caption = Text("Input: triangulated sample domain (12 tris)",
                       font_size=22).to_edge(UP, buff=0.3)
        self.play(Write(caption))
        self.play(Create(edges_group), run_time=1.8)
        self.play(FadeIn(tri_polys, lag_ratio=0.05), run_time=1.2)
        self.play(FadeIn(vert_dots, lag_ratio=0.02), run_time=0.8)
        self.wait(0.8)
        self.play(FadeOut(caption))
        return tri_polys, edge_lines, vert_dots

    def _label_layer(self, tri_polys):
        caption = Text("Layer 1 (outer band): all tris touch boundary",
                       font_size=22).to_edge(UP, buff=0.3)
        self.play(Write(caption))
        self.play(*[
            t.animate.set_fill(ORANGE, opacity=0.35) for t in tri_polys
        ], run_time=1.0)
        self.wait(0.6)
        self.play(*[
            t.animate.set_fill(TRI_FILL, opacity=TRI_FILL_OPACITY) for t in tri_polys
        ], run_time=0.6)
        self.play(FadeOut(caption))

    def _draw_boundary_path(self):
        caption = Text("Walk path along outer vertices (CCW)",
                       font_size=22).to_edge(UP, buff=0.3)
        self.play(Write(caption))
        arrows = VGroup()
        for k in range(len(BOUNDARY)):
            a = VERTS[BOUNDARY[k]]
            b = VERTS[BOUNDARY[(k + 1) % len(BOUNDARY)]]
            arr = Arrow(
                start=a, end=b, buff=0.12,
                stroke_width=4, color=PATH_COLOR,
                max_tip_length_to_length_ratio=0.18,
            )
            arrows.add(arr)
        self.play(Create(arrows, lag_ratio=0.1), run_time=2.0)
        self.wait(0.6)
        self.play(FadeOut(caption))
        return arrows

    def _merge_phase(self, tri_polys, edge_lines, path_arrows):
        caption = Text(
            "Identify every-other interior edge -> merge tri pairs into quads",
            font_size=22,
        ).to_edge(UP, buff=0.3)
        self.play(Write(caption))

        # For each merge pair: highlight shared diagonal red, fade it,
        # then morph the two triangles into a single quad polygon.
        for (ti_a, ti_b, (u, v)) in MERGE_PAIRS:
            tri_a = tri_polys[ti_a]
            tri_b = tri_polys[ti_b]
            ekey = tuple(sorted((u, v)))
            diag = edge_lines[ekey]

            # Build the quad in CCW order from the two tris' vertices.
            a, c, d = TRIS[ti_a]                            # (a, c, d)
            _, dd, b = TRIS[ti_b]                           # (a, d, b)
            assert dd == d
            quad_pts = [VERTS[a], VERTS[c], VERTS[d], VERTS[b]]
            quad = Polygon(
                *quad_pts,
                color=EDGE_COLOR, stroke_width=EDGE_WIDTH,
                fill_color=QUAD_FILL, fill_opacity=QUAD_FILL_OPACITY,
            )

            # Flash diagonal, fade tris into quad.
            self.play(diag.animate.set_color(DIAG_HIGHLIGHT).set_stroke(width=5),
                      run_time=0.35)
            self.play(Indicate(diag, color=DIAG_HIGHLIGHT, scale_factor=1.05),
                      run_time=0.35)
            self.play(
                FadeOut(diag),
                ReplacementTransform(VGroup(tri_a, tri_b), quad),
                run_time=0.6,
            )
            # Swap into tri_polys group so later iterations still reference correctly.
            tri_polys.submobjects[ti_a] = quad
            tri_polys.submobjects[ti_b] = quad  # both indices point to merged quad

        self.wait(0.4)
        self.play(FadeOut(path_arrows), FadeOut(caption))

    def _final_card(self):
        caption = Text("Result: 6 quadrilaterals from 12 triangles",
                       font_size=24).to_edge(UP, buff=0.3)
        self.play(Write(caption))
        self.wait(2.0)
