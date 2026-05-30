"""Matplotlib-only renderer for the QuADMESH logo animation GIF.

Produces ``videos/quadmesh_logo.gif`` without manim/ffmpeg/chilmesh — pure numpy
+ matplotlib. Mirrors the content, colors, and geometry of ``quadmesh_logo.py``
(the manim reference), including the 6-spoke annulus, triangle-to-quad morph of
4 selected pairs, title, and tagline.

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

# Colors (from quadmesh_logo.py)
BG_COLOR = "#0d0d0f"
TITLE_COLOR = "#ffd34e"
EDGE_COLOR = "#e8e8e8"
TRI_FILL = "#c97b2f"
QUAD_FILL = "#2e7fcf"
TAGLINE_COLOR = "#e8e8e8"

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
    """Render logo animation with frame-hold pattern."""

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
        ("title_fade_in", hold),
        ("triangles_draw", hold),
        ("morph_tris_fade", hold),
        ("morph_quads_fade", hold),
        ("tagline_fade_in", hold),
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

    # Text elements
    title = ax.text(
        0, 2.6, "QuADMESH", ha="center", va="center",
        fontsize=60, fontweight="bold", color=TITLE_COLOR, alpha=0.0
    )
    tagline = ax.text(
        0, -2.6, "triangles in · quads out", ha="center", va="center",
        fontsize=22, fontstyle="italic", color=TAGLINE_COLOR, alpha=0.0
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

    def draw(frame):
        stage_name, progress = frame

        # Reset alphas
        tri_alphas[:] = 1.0
        quad_alphas[:] = 0.0

        if stage_name == "title_fade_in":
            title.set_alpha(progress)
        elif stage_name == "triangles_draw":
            title.set_alpha(1.0)
        elif stage_name == "morph_tris_fade":
            title.set_alpha(1.0)
            # Fade out triangles that are being morphed
            for tri1_idx, tri2_idx in quad_tri_indices:
                tri_alphas[tri1_idx] = 1.0 - progress
                tri_alphas[tri2_idx] = 1.0 - progress
        elif stage_name == "morph_quads_fade":
            title.set_alpha(1.0)
            # Fade out remaining morphing tris, fade in quads
            for tri1_idx, tri2_idx in quad_tri_indices:
                tri_alphas[tri1_idx] = 0.0
                tri_alphas[tri2_idx] = 0.0
            for i in range(len(quads)):
                quad_alphas[i] = progress
        elif stage_name == "tagline_fade_in":
            title.set_alpha(1.0)
            for i in range(len(quads)):
                quad_alphas[i] = 1.0
            tagline.set_alpha(progress)
        else:  # hold_final
            title.set_alpha(1.0)
            tagline.set_alpha(1.0)
            for i in range(len(quads)):
                quad_alphas[i] = 1.0

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

        return tri_collection, quad_collection, title, tagline

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
