# Feature Specification: Quadmeshing Algorithm Survey & Benchmark Branch

**Feature Branch**: `002-quadmeshing-algorithm-survey`
**Created**: 2026-05-22
**Status**: Draft
**Input**: Issues #9 (parent — survey popular quadmeshing algorithms for benchmarking against QuADMESH+), #10 (qmorph open-source availability)

## Purpose

Catalog popular direct and indirect quadrangular mesh generation algorithms. For each, record (a) algorithm class, (b) canonical reference, (c) open-source implementation availability, (d) license, (e) input/output compatibility with the chilmesh/QuADMESH pipeline, (f) suitability as a benchmarking baseline for QuADMESH+ on fully-quad and mixed-element targets.

Deliverable: this spec + per-algorithm sub-issues. NO algorithm implementations land in this branch — each candidate adopted for benchmarking gets its own follow-up issue and spec under `specs/003-...`, `specs/004-...`, etc.

## User Scenarios & Testing

### User Story 1 — Researcher locates baseline candidates (Priority: P1)

Researcher reviewing QuADMESH+ benchmark plan opens `specs/002-quadmeshing-algorithm-survey/spec.md`. Reads §"Algorithm Catalog". Picks 2–3 baselines whose license + I/O permit benchmarking and files an adoption sub-issue.

**Independent Test**: Open the spec; for each algorithm row, every column (class, reference, impl URL, license, I/O fit, benchmark suitability) is populated or marked `[GAP — research needed]`. A reader can decide adoption without external lookups for the populated rows.

**Acceptance Scenarios**:

1. **Given** the catalog table, **When** a row is marked "adopt", **Then** a tracking sub-issue exists with title `Adopt <algorithm> as QuADMESH+ benchmark baseline` and links back to this spec.
2. **Given** an algorithm with no open-source impl, **When** captured, **Then** it is still listed with `Impl: none` and rationale (write-from-paper effort estimate, or skip).

### User Story 2 — qmorph status answered (Priority: P2)

Issue #10 asker reads the spec's qmorph row and learns whether an open-source qmorph implementation exists, what license, and whether it is adoptable.

**Independent Test**: The qmorph row of the catalog table contains a concrete answer (URL or "none found after search of <sources>") plus a recommendation.

**Acceptance Scenarios**:

1. **Given** the catalog, **When** the reader searches "qmorph", **Then** they find a row with impl URL or explicit "none found" with sources searched.

### Edge Cases

- Algorithm has only commercial impl (Gmsh quad recombine plugin licensed differently than core): record license per binary, mark adoption blocker.
- Algorithm published but no code released and no clear pseudocode: mark `Impl: paper-only`, defer.
- Multiple impls of same algorithm (e.g., Blossom-Quad in Gmsh + standalone): list the cleanest dependency-wise.

## Requirements

### Functional Requirements

- **FR-001**: Catalog MUST cover both direct (advancing-front, paving, qmorph) and indirect (tri→quad merging, mixed-integer, Blossom-Quad) families.
- **FR-002**: Each catalog entry MUST record: name, family, year, canonical citation, open-source impl URL (or "none"), license, input mesh format, output mesh format, dependency on geometry/PDE solver, fit-with-chilmesh comment.
- **FR-003**: Catalog MUST include qmorph (resolves #10).
- **FR-004**: Spec MUST close with a "Recommended Baselines" shortlist of ≤5 candidates flagged for sub-issue creation.
- **FR-005**: Each shortlisted candidate MUST have a sub-issue opened on `domattioli/QuADMesh` before #9 closes.
- **FR-006**: No algorithm implementation lands in this branch. Spec-only.

### Key Entities

- **Algorithm Catalog Row**: name, family, year, citation, impl_url, license, input_fmt, output_fmt, deps, chilmesh_fit, adoption_status.

## Algorithm Catalog *(filled iteratively; initial scaffold)*

| Name | Family | Year | Citation | Impl URL | License | Input | Output | Deps | chilmesh fit | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| Paving | direct advancing-front | 1991 | Blacker & Stephenson, IJNME | [GAP] | [GAP] | boundary loops | all-quad | none | candidate — boundary-loop input matches chilmesh | research |
| Q-Morph | direct advancing-front (tri-input) | 1998 | Owen, Staten, Canann, Saigal, IJNME | [GAP — search Verdict/Mesquite/CUBIT, INRIA Yams, github] | likely none open | tri mesh | all-quad | tri mesh + front | strong fit — tri input is chilmesh native | resolves #10 |
| Blossom-Quad | indirect tri-recombine + perfect-matching | 2010 | Remacle et al., IJNME | Gmsh (gmsh.info, GPL) | GPL-2.0+ | tri mesh | all-quad | Gmsh runtime or libgmsh | adoptable if Gmsh dep acceptable | candidate |
| Mixed-Integer Quadrangulation | indirect global parametrization | 2009 | Bommes, Zimmer, Kobbelt, SIGGRAPH | libigl `comiso`, CoMISo standalone | MPL-2.0 / GPL | tri mesh + frame field | quad mesh | CoMISo, libigl | heavy deps; benchmark only | research |
| Instant Field-Aligned Meshes | indirect field-guided | 2015 | Jakob, Tarini, Panozzo, Sorkine-Hornung, SIGGRAPH Asia | github wjakob/instant-meshes | BSD-3 | tri mesh | quad/quad-dominant | none external | strong candidate, light deps | candidate |
| QuadCover | indirect cross-field + global param | 2007 | Kälberer, Nieser, Polthier, EG | [GAP] | [GAP] | tri mesh | quad | [GAP] | research | research |
| Tri-Merge (greedy) | indirect tri-pair merge | classical | many | trivial; reimplement | n/a | tri mesh | quad-dominant | none | weak baseline; useful as floor | reimplement-stub |
| Catmull-Clark on coarse quad | refinement | 1978 | Catmull & Clark | many | varies | coarse quad | refined quad | none | not a generator; out of scope | reject |

`[GAP]` = open research task — fill via web/literature search in a follow-up commit on this branch.

## Recommended Baselines *(initial proposal — refine after gaps filled)*

1. **Blossom-Quad** (via Gmsh) — well-maintained, indirect, accepts tri input from chilmesh.
2. **Instant Meshes** — light deps, BSD, widely cited baseline.
3. **Q-Morph** — high research value if any open impl exists; matches QuADMESH+ family (direct advancing-front, tri-input). If no impl → defer or scope a clean-room port as separate spec.
4. **Tri-Merge greedy** — trivial floor baseline; sanity-check QuADMESH+ outperforms a naive merger.
5. *(reserve slot for one mixed-element-capable method)*

## Out of Scope

- Implementing any of the listed algorithms in this branch.
- Benchmark harness itself (separate spec: `003-quadmesh-benchmark-harness` — file as sub-issue).
- Hexahedral mesh generators.
- GUI / interactive tools (CUBIT, Gmsh GUI workflows).

## Sub-Issues to File (after spec merges)

- `Adopt Blossom-Quad (Gmsh) as QuADMESH+ benchmark baseline` — parent #9.
- `Adopt Instant Meshes as QuADMESH+ benchmark baseline` — parent #9.
- `Investigate Q-Morph open-source availability and adoption path` — parent #9, resolves #10.
- `Implement greedy tri-merge floor baseline` — parent #9.
- `Spec the QuADMESH+ benchmark harness` — parent #9 (precondition for any baseline being useful).

## Open Questions / Clarifications

- **NEEDS CLARIFICATION**: Benchmark targets — fully-quad only, or include mixed-element acceptance criteria from chilmesh? (Issue #9 says both; confirm metric set.)
- **NEEDS CLARIFICATION**: License threshold — is GPL acceptable in the benchmark harness, or restrict to permissive (BSD/MIT/MPL)?
- **NEEDS CLARIFICATION**: Are paper-only algorithms (no code) in scope for clean-room reimplementation, or strictly compare against existing impls?
