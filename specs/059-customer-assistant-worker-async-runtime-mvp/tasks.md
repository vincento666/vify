# Tasks 059: Customer Assistant Worker Async Runtime MVP

## 059.0 Sign-off

- [x] Confirm 059 targets one customer-assistant worker path only.
- [x] Confirm worker async refs must point to a real worker run.
- [x] Confirm ChatflowSopWorker remains legacy in this slice.
- [x] Confirm cancellation semantics are cooperative or explicitly unsupported.
- [x] Confirm worker creation is idempotent and cannot duplicate a run on retry.
- [x] Confirm background runners do not reuse request-scoped DB sessions.
- [x] Confirm worker event payloads are redacted.

## 059.1 Worker Run Contract

- [x] RED: contract test fails because worker status/result/event refs are not
      fetchable.
- [x] Add worker run identity and status model.
- [x] Add worker event persistence and sequence ordering.
- [x] Add idempotency key or request hash for worker creation.
- [x] Add monotonic terminal status transition guard.
- [x] Add status/result/events API or equivalent service contract.

## 059.2 First Worker Path

- [x] RED: selected worker cannot run through async worker runtime.
- [x] Connect one low-risk worker to the worker runtime.
- [x] Preserve existing `WorkerResult` compatibility.
- [x] Return real worker refs through customer-assistant payloads.

## 059.3 Timeout And Cancel

- [x] RED: timeout/cancel events are missing from the worker event stream.
- [x] Emit durable timeout events.
- [x] Add cancellation request path.
- [x] Emit `worker_cancelled` or `worker_cancel_unsupported`.

## 059.4 Runner Recovery

- [x] RED: background runner fails when the request DB session is closed.
- [x] Ensure worker runner opens an independent session/unit of work.
- [x] RED: retrying the same worker request creates duplicate worker runs.
- [x] Deduplicate worker creation by stable idempotency key.
- [x] Add restart/recovery behavior or explicit interrupted-run failure event.

## 059.5 Gates

- [x] Run focused customer-assistant backend tests.
- [x] Run existing harness sub-agent contract tests.
- [x] Save evidence under `artifacts/slices/059-customer-assistant-worker-async-runtime-mvp/`.

Evidence:

- RED: `artifacts/slices/059-customer-assistant-worker-async-runtime-mvp/red.txt`
- Unit: `artifacts/slices/059-customer-assistant-worker-async-runtime-mvp/unit.txt`
- Integration: `artifacts/slices/059-customer-assistant-worker-async-runtime-mvp/integration.txt`
- Contract: `artifacts/slices/059-customer-assistant-worker-async-runtime-mvp/contract.txt`
- E2E: `artifacts/slices/059-customer-assistant-worker-async-runtime-mvp/e2e.txt`
- Browser UAT: `artifacts/slices/059-customer-assistant-worker-async-runtime-mvp/uat.md`
