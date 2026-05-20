# Tri2Quad Manim Visualization

Animated illustration of the layered triangle-to-quadrilateral routine
implemented in `02_QuADMESH_Library/02_Tri2Quad_Routine/Tri2QuadRoutine.m`.

## What it shows

A small 4 cols x 3 rows sample domain (12 triangles, single layer) is fed
through the same conceptual steps as the MATLAB routine:

1. Triangulated input is drawn.
2. The outer layer (Layer 1) is highlighted.
3. A CCW path along the outer boundary vertices is traced.
4. Every-other interior edge (the cell diagonal) is flagged for removal;
   element-flagging ensures adjacent triangles are skipped.
5. Each flagged edge is removed and the two incident triangles merge into
   one quadrilateral.

Result: 12 triangles -> 6 quadrilaterals.

## Requirements

```
pip install manim
# Linux system deps: libpango1.0-dev libcairo2-dev pkg-config
```

## Render

```
# 480p15 preview (fast)
manim -ql visualization/manim_tri2quad.py Tri2QuadScene

# 720p30
manim -qm visualization/manim_tri2quad.py Tri2QuadScene

# 1080p60
manim -qh visualization/manim_tri2quad.py Tri2QuadScene
```

Output lands in `media/videos/manim_tri2quad/<resolution>/Tri2QuadScene.mp4`.

## Scope

This is a pedagogical visualization, not a faithful execution of the
MATLAB code path. Merge sequencing is choreographed to mirror the
algorithm's element-flagging outcome on this uniformly-diagonal grid.
Real meshes (irregular layers, leftover tris, post-processing) are not
exercised here.
