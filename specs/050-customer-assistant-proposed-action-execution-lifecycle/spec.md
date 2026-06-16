# Spec 050: Customer Assistant Proposed Action Execution Lifecycle

## Goal

Extend proposed actions from confirm/reject records into an auditable execution
lifecycle backed by simulation-semantic mock executors.

050 still does not perform real high-risk external writes.

## Dependency

050 depends on:

- 045 proposed-action persistence;
- 046 operator controls;
- 048 live event streaming.

## Lifecycle

Required statuses:

```text
PENDING
CONFIRMED
REJECTED
EXECUTING
EXECUTED
FAILED
```

050 should preserve existing confirm/reject behavior and add execution after
approval. The preferred MVP API is:

```text
POST /api/v1/customer-assistant/proposed-actions/{actionId}/execute
```

Execution requires status `CONFIRMED`.

## Mock Executor Boundary

Executors are mock implementations with real business semantics:

- realistic success/failure codes;
- realistic latency;
- audit payload;
- idempotent execution key;
- no external side effects.

Example executor refs:

```text
refund_submit_mock
ticket_change_mock
send_customer_message_mock
```

## MVP Scope Guard

050 is an action-lifecycle MVP. It adds auditable confirmation and
simulation-semantic execution after operator approval. It must not call real
external write APIs, block the original assistant run waiting for approval, or
introduce a generic human-in-the-loop runtime.

## Acceptance Criteria

- Confirmed action can be executed through the mock executor.
- Pending action cannot execute before confirmation.
- Rejected action cannot execute.
- Execution records audit metadata and status transitions.
- Execution failure records `FAILED` and error details.
- SSE emits proposed-action lifecycle events.
- No real external write API is called.
