# videos/scripts

Reproducible video assets demonstrating the Python port (`chilmesh`) of the
MATLAB QuADMesh+ pipeline.

## Files

| File | Purpose |
|------|---------|
| `build_pipeline_snapshots.py` | Runs the 4-stage pipeline (Raw → ADMESH truss → FEM smoother → right-iso stub) on the annulus fixture; dumps per-stage points / connectivity / quality stats to JSON. |
| `pipeline_annulus_scene.py`   | Manim scene that consumes the JSON and renders `../readme_pipeline_annulus.mp4`. |

## Reproduce

```bash
# 1. install deps
pip install chilmesh manim scipy
sudo apt-get install -y libpango1.0-dev ffmpeg   # only needed if manim fails on import

# 2. build snapshots
python videos/scripts/build_pipeline_snapshots.py /tmp/readme_pipeline.json

# 3. render mp4 (1080p30)
cd videos/scripts
manim -qh pipeline_annulus_scene.py ReadmePipeline

# rendered mp4 lands under ./media/videos/.../ReadmePipeline.mp4
# copy/symlink to videos/readme_pipeline_annulus.mp4
```

## Stage results (annulus, 380 verts / 580 elems)

| Stage  | Method                                  | Median Q | Iso-dev (deg) |
|--------|-----------------------------------------|---------:|--------------:|
| Row 1  | Raw Delaunay input                      | 0.491    | 30.23         |
| Row 2  | ADMESH truss warm-start + re-Delaunay   | 0.727    | 21.88         |
| Row 3  | FEM smoother (Balendran) + re-Delaunay  | 0.749    | 21.62         |
| Row 4  | Right-iso stub + re-Delaunay            | 0.692    | 17.16         |

Row 4 trades skewness Q for right-iso angle deviation — that is the
intended behaviour of the quad-prep smoother (preparing triangle pairs
for fusion into quads). The original ADMESH `quad_prep.smooth_for_quadrangulation`
module isn't shipped here, so Row 4 uses an inline heuristic with the same
target ({45, 45, 90} per triangle).
