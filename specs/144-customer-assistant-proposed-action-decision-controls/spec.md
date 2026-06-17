# 144 Customer Assistant Proposed Action Decision Controls

## Status

Complete.

## Goal

The operator workbench must expose product-facing decision inputs for pending
proposed actions. Operators can enter a confirmation note before confirming an
action, or a rejection reason before rejecting it, and the panel sends those
values through the decision-note API/audit path from slice 143.

## Acceptance Criteria

- Pending proposed action rows show compact Ant Design inputs for confirmation
  note and rejection reason.
- The inputs live only in the operator proposed-action panel, not the customer
  conversation lane.
- Confirm sends `{ note }` when the confirmation note is non-empty.
- Reject sends `{ reason }` when the rejection reason is non-empty.
- Empty inputs preserve the existing no-body confirm/reject behavior.
- Decision drafts clear after a successful confirm/reject.
- No bare `px` visual dimensions are introduced.
- Frontend unit/rem, build, and real browser UAT pass.

## Non-Goals

- Changing backend API semantics.
- Adding modal confirmation flows.
- Reworking proposed action edit controls.

## Evidence

Evidence lives under
`artifacts/slices/144-customer-assistant-proposed-action-decision-controls/144.1/`.

- RED panel contract: `red-panel.txt`
- RED interaction contract: `red-interactions.txt`
- Panel green: `panel-green.txt`
- Interaction green: `interactions-green.txt`
- API/runtime green: `api-runtime-green.txt`
- Rem gate: `rem-green.txt`
- Full frontend unit: `frontend-unit.txt`
- Frontend build: `frontend-build.txt`
- Browser UAT: `browser-uat.txt`
- Browser screenshot: `screenshots/decision-controls.png`
- Rem scan: `rem-scan.txt`
- Secret/SQLite scan: `secret-sqlite-scan.txt`
