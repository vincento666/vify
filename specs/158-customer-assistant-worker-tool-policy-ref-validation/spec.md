# Spec 158: Customer Assistant Worker Tool Policy Ref Validation

## Status

Slice 158.1 complete.

## Goal

Make worker/skill configuration safer by rejecting unknown `toolPolicyRef`
values instead of silently falling back to the default ReAct tool policy.
Productized MVP demos need configuration errors to be visible at save time or
worker startup time, not hidden behind permissive behavior.

## Functional Requirements

- Define the supported customer-assistant tool policy refs in one domain module.
- Reject unsupported `toolPolicyRef` values during worker profile update.
- Reject unsupported ReAct tool policies during runtime policy resolution.
- Preserve existing supported refs:
  `customer_assistant_worker_tool_default`, `customer_assistant_react_default`,
  `strict-read-before-write`, `manual_confirm_lookup_tools`,
  `refund_policy_tools`, and `read_only_knowledge_tools`.
- Keep `manual_confirm_lookup_tools` behavior unchanged.

## Non-Goals

- Do not add database schema.
- Do not add frontend UI.
- Do not validate model or prompt refs yet; those still require a provider/prompt
  registry slice.

## Acceptance Criteria

- RED unit test proves unknown ReAct `toolPolicyRef` currently falls back.
- RED MySQL8 integration test proves profile update currently accepts unknown
  `toolPolicyRef`.
- Focused unit and integration tests pass after validation is implemented.
- Focused ruff passes for touched backend files.

## Evidence

Evidence lives under
`artifacts/slices/158-customer-assistant-worker-tool-policy-ref-validation/158.1/`.

- RED unit: `red-unit.txt`
- RED integration: `red-integration.txt`
- Unit: `unit.txt`
- Integration: `integration.txt`
- Contract: `contract.txt`
- Ruff: `ruff.txt`
