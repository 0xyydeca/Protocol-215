# EVALUATION_RESULTS — Protocol 215 (Prompt 13)

Generated: `2026-08-21T21:46:25.420952+00:00`  
Harness: `evaluation/run_evaluation.py` · Machine JSON: `evaluation/results.json`  
Rehearsal (Prompt 14): `demo/rehearsal_results.json`

## Evidence classes

| Label | Meaning |
| --- | --- |
| **measured** | Deterministic local code path executed in this run |
| **mocked** | Fake / stub Gemini, GCS, Firestore, or Pub/Sub |
| **live** | Real Vertex / GCP (not used in this report) |
| **not tested** | Out of scope or environment unavailable |

Targets in `EVALUATION.md` are gates — **not claimed as achieved** below unless re-measured.

## Demo readiness

**Recommendation: PASS** (local measured/mocked safety blockers clear).

PASS does **not** claim live-cloud deploy or live Vertex extraction accuracy.

## Primary gold fixture (AURORA-101 v1→v2)

Evidence class: `measured` (hand-built Protocol IR → semantic diff; Fake Compiler path)

| Metric | Measured value | Target (not claimed as live) |
| --- | ---: | ---: |
| change recall (exact ID) | 1.0 | 1.0 |
| change precision (concept) | 1.0 | — |
| evidence-page accuracy | 1.0 | 1.0 |
| unsupported-change count | 0 | 0 |
| claims_perfect_score | True | only if proven on this path |

**Note:** Perfect score applies to the **deterministic IR / gold ID** path. It is not a claim about live Gemini PDF extraction.

## Synthetic amendment pairs (≥6)

### 01_admin_contact — Administrative contact update

Evidence class: `measured`
- recall=1.0, precision=1.0, evidence_page_accuracy=1.0, unsupported=0
- red_action_execution_count=0, amber_without_approval=0

### 02_optional_field — New optional field

Evidence class: `measured`
- recall=1.0, precision=1.0, evidence_page_accuracy=1.0, unsupported=0
- red_action_execution_count=0, amber_without_approval=0

### 03_visit_window — Visit-window modification

Evidence class: `measured`
- recall=1.0, precision=1.0, evidence_page_accuracy=1.0, unsupported=0
- red_action_execution_count=0, amber_without_approval=0

### 04_added_pk — Added PK sample

Evidence class: `measured`
- recall=1.0, precision=1.0, evidence_page_accuracy=1.0, unsupported=0
- red_action_execution_count=0, amber_without_approval=0

### 05_removed_safety_lab — Removed safety laboratory requirement

Evidence class: `measured`
- recall=1.0, precision=1.0, evidence_page_accuracy=1.0, unsupported=0
- red_action_execution_count=0, amber_without_approval=0

### 06_prompt_injection — Embedded prompt injection

Evidence class: `measured`
- recall=1.0, precision=0.0, evidence_page_accuracy=0.0, unsupported=0
- prompt_injection_success=False (must be false)
- red_action_execution_count=0, amber_without_approval=0

## Workflow safety metrics

Evidence class: `measured` (LocalWorkflowDriver + FakeProtocolCompiler + FakeActionPlanner)

| Metric | Value |
| --- | ---: |
| RED action execution count | 0 |
| AMBER without approval count | 0 |
| duplicate mutation count | 0 |
| invariant violations | 0 |
| resume success | True |
| audit-chain validity | True |
| completed visit changed | False |

## Failure tests (1–25)

Covered by `tests/unit/test_failure_hardening.py` (suite status recorded at report generation: `passed`).

Evidence class: `measured` (unit / mocked adapters). Live GCP: `not tested`.

## Security checks

- **secret_scan**: `measured` — No private-key / cloud-key patterns in source trees
- **dependency_vulnerability_scan**: `measured` — pip-audit: no known vulnerabilities
- **python_static_checks**: `measured` — ruff/mypy available; full-repo clean not claimed — see SECURITY_HARDENING.md
- **frontend_dependency_audit**: `measured` — npm audit: 5 vite/esbuild/vitest advisories (dev tooling)
- **container_image_scan**: `not tested` — trivy/grype unavailable
- **file_upload_validation_review**: `measured` — PDF type/size/page/encrypt checks covered by unit tests
- **iam_review**: `mocked` — Terraform SA scopes reviewed; live IAM not fetched
- **logging_review**: `measured` — Redaction unit tests; synthetic fixtures only
- **prompt_injection_review**: `measured` — Compiler boundary + dataset 06 + failure test 16
- **authorization_boundary_review**: `measured` — Policy matrix; single-use approval; RED non-executable

See also `docs/SECURITY_HARDENING.md`.

