# Tasks

## 198.1 Backend Message Gateway

- [x] RED: message API auto-creates and reuses sessions.
- [x] RED: projected events include `message.delta`, `message.completed`,
      `requires_input`, and `run.completed`.
- [x] GREEN: add backend schema, routes, service projection, and refs.
- [x] GREEN: idempotent replay does not append duplicate projection events.
- [x] GREEN: expose SOP-backed Chatflow `chatflowSession` and `recovery` refs.
- [x] Gate: focused customer-assistant contract tests.
- [x] Gate: related customer-assistant e2e SSE test.
- [x] Evidence: save RED/GREEN/gate output under
      `artifacts/slices/198-customer-assistant-session-message-gateway/198.1/`.

## 198.2 Frontend/UAT

- [x] Prefer the new message helper where safe.
- [x] Verify remScaleClosure and full frontend unit tests.
- [x] Browser UAT with first message, second message, and afterSequence recovery.
- [x] Evidence: save UAT notes and screenshot under
      `artifacts/slices/198-customer-assistant-session-message-gateway/198.1/`.
