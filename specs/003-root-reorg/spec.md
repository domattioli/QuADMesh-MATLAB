# Feature Specification: Root Directory Reorganization

**Feature Branch**: `003-root-reorg`
**Created**: 2026-05-22
**Status**: Draft — operator approval required before any file moves
**Input**: Issue #13 ("request: root reorg — some folders now exist as own repos, some don't; want conventional software-package layout")

## Purpose

Convert QuADMesh's MATLAB-research-project root layout (numeric prefixes, mixed-purpose dirs, dead duplicates of upstream repos) into a conventional Python-package layout. Spec defines the target shape, phases the migration, and lists sub-issues — does NOT execute moves. Operator approves the target before any rename/delete lands.

## User Scenarios & Testing

### User Story 1 — New contributor reads root and finds the package (Priority: P1)

New contributor `cd`s into the repo, runs `ls`, and sees standard Python-package files (`pyproject.toml`, `src/`, `tests/`, `docs/`) without numeric-prefix directories from a 2015–2017 MATLAB project.

**Why this priority**: Current root scares new contributors with `00_…/01_…/05_…` dirs that are mostly historical or duplicates of upstream repos. Conventional layout is table stakes for a Python package.

**Independent Test**: `ls` on the repo root produces only files/dirs from the target layout (§"Target layout"). No numeric-prefix dirs at root.

**Acceptance Scenarios**:

1. **Given** post-migration repo root, **When** `pip install -e .` runs from root, **Then** install succeeds (no need to `cd python/`).
2. **Given** post-migration repo root, **When** `pytest` runs from root, **Then** test discovery finds `tests/` automatically.
3. **Given** post-migration repo root, **When** a contributor looks for the MATLAB reference source, **Then** they find it under `matlab/` (clearly labeled "legacy reference, not installable").

### User Story 2 — Dead duplicates removed without losing history (Priority: P2)

`00_CHILMesh_Class/` and `01_ADMESH_Library/` are duplicates of upstream repos (`domattioli/CHILmesh`, `domattioli/ADMESH`) — verified by inspection. Removed from working tree but recoverable via git history.

**Independent Test**: `git log --follow -- 00_CHILMesh_Class/` (post-move) shows the dir existed prior to the delete commit; `git show <pre-move-sha>:00_CHILMesh_Class/@CHILmesh/` recovers content.

**Acceptance Scenarios**:

1. **Given** the delete commit, **When** operator wants to recover a deleted MATLAB file, **Then** `git show <sha>:<path>` returns it.
2. **Given** the new layout, **When** contributor needs CHILmesh source, **Then** README points them to `https://github.com/domattioli/CHILmesh`.

### User Story 3 — Test fixtures stay reachable (Priority: P1)

Python port tests currently load .14 mesh files from `03_CHILMesh_Test_Cases/01_.14_Files/`. Move must preserve test access without breaking the `chilmesh` runtime path either.

**Independent Test**: `cd python && pytest -q` passes pre-move and post-move with the same 52 test count.

**Acceptance Scenarios**:

1. **Given** the moved fixtures under `tests/fixtures/meshes/`, **When** pytest runs, **Then** all 52 tests pass.
2. **Given** the chilmesh dep, **When** chilmesh code references a fixture path that lived in `03_…`, **Then** either chilmesh has its own fixtures (verified upstream) or a compatibility symlink remains.

### Edge Cases

- **Embedded paths in MATLAB scripts**: `02_QuADMESH_Library/**/*.m` may reference sibling-dir paths (`../03_CHILMesh_Test_Cases/...`). Audit before moving; fix or freeze MATLAB in place.
- **Git LFS**: `03_CHILMesh_Test_Cases/` is 83 MB (binary .mat, .zip). Confirm not LFS-tracked before moving, or migrate LFS pointers correctly.
- **`videos/` is 14 MB**: keep at root; referenced by README. Not moved.
- **Hidden duplicates**: `.DS_Store` in `00_CHILMesh_Class/` confirms macOS pollution; clean up in delete commit.

## Requirements

### Functional Requirements

- **FR-001**: Target root MUST contain ONLY: standard package files (`pyproject.toml`, `README.md`, `LICENSE`, `CLAUDE.md`, `MANIFEST.in`, `.gitignore`), conventional dirs (`src/`, `tests/`, `docs/`, `specs/`), and project-specific dirs (`videos/`, `matlab/`).
- **FR-002**: Python package source MUST live at `src/quadmesh/` (PEP 517/518 src-layout), not nested under `python/`.
- **FR-003**: Python tests MUST live at `tests/` at repo root.
- **FR-004**: Pure-MATLAB legacy MUST be preserved at `matlab/` with subdirs `matlab/quadmesh/` (was `02_QuADMESH_Library/`), `matlab/test_cases/` (subset of `03_CHILMesh_Test_Cases/` still relevant), `matlab/results/` (was `05_Results/`).
- **FR-005**: Duplicate-of-upstream dirs (`00_CHILMesh_Class/`, `01_ADMESH_Library/`, `04_CHIL_Supporting_Functions/`) MUST be deleted; README explains the move + links to upstream repos.
- **FR-006**: Migration MUST happen in phases (sub-issues §"Sub-issues"); each phase is a separate PR with passing pytest.
- **FR-007**: `pyproject.toml` `[tool.setuptools.packages.find]` config MUST be updated to discover `src/quadmesh/`.
- **FR-008**: README MUST be rewritten to document the new layout + reproduce instructions from repo root (`pip install -e .` not `pip install -e python`).

### Key Entities

- **Target layout** (§ below)
- **Migration phase** (single PR with: spec → diff → green tests → atomic moves via `git mv`)
- **Sub-issue** (one per migration phase)

## Target layout

```
QuADMesh/
├── README.md                  # rewritten — points at new paths
├── LICENSE
├── CLAUDE.md                  # already updated 2026-05-22 (routine pointer + branch rule)
├── pyproject.toml             # promoted from python/pyproject.toml
├── MANIFEST.in                # new — exclude matlab/, videos/, tests/fixtures/ from wheel
├── .gitignore                 # existing
├── .specify/                  # existing (speckit constitution + templates)
├── src/
│   └── quadmesh/              # promoted from python/quadmesh/
│       ├── __init__.py
│       ├── cli.py
│       ├── pipeline.py
│       └── …
├── tests/                     # promoted from python/tests/
│   ├── conftest.py
│   ├── fixtures/              # subset of 03_CHILMesh_Test_Cases/01_.14_Files/ still in use
│   │   └── meshes/
│   ├── test_pipeline.py
│   └── …
├── docs/
│   └── sessions/              # existing
├── specs/
│   ├── 001-matlab-to-python-port/
│   ├── 002-quadmeshing-algorithm-survey/
│   └── 003-root-reorg/        # this spec
├── videos/                    # existing — README assets, keep at root
├── matlab/                    # NEW — legacy MATLAB consolidated
│   ├── README.md              # NEW — "legacy reference, not installable; see src/quadmesh/ for Python port"
│   ├── quadmesh/              # was 02_QuADMESH_Library/
│   ├── test_cases/            # subset of 03_CHILMesh_Test_Cases/ still relevant
│   └── results/               # was 05_Results/
└── (deleted — recoverable via git history)
    ├── 00_CHILMesh_Class/         # duplicate of github.com/domattioli/CHILmesh
    ├── 01_ADMESH_Library/         # duplicate of github.com/domattioli/ADMESH
    ├── 04_CHIL_Supporting_Functions/  # 2 .m files; upstreamed or dead
    ├── python/                    # contents promoted to src/ + tests/ + pyproject.toml
    └── 03_CHILMesh_Test_Cases/    # in-use fixtures → tests/fixtures/meshes/; rest → matlab/test_cases/ or deleted
```

## Migration phases (sub-issues to file)

Each phase = one PR with passing pytest. Operator approves each PR before next phase starts.

| Phase | Title | Scope | Risk |
|---|---|---|---|
| P0 | Audit MATLAB embedded paths in `02_QuADMESH_Library/**/*.m` | Read-only: grep for `../03_CHILMesh_Test_Cases`, `../00_CHILMesh_Class`, etc. Report path-rewrite work needed if MATLAB is kept runnable. | low |
| P1 | Promote `python/` to root | `git mv python/quadmesh src/quadmesh`; `git mv python/tests tests`; `git mv python/pyproject.toml .`; update `pyproject.toml` paths; verify `pip install -e .` + `pytest` green. | medium — touches package install |
| P2 | Move test fixtures | `git mv 03_CHILMesh_Test_Cases/01_.14_Files tests/fixtures/meshes`; audit + update test path constants; verify all 52 tests green. | medium — fixture-path strings |
| P3 | Consolidate MATLAB legacy under `matlab/` | `git mv 02_QuADMESH_Library matlab/quadmesh`; `git mv 05_Results matlab/results`; move surviving `03_CHILMesh_Test_Cases/` content to `matlab/test_cases/`; write `matlab/README.md`. | low — MATLAB-only, no Python imports affected |
| P4 | Delete duplicates of upstream repos | `git rm -r 00_CHILMesh_Class 01_ADMESH_Library 04_CHIL_Supporting_Functions`; update README to point at `github.com/domattioli/{CHILmesh,ADMESH}`. | low — files recoverable via git history |
| P5 | Rewrite root README | New layout map + install/run commands from repo root + links to upstream repos for replaced dirs. | low |

## Out of scope

- Renaming the repo itself (`QuADMesh` stays).
- Touching chilmesh upstream (its layout is its own concern).
- Changing the Python package name (`quadmesh` stays).
- Migrating to Poetry / Hatch / pdm — `pip install -e .` with setuptools stays.
- Adding new tests — port-stage tests already cover post-move.
- CI updates beyond pyproject.toml path moves (no GitHub Actions exist yet in this repo).

## Open Questions / Clarifications

- **NEEDS CLARIFICATION**: Keep MATLAB runnable from new `matlab/` path (requires P0 audit + path rewrites in .m files) OR freeze MATLAB as historical-reference-only (skip path rewrites; `matlab/README.md` says "preserved for citation; run from a checkout pre-2026-05-22 if you need MATLAB execution")?
- **NEEDS CLARIFICATION**: `03_CHILMesh_Test_Cases/` is 83 MB. Are any fixtures NOT used by current 52 Python tests + not needed for MATLAB reference? Audit + delete dead ones during P2.
- **NEEDS CLARIFICATION**: `04_CHIL_Supporting_Functions/` has 2 files (`MYcell2mat.m`, `saveMesh.m`). Are these already in upstream CHILmesh repo, or should they move to `matlab/quadmesh/utilities/` before P4 deletes the dir?
- **NEEDS CLARIFICATION**: `MANIFEST.in` strategy for the wheel — exclude `matlab/`, `videos/`, `tests/`, `docs/`, `specs/`?

## Decision log (rolling — fill as phases execute)

- 2026-05-22 — Spec drafted. NO file moves executed in this PR; awaiting operator approval of target layout.

## Sub-issues to file (after spec approved)

- `P0: Audit MATLAB embedded paths in 02_QuADMESH_Library/**/*.m` — parent #13.
- `P1: Promote python/ to root (src/quadmesh/, tests/, pyproject.toml)` — parent #13.
- `P2: Move test fixtures to tests/fixtures/meshes/` — parent #13.
- `P3: Consolidate MATLAB legacy under matlab/` — parent #13.
- `P4: Delete duplicates of upstream repos (00_, 01_, 04_)` — parent #13.
- `P5: Rewrite root README for new layout` — parent #13.
