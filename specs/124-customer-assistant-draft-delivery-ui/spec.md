# Feature Spec: Customer Assistant Draft Delivery UI

## Status

Complete.

## User Story

As a customer-service operator, after I review and confirm a customer reply
draft, I can send it through the MVP draft-delivery outbox from the workbench
and see delivery/audit evidence without leaving the session.

## Functional Requirements

- The frontend API client exposes
  `POST /api/v1/customer-assistant/proposed-actions/{actionId}/deliver`.
- The runtime state layer can deliver a confirmed `send_customer_message`
  action and refresh task, event, proposed-action, metrics, and audit ledgers.
- The proposed-action panel shows an operator-only delivery button only for
  confirmed customer-reply draft actions.
- The delivery button must not replace confirm/reject/modify semantics.
- Sent/failed delivery results must show a compact receipt on the action row.

## Non-Goals

- New backend delivery semantics; slice 118 owns the mock outbox.
- Real external channel delivery.
- Changing proposed-action confirmation safety rules.
- Large redesign of the workbench action panel.

## Acceptance Criteria

- RED API/runtime/panel tests fail before the UI/API/runtime path exists.
- Focused frontend/rem gates pass.
- Full frontend unit/build pass when integrated.
- Browser UAT confirms a seeded/created draft action can be confirmed,
  delivered, and the event/audit timeline shows `draft_delivery_sent`.

## Evidence

Evidence lives under
`artifacts/slices/124-customer-assistant-draft-delivery-ui/124.1/`.

- RED: `red.txt`
- Focused frontend/rem: `frontend-rem.txt`
- Full frontend unit: `frontend-full.txt`
- Frontend build: `frontend-build.txt`
- Browser UAT: `browser-uat.txt`, `uat-report.json`, `uat.md`
- Screenshot: `screenshots/draft-delivery-ui.png`
