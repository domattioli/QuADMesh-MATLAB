# Session 2026-05-24 — structured sweep + bowtie fix

**Repo:** QuADMesh
**Branch:** `daily-issue-fixing`
**Outcome:** complete
**Duration:** ~90 min

## What worked

1. Structured every-other-edge sweep (`_sweep_pairs`) seeded into matcher: zero invariant breakage, structuredMesh1 0.481→0.951. Commit `acc1345`.
2. Stage-by-stage bowtie count trace pinpointed two culprits: `cleanup_boundary_quads` global remap (10 bt) + `two_part_smoother` vert moves (145 bt). Commit `a36ba04`.
3. `repair._fix_bowties` already proven on WNAT_Hagen in docstring — wired as targeted post-smoother step.

## Pain YAML

```yaml
pains:

- pain: "python /tmp/script.py sys.path[0]=/tmp not cwd — 3 background tool failures before PYTHONPATH fix"
  frequency: once
  severity: medium
  evidence: "ModuleNotFoundError quadmesh; tasks bfhv10j99 bft6tfgrg bw2q31fue exit 1"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: python-script-runner
  domi_issue: null
  saved_time_estimate_min: 5

- pain: "git push 403 via local proxy; GITHUB_TOKEN direct-remote workaround"
  frequency: recurring-across-sessions
  severity: medium
  evidence: "commit a36ba04 push via token URL"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: git-push-fallback
  domi_issue: "#18"
  saved_time_estimate_min: 2

- pain: "system branch claude/mesh-quad-triangle-spec-IIvKw conflicts with CLAUDE.md daily-issue-fixing"
  frequency: recurring-across-sessions
  severity: low
  evidence: "pre-flight check; 0 min lost"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: enforce-branch-policy
  domi_issue: "#13"
  saved_time_estimate_min: 0
```

## Counts
- Pain points: 3
- Recurring cross-session: 2 (#18 git push, #13 branch)
- Votes cast: #18 (MCP comment)
- New requests filed: 0
- DomI #9 comment: yes
