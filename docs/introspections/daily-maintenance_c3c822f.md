# Session Handoff — QuADMESH · daily-maintenance@c3c822f · 2026-05-30

**Task:** #53 — `chore: sync DomI@<sha>` (refresh `.domi-pin`)
**Phase:** maintenance
**Progress:** 100% — pin refreshed, issue closed, rolling PR updated
**Branch:** daily-maintenance
**Duration:** ~20 min
**Tool failures:** 0 (`update_pin.sh` no-op'd as designed — no token; handled via inline-fallback)
**Outcome:** complete

## Pre-flight

- branch_policy_conflict: accepted_override — harness default branch was `claude/zen-ride-FrgJJ`, but the committed routine §1/§2 + repo CLAUDE.md + operator all mandate `daily-maintenance`. Checked out the existing tracking branch `daily-maintenance` (no new branch created).
- mcp_scope_gap: no (GitHub MCP read+write worked for issues/PR/commits on `domattioli/QuADMESH` + read on `domattioli/DomI`)
- label_scheme_mismatch: no (`domi-sync` is a known repo-local label, issue #20)

## What worked (top 3, with evidence)

1. **Inline-fallback sync via authenticated MCP.** `update_pin.sh`/`check_pin.sh` only carry `gh`/`curl` transports; both 404 on the private DomI repo in a token-less container. Derived the pin from `mcp__github__list_commits` (main HEAD `c832cf7`) + the local DomI checkout, replicating the script's strip-trailing-newline `sha256` of `MANIFEST.md` → `c9e2126…`. Pin is byte-consistent with what `check_pin.sh` will recompute once a token is present.
2. **Eligibility filter cleanly isolated the one executable item.** Of 13 open issues, every operator-approved one was recently-worked (<24h, PR #59), cross-repo blocked (#46), upstream-blocked (#22), or awaiting operator input (#9/#17/#18/#20/#21/#26/#28). #53 was the only unblocked, no-operator-input task — and is the routine's own §2 step-5 mandate.
3. **Reused the rolling PR #59** (refreshed description + head sha) instead of opening a new one, per DomI #128.

## What didn't (top 3, with evidence)

1. **`sync-from-domi`'s scripts have no MCP transport.** In a token-less container with authenticated MCP available, `update_pin.sh` cannot refresh the pin at all (curl → private-repo 404, no `gh`). The pin had to be hand-derived. The scripts assume `gh`/`GITHUB_TOKEN`; the routine's own §2 says MCP is the authenticated path, but the scripts can't use it. (Ran `update_pin.sh`; silent no-op, `.domi-pin` unchanged.)
2. **DomI contract plugins (`introspect`/`sync-from-domi`/`request-from-domi`) not installed mid-session** — close-out + sync both done via inline scripts. Recurring (3× now in local corpus) → DomI #114.
3. **`caveman`/`cavecrew` slash-commands unavailable** — `caveman` plugin not loaded this session (adopted the ultra prose style manually); `cavecrew` does not exist in DomI at all (only `caveman`, `caveman-commit`, `caveman-review`). No subagent was needed this session (no source code written), so the real `Agent`-tool/Haiku path was not exercised.

## Recurring frictions (from local corpus)

- DomI contract plugins not installed mid-session — 3rd observation → DomI #114.
- Routine container lacks `gh`/token; authenticated GitHub access is MCP-only, but the DomI sync/check scripts have no MCP transport → pin refresh requires a manual derivation each token-less session.

## Pain → skill table

| Pain | Severity | DomI issue | Saved-min/session |
|---|---|---|---|
| `update_pin.sh`/`check_pin.sh` have no MCP transport → cannot refresh/verify `.domi-pin` in token-less containers despite authenticated MCP | high | candidate: add MCP fallback to sync-from-domi scripts (or a thin `mcp-domi-pin` skill) | ~10 |
| Contract plugins not loaded mid-session | medium | DomI #114 | ~5 |
| `pytest tests/` gate needs `dev_setup.sh` + network; not applicable to metadata-only diffs but unclear when to skip | low | QuADMESH-local doc | ~3 |

## Pain corpus (machine-readable)

```yaml
session_id: daily-maintenance@c3c822f
repo: QuADMESH
branch: daily-maintenance
date: 2026-05-30
duration_min: 20
issue_worked: "#53"
phase: maintenance
outcome: complete
tool_failure_count: 0
workarounds:
  - "derived .domi-pin via authenticated GitHub MCP + local DomI checkout (update_pin.sh curl path 404s on private repo, no token/gh)"
  - "replicated update_pin.sh strip-trailing-newline sha256 of MANIFEST.md so check_pin.sh validates green later"
  - "ran /introspect close-out via inline scripts (contract plugins not loaded)"
  - "adopted caveman ultra prose style manually (caveman plugin not loaded; cavecrew skill does not exist)"
pre_flight:
  branch_policy_conflict: true
  mcp_scope_gap: false
  label_scheme_mismatch: false
  notes: "harness default branch claude/zen-ride-FrgJJ overridden by routine/CLAUDE.md/operator -> daily-maintenance (existing branch, no new branch)"
pain_points:
  - pain: "sync-from-domi scripts (update_pin.sh/check_pin.sh) only support gh/curl; both fail on private DomI in token-less containers, even though authenticated MCP is available"
    frequency: recurring-across-sessions
    severity: high
    evidence: "no GITHUB_TOKEN, no gh; update_pin.sh silent no-op; pin had to be hand-derived from mcp list_commits + local checkout"
    existing_skill_should_have_caught_it: "sync-from-domi"
    missing_skill_would_have_prevented_it: "MCP transport in update_pin.sh/check_pin.sh, or a thin mcp-domi-pin helper"
    domi_issue: 114
    saved_time_estimate_min: 10
  - pain: "DomI contract plugins not installed mid-session; close-out + sync done by inline scripts"
    frequency: recurring-across-sessions
    severity: medium
    evidence: "introspect/sync-from-domi/request-from-domi slash-commands unavailable; ran plugins/*/scripts by hand from DomI checkout"
    existing_skill_should_have_caught_it: "no"
    missing_skill_would_have_prevented_it: "declarative enable at container start (settings.json) — fixes next session only"
    domi_issue: 114
    saved_time_estimate_min: 5
actions_taken:
  votes_cast: []
  new_requests_filed: []
  closed_issues_flagged_for_reopen: []
  introspect_design_proposal_on_9: false
introspection_meta:
  what_worked: "MCP-derived pin with script-faithful hashing; tight eligibility filter; rolling-PR reuse"
  what_was_hard: "no MCP transport in the sync scripts; reconstructing exact hash semantics to stay check_pin-green"
```

## Next session — pick up here

- **DomI sync mechanism**: the highest-leverage fix surfaced this session — `sync-from-domi`'s `update_pin.sh`/`check_pin.sh` need an MCP transport (or a small `mcp-domi-pin` helper) so token-less containers can refresh/verify `.domi-pin` without hand-derivation. Candidate vote/file against DomI #114 (or a new `scope: skill` request) on a session where `request-from-domi` is reachable.
- **Open queue unchanged**: #57 (awaiting operator visual confirm of README hero), #55 (skeleton + structure-vs-layer, operator scoping), #46 (onion `.14`, cross-repo ADMESH-Domains#93), #22 (blocked on CHILmesh#94), #38 (memo, awaiting operator), #9/#17/#18/#20/#21/#26/#28 (research/labels awaiting operator input).
- **Pre-existing test debt** (carry-over): `_tri_removal.py:194` IndexError (`test_route_dispatches_edge_bisection_when_interior`); `test_faithful_*` hang (>70s, no `slow` marker); no PR/push CI to catch import-smoke regressions.
