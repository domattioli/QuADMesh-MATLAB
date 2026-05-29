# Session Handoff — QuADMesh @ 8d3e2f1

**Session:** 2026-05-29T20Z-daily-maintenance (hour-20 slot)
**Date:** 2026-05-29
**Model:** (model id withheld from repo artifacts per session policy)
**Branch:** daily-maintenance

---

## What shipped this session

- **#38** parallelization-strategy options memo → `docs/parallelization-strategy-memo.md`
  (commit `8d3e2f1`). Decomposition memo only, no implementation (matches the issue's
  stated scope: "a short options memo, not code"). Recommendation: batch-level
  multiprocessing over `run_pipeline` (`pipeline.py:14`), gated on a determinism fix.
- Rolling PR #59 description + title refreshed (reused, not duplicated).
- Issue #38 answered with a grounded comment + open questions for the operator.

## Next steps (priority order)

1. **#38 follow-up (operator-gated):** answer the memo's 3 open questions — (a) green-light
   a determinism repro, (b) frequency of multi-component inputs, (c) numba/cython appetite.
   Determinism fix is the prerequisite for any parallel batch work.
2. **Determinism repro:** run a canonical fixture N times, diff connectivity, pin which
   `set()` accumulator (`_match_faithful.py:54,88` / `identify_edges.py:140` / `repair.py:71`)
   drives nondeterministic merge order. The bug is real (per #38) but undocumented in code.
3. **#57 / #51:** operator visual-confirm the README hero renders on github.com; #51 is a
   confirmed dup of #57 (close-decision is operator's).
4. **#46 (onion hero):** blocked here — needs `manim` (not installed in routine container)
   + cross-repo `.14` from ADMESH-Domains#93. Revisit when tooling/dep available.
5. **#22:** upstream-blocked on CHILmesh#94 (mesh mutation API). Skip until that lands.

## Open questions

- Which `set()` is the actual nondeterminism root? (unconfirmed — needs repro)
- Are disconnected/multi-component domains common enough to justify an upstream chilmesh
  connected-component split? (decides memo option #4)
- Is the `test_faithful_*` pytest hang (>70s) worth a dedicated bug issue + spec? It blocks
  full-suite validation and the faithful path is WIP (T017/T018).

## Lessons (pain → fix)

- **Subagent fabricated source quotes.** The read-only mapping subagent returned two
  invented `# FIXME`/`# TODO` comment quotes (determinism finding) that do not exist in the
  tree (`grep determin|fixme|todo` → 0 matches). **Fix:** always verify subagent-supplied
  *quotes and line numbers* against source before publishing them as fact — the subagent
  itself flagged its line numbers as "approximate", which was the tell. Cost: ~4 verify
  calls; caught before anything false shipped.
- **Parallel tool batches corrupted/cancelled output** repeatedly this session (blank or
  command-echo results when many Bash calls ran in one block). **Fix:** for
  verification-critical commands, run single Bash calls sequentially; reserve parallel
  batches for clearly-independent, non-load-bearing reads.
- **Tooling gaps are hard stops, not warnings:** `pytest` and `manim` absent in the routine
  container → cannot validate Python or render hero assets. Routine forbids auto-install.
  Pick research/docs issues when the executable backlog needs missing binaries.
- **`/caveman` + `/caveman:cavecrew` not invocable** despite being enabled in
  `.claude/settings.json` — plugins load at container start, and this session's skill
  registry lacked them. Emulated caveman-ultra style in prose; used the Agent tool as the
  real "cavecrew" subagent mechanism (also what DomI CLAUDE.md mandates for code).

## Files touched

- `docs/parallelization-strategy-memo.md` (new)
- `docs/introspections/daily-maintenance_8d3e2f1.md` (this file)

## State for next session (session-resume reads this)

- Branch: `daily-maintenance` @ `8d3e2f1`, clean, tracking origin.
- Rolling PR: **#59** (draft, daily-maintenance→main, mergeable clean) — reuse it; do not
  open a second. Operator-merged only.
- `.domi-pin` = DomI@`22cc443`; sync-issue #53 references older `20ba0c6` (repo already
  past it). sync-from-domi plugin not installed in container — inline fallback only.
- Eligible-issue backlog after this session is research/blocked: #38 (awaiting operator
  answers), #28/#26/#21/#18/#17/#9 (research), #22 (CHILmesh#94-blocked), #46 (manim/dep
  blocked), #20/#51/#57 (operator-decision).
