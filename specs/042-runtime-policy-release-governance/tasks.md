# Tasks 042: Runtime Policy Release Governance

## 042.0 Spec And Boundary

- [x] Confirm 042 numbering is unused.
- [x] Define backend-only release governance scope.
- [x] Confirm no frontend work in 042.
- [x] Confirm 041 owns profile config and decision logging.

## 042.1 Validation and evaluation run model

- [ ] RED: malformed profile can be validated successfully.
- [ ] RED: evaluation run table/API does not exist.
- [ ] Add validation service for profile schema, thresholds, classifier config,
  fallback Agent config, and guardrail defaults.
- [ ] Add `RuntimePolicyEvaluationRun` table/repository/service.
- [ ] Add validation API.
- [ ] Save evidence under
  `artifacts/slices/042-runtime-policy-release-governance/042.1/`.
- [ ] Commit 042.1 only.

## 042.2 Golden matrix and decision-log replay

- [ ] RED: 040 golden matrix cannot replay against candidate profile.
- [ ] RED: historical decision logs cannot replay against candidate profile.
- [ ] Add deterministic golden-matrix replay harness.
- [ ] Add decision-log replay harness with filters.
- [ ] Persist expected-vs-actual results and aggregate risk deltas.
- [ ] Save evidence under
  `artifacts/slices/042-runtime-policy-release-governance/042.2/`.
- [ ] Commit 042.2 only.

## 042.3 Release approval, canary, and activation gate

- [ ] RED: activate succeeds before validation/replay/approval gates pass.
- [ ] RED: profile version drift does not invalidate old evaluation.
- [ ] Add release record model.
- [ ] Add approve API.
- [ ] Add canary API.
- [ ] Add activate API with hard gate checks.
- [ ] Save evidence under
  `artifacts/slices/042-runtime-policy-release-governance/042.3/`.
- [ ] Commit 042.3 only.

## 042.4 Rollback and audit

- [ ] RED: rollback cannot restore previous active profile.
- [ ] RED: release transitions do not emit audit events.
- [ ] Add rollback API.
- [ ] Add audit event table/service.
- [ ] Prove active profile switches back to previous release.
- [ ] Prove release and evaluation APIs expose audit/evidence.
- [ ] Save evidence under
  `artifacts/slices/042-runtime-policy-release-governance/042.4/`.
- [ ] Commit 042.4 only.
