# quadmesh

Tri-to-quad mesh generator. Port of MATLAB QuADMESH+. Build on `chilmesh`.

## Pipeline

```
tri -> create_quad_domain -> tri2quad -> post_process -> quad
```

1. `create_quad_domain` — pick tris (whole mesh or polygon mask).
2. `tri2quad` — sweep layers outward, merge tri pairs into quads.
3. `post_process` — doublet collapse, quad-vert merge, boundary cleanup, smooth.

## Install

```bash
pip install -e .
pytest          # 25+ tests
```

## Use

```python
from chilmesh import CHILmesh
from quadmesh import tri2quad, post_process, two_part_smoother

tri = CHILmesh.read_from_fort14("mesh.14")
quad = tri2quad(tri)
quad = post_process(quad, n_smooth_iter=50)
```

## CLI

```bash
quadmesh mesh.14 -o out.14
quadmesh mesh.14 -o out.14 --no-remove-edges --n-smooth-iter 100
quadmesh mesh.14 -o out.14 --no-post-process
```

## v0.2 new

- `CleanupBoundaryQuads` shift mode (`can_remove_edges=False`). Move corner inward. Before: no-op. Now: work.
- `two_part_smoother`. Interleave angle + FEM smooth. Port of MATLAB `twoPartSmoother.m`.
- 25+ tests.

## Numbers

| Mesh | Tris | Layers | Pipeline |
|---|---|---|---|
| Test_Case_1 | 2417 | 7 | <1 s |
| Block_O | 5214 | 9 | ~1.2 s |

## Provenance

MAT src: `../02_QuADMESH_Library/`. Map: `MAPPING.md`. Spec: `../specs/001-matlab-to-python-port/`.

## Cite

Mattioli, D. D. (2017). _QuADMESH+: A Quadrangular ADvanced Mesh Generator_. Master's thesis, OSU.
