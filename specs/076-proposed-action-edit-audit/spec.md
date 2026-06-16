# 076 Proposed Action Edit Audit

## Goal

Complete the customer-assistant human confirmation loop by allowing operators to
modify a pending proposed action before confirmation, while preserving an audit
event and preventing edits after confirm/reject/execute.

## Acceptance Criteria

- Pending proposed actions can be patched through the API with revised title
  and payload.
- Non-pending proposed actions cannot be modified.
- Modification writes an auditable `proposed_action_modified` event containing
  the action id/type and changed fields without leaking secrets.
- The workbench exposes a compact edit flow for pending actions, refreshes local
  action state after save, and keeps confirm/reject/execute semantics unchanged.
- Browser UAT proves modify -> confirm -> execute remains a visible operator
  loop.

## Slices

### 076.1 Backend Modify API And Audit

Add repository/service/router support for patching pending proposed actions and
persisting audit events.

### 076.2 Workbench Modify Flow

Add frontend API/runtime helpers, an edit affordance in the pending-action
panel, and browser UAT.

## Evidence

Evidence lives under
`artifacts/slices/076-proposed-action-edit-audit/<slice>/`.

## Non-goals

- Rich field-by-field forms for every action type are not required; the MVP edit
  affordance may use compact JSON payload editing.
- Bulk edits and approval chains are deferred.
