# quadmesh (Python)

Port of MATLAB QuADMESH+ tri-to-quad mesh generator. Sit on top of `chilmesh`.

## Pipeline

```
CHILmesh (triangular) → create_quad_domain → tri2quad → post_process → quad mesh
```

Stages:

1. **create_quad_domain** — pick triangle subset for conversion (whole mesh, polygon mask, etc.).
2. **tri2quad** — sweep layers outward; merge adjacent tri pairs into quads; bisect/insert/remove edges to absorb stragglers.
3. **post_process** — doublet collapse, quad-vertex merge, boundary-quad cleanup, FEM smoothing.

## Install

```bash
pip install -e .            # depends on chilmesh
pytest                      # run tests
```

## Quick use

```python
from chilmesh import CHILmesh
from quadmesh import tri2quad, post_process

tri = CHILmesh.read_from_fort14("Test_Case_1.14")
quad = tri2quad(tri, can_remove_edges=True)
quad = post_process(quad, can_remove_edges=True, n_smooth_iter=50)
```

## Provenance

MATLAB source in `../02_QuADMESH_Library/`. Per-routine MATLAB→Python map in `MAPPING.md`.

## CLI

```bash
quadmesh path/to/tri.14 -o out.14
quadmesh tri.14 -o out.14 --polygon poly.csv --n-smooth-iter 50
quadmesh tri.14 -o out.14 --no-post-process    # raw tri2quad output
```

## Performance

Block_O (5214 tris, 9 layers) — full pipeline: ~1.2s. Mean output quality ≈ 0.84.
Test_Case_1 (2417 tris, 7 layers) — full pipeline: <1s.

## Status

v0.1 port: tri-pair merge + post-process (doublet, QVM, boundary cleanup, smoothing) + CLI.
Aggressive leftover-tri routing and `CleanupBoundaryQuads` shift mode deferred to v0.2 — see `MAPPING.md`.

## Spec

Spec-driven via speckit: `../specs/001-matlab-to-python-port/`.

## Citation

Mattioli, D. D. (2017). _QuADMESH+: A Quadrangular ADvanced Mesh Generator for Hydrodynamic Models_ [Master's thesis, Ohio State University].
