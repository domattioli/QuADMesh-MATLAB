# CLAUDE.md

## Faithfulness invariant (non-negotiable)

Interior residual triangle (tri with NO domain-boundary edge) after tri2quad = **NOT a faithful QuADMESH+ implementation**. Zero interior tris is mandatory — a properly-implemented QuADMESH+ never leaves one. Only **boundary** tris may remain (thesis minimizes even those; ≤1 typical). Pinned by `tests/test_no_interior_tris.py`.

Status: `method="matching"` has zero interior tris by construction (faithful on this axis). `method="faithful"` per-layer loop (T020/T004) now implemented — zero interior tris confirmed, quality 0.375→0.573 on Test_Case_1. **Still WIP** — Ch 4 IE-before-OE interior heuristics (T017) and boundary-layer OE-before-IE + walkability pre-pass (T018) are not yet implemented; until those land, `method="faithful"` must not be made default.

## Routine

Routine lives in `DomI/claude_routine_instructions.md` (private). Textbox payload format + per-repo profile knobs in §6–§7 there. Do not duplicate routine prose here.

## Branch rule

All ongoing work goes on `daily-issue-fixing`. Do not push to `master`/`main` directly. Do not push to historical branches (`python-porting-project`, `claude/affectionate-heisenberg-prShD`, `claude/awesome-goodall-cqPYK`, `claude/awesome-goodall-Tbur3`).

New session branches discouraged — work directly on `daily-issue-fixing`, PR → `main`. `branch_guard.sh` (DomI plugin) blocks non-allowlisted names.

## Layout

Conventional src-layout Python package (reorganized 2026-05-24, was numeric-prefix MATLAB-project layout):

- `src/quadmesh/` — Python port of QuADMESH+ (the package; `pip install -e .` from root).
- `tests/` — pytest suite; `tests/fixtures/meshes/` holds the `.14` test meshes.
- `docs/MAPPING.md` — MATLAB → Python function map + chilmesh gaps.
- `docs/sessions/session-NNN.md` — per-session handoff notes.
- `specs/001-matlab-to-python-port/`, `specs/003-root-reorg/` — speckit spec/plan/tasks.
- `matlab/` — frozen legacy MATLAB reference (was `02_QuADMESH_Library/`, `04_CHIL_Supporting_Functions/`). Not installable.
- `archive/` — in-repo holding pen for future removal: MATLAB `@CHILmesh`/ADMESH dups of upstream repos, `.mat` binaries, old results.
- `videos/` — README demo assets.

## chilmesh

External Python dep. Issues filed against it for missing/slow APIs: #132 (`merge_elements`), #133 (`ccw_edges_around_vert`), #134 (adjacencies flag), #138 (`submesh`), #139 (`angle_based_smoother` perf).

## Test + run

```
pip install -e .              # from repo root (src-layout)
pytest -q                     # 79 tests, ~40s
python -m quadmesh.cli <input.14> -o <out.14>
```

## Session lifecycle

**Start of session**: invoke `session-resume` skill from DomI upstream (read latest `docs/sessions/session-NNN.md`, restore context: branch, PR, in-progress tasks, blockers). If skill not yet available upstream, do the equivalent manually: read latest handoff + `specs/001-matlab-to-python-port/tasks.md`.

**End of session**: invoke `handoff` skill from DomI upstream to write `docs/sessions/session-NNN.md` (next N) with: what changed, key decisions, files touched, what comes next, branch/PR state, open chilmesh issues. If skill not yet available upstream, do the equivalent manually.

DomI skill names tracked; replace manual prose with skill invocation once landed.
