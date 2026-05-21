This class is a bi-product of a project, funded by Aquaveo, at The Ohio State University in 2015-2017.

The repository focuses on a class for representing triangular, quadrangular, and mixed-element polygonal meshes for hydrodynamic domains. Research related to the original work is ongoing.

## Python port

Legacy 4-row CHILmesh pipeline (Raw → ADMESH truss → FEM smoother → right-iso) running on the annulus fixture via the Python port (`chilmesh`):

![CHILmesh annulus pipeline](videos/readme_pipeline_annulus.gif)

Vertex IDs persist across stages and morph continuously between snapshots; polygon edges cross-fade per stage because Delaunay re-triangulation runs after every smoother that moves vertices freely. Reproducible build scripts under [`videos/scripts/`](videos/scripts/README.md); higher-fidelity mp4 at [`videos/readme_pipeline_annulus.mp4`](videos/readme_pipeline_annulus.mp4).

Stage results on the annulus (380 verts / 580 elems):

| Stage | Method | Median Q | Iso-dev (deg) |
|-------|--------|---------:|--------------:|
| Row 1 | Raw Delaunay input | 0.491 | 30.23 |
| Row 2 | ADMESH truss warm-start + re-Delaunay | 0.727 | 21.88 |
| Row 3 | FEM smoother (Balendran) + re-Delaunay | 0.749 | 21.62 |
| Row 4 | Right-iso stub + re-Delaunay | 0.692 | 17.16 |

### Tri2Quad routine demo

End-to-end QuADMESH+ run on a smaller annulus (131 tris / 79 verts / 3 layers), showing the algorithmic stages from `python/quadmesh/pipeline.py`: triangulated input → layer decomposition → `tri2quad_routine` → `post_process_routine` (doublet collapse, quad-vertex merge, angle + FEM smoothing).

<video src="https://raw.githubusercontent.com/domattioli/QuADMesh-MATLAB/python-porting-project/videos/tri2quad_pipeline_annulus.mp4" controls width="720"></video>

Direct link: [`videos/tri2quad_pipeline_annulus.mp4`](videos/tri2quad_pipeline_annulus.mp4). Generator: [`videos/scripts/tri2quad_pipeline_annulus.py`](videos/scripts/tri2quad_pipeline_annulus.py).

Reproduce:

```
pip install -e python
pip install manim scipy
manim -qm videos/scripts/tri2quad_pipeline_annulus.py AnnulusPipelineScene
```

Citation:
Mattioli, Mattioli, D. D. (2017). QuADMESH+: A Quadrangular ADvanced Mesh Generator for Hydrodynamic Models [Master's thesis, Ohio State University]. OhioLINK Electronic Theses and Dissertations Center. http://rave.ohiolink.edu/etdc/view?acc_num=osu1500627779532088