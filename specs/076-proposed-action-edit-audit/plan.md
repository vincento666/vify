# 076 Plan

## 076.1 Backend Modify API And Audit

- Add a request schema for proposed-action patch input.
- Add repository update support for title and payload JSON.
- Add service guard: only `PENDING` actions can be modified.
- Add audit event `proposed_action_modified` with changed field names.
- Expose `PATCH /api/v1/customer-assistant/proposed-actions/{id}`.

TDD seams:

- RED integration test: patch endpoint is missing.
- RED integration test: confirmed action modification is rejected.
- GREEN implementation with focused service/repository/router changes.

## 076.2 Workbench Modify Flow

- Add frontend API/runtime helper for proposed-action patch.
- Render edit controls for pending actions only.
- Save modified title/payload into local state and keep confirm/reject/execute
  buttons intact.
- Extend browser UAT to modify a pending action before confirming it.

## Gates

Each slice saves RED, unit/integration, browser UAT when frontend-visible,
docs evidence, and commits independently.
