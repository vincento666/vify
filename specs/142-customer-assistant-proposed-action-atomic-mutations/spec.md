# 142 Customer Assistant Proposed Action Atomic Mutations

## Status

Complete.

## Goal

Human confirmation mutations must claim pending proposed actions atomically.
Confirm, reject, and modify flows must not overwrite a concurrent terminal
decision or append duplicate audit events after the pending claim is stale.

## Acceptance Criteria

- Confirm uses an atomic `PENDING -> CONFIRMED` claim before appending audit
  events.
- Reject uses an atomic `PENDING -> REJECTED` claim before appending audit
  events.
- Modify updates title/payload only while the row is still `PENDING`; stale
  claims fail with the same product error as non-pending edits.
- A stale claim does not append `proposed_action_confirmed`,
  `proposed_action_rejected`, or `proposed_action_modified`.
- Existing execute/deliver atomic transitions keep working.
- MySQL8-backed integration/contract/customer-assistant regression gates pass.

## Non-Goals

- Adding reject reasons or approval notes.
- Changing frontend visual layout.
- Adding database migrations.

## Evidence

Evidence lives under
`artifacts/slices/142-customer-assistant-proposed-action-atomic-mutations/142.1/`.

- RED ordinary stale claims: `red.txt`
- RED task-command stale claim: `task-command-red.txt`
- Focused green: `focused-green-2.txt`
- Integration green: `integration-green-2.txt`
- Contract green: `contract-green.txt`
- Customer-assistant regression: `customer-assistant-regression.txt`
- Browser UAT: `browser-uat.txt`
- Browser screenshot: `screenshots/atomic-mutations.png`
- Ruff: `ruff-2.txt`
