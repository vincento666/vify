# Tasks 042: Runtime Policy Release Governance

## 042.0 Spec And Boundary

- [x] Confirm 042 numbering is unused.
- [x] Define backend-only release governance scope.
- [x] Confirm no frontend work in 042.
- [x] Confirm 041 owns profile config and decision logging.

## 042.1 Validation and evaluation run model

- [x] RED: malformed profile can be validated successfully.
- [x] RED: evaluation run table/API does not exist.
- [x] Add validation service for profile schema, thresholds, classifier config,
  fallback Agent config, and guardrail defaults.
- [x] Add `RuntimePolicyEvaluationRun` table/repository/service.
- [x] Add validation API.
- [x] Save evidence under
  `artifacts/slices/042-runtime-policy-release-governance/042.1/`.
- [x] Commit 042.1 only.

## 042.2 Golden matrix and decision-log replay

- [x] RED: 040 golden matrix cannot replay against candidate profile.
- [x] RED: historical decision logs cannot replay against candidate profile.
- [x] Add deterministic golden-matrix replay harness.
- [x] Add decision-log replay harness with filters.
- [x] Persist expected-vs-actual results and aggregate risk deltas.
- [x] Save evidence under
  `artifacts/slices/042-runtime-policy-release-governance/042.2/`.
- [x] Commit 042.2 only.

## 042.3 Release approval, canary, and activation gate

- [x] RED: activate succeeds before validation/replay/approval gates pass.
- [x] RED: profile version drift does not invalidate old evaluation.
- [x] Add release record model.
- [x] Add approve API.
- [x] Add canary API.
- [x] Add activate API with hard gate checks.
- [x] Save evidence under
  `artifacts/slices/042-runtime-policy-release-governance/042.3/`.
- [x] Commit 042.3 only.

## 042.4 Rollback and audit

- [x] RED: rollback cannot restore previous active profile.
- [x] RED: release transitions do not emit audit events.
- [x] Add rollback API.
- [x] Add audit event table/service.
- [x] Prove active profile switches back to previous release.
- [x] Prove release and evaluation APIs expose audit/evidence.
- [x] Save evidence under
  `artifacts/slices/042-runtime-policy-release-governance/042.4/`.
- [x] Commit 042.4 only.
