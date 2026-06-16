# Feature Spec: Customer Assistant Action Ledger Refresh

## Status

Complete.

## User Story

As a customer-assistant operator, after I modify, confirm, reject, or execute a proposed action, I immediately see the server-side writeback, refreshed event timeline, refreshed proposed-action ledger, metrics, and operator audit without needing a manual page refresh.

## Functional Requirements

- Proposed-action mutation flows must refresh the full customer-assistant ledgers after the mutation succeeds.
- The refreshed ledgers must include tasks, events, proposed actions, session metrics, and operator audit.
- Existing task-command confirmation behavior must remain unchanged while sharing the same refresh path.
- The UI must keep the locally returned action status visible while replacing stale ledgers with server state.
- The change must stay inside the customer assistant frontend runtime lane.

## Non-Goals

- Adding or changing backend proposed-action APIs.
- Changing Runtime Lab, workflow runtime, seed data, or live LLM acceptance gates.
- Changing visual layout, spacing, or CSS.

## Acceptance Criteria

- RED frontend runtime test proves reject/execute/edit currently do not reload action/event ledgers after mutation.
- Focused frontend runtime tests pass after implementation.
- Existing customer assistant interaction/view-model tests remain green for action controls.
- Browser UAT verifies a confirmed/executed proposed action refreshes the operator audit and writeback rows in the product workbench.

## Evidence

Evidence lives under `artifacts/slices/108-customer-assistant-action-ledger-refresh/108.1/`.

- RED: `red.txt`
- Focused frontend unit: `frontend-runtime.txt`
- Customer assistant frontend regressions: `frontend-customer-assistant.txt`
- Browser UAT: `uat.md`
- Screenshot: `screenshots/action-ledger-refresh.png`
