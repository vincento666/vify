# Plan 042: Runtime Policy Release Governance

## Architecture

```text
RuntimePolicyProfileService
  -> RuntimePolicyValidationService
  -> RuntimePolicyReplayService
       -> 040 golden matrix
       -> RuntimeDecisionLog replay
  -> RuntimePolicyReleaseService
       -> approve
       -> canary
       -> activate
       -> rollback
```

042 builds governance around 041. It does not change the route layers
themselves.

## Data Model

Add:

```text
runtime_policy_evaluation_run
runtime_policy_release
runtime_policy_audit_event
```

Evaluation run should store:

- input profile id/version;
- evaluation type;
- selected log filters;
- expected-vs-actual results;
- aggregate metrics;
- risk deltas;
- pass/fail status;
- failure reasons.

## TDD Strategy

RED tests first:

- malformed profile validates before validation exists;
- activate succeeds without evaluation;
- old evaluation still works after profile version changes;
- replay lacks expected-vs-actual evidence;
- rollback cannot restore previous active profile;
- audit events are missing.

GREEN:

- add validation service;
- add golden matrix replay harness;
- add decision-log replay harness;
- add release records and gate checks;
- add canary/activate/rollback APIs;
- add audit events;
- keep frontend untouched.

## SDD Gate

042 may start only after 041 evidence proves profile CRUD, profile resolution,
and decision logging. 042 must not bypass 041's profile API or mutate
runtime-lab route logic directly.

Each slice must update `spec.md`, `plan.md`, `tasks.md`, and evidence under:

```text
artifacts/slices/042-runtime-policy-release-governance/
  042.1/
  042.2/
  042.3/
  042.4/
```

042 is complete only when activation is impossible without successful
validation/replay/approval gates, and rollback is proven through backend tests.

## Slice Progress

- 042.1 complete: validation catches malformed persisted profiles, stores
  passed/failed evaluation runs with guardrail defaults, exposes validation and
  evaluation-run APIs, and preserves the 040 route matrix in focused backend
  E2E gates plus browser UAT.
- 042.2 complete: golden matrix replay and decision-log replay persist
  expected-vs-actual results plus aggregate risk deltas, support decision-log
  filters, and preserve the 040 route matrix in focused backend E2E gates plus
  browser UAT.
- 042.3 complete: release approval, canary, and activation APIs persist release
  state, enforce validation/replay/approval/version gates before activation,
  archive the previous active profile on activation, and preserve runtime-lab
  route boundaries in focused backend E2E gates plus browser UAT.

## Non-Goals

- no frontend management UI;
- no automatic policy recommendation;
- no production traffic balancer outside runtime-lab binding;
- no mandatory live provider calls.
