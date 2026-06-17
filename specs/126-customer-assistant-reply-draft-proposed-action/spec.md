# Feature Spec: Customer Assistant Reply Draft Proposed Action

## Status

Complete.

## User Story

As a customer-service operator, when the assistant produces a customer reply
draft during a normal customer turn, I receive a pending, auditable
`send_customer_message` proposed action that I can confirm and deliver from the
workbench.

## Functional Requirements

- Normal customer-assistant turns that produce a non-empty customer reply draft
  create a `send_customer_message` proposed action.
- The proposed action remains `PENDING` until an operator confirms it.
- The proposed action payload includes the draft, channel, conversation/session
  reference, recipient context when available, and run metadata.
- The action must be idempotent per run and must not duplicate on replay.
- The action must use existing sanitization on API/event/audit surfaces.
- Confirming and delivering the generated action uses the existing draft
  delivery outbox and records `draft_delivery_sent`.

## Non-Goals

- Real external delivery channels.
- Replacing the delivery outbox core from slice 118.
- Frontend changes; slice 124 already exposes the operator control.
- Removing `stub_qa` naming; slice 127 owns demo/default worker destubbing.

## Acceptance Criteria

- RED public API test fails because normal turns do not yet generate
  `send_customer_message`.
- Focused contract/integration tests pass after implementation.
- Browser UAT is not required for this backend-only bridge because slice 124
  already verifies the UI confirm/deliver flow and this slice verifies the same
  generated action through public API.

## Evidence

Evidence lives under
`artifacts/slices/126-customer-assistant-reply-draft-proposed-action/126.1/`.

- RED: `red.txt`
- Focused backend: `backend-focused.txt`
- Contract: `contract.txt`
- Expanded backend gate: `backend-focused-expanded.txt`
- Adapter/two-stage compatibility: `adapter-two-stage.txt`
- Ruff: `ruff.txt`
- Full customer-assistant integration probe: `integration-customer-assistant.txt`
  remains red only from the known temporary SQLite fixture-order leak
  (`unable to open database file`) after the focused 126/127 gates pass.
- Docs: this spec, `plan.md`, and `tasks.md`
