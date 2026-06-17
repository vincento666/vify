# Feature Spec: Customer Assistant ReAct Tool Policy Runtime Gate

## Status

Complete.

## User Story

As an operator configuring customer-assistant workers, when I set a ReAct worker
profile `toolPolicyRef`, the runtime enforces that tool policy instead of only
showing it as evidence.

## Functional Requirements

- Resolve configured ReAct worker `toolPolicyRef` into an in-process runtime
  policy.
- Continue using `toolRefs` as the allowed tool allowlist.
- Add a built-in `manual_confirm_lookup_tools` policy that requires manual
  confirmation for `lookup_order`, even though it is otherwise a read tool.
- A manually confirmed tool call must return a `WAITING` worker result with a
  pending proposed action and must not execute the underlying tool.
- Unknown policy refs keep the current default behavior for compatibility.

## Non-Goals

- No database schema changes.
- No frontend changes.
- No proposed-action execution implementation for manually confirmed read
  tools.
- No new external provider or network dependency.

## Acceptance Criteria

- RED unit test fails before implementation because `lookup_order` executes
  directly under `manual_confirm_lookup_tools`.
- RED integration test fails before implementation because a patched worker
  profile with `toolPolicyRef=manual_confirm_lookup_tools` completes instead of
  waiting for proposed action confirmation.
- Focused unit and integration tests pass after implementation.
- The default `strict-read-before-write` and unknown refs remain compatible with
  existing green tests.
- Focused ruff passes for the touched backend domain and test files.

## Evidence

Evidence lives under
`artifacts/slices/150-customer-assistant-react-tool-policy-runtime-gate/150.1/`.

- RED unit: `red-unit.txt`
- RED integration: `red-integration.txt`
- Focused unit: `unit.txt`
- Focused integration: `integration.txt`
- Focused ruff: `ruff.txt`
