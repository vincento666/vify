# Spec 198: Customer Assistant Session Message Gateway

## Goal

Connect the customer-assistant entrypoint to the production Chatflow/SOP
session-message contract without removing the existing turn API.

This slice covers Phase 5 of `docs/chatflow-workflow-production-upgrade.md`:
customer assistant sends messages through a session-first model, exposes
conversation/run refs, streams the unified external event names, and supports
`sessionId + afterSequence` recovery.

## In Scope

- Add a message-first customer-assistant API:
  - `POST /api/v1/customer-assistant/messages`
  - `POST /api/v1/customer-assistant/sessions/{sessionId}/messages`
- Omitted `sessionId` creates a customer-assistant session.
- Existing `sessionId` reuses that session.
- Idempotency remains scoped to the customer-assistant session and request hash.
- Responses expose:
  - `sessionId`
  - `conversationId`
  - `runId`
  - `status`
  - `answer`
  - `requiresInput`
  - `eventsRef`
  - `eventStreamRef`
  - `chatflowSession` when a SOP worker is backed by Chatflow runtime
  - `recovery` with the customer-assistant `afterSequence` cursor
- Persist customer-facing event projections:
  - `message.delta`
  - `message.completed`
  - `requires_input`
  - `handoff_requested`
  - `run.completed`
  - `run.failed`
- Existing `/sessions/{sessionId}/events/stream?afterSequence=` remains the
  recovery channel.

## Out of Scope

- Durable worker replacement.
- New frontend visual redesign.
- Replacing all existing `/turns` callers in this slice.
- Creating specs for gate-only cleanup or unrelated failing tests.

## Acceptance Criteria

- A client can call `/customer-assistant/messages` without `sessionId` and get a
  session plus message-style response.
- A client can call `/sessions/{sessionId}/messages` and continue the same
  session.
- Replaying the same idempotency key on the same session returns the same run
  without duplicate projection events.
- Session events and SSE recovery expose the unified event names needed by the
  customer-assistant UI.
- SOP-backed turns expose stable Chatflow session/runtime refs so customer
  assistant debugging can correlate the business session with the Chatflow run.
