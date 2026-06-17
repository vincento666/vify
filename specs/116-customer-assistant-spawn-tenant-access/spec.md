# Feature Spec: Customer Assistant Spawn Tenant Access

## Status

Complete.

## User Story

As a host-embedded customer-assistant operator, I can spawn a background customer-assistant sub-agent only for sessions in my tenant, and the resulting run leaves enough sanitized host-context audit evidence to explain who triggered it.

## Functional Requirements

- `POST /api/v1/customer-assistant/harness/spawn-sub-agent` must enforce the same tenant ownership check as normal customer-assistant session operations.
- A host user with `customer_assistant:operate` in tenant B must not spawn a sub-agent against a tenant A session.
- The foreground spawn request and the background sub-agent execution must use the same `RequestContext`.
- Background sub-agent execution must append sanitized host-context audit evidence without leaking raw secrets.
- Local development requests without host headers continue to work unchanged.

## Non-Goals

- New customer-assistant frontend controls.
- New external channel delivery or real agent orchestration beyond the existing harness endpoint.
- Changing worker scheduling, ReAct logic, proposed-action semantics, or seed story data.

## Acceptance Criteria

- RED evidence proves cross-tenant spawn was incorrectly accepted before the fix.
- Integration evidence proves cross-tenant spawn now returns a 403 envelope.
- Integration evidence proves same-tenant background sub-agent execution records host-context audit data.
- Focused customer-assistant regressions pass.
- Ruff passes for touched Python files.

## Evidence

Evidence lives under `artifacts/slices/116-customer-assistant-spawn-tenant-access/`.

- RED: `red.txt`
- Focused integration: `integration.txt`
- Customer-assistant API regression: `customer-assistant-regression.txt`
- Ruff: `ruff.txt`
