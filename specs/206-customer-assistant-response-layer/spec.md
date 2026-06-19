# Spec 206: Customer Assistant Response Summary

## Goal

Add a Phase 8 response summary layer to the customer assistant message gateway.

The customer assistant stays conversation-first while exposing run summary
metadata and simplified events for customer/operator surfaces.

## In Scope

- Add `latencyMs`, `usage`, `retryable`, `eventSummary`, and `runSummary` to
  customer assistant message responses.
- Keep existing `events` and ledger refs for compatibility during migration.
- Ensure summary events omit raw payloads.

## Out of Scope

- Async worker runtime changes.
- Removing legacy inline events.
- Customer assistant visual redesign.

## Acceptance Criteria

- `POST /api/v1/customer-assistant/messages` returns summary metadata and
  payload-free `eventSummary`.
- `eventsRef` remains available for the full event ledger.
- Existing session reuse and idempotency behavior remains compatible.
