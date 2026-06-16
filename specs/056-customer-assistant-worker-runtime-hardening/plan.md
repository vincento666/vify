# Plan 056: Customer Assistant Worker Runtime Hardening

## Runtime Design

Introduce a minimal worker run abstraction inside customer assistant before
generalizing to Workflow/Chatflow:

```text
customer_assistant_worker_run
customer_assistant_worker_event
```

If adding tables is too heavy for the first slice, store worker run refs in the
existing event/task payloads and create an ADR explaining the limitation.

## Timeout Strategy

MVP options:

- cooperative timeout for fake/test workers;
- thread-pool timeout with non-blocking scheduler return;
- process-isolated timeout for hard kill where feasible.

The selected strategy must be explicit. It must not pretend a thread timeout is
a hard cancellation if the thread can keep running.

## Compatibility

Existing `LocalWorkerScheduler.run()` can remain as a wrapper, but it must call
the new worker run manager internally when hardening mode is enabled.

## Browser UAT

Expose timeout/cancel state in the operator panel event timeline and task
ledger, even if the control button is backend-only in the first MVP.
