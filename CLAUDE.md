# CLAUDE.md

## Branch rule

All ongoing work goes on `python-porting-project`. Do not push to `master`, `claude/affectionate-heisenberg-prShD`, `claude/awesome-goodall-cqPYK`, or `claude/awesome-goodall-Tbur3` — those are historical (v0.1/v0.2/v0.3 stack, superseded by PR #5).

New session branches may be created off `python-porting-project` and merged back via PR.

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
