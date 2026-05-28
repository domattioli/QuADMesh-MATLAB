# Session 2026-05-24 — faithful per-layer tri2quad sweep (WIP) + demo layer-sequence

**Repo:** QuADMesh
**Branch:** `faithful-tri2quad-sweep` (cut from `daily-issue-fixing`)
**PR:** #37 (draft)
**Outcome:** partial (demo fix complete; faithful sweep committed WIP, invariant not yet met)
**Duration:** ~60 min (incl. async build subagent that hit its own token limit)

## What worked

1. Parity-impossibility proof pinned the demo's "overlapping quads" to a real algorithm bug (not manim): `_point_insert_tri_pairs` cannot tile a pentagon + interior pt into 2 quads (8 = 5 + 2k → k=1.5). Drove the decision to do the full `Tri2QuadRoutine` port. Commit `b2fe8ab`.
2. Shapely pairwise quad-intersection (area > 1e-7) as a hard empirical overlap gate on the annulus fixture — caught defects min-angle quality is blind to. Documented in handoff validation script.
3. Seedless-vs-seeded matching probe isolated the `_global_saturate` defect precisely: with seeds → 1 interior leftover; seedless → 0. Concrete next-session fix, not a vague "needs work".

## Pain YAML

```yaml
pains:

- pain: "system/task branch claude/mesh-quad-triangle-spec-IIvKw + CLAUDE.md daily-issue-fixing + explicit user 'own branch' = 3-way branch directive conflict; resolved by user-explicit precedence"
  frequency: recurring-across-sessions
  severity: low
  evidence: "pre-flight; work landed on faithful-tri2quad-sweep per explicit user instruction; 0 min lost"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: enforce-branch-policy
  domi_issue: "#13"
  saved_time_estimate_min: 2

- pain: "faithful method='faithful' path leaves interior residual tris across MULTIPLE sessions (zero-interior invariant); each session re-diagnoses the same gap from a different angle"
  frequency: recurring-across-sessions
  severity: high
  evidence: "annulus elems=73 tris=7 INTERIOR_tris=7 overlaps=21; prior corpus 2026-05-23T20Z-tri2quad-zero-interior, 2026-05-24-sweep-bowtie-fix, 2026-05-24T14Z-fold-seam-zip-rule"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: none — implementation gap, not tooling
  domi_issue: null
  saved_time_estimate_min: 0

- pain: "async build subagent hit its OWN session token limit mid-task ('You've hit your session limit'); left work uncommitted; main thread had to validate + commit blind"
  frequency: once
  severity: medium
  evidence: "task aac1ca64fb90702ea status completed, result 'You've hit your session limit · resets 6:30pm'"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: subagent-budget-guard
  domi_issue: null
  saved_time_estimate_min: 5

- pain: "git remote URL embeds GITHUB_TOKEN in plaintext; echoed into tool output on every push (git remote -v)"
  frequency: recurring-across-sessions
  severity: medium
  evidence: "push output exposed ghp_... token in remote URL"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: token-hygiene-guard
  domi_issue: null
  saved_time_estimate_min: 0

- pain: "faithful_sweep non-deterministic run-to-run (66 quads/7 interior vs 96/23 same input, fresh processes); suspect dict/layer iteration ordering"
  frequency: once
  severity: medium
  evidence: "two PYTHONPATH=src runs of faithful_sweep(m) on identical annulus gave different counts"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: none — implementation gap
  domi_issue: null
  saved_time_estimate_min: 0
```

## Counts

- Pain points: 5
- Recurring (cross-session): 3 (branch conflict, faithful interior-tri gap, token-in-remote)
- Votes cast: #13 (branch policy)
- New requests filed: none (gaps are implementation, not tooling; subagent-budget-guard noted but single occurrence)
- Comment on #9: yes
