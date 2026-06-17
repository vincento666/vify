# 143 Customer Assistant Proposed Action Decision Notes

## Status

Complete.

## Goal

Human confirmation decisions must carry an operator-facing decision note through
the proposed action, event ledger, and operator audit trail. Confirmation can
include an approval note, rejection can include a rejection reason, and all
public surfaces must redact phone numbers, order numbers, and secret-looking
tokens.

## Acceptance Criteria

- `POST /api/v1/customer-assistant/proposed-actions/{id}/confirm` accepts an
  optional JSON body with `note`.
- `POST /api/v1/customer-assistant/proposed-actions/{id}/reject` accepts an
  optional JSON body with `reason` or `note`.
- Existing no-body confirm/reject calls remain compatible.
- The action response `result.decision` contains the sanitized note/reason when
  one is supplied.
- `proposed_action_confirmed`, `proposed_task_command_confirmed`, and
  `proposed_action_rejected` events include sanitized decision metadata.
- Operator audit summaries include the sanitized approval note or rejection
  reason and do not leak raw phone/order/token values.
- Frontend API/runtime helpers can pass optional decision payloads without
  changing the visual UI in this slice.
- MySQL8-backed focused tests, contract/regression gates, and browser API UAT
  pass.

## Non-Goals

- Adding visible note/reason input controls to the agent panel.
- Changing database schema.
- Changing execute/deliver semantics.

## Evidence

Evidence lives under
`artifacts/slices/143-customer-assistant-proposed-action-decision-notes/143.1/`.

- RED backend: `red-backend.txt`
- RED frontend API: `red-frontend-api.txt`
- RED frontend runtime: `red-frontend-runtime.txt`
- Focused backend green: `focused-backend-green.txt`
- Frontend API green: `frontend-api-green.txt`
- Frontend runtime green: `frontend-runtime-green.txt`
- Frontend full unit/rem green: `frontend-unit.txt`
- Frontend build: `frontend-build.txt`
- Customer-assistant regression final green:
  `customer-assistant-regression-green.txt`
- Load-sensitive worker threshold rerun: `flaky-worker-rerun.txt`
- Browser UAT: `browser-uat.txt`
- Browser screenshot: `screenshots/decision-notes.png`
- Ruff: `ruff.txt`
- Secret/SQLite scan: `secret-sqlite-scan.txt`
