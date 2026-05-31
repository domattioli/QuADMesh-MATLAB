# Delaware Bay tri2quad hero (WIP)

**Status: work-in-progress.** Not yet README-quality — staged here for
iteration before promotion.

Animates the full QuADMESH pipeline on a graded **Delaware Bay** mesh:

1. **Initialized** — size-aware scatter inside the real Delaware Bay outline.
2. **Truss solver** — DistMesh force balance.
3. **FEM smoothed** — Laplacian smoothing peaks triangle quality.
4. **Tri2Quad** — `quadmesh.tri2quad_routine` pairs adjacent triangles by
   **removing their shared diagonal edge** (nodes stay fixed). ~6.4k tris →
   ~3.1k quads.

Elements colored on the magenta→purple→cyan quality colormap
(`#e040fb` → `#7c4dff` → `#00e5ff`). Wordmark: **Qu** magenta, **ADMESH** cyan.

## Files

- `precompute_delbay_stages.py` — builds tri trajectories + runs tri2quad,
  writes `delbay_stages.npz`.
- `delbay_hero.py` — Manim scene (needs system libs: cairo, pango, ffmpeg).
- `render_full_pipeline.py` — matplotlib fallback renderer (no manim needed);
  emits `delbay_hero.gif` / `.mp4`.
- `edge_removal.py` — recomputes quads on fixed node set, captures removed
  diagonal edges → `edge_removal_data.npz`.
- `delbay_edge_removal.{gif,mp4}` — closeup of stage-4 edge removal.
- `delbay_stages.npz`, `delbay_ring.npy`, `edge_removal_data.npz` — cached data.

## TODO before README promotion

- [ ] Render via manim (current renders are matplotlib stand-ins).
- [ ] Decide on optional 5th stage: squeeze 138 leftover boundary tris → quad-pure.
- [ ] Tighten timing / framecount; current is coarse-sampled.
- [ ] Confirm Qu/ADMESH wordmark renders in manim scene (only in delbay_hero.py).

## Regenerate

```bash
python precompute_delbay_stages.py      # → delbay_stages.npz
python edge_removal.py                  # → edge_removal_data.npz
python render_full_pipeline.py          # → delbay_hero.gif + .mp4
```
