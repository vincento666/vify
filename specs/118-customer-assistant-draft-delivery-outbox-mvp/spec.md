# Feature Spec: Customer Assistant Draft Delivery Outbox MVP

## Status

Slice 118.1 complete.

## User Story

As a customer-assistant operator, after approving a customer-facing reply draft I can send it through a local mock outbox and see the delivery status in the same proposed-action, event, and operator-audit surfaces already used for assistant actions.

## Functional Requirements

- Add a backend-only endpoint:

```text
POST /api/v1/customer-assistant/proposed-actions/{actionId}/deliver
```

- Delivery requires an existing proposed action in `CONFIRMED` status.
- The action must represent a customer reply draft, using `send_customer_message` for this MVP.
- The endpoint sends only through a local/mock channel adapter. No external provider, webhook, or real channel API may be called.
- A successful mock send transitions the action through a delivery-in-progress state and then persists `SENT`.
- A mock adapter failure persists `FAILED` with a redacted error/result payload.
- Returned action data, session events, proposed-action list, and operator audit rows must not expose raw phone numbers, order numbers, or secret/token values.
- Delivery events must be visible through `GET /sessions/{sessionId}/events` and summarized through `GET /sessions/{sessionId}/operator-audit`.

## Non-Goals

- Frontend controls for delivery.
- Real omnichannel inbox delivery, provider credentials, retries, queues, or webhooks.
- New database tables or a durable external outbox.
- Changing existing `/execute` proposed-action behavior.
- Touching workflow or frontend customer-assistant files.

## Acceptance Criteria

- RED integration evidence proves the draft delivery endpoint is missing before implementation.
- Focused integration proves approved draft delivery persists and returns `SENT`.
- Focused integration proves mock adapter failure persists and returns `FAILED`.
- Focused integration proves action, event, and operator-audit surfaces redact sensitive payloads.
- Ruff passes for touched backend Python files.
- Browser UAT is documented as deferred because this slice adds no UI.

## Evidence

Evidence lives under `artifacts/slices/118-customer-assistant-draft-delivery-outbox-mvp/118.1/`.

- RED: `red.txt`
- Focused integration: `integration.txt`
- Customer-assistant backend regression: `customer-assistant-regression.txt`
- Ruff: `ruff.txt`
- Browser UAT note: `uat.md`
