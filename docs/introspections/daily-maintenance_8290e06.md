# Introspection — daily-maintenance@8290e06

**Session:** 2026-05-29T08Z QuADMESH daily-maintenance routine (hour-08 schedule slot)
**Model:** claude-opus-4-8
**Repo:** QuADMESH · **Branch:** daily-maintenance · **PR:** #59 (rolling, reused)

## Summary

Picked #55 (operator-approved feat, top eligible after #57 filtered as recently-worked).
Mapped the layers/skeleton/medial-axis surface: layers computed in chilmesh, read-only
here; no skeleton/medial-axis code. Shipped additive `compute_mesh_structure(domain, kind)`
+ specs/004; layers wired, skeleton/medial_axis raise NotImplementedError (no invented algo).
While running the profile gate (`pytest tests/`) found the package unimportable — root-caused
+ fixed a pre-existing regression. Two commits: fix (0e268cb), feat (8290e06).

## Pain signals (corpus)

- pain: caveman/introspect/sync-from-domi/request-from-domi plugins NOT loaded as slash-commands
    at container start (instructions_on_start.sh shows all 4 marketplace installs fail). Ran
    caveman/introspect/handoff INLINE from DomI checkout per #114 fallback.
  frequency: recurring-across-sessions
  severity: medium
  evidence: instructions_on_start.sh output "DomI marketplace add failed"; same as ed21a61 session.
  routed_to: DomI #114 (declarative plugin enablement) — already open, no new vote needed.
- pain: profile validation gate `pytest tests/` does NOT complete in the routine container —
    test_faithful_invariants.py + test_faithful_pairing.py HANG (>70s, SIGTERM'd the full run
    twice). Had to validate per-file with a timeout wrapper to get a pass/fail map.
  frequency: recurring-this-session
  severity: high
  evidence: full `pytest tests/` SIGTERM EXIT=143/timeout; per-file map green except faithful path.
  missing_skill_would_have_prevented_it: a `baseline-then-validate` / per-file-timeout validation
    harness (route to existing baseline-then-validate proposal if one is open in DomI).
- pain: pre-existing regression sat undetected — 58c141e left def two_part_smoother un-renamed +
    the #35 remove_unused_vertices guard never called, so `import quadmesh` collect-errored. The
    prior (docs-only) session skipped pytest, so nothing caught it.
  frequency: once
  severity: critical
  evidence: ImportError fem_smoother in __init__.py:7 on clean HEAD 7cfffb4 (baseline-confirmed).
  missing_skill_would_have_prevented_it: a pre-commit/CI "import smoke" lane that runs even for
    docs-only PRs; rename-completeness lint. Note: repo has no PR/push CI (only publish.yml).
- finding (not mine — pre-existing, WIP faithful path): test_route_dispatches_edge_bisection_when_interior
    IndexError at _tri_removal.py:194 (index 5 oob size 5); test_tri_removal_faithful.py 1 fail.
    Untouched by this diff. CLAUDE.md marks faithful path WIP (T017/T018). Candidate new bug issue.

## Next-session state

See docs/sessions/session-011.md (handoff session-resume reads). Top of queue next:
#33 (fold-aware validity metric) or the faithful-path hang/IndexError cleanup (#55 follow-ups in specs/004).
