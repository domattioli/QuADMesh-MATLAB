# Session Handoff — QuADMESH · daily-maintenance_d60980c · 2026-05-30

**Task:** #46 — onion-shaped hero domain for the QuADMESH layers visualization.
**Phase:** implementation (foundational slice).
**Progress:** onion boundary-polygon generator shipped + tested; triangulation/.14, layer sweep, tri2quad, render slices remain (enumerated on #46).
**Branch:** daily-maintenance
**Duration:** ~45 min
**Tool failures:** 2 (full/broad `pytest tests/` timed out at 144 — faithful-test hang; switched to targeted validation)
**Outcome:** complete for the in-scope increment.

## Pre-flight

- branch_policy_conflict: caught_and_resolved  <!-- harness checked out claude/zen-ride-BuOHR; routine §1 + CLAUDE.md + operator all mandate daily-maintenance. daily-maintenance already existed on origin → plain checkout, NO branch created. -->
- mcp_scope_gap: no  <!-- GitHub MCP fully functional; list_issues/list_pull_requests/update_pull_request/add_issue_comment all worked. -->
- label_scheme_mismatch: no  <!-- repo uses priority:/status:/type: + "status: operator approved"; matched §3 sort. -->

## What worked (top 3, with evidence)

1. Eligibility filter did real work: #57 (11.6h) + #55 (18h) screened out by the <24h recently-worked rule (git log --grep + dates); #22 screened by open upstream CHILmesh#94. Left #46 as the clean top-of-sort operator-approved pick.
2. `scripts/dev_setup.sh` provisioned the real gate (venv + editable CHILmesh + quadmesh[dev]); PyPI reachable this container. New module validated against a genuine `pytest` run (8/8), not a syntax-only fallback.
3. Haiku subagent (cavecrew-builder) given exact parametrization + the test's required assertions → correct first pass. Orchestrator re-ran the suite independently + eyeballed a render before commit (silhouette reads as an onion: oblate body, centered stem nub, off-center bottom minimum from the root dimple).

## What didn't (top 3, with evidence)

1. Full `pytest tests/` unrunnable — `test_faithful_invariants/pairing` + `test_tri_removal_faithful` hang; even with those 3 ignored a broad run still timed out at 200s. Cost two killed runs (~exit 144). Recurring (documented on PR #59). A per-file `pytest-timeout` / `slow` marker would make the routine gate completable.
2. `caveman` / `introspect` / `sync-from-domi` / `speckit` plugins not enabled at container start (marketplace add fails on the private DomI repo with no token) → caveman run inline as prose style, introspect/sync/speckit run as inline protocol. Recurring across ~6 sessions (#114).
3. Pre-existing `IndexError` in `test_tri_removal.py::test_route_dispatches_edge_bisection_when_interior` (`_tri_removal.py:194`) still open — surfaced again during validation triage.

## Recurring frictions (from local corpus)

- DomI contract plugins never install in the cloud container (no token) — observed across prior daily-maintenance sessions; inline fallback each time (#114).
- Full `pytest tests/` hangs on faithful tests — observed in prior sessions; still no per-file timeout wrapper.

## Pain → skill table

| Pain | Severity | DomI issue | Saved-min/session |
|---|---|---|---|
| `pytest tests/` validation gate hangs on faithful tests; no per-file timeout → routine can't run the declared gate | medium | candidate: per-file `pytest-timeout` wrapper skill / `slow`-marker convention | ~8 |
| Contract plugins uninstallable in cloud (no token); every session re-derives inline fallback | medium | #114 (declarative enable + vendored fallback) | ~6 |

## Next steps (for the next #46 session)

1. Triangulate `onion_polygon()` → `.14` (~2–5k elements). `.14` export path is cross-posted to ADMESH-Domains#93; coordinate there.
2. Run the CHILmesh skeleton layer sweep on the onion mesh; confirm ≥20 concentric layers.
3. Faithful `tri2quad` pass → assert zero interior tris (CLAUDE.md invariant).
4. Render the layer sweep; commit the still/animation as the README hero asset.

## Pain corpus (machine-readable)

```yaml
session_id: daily-maintenance_d60980c
repo: QuADMESH
branch: daily-maintenance
date: 2026-05-30
duration_min: 45
issue_worked: "#46"
phase: implementation
outcome: complete_increment
shipped:
  - "src/quadmesh/domains.py::onion_polygon (parametric watertight onion boundary)"
  - "tests/test_domains.py (8 tests, all pass)"
validation: "pytest tests/test_domains.py -> 8 passed; full suite skipped (faithful-test hang)"
pains:
  - id: pytest-gate-hang
    severity: medium
    detail: "full pytest tests/ hangs on test_faithful_*; no per-file timeout; routine cannot run declared gate"
    routing: "candidate new skill: pytest-timeout wrapper / slow-marker convention"
  - id: contract-plugins-uninstallable
    severity: medium
    detail: "caveman/introspect/sync-from-domi/speckit not enabled at container start; inline fallback used"
    routing: "DomI#114"
subagents:
  - type: general-purpose
    model: haiku
    preset: cavecrew-builder
    task: "onion_polygon generator + test"
    verified_independently: true
```
