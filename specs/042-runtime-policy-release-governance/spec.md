# Spec 042: Runtime Policy Release Governance

## Goal

Add backend-only evaluation, release gate, canary, activation, and rollback
governance for `RuntimePolicyProfile`.

042 ensures route-policy changes cannot go live merely because a profile was
edited. Activation must be blocked until validation and replay evaluation pass,
and every activation must be auditable and reversible.

## Dependency

042 starts only after 041 is complete:

- `RuntimePolicyProfile` exists;
- runtime-lab resolves effective profiles;
- classifier and fallback Agent config can come from profile;
- `RuntimeDecisionLog` captures policy snapshot and route evidence;
- profile CRUD and decision-log APIs pass backend gates.

## Scope

In scope:

- validation run API;
- 040 golden matrix replay API;
- historical decision-log replay API;
- evaluation report persistence;
- risk-delta calculation;
- release request/approval model;
- canary percentage model;
- activate API with hard gates;
- rollback API;
- audit events for validate, replay, approve, activate, rollback.

Out of scope:

- frontend release console;
- production traffic router implementation outside runtime-lab binding;
- automatic threshold recommendation;
- live LLM mandatory evaluation;
- changing 041 profile schema except for release metadata.

## Release State Machine

```text
draft
  -> validating
  -> evaluated
  -> approved
  -> canary
  -> active
  -> archived
```

Failure paths:

```text
validating -> draft
evaluated -> draft
approved -> draft
canary -> rolled_back
active -> rolled_back
```

The exact persisted status names may be normalized, but the behavior must keep
these transitions explicit and auditable.

## Release Gate

`activate` must fail unless all requirements hold:

```text
profile exists
profile is not archived
schema validation passed
040 golden matrix replay passed
historical decision-log replay report exists
risk deltas are within configured guardrails
approver exists
rollback target exists unless this is first activation
profile version has not changed since evaluation
```

No direct "force activate" API is allowed in 042.

## Evaluation Inputs

Golden matrix:

- use the final 040 scenario matrix;
- expected action/source/reason/state-mutation assertions must be explicit;
- matrix replay should be deterministic with fake/local providers by default.

Historical decision logs:

- replay selected logs against candidate profile;
- compare old action/source/reason with candidate result;
- report changed decisions, handoff-rate delta, clarification-rate delta,
  FAQ/RAG/Agent hit-rate delta, SOP mutation-risk delta, and unsupported action
  count.

## Backend API

```text
POST /api/v1/runtime-policy/profiles/{profile_id}/validate
POST /api/v1/runtime-policy/profiles/{profile_id}/replay/golden-matrix
POST /api/v1/runtime-policy/profiles/{profile_id}/replay/decision-logs
GET  /api/v1/runtime-policy/evaluation-runs
GET  /api/v1/runtime-policy/evaluation-runs/{run_id}
POST /api/v1/runtime-policy/profiles/{profile_id}/approve
POST /api/v1/runtime-policy/profiles/{profile_id}/canary
POST /api/v1/runtime-policy/profiles/{profile_id}/activate
POST /api/v1/runtime-policy/releases/{release_id}/rollback
GET  /api/v1/runtime-policy/releases
GET  /api/v1/runtime-policy/releases/{release_id}
```

All APIs are backend-only. The host production system can build its own
operator UI on top of them.

## Release Record

Persist `RuntimePolicyRelease`:

```text
id
profile_id
profile_version
previous_active_profile_id
previous_active_profile_version
evaluation_run_ids
status
canary_percent
approved_by
activated_by
rolled_back_by
activated_at
rolled_back_at
rollback_reason
audit_snapshot
```

## Guardrail Defaults

Initial backend defaults may be conservative:

```text
max_handoff_rate_delta = 0.10
max_clarification_rate_delta = 0.15
max_sop_mutation_risk_delta = 0.00
max_unsupported_action_count = 0
require_golden_matrix_pass = true
require_replay_report = true
```

These guardrails should be configurable through backend policy governance, but
not through frontend in 042.

## Acceptance Criteria

- validation API rejects malformed profiles and unsafe route parameters;
- golden-matrix replay persists expected-vs-actual results;
- decision-log replay persists comparison and risk deltas;
- activate fails before validation/replay/approval/rollback target gates pass;
- profile version drift invalidates old evaluation;
- canary state can be recorded and queried;
- activation writes release record and switches effective profile;
- rollback restores previous active profile;
- all release transitions emit audit events;
- no frontend files are modified.

## Completion Capability

After 042, a host production system can safely operate route policies through
backend APIs: evaluate, approve, canary, activate, observe, and rollback
RuntimePolicyProfile changes without relying on Hify frontend.

## Specification Sign-off

Status: ready for implementation.

042 is a backend-only release-governance spec. It must not add frontend UI or
allow direct activation without evaluation gates.

## Implementation Status

- 042.1 complete: profile validation service, guardrail defaults,
  `RuntimePolicyEvaluationRun` persistence, validation API, evaluation-run
  list/detail APIs, backend E2E regression, and browser UAT evidence are
  recorded under
  `artifacts/slices/042-runtime-policy-release-governance/042.1/`.
