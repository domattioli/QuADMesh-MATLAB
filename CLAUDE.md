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

## Session handoff

End every session by writing `docs/sessions/session-NNN.md` with: what changed, key decisions, files touched, what comes next, branch/PR state.
