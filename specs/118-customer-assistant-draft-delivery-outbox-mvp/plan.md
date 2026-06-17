# Plan: Customer Assistant Draft Delivery Outbox MVP

## Slice 118.1

Add the backend-only local/mock outbox boundary for approved customer reply drafts.

## Approach

1. Add integration tests that seed confirmed `send_customer_message` proposed actions and call the new delivery endpoint.
2. Keep persistence on the existing proposed-action row by using `status` and `result_json`; avoid schema work.
3. Add a minimal mock channel adapter in the customer-assistant backend domain.
4. Add a service method that atomically claims a `CONFIRMED` draft for delivery, invokes the mock adapter, persists `SENT` or `FAILED`, and appends redacted lifecycle events.
5. Add the FastAPI route and request schema only if the endpoint needs a body. For 118.1, the approved action payload is the source of delivery input.
6. Extend operator-audit whitelist summaries for delivery events.
7. Run the focused integration test and ruff, then save evidence.

## Test Strategy

- Focused integration: `tests/integration/customer_assistant/test_draft_delivery_outbox.py`.
- The success path checks endpoint response, proposed-action list, event list, and operator audit.
- The failure path uses a local mock payload flag and checks `FAILED` persistence.
- Redaction checks serialize all returned surfaces and assert raw phone/order/token values are absent.

## Browser UAT

Deferred to a later UI slice. This slice is backend-only and adds no visible control.

## Risks

- Existing action status metrics are string-count based, so adding `SENT` is additive.
- Existing operator audit is whitelist-based; delivery event types must be added explicitly or the audit surface will silently omit them.
- The MVP must stay local/mock-only and not reuse workflow channel delivery code.
