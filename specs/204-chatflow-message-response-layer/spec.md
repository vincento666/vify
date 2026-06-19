# Spec 204: Chatflow Message Response Summary

## Goal

Bring the Chatflow `messages` gateway response into the Phase 8 external API
summary layer.

This keeps the session/message-first contract while adding the same production
metadata exposed by runtime results.

## In Scope

- Add `result`, `latencyMs`, `usage`, `retryable`, and simplified `events` to
  Chatflow message responses.
- Reuse the runtime result projection produced for each message turn.
- Preserve existing compatibility fields while downstream consumers migrate.

## Out of Scope

- Removing legacy debug refs from Chatflow responses.
- Customer assistant response cleanup.
- Frontend wording and canvas UI convergence.

## Acceptance Criteria

- `POST /api/v1/chatflows/{id}/messages` returns `sessionId`, `conversationId`,
  `runId`, `status`, `answer`, `result`, `latencyMs`, `usage`, `retryable`,
  simplified `events`, and runtime refs.
- Simplified response events do not contain raw event payloads.
- Existing idempotency and no-wait behavior remains compatible.
