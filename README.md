<h1 align="center">QuADMESH</h1>

<p align="center">
  <strong>A Quadrangular ADvanced, automatic unstructured MESH generator for 2D shallow-water models.</strong><br>
  Python port of the MATLAB QuADMESH library and a Pythonic API.
</p>

<p align="center">
  <a href="https://pypi.org/project/admesh2D/"><img src="https://img.shields.io/pypi/v/admesh2D.svg?label=PyPI" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+"></a>
  <a href="https://github.com/domattioli/QuADMESH/actions/workflows/tests.yml"><img src="https://github.com/domattioli/QuADMESH/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://doi.org/10.5281/zenodo.20350483"><img src="https://zenodo.org/badge/119912466.svg" alt="DOI"></a>
  <a href="https://github.com/domattioli/QuADMESH/issues"><img src="https://img.shields.io/github/issues/domattioli/QuADMESH.svg" alt="Open issues"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
</p>

---

## Contents

- [Why QuADMESH](#why-quadmesh)           -- coming soon...
- [Install](#install)                     -- coming soon...
- [Quickstart](#quickstart)               -- coming soon...
- [Tri2Quad](#tri2quad)
- [Demo](#demo)
- [Status &amp; roadmap](#status--roadmap) -- coming soon...
- [Documentation](#documentation)          -- coming soon...
- [Citation](#citation)
- [Related projects](#Related-projects)
- [Contact](#contact)
- [License](#license)

---

## Python port of MATLAB Functionality -- Coming very soon (est. June 2026)

## Tri2Quad

Step-by-step illustration of the Tri2Quad layer routine on a 6×6 vertex grid (50 triangles, three layers). Processes innermost layer first per MATLAB's `for iLayer = Domain.nLayers:-1:1` loop in `02_QuADMESH_Library/02_Tri2Quad_Routine/Tri2QuadRoutine.m`: walk CCW boundary path, flag every-other interior edge via element-flagging, merge each triangle pair into a quad.

![Tri2Quad on 6x6 grid](videos/tri2quad_6x6_grid.gif)

Higher-fidelity mp4: [`videos/tri2quad_6x6_grid.mp4`](videos/tri2quad_6x6_grid.mp4). Generator: [`videos/scripts/tri2quad_6x6_grid.py`](videos/scripts/tri2quad_6x6_grid.py).

## Demo

End-to-end QuADMESH+ run on a smaller annulus (131 tris / 79 verts / 3 layers), showing the algorithmic stages from `python/quadmesh/pipeline.py`: triangulated input → layer decomposition → `tri2quad_routine` → `post_process_routine` (doublet collapse, quad-vertex merge, angle + FEM smoothing).

![Tri2Quad pipeline on annulus](videos/tri2quad_pipeline_annulus.gif)

Higher-fidelity mp4: [`videos/tri2quad_pipeline_annulus.mp4`](videos/tri2quad_pipeline_annulus.mp4). Generator: [`videos/scripts/tri2quad_pipeline_annulus.py`](videos/scripts/tri2quad_pipeline_annulus.py).

Reproduce:

```
pip install -e python
pip install manim scipy
manim -qm videos/scripts/tri2quad_pipeline_annulus.py AnnulusPipelineScene
```
## Status & roadmap
As of May 2026 we are so back.
  - Currently porting the original code to Python
  - Next will optimize python, evaluate if C++ or Rust makes sense.
  - Finally going to implement it formally within a unifed ADMESH Library.

## Citation

**Algorithm / theory** (cite the original paper):

> Mattioli, DO (2017). QuADMESH+: A Quadrangular ADvanced Mesh Generator for Hydrodynamic Models. The Ohio State University, OhioLINK - Electronic Theses and Dissertations Center. Master's Thesis. <[http://rave.ohiolink.edu/etdc/view?acc_num=osu1500627779532088](ttp://rave.ohiolink.edu/etdc/view?acc_num=osu1500627779532088)>

**This software** (cite the archived release):

> Mattioli, DO, Kubatko, EJ (2026). QuADMESH: A Quadrangular ADvanced, automatic unstructured MESH generator for 2D hydrodynamic domains. Zenodo. <[https://doi.org/10.5281/zenodo.20264101](https://doi.org/10.5281/zenodo.20350484)>

The DOI `10.5281/zenodo.20264101` resolves to the latest release; version-specific DOIs are listed on the [Zenodo record](https://doi.org/10.5281/zenodo.20264101). A [`CITATION.cff`](CITATION.cff) is provided at the repo root for tools that consume it (GitHub's "Cite this repository" button, Zotero, etc.). Paper copy: [`papers/Conroy-2012-ADMESH.pdf`](papers/Conroy-2012-ADMESH.pdf).

## Related projects

- **[ADMESH](https://github.com/domattioli/ADMESH)** — C++ implementation with pythonic wrapper and API..
- **[CHILmesh](https://github.com/domattioli/CHILmesh)** — federated registry of ADCIRC-compatible meshes for discovery, lineage tracking, and community contribution. Built as a companion to this library.

## Contact

Dominik Mattioli - ([repo owner](https://github.com/domattioli/QuADMESH))
Ethan J Kubatko  — [kubatko.3@osu.edu](mailto:kubatko.3@osu.edu)

## License

Apache 2.0 — see [`LICENSE`](LICENSE).

