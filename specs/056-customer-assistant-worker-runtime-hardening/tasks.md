# Tasks 056: Customer Assistant Worker Runtime Hardening

## 056.0 Sign-off

- [x] Confirm 056 is customer-assistant worker hardening, not Workflow/Chatflow
      runtime v2.
- [x] Confirm worker async refs are customer-assistant scoped and only serve as
      a reference contract for later Workflow/Chatflow runtime v2.
- [x] Confirm cancellation can be cooperative in MVP if hard kill is documented.
- [x] Confirm no WebSocket/Redis dependency.

## 056.1 Worker Run Contract

- [x] RED: contract test fails because `workerAsyncRefs.supported` is false.
- [x] Add worker run identity and refs for one worker path.
- [x] Keep worker run storage customer-assistant scoped, or document payload-only
      refs as an MVP limitation.
- [x] Return refs through 052 sub-agent result payload.

## 056.2 Hard Timeout

- [x] RED: blocked worker test proves current scheduler waits too long.
- [x] Add timeout behavior that returns control within configured wall-clock
      limit.
- [x] Emit `worker_timeout_started` and `worker_timed_out` events.

## 056.3 Cancellation

- [x] RED: cancel endpoint/status test fails.
- [x] Add cancel endpoint or service method.
- [x] Emit `worker_cancel_requested` and `worker_cancelled` or
      `worker_cancel_unsupported` events.

## 056.4 UI Evidence

- [x] Show timeout/cancel state in task ledger or event timeline.
- [x] Run frontend focused tests, rem gate, and build.

## 056.5 Gates

- [x] Run backend customer-assistant gates.
- [x] Run Browser UAT with a timeout fixture.
