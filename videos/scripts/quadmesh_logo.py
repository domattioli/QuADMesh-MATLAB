from manim import *
import numpy as np
from typing import List, Tuple

# Manim 0.20.x config (must be set before Scene class)
config.pixel_height = 1080
config.pixel_width = 1920
config.frame_rate = 30
config.background_color = "#0d0d0f"


class QuadmeshLogoScene(Scene):

    EDGE_COLOR = "#e8e8e8"
    TRI_FILL = "#c97b2f"
    QUAD_FILL = "#2e7fcf"
    ACCENT_COLOR = "#ffd34e"

    def construct(self):
        # 1. Fade in title
        title = Text("QuADMESH", font_size=80, weight=BOLD, color=self.ACCENT_COLOR)
        title.to_edge(UP, buff=0.8)
        self.play(FadeIn(title), run_time=1.0)
        self.wait(0.3)

        # 2. Build annulus mesh
        mesh = self.create_annulus_mesh()
        mesh_group = VGroup(*mesh["triangles"])
        mesh_group.scale(1.5)
        mesh_group.center()

        self.play(FadeIn(mesh_group), run_time=0.5)
        self.wait(0.2)

        # Animate triangles appearing one by one
        for tri in mesh["triangles"]:
            self.add(tri)
        self.wait(0.5)

        # 3. Tri→Quad morph: select 4 triangle pairs and merge
        tri_indices = mesh["triangles"]
        quad_pairs = [0, 2, 4, 5]  # Select 4 of 6 pairs to merge

        quads_to_add = []
        tris_to_remove = []

        for pair_idx in quad_pairs:
            tri1_idx = pair_idx * 2
            tri2_idx = pair_idx * 2 + 1

            if tri1_idx < len(tri_indices) and tri2_idx < len(tri_indices):
                tri1 = tri_indices[tri1_idx]
                tri2 = tri_indices[tri2_idx]

                quad = self.create_quad_from_triangles(tri1, tri2)
                if quad is not None:
                    quads_to_add.append(quad)
                    tris_to_remove.append(tri1)
                    tris_to_remove.append(tri2)

        morph_duration = 1.5
        for tri in tris_to_remove:
            self.play(
                tri.animate.set_fill(opacity=0),
                run_time=morph_duration / 2,
                rate_func=smooth,
            )

        for quad in quads_to_add:
            self.add(quad)
            self.play(
                quad.animate.set_fill(opacity=0.9),
                run_time=morph_duration / 2,
                rate_func=smooth,
            )

        self.wait(1.5)
        self.wait(1.5)

        # 4. Tagline
        tagline = Text(
            "triangles in · quads out",
            font_size=36,
            color=self.EDGE_COLOR,
            slant=ITALIC,
        )
        tagline.next_to(mesh_group, DOWN, buff=1.0)
        self.play(FadeIn(tagline), run_time=1.0)
        self.wait(1.0)

        self.play(FadeOut(Group(title, mesh_group, tagline)), run_time=1.0)
        self.wait(0.5)

    def create_annulus_mesh(self) -> dict:
        n_spokes = 6
        inner_r = 1.0
        outer_r = 2.2

        inner_verts = []
        outer_verts = []

        for i in range(n_spokes):
            angle_inner = 2 * np.pi * i / n_spokes
            angle_outer = angle_inner + np.pi / n_spokes

            inner_verts.append(
                np.array([inner_r * np.cos(angle_inner), inner_r * np.sin(angle_inner), 0])
            )
            outer_verts.append(
                np.array([outer_r * np.cos(angle_outer), outer_r * np.sin(angle_outer), 0])
            )

        triangles = []
        triangle_verts = []

        for i in range(n_spokes):
            i_next = (i + 1) % n_spokes

            verts1 = [inner_verts[i], outer_verts[i], inner_verts[i_next]]
            tri1 = self.create_triangle(verts1, self.TRI_FILL)
            triangles.append(tri1)
            triangle_verts.append(verts1)

            verts2 = [outer_verts[i], outer_verts[i_next], inner_verts[i_next]]
            tri2 = self.create_triangle(verts2, self.TRI_FILL)
            triangles.append(tri2)
            triangle_verts.append(verts2)

        return {
            "triangles": triangles,
            "vertices": np.array(inner_verts + outer_verts),
            "triangle_vertices": triangle_verts,
        }

    def create_triangle(self, vertices: List[np.ndarray], fill_color: str) -> Polygon:
        points = [v if len(v) == 3 else np.array([v[0], v[1], 0.0]) for v in vertices]
        return Polygon(*points, color=self.EDGE_COLOR, fill_color=fill_color, fill_opacity=0.8)

    def create_quad_from_triangles(self, tri1: Polygon, tri2: Polygon) -> Polygon:
        pts1 = tri1.get_vertices()
        pts2 = tri2.get_vertices()

        quad_points = []
        seen = set()

        for pt in np.vstack([pts1, pts2]):
            pt_tuple = tuple(np.round(pt, 4))
            if pt_tuple not in seen:
                quad_points.append(pt)
                seen.add(pt_tuple)

        if len(quad_points) >= 4:
            return Polygon(
                *quad_points[:4],
                color=self.EDGE_COLOR,
                fill_color=self.QUAD_FILL,
                fill_opacity=0.0,
            )
        return None
