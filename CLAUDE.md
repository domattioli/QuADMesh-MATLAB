# CLAUDE.md

## Faithfulness invariant (non-negotiable)

Interior residual triangle (tri with NO domain-boundary edge) after tri2quad = **NOT a faithful QuADMESH+ implementation**. Zero interior tris is mandatory — a properly-implemented QuADMESH+ never leaves one. Only **boundary** tris may remain (thesis minimizes even those; ≤1 typical). Pinned by `python/tests/test_no_interior_tris.py`.

Status: `method="matching"` has zero interior tris by construction (faithful on this axis). `method="faithful"` (layer sweep) currently leaves interior tris → it is **WIP, NOT yet faithful**; closing that gap (Ch 4 IE-before-OE + inter-layer matching, faithful-port-tasks T017/T018) is required before it can be called faithful or made default.

## Routine

Routine lives in `DomI/claude_routine_instructions.md` (private). Textbox payload format + per-repo profile knobs in §6–§7 there. Do not duplicate routine prose here.

## Branch rule

All ongoing work goes on `daily-issue-fixing`. Do not push to `master`/`main` directly. Do not push to historical branches (`python-porting-project`, `claude/affectionate-heisenberg-prShD`, `claude/awesome-goodall-cqPYK`, `claude/awesome-goodall-Tbur3`).

New session branches discouraged — work directly on `daily-issue-fixing`, PR → `main`. `branch_guard.sh` (DomI plugin) blocks non-allowlisted names.

## Layout

- `python/` — Python port of QuADMESH+ (lives in this repo per operator decision).
- `python/MAPPING.md` — MATLAB → Python function map + chilmesh gaps.
- `specs/001-matlab-to-python-port/` — speckit spec/plan/tasks.
- `docs/sessions/session-NNN.md` — per-session handoff notes.
- `02_QuADMESH_Library/`, `03_CHILMesh_Test_Cases/`, etc. — original MATLAB source + fixtures.

## chilmesh

External Python dep. Issues filed against it for missing/slow APIs: #132 (`merge_elements`), #133 (`ccw_edges_around_vert`), #134 (adjacencies flag), #138 (`submesh`), #139 (`angle_based_smoother` perf).

## Test + run

```
cd python && pytest -v        # 35 tests, ~13s
python -m quadmesh.cli <input.14> -o <out.14>
```

## Session lifecycle

**Start of session**: invoke `session-resume` skill from DomI upstream (read latest `docs/sessions/session-NNN.md`, restore context: branch, PR, in-progress tasks, blockers). If skill not yet available upstream, do the equivalent manually: read latest handoff + `specs/001-matlab-to-python-port/tasks.md`.

**End of session**: invoke `handoff` skill from DomI upstream to write `docs/sessions/session-NNN.md` (next N) with: what changed, key decisions, files touched, what comes next, branch/PR state, open chilmesh issues. If skill not yet available upstream, do the equivalent manually.

DomI skill names tracked; replace manual prose with skill invocation once landed.
