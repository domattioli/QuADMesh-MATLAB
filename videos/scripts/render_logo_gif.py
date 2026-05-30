"""Matplotlib-only renderer for the QuADMESH logo animation GIF.

Produces ``videos/quadmesh_logo.gif`` without manim/ffmpeg/chilmesh — pure numpy
+ matplotlib. Mirrors the content, colors, and geometry of ``quadmesh_logo.py``
(the manim reference), including the 6-spoke annulus, triangle-to-quad morph of
4 selected pairs, and animated wordmark with letter color morphing.

Run:
    python videos/scripts/render_logo_gif.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection

BG_COLOR = "#0d0d0f"
ADMESH_COLOR_INITIAL = "#00CC44"
ADMESH_COLOR_FINAL = "#CC00CC"
EDGE_COLOR = "#e8e8e8"
TRI_FILL = "#c97b2f"
QUAD_FILL = "#2e7fcf"

OUT = Path(__file__).resolve().parents[1] / "quadmesh_logo.gif"


def create_annulus_mesh(n_spokes=6, inner_r=1.0, outer_r=2.2):
    """Create 6-spoke annulus with 12 triangles (2 per spoke).

    Returns:
        dict with keys:
            - 'inner_verts': list of n_spokes inner vertices
            - 'outer_verts': list of n_spokes outer vertices
            - 'triangles': list of 12 triangle vertex index triplets
            - 'tri_coords': list of 12 triangles, each with 3 (x,y) coords
    """
    inner_verts = []
    outer_verts = []

    for i in range(n_spokes):
        angle_inner = 2 * np.pi * i / n_spokes
        angle_outer = angle_inner + np.pi / n_spokes

        inner_verts.append([inner_r * np.cos(angle_inner), inner_r * np.sin(angle_inner)])
        outer_verts.append([outer_r * np.cos(angle_outer), outer_r * np.sin(angle_outer)])

    triangles = []
    tri_coords = []

    for i in range(n_spokes):
        i_next = (i + 1) % n_spokes

        # Triangle 1: [inner_i, outer_i, inner_next]
        tri1_verts = [inner_verts[i], outer_verts[i], inner_verts[i_next]]
        triangles.append((i, n_spokes + i, i_next))
        tri_coords.append(tri1_verts)

        # Triangle 2: [outer_i, outer_next, inner_next]
        tri2_verts = [outer_verts[i], outer_verts[i_next], inner_verts[i_next]]
        triangles.append((n_spokes + i, n_spokes + i_next, i_next))
        tri_coords.append(tri2_verts)

    return {
        "inner_verts": inner_verts,
        "outer_verts": outer_verts,
        "triangles": triangles,
        "tri_coords": tri_coords,
    }


def merge_triangle_pair(tri1_coords, tri2_coords):
    """Merge two triangles into a quad by finding 4 unique vertices.

    Returns:
        list of 4 (x,y) coords forming the quad in CCW order around centroid,
        or None if < 4 unique verts.
    """
    pts = np.vstack([tri1_coords, tri2_coords])
    # Round to avoid float precision issues
    unique_pts = []
    seen = set()
    for pt in pts:
        pt_rounded = tuple(np.round(pt, 6))
        if pt_rounded not in seen:
            unique_pts.append(pt)
            seen.add(pt_rounded)

    if len(unique_pts) >= 4:
        quad_pts = unique_pts[:4]
        # Order vertices CCW around centroid to avoid self-intersecting polygon
        quad_arr = np.array(quad_pts)
        centroid = quad_arr.mean(axis=0)
        angles = np.arctan2(quad_arr[:, 1] - centroid[1], quad_arr[:, 0] - centroid[0])
        ccw_indices = np.argsort(angles)
        return [quad_pts[i] for i in ccw_indices]
    return None


def render(out=OUT, hold=16, fps=18):
    """Render logo animation with wordmark and letter color morphing."""

    # Build mesh
    mesh = create_annulus_mesh()
    tri_coords = mesh["tri_coords"]

    # Identify quad pairs to morph: pairs [0, 2, 4, 5] (pairs share edge, merge)
    quad_pairs = [0, 2, 4, 5]
    quads = []
    quad_tri_indices = []
    for pair_idx in quad_pairs:
        tri1_idx = pair_idx * 2
        tri2_idx = pair_idx * 2 + 1
        quad = merge_triangle_pair(tri_coords[tri1_idx], tri_coords[tri2_idx])
        if quad is not None:
            quads.append(quad)
            quad_tri_indices.append((tri1_idx, tri2_idx))

    # Frames: discrete holds for animation stages
    # (stage_name, hold_count)
    stage_specs = [
        ("mesh_fade_in", hold),
        ("triangles_draw", hold),
        ("morph_tris_fade", hold),
        ("morph_quads_fade", hold),
        ("qu_fly_in", hold),
        ("hold_final", hold),
    ]

    frames = []
    for stage_name, count in stage_specs:
        for i in range(count):
            frames.append((stage_name, i / count))

    # Setup figure
    fig, ax = plt.subplots(figsize=(6.8, 6.8))
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(-2.8, 2.8)
    ax.set_ylim(-3.0, 3.0)
    ax.set_aspect("equal")
    ax.axis("off")

    # Create ADMESH letter text objects
    # Letters: A, D, M, E, S, H
    # Positions: x = -1.125, -0.675, -0.225, 0.225, 0.675, 1.125
    # y = -2.6 for all
    admesh_letters = "ADMESH"
    admesh_x_positions = [-1.125, -0.675, -0.225, 0.225, 0.675, 1.125]
    admesh_texts = []
    for letter, x_pos in zip(admesh_letters, admesh_x_positions):
        text_obj = ax.text(
            x_pos, -2.6, letter, ha="center", va="center",
            fontsize=50, fontweight="bold",
            color=ADMESH_COLOR_INITIAL, alpha=0.0
        )
        admesh_texts.append(text_obj)

    # Create "Qu" text object
    # Starts at x=-6.0 (off-screen left), animates to x=-1.35 (right-aligned before A)
    qu_text = ax.text(
        -6.0, -2.6, "Qu", ha="right", va="center",
        fontsize=50, fontweight="bold",
        color=ADMESH_COLOR_FINAL, alpha=0.0
    )

    # Patch collections for triangles and quads
    tri_patches = [MplPolygon(tri_coords[i]) for i in range(len(tri_coords))]
    tri_collection = PatchCollection(tri_patches, edgecolors=EDGE_COLOR, linewidths=0.8)
    ax.add_collection(tri_collection)

    quad_patches = [MplPolygon(quad) for quad in quads]
    quad_collection = PatchCollection(quad_patches, edgecolors=EDGE_COLOR, linewidths=0.8)
    ax.add_collection(quad_collection)

    # Alpha tracking for triangles and quads
    tri_alphas = np.ones(len(tri_coords))
    quad_alphas = np.zeros(len(quads))

    # Color tracking for ADMESH letters
    admesh_colors = [ADMESH_COLOR_INITIAL] * 6

    def draw(frame):
        stage_name, progress = frame

        # Reset alphas and colors
        tri_alphas[:] = 1.0
        quad_alphas[:] = 0.0
        for _i in range(6): admesh_colors[_i] = ADMESH_COLOR_INITIAL

        mesh_alpha = 0.0
        qu_x = -6.0
        qu_alpha = 0.0

        if stage_name == "mesh_fade_in":
            mesh_alpha = progress
            for text_obj in admesh_texts:
                text_obj.set_alpha(progress)

        elif stage_name == "triangles_draw":
            mesh_alpha = 1.0
            for text_obj in admesh_texts:
                text_obj.set_alpha(1.0)

        elif stage_name == "morph_tris_fade":
            mesh_alpha = 1.0
            for text_obj in admesh_texts:
                text_obj.set_alpha(1.0)
            # Fade out triangles that are being morphed
            for tri1_idx, tri2_idx in quad_tri_indices:
                tri_alphas[tri1_idx] = 1.0 - progress
                tri_alphas[tri2_idx] = 1.0 - progress

        elif stage_name == "morph_quads_fade":
            mesh_alpha = 1.0
            for text_obj in admesh_texts:
                text_obj.set_alpha(1.0)
            # Fade out remaining morphing tris, fade in quads
            for tri1_idx, tri2_idx in quad_tri_indices:
                tri_alphas[tri1_idx] = 0.0
                tri_alphas[tri2_idx] = 0.0
            for i in range(len(quads)):
                quad_alphas[i] = progress

            # Change letter colors from right to left: H, S, E, M, D, A
            # Letter index from right: 0=H, 1=S, 2=E, 3=M, 4=D, 5=A
            # When progress >= i/6, letter i (from right) flips to magenta
            # Letter position in ADMESH array: A=0, D=1, M=2, E=3, S=4, H=5
            for letter_idx in range(6):
                if progress >= letter_idx / 6.0:
                    # letter_idx from right: 0=H, 1=S, 2=E, 3=M, 4=D, 5=A
                    # Maps to position: 5, 4, 3, 2, 1, 0
                    admesh_colors[5 - letter_idx] = ADMESH_COLOR_FINAL

        elif stage_name == "qu_fly_in":
            mesh_alpha = 1.0
            for text_obj in admesh_texts:
                text_obj.set_alpha(1.0)
            for i in range(len(quads)):
                quad_alphas[i] = 1.0
            for _i in range(6): admesh_colors[_i] = ADMESH_COLOR_FINAL

            # Animate "Qu" x position from -6.0 to -1.35
            qu_x = -6.0 + 4.65 * progress
            qu_alpha = 1.0

        else:  # hold_final
            mesh_alpha = 1.0
            for text_obj in admesh_texts:
                text_obj.set_alpha(1.0)
            for i in range(len(quads)):
                quad_alphas[i] = 1.0
            for _i in range(6): admesh_colors[_i] = ADMESH_COLOR_FINAL
            qu_x = -1.35
            qu_alpha = 1.0

        # Set triangle colors and alphas
        tri_facecolors = np.array([
            (*hex_to_rgb(TRI_FILL), tri_alphas[i]) for i in range(len(tri_coords))
        ])
        tri_collection.set_facecolor(tri_facecolors)

        # Set quad colors and alphas
        quad_facecolors = np.array([
            (*hex_to_rgb(QUAD_FILL), quad_alphas[i]) for i in range(len(quads))
        ])
        quad_collection.set_facecolor(quad_facecolors)

        # Update ADMESH letter colors
        for i, text_obj in enumerate(admesh_texts):
            text_obj.set_color(admesh_colors[i])

        # Update "Qu" position and alpha
        qu_text.set_x(qu_x)
        qu_text.set_alpha(qu_alpha)

        return tri_collection, quad_collection, *admesh_texts, qu_text

    anim = FuncAnimation(fig, draw, frames=frames, blit=False)
    anim.save(out, writer=PillowWriter(fps=fps))
    plt.close(fig)


def hex_to_rgb(hex_color):
    """Convert '#RRGGBB' to (R, G, B) with values in [0, 1]."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))


if __name__ == "__main__":
    render()
    print(f"wrote {OUT}")
