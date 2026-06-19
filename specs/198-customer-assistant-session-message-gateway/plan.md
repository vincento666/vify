# Plan

## Slice 198.1 Backend Message Gateway

1. Add contract RED tests for message-first customer-assistant API and event
   projections.
2. Add a schema for optional `sessionId` message requests.
3. Add service method that creates or reuses a session, delegates to the existing
   turn runtime, and projects the result into external message semantics.
4. Persist projection events only for non-replayed turns.
5. Project SOP-backed Chatflow session/runtime refs into `chatflowSession` and
   `recovery`.
6. Keep `/sessions/{sessionId}/turns` unchanged for compatibility.
7. Run focused customer-assistant contract/e2e gates and shared frontend
   rem/unit gates.

## Slice 198.2 Frontend/UAT

1. Prefer the new message API in customer-assistant API helpers.
2. Verify existing event stream client recovers by `afterSequence`.
3. Add browser UAT that sends a first message, reuses the session, and resumes
   the stream after a stored sequence.

## Risks

- Existing async worker runtime files are dirty. This slice must work with those
  changes and avoid rewriting worker scheduling internals.
- Some event names are projections over existing worker/run events; they are not
  a durable-worker replacement.
