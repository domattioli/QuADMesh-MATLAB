<!-- Session handoff + corpus entry. Caveman style. introspect@DomI v1.3. -->

# Session Handoff — QuADMESH · daily-issue-fixing@bcacf91 · 2026-05-27

**Task:** Hour-14 routine slot (QuADMESH per schedule). Close #35; ship reproducible-env chore.
**Phase:** implementation
**Progress:** 100% of session scope — #35 closed, #48 filed+resolved, gate green.
**Branch:** daily-issue-fixing
**Duration:** ~30 min
**Tool failures:** 0
**Outcome:** complete

## Pre-flight

- branch_policy_conflict: caught_and_resolved  <!-- harness put repo on claude/modest-ramanujan-j1tU7; switched to daily-issue-fixing per routine §1 + operator. Local branch first based on main; reset --hard to origin/daily-issue-fixing (600bacb) so rolling PR #47 not orphaned. -->
- mcp_scope_gap: no
- label_scheme_mismatch: no  <!-- priority:/type:/timeline: scheme as expected -->

## What worked (top 3, with evidence)

1. Branch reconciliation before any work (`git ls-remote` caught that local daily-issue-fixing was based on main, not the rolling-PR head 600bacb; reset --hard avoided orphaning PR #47).
2. dev_setup.sh validated three ways before commit (fresh `.venv` rebuild → 87 passed; idempotent re-run; missing-sibling → exit 1 + clone hint).
3. #35 close was evidence-backed, not guessed (read all 3 comments → QuADMESH-side complete, residual is CHILmesh#174; owner-Claude comment already recommended close).

## What didn't (top 3, with evidence)

1. Fresh container had no numpy/scipy/chilmesh/pytest — `pytest tests/` gate could not run until a venv was hand-built. THIS session fixed it locally (dev_setup.sh) and is the recurring pain DomI #148 tracks.
2. DomI contract plugins failed to install at session start (marketplace add ✗) — `/introspect`, `/sync from DomI` unavailable; ran introspect inline per #114 fallback. Recurring (corpus 2x).
3. `gh` absent → introspection script's DomI vote-candidate section skipped; did the DomI feedback loop via MCP instead.

## Recurring frictions (from local corpus)

- Fresh-container test deps absent (numpy/scipy/chilmesh/pytest) — observed sessions 007, 008, and this one → DomI #148, now mitigated locally by dev_setup.sh.
- DomI plugins not installed mid-session — observed in 2 prior corpus entries → DomI #114.

## Pain → skill table

| Pain | Severity | DomI issue | Saved-min/session |
|---|---|---|---|
| Test-venv hand-build before gate | medium | #148 (QuADMESH already +1; ref impl posted) | ~5 |
| DomI plugins not installed mid-session | medium | #114 | ~10 |

## Pain corpus (machine-readable)

```yaml
session_id: daily-issue-fixing@bcacf91
repo: QuADMESH
branch: daily-issue-fixing
date: 2026-05-27
duration_min: 30
issue_worked: "#35 (closed), #48 (filed+resolved)"
phase: implementation
outcome: complete

tool_failure_count: 0
workarounds:
  - introspect-run-inline-no-plugin
  - gh-absent-domi-loop-via-mcp

pre_flight:
  branch_policy_conflict: true
  mcp_scope_gap: false
  label_scheme_mismatch: false
  notes: "Harness branch claude/modest-ramanujan-j1tU7; switched to daily-issue-fixing. Local branch reset --hard to origin/daily-issue-fixing to avoid orphaning rolling PR #47."

pain_points:
  - pain: "Fresh container lacks numpy/scipy/chilmesh/pytest; pytest tests/ gate cannot run until venv hand-built"
    frequency: recurring-across-sessions
    severity: medium
    evidence: "import chilmesh / python -m pytest both ModuleNotFoundError on fresh container 2026-05-27T14Z; same sessions 007/008"
    existing_skill_should_have_caught_it: "ensure-test-venv (proposed, #148)"
    missing_skill_would_have_prevented_it: true
    domi_issue: "#148"
    saved_time_estimate_min: 5
  - pain: "DomI contract plugins not installed at session start (marketplace add failed)"
    frequency: recurring-across-sessions
    severity: medium
    evidence: "instructions_on_start.sh step 5: DomI marketplace add failed / 3x install failed"
    existing_skill_should_have_caught_it: "plugin-install-with-vendored-fallback (proposed, #114)"
    missing_skill_would_have_prevented_it: true
    domi_issue: "#114"
    saved_time_estimate_min: 10

actions_taken:
  votes_cast: []                              # QuADMESH already +1 on #148; posted ref-impl evidence, not a re-vote
  new_requests_filed: []                       # QuADMESH#48 is repo-local, not a DomI skill request
  closed_issues_flagged_for_reopen: []
  introspect_design_proposal_on_9: false

introspection_meta:
  what_worked: "validate-before-commit on the shell script (3 paths) caught nothing broken but proved acceptance"
  what_was_hard: "reconciling a freshly-created local daily-issue-fixing against the existing remote rolling-PR head"
```

## Next session — pick up here

1. [ ] #25 M3 remainder (T026/T028/T029): edge_insertion case-2 iLayer-1 retri, LayerState bookkeeping, per-layer adjacency rebuild, wire faithful router into live sweep. Spec-kit required (algorithm parity).
2. [ ] #46 onion hero domain — blocked on ADMESH-Domains#93 producing the `.14`; check that first.
3. [ ] Research backlog (#38 parallelization memo, #33 fold-aware metric, #28 truss-on-quad) — planning-only deliverables.

**Files to read first:**
- `specs/001-matlab-to-python-port/faithful-port-tasks.md` — the T0xx task IDs for #25 M3.
- `src/quadmesh/_tri_removal.py` — `route_leftover_tri` case-2 branch (where case-2 split landed).
- `scripts/dev_setup.sh` — run this FIRST to get `pytest tests/` working.

**Context to remember:**
- Branch was reset --hard onto origin/daily-issue-fixing (600bacb) at start; rolling PR #47 is the single long-lived PR — reuse, never open a second.
- #35 closed this session; do not reopen without new evidence beyond CHILmesh#174.

## Routing decisions taken this session

- Votes on existing skill-proposal issues: 0 (QuADMESH already +1 on #148; posted reference-impl evidence comment instead)
- New requests filed: 0
- Closed issues flagged for reopen: 0
- Comments on DomI #9: 0
- PR description updated: yes (#47)

---
_Written via `introspect@DomI` v1.3 (inline, plugin not installed) from QuADMESH. Caveman style. Pairs with `handoff@DomI` v1.0._
