# 153 Runtime Lab SOP v2 Raw Event Debug Trace

## User Story

As an operator demoing a Runtime Lab SOP conversation, I need each Chatflow SOP task trace to expose durable Runtime v2 refs and raw event context so the browser/debug panel can jump from the business task to the exact runtime event stream.

## Acceptance Criteria

1. Runtime Lab `/api/v1/runtime-lab/sessions/{sessionId}/chatflow-trace` includes Runtime v2 raw refs for every bound Chatflow task:
   - `statusRef`
   - `eventsRef`
   - `eventStreamRef`
   - `nodesRef`
   - `resultRef`
2. The exposed `eventsRef` can be fetched by tests without URL reconstruction.
3. Raw Runtime v2 events for the SOP task retain `callerContext` containing:
   - `source=runtime-lab`
   - `sop_key`
   - `session_id`
   - `task_id`
4. Waiting and resumed lifecycle events both retain the same caller context.
5. MySQL8 remains the only supported persistence target for this gate.

## Out Of Scope

- New UI panels.
- New Runtime v2 node semantics.
- SQLite compatibility or fallback.
