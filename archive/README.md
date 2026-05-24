# Archive

Historical material kept in-repo for now, staged for future removal. Nothing here
is needed to build, install, test, or run the Python package. Most of it either
duplicates a standalone upstream repo or is MATLAB-opaque binary data.

## Contents

| Dir | Was | Why archived |
|---|---|---|
| `chilmesh_class/` | `00_CHILMesh_Class/` | MATLAB `@CHILmesh` class — duplicates the **external `chilmesh` Python dependency** (the modernized requirement). The port depends on `chilmesh>=0.4.0`, not this. See `github.com/domattioli/CHILmesh`. |
| `admesh_library/` | `01_ADMESH_Library/` | MATLAB ADMESH library — duplicate of `github.com/domattioli/ADMESH`. |
| `matlab_test_cases/` | `03_CHILMesh_Test_Cases/` (minus `.14` meshes) | MATLAB-opaque `.mat`/`.zip` mesh binaries (~83 MB). The `.14` ASCII meshes the Python tests use moved to [`../tests/fixtures/meshes/`](../tests/fixtures/meshes/). |
| `results/` | `05_Results/` | Old MATLAB result outputs. |

## Recovery

Everything is in git history. After this archive is eventually deleted, recover any
file with:

```
git log --all --full-history -- <old-or-new-path>
git show <sha>:<path>
```
