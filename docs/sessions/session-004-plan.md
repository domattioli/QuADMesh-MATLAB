# Session 004 Plan — QuADMesh Python Port v0.4

**Branch**: continue on `python-porting-project` (or feature branch off it, merged back via PR).
**Predecessor**: session-003 (PR #5 merges v0.1+v0.2+v0.3 → master).
**Spec**: `specs/001-matlab-to-python-port/tasks.md` — v0.4 backlog.

## Goal

Close the v0.4 backlog items that are now (or soon) unblocked, and bring element-count parity with MATLAB on canonical fixtures.

## Inventory of work

### Blocked on chilmesh
| item | blocker | action this session |
|---|---|---|
| Sub-domain smoother (T11.5) | chilmesh#138 (`submesh()`) | check issue status; if landed, port `twoPartSmoother.m` boundary/interior split |
| Aggressive tri routing (T14.10) | chilmesh#132 (`merge_elements`) | check issue status; if landed, wire `route_leftover_tri(aggressive=True)` to real merge |
| `angle_based_smoother` default-on | chilmesh#139 (perf ~42s/pass) | revisit only if chilmesh ships vectorised smoother |

### Independent (start here)
1. **T4.6 — Aggressive-path tests** (`python/tests/test_tri_removal.py`)
   - Unit-test `edge_insertion` cases 1/2.
   - Unit-test `edge_bisection` (post-bug-fix from v0.3 / T14.2).
   - Build minimal 3-tri WorkingMesh fixtures.
2. **Element-count parity** (`python/tests/test_parity.py`)
   - Pick canonical fixtures: `Test_Case_1.14` + `Block_O.14`.
   - Capture MATLAB output elem/vert counts (run MATLAB once or check existing artifacts).
   - Assert Python output within tolerance (±5% on elem count, ±2% on quad fraction).
3. **Edge-insertion case-2 retriangulation** (T11.6, T14.10 dependency)
   - Currently deferred — requires stateful layer sweep redesign.
   - Scope: design doc only in this session (`specs/001-matlab-to-python-port/case-2-design.md`).
   - Identify state needed in `tri2quad_routine` for iLayer-1 mutation.

## Acceptance

- All current 35 tests still green.
- +N tests for aggressive path (T4.6) — target ≥5.
- Parity test framework lands even if asserts are loose initially.
- Case-2 design doc reviewed.
- Session-004 handoff (`docs/sessions/session-004.md`) written via `handoff` skill.

## Risks / open questions

- Do MATLAB fixtures + reference outputs exist? If not, need to run MATLAB once to capture goldens.
- `submesh()` API shape — if chilmesh#138 lands, may require minor refactor of `two_part_smoother` signature.
- v0.4 is the last "easy" milestone. v0.5+ enters ADMESH library (`01_ADMESH_Library/`) which is out of scope for the original port goal — confirm with operator.

## Start-of-session checklist

1. Invoke `session-resume` (or read `session-003.md` + `tasks.md`).
2. `git checkout python-porting-project && git pull`.
3. `cd python && pytest -v` — confirm 35 green baseline.
4. Check chilmesh#132 + #138 status (may unblock entries above).
