# Spec 177: Customer Assistant Worker Risk Policy Ref Validation

## Status

Slice 177.1 complete.

## Goal

Make worker/skill risk configuration explicit by rejecting unknown
`riskPolicyRef` values before they are persisted. The MVP demo must not silently
accept a misspelled risk strategy and then show misleading safety metadata to
operators.

## Functional Requirements

- Define supported customer-assistant risk policy refs in one domain module.
- Reject unsupported `riskPolicyRef` values during worker profile update.
- Preserve existing supported refs: `manual_confirm`,
  `manual_confirm_high_risk`, and `read_only`.
- Keep existing blank-reference validation and worker routing behavior.

## Non-Goals

- Do not add a risk-policy admin UI.
- Do not change ReAct high-risk tool semantics in this slice.
- Do not validate model, prompt, or output schema refs yet.

## Acceptance Criteria

- RED MySQL8 integration test proves profile update currently accepts an
  unknown `riskPolicyRef`.
- Focused MySQL8 worker-profile integration tests pass after validation.
- Focused ruff passes for touched backend files.

## Evidence

Evidence lives under
`artifacts/slices/177-customer-assistant-worker-risk-policy-ref-validation/177.1/`.

- RED integration: `red-integration.txt`
- Integration: `integration.txt`
- Ruff: `ruff.txt`
