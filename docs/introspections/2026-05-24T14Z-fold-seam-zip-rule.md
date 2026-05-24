# Session 2026-05-24T14Z — fold-seam (flagged-edge) guard #31

**Repo:** QuADMesh
**Branch:** `daily-issue-fixing`
**Outcome:** complete (PR #29 updated, head `b33e932`)
**Duration:** ~75 min

## What worked

1. Thesis-grounded fix. Extracted the exact "flagged edge = any edge composed of two inner vertices" definition (p39) + Figure 4.1 caption from `docs/Mattioli_Thesis.pdf` via `pypdf`, so the implementation matches the source instead of guessing from the issue text. Commit `b33e932`.
2. Scoping flagged edges to **interior** sub-mesh IV–IV edges (not all IV–IV) makes the guard fire only at genuine fold seams — zero-interior-residual guarantee held on all 5 fixtures.
3. Before/after instrumentation at the `_match_tris_to_quads` level (forbidden=None vs flagged) gave a clean, test-able metric: cross-fold quads 6/14/5/12/70 → 0.
4. When asked "why no quality gain", measuring the *affected* quads (70 cross-fold, med 0.406; 3411 rerouted, 0.534→0.533) instead of the global boxplot produced the real answer: correctness fix, metric-blind.

## Pain YAML

```yaml
pains:

- pain: "fresh container: no numpy/scipy/chilmesh in the uv-tool pytest interpreter; gate uncrunnable until a venv was built from pyproject deps"
  frequency: recurring-across-sessions
  severity: high
  evidence: "pytest ModuleNotFoundError chilmesh; built python/.venv via uv pip install + editable chilmesh/quadmesh"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: python-env-bootstrap
  domi_issue: null
  saved_time_estimate_min: 8

- pain: "cryptography rust binding broken (_cffi_backend) blocked pypdf/pdfminer until force-reinstall cffi"
  frequency: once
  severity: medium
  evidence: "pyo3_runtime.PanicException importing cryptography; fixed via pip install --force-reinstall cffi"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: pdf-extract-tool
  domi_issue: null
  saved_time_estimate_min: 5

- pain: "no poppler-utils -> Read tool cannot render thesis PDF pages; fell back to pypdf text extraction"
  frequency: once
  severity: low
  evidence: "pdftoppm is not installed error from Read(pages=...)"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: pdf-extract-tool
  domi_issue: null
  saved_time_estimate_min: 3

- pain: "system-prompt branch claude/focused-maxwell-L25BG conflicts with routine+CLAUDE.md daily-issue-fixing"
  frequency: recurring-across-sessions
  severity: low
  evidence: "pre-flight; resolved to daily-issue-fixing (branch_guard allowlist + explicit operator order); 0 min lost"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: enforce-branch-policy
  domi_issue: "#13"
  saved_time_estimate_min: 0

- pain: "validation gate inherited RED: test_parity TC1 mean 0.375 vs 0.739 pre-existed at parent f7a11b2; routine demands green before done but the failure is out-of-scope for #31"
  frequency: once
  severity: medium
  evidence: "stash-verified failing without my changes; matching-path, untouched by #31"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: gate-baseline-tracker
  domi_issue: null
  saved_time_estimate_min: 4

- pain: "numpy 2.x removed ndarray.ptp -> plot script crash"
  frequency: once
  severity: low
  evidence: "AttributeError 'numpy.ndarray' object has no attribute 'ptp'; switched to np.ptp(arr,axis=0)"
  existing_skill_should_have_caught_it: none
  missing_skill_would_have_prevented_it: none
  domi_issue: null
  saved_time_estimate_min: 1
```

## Counts
- Pain points: 6
- Recurring cross-session: 2 (env-bootstrap, #13 branch)
- New issues filed: parity regression (matching pipeline), fold-aware-metric follow-up
- Votes cast: 0 (DomI feedback loop deferred — narrow operator scope this session)
- DomI #9 comment: no
