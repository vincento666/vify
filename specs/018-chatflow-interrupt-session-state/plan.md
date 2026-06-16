# Plan 018: Chatflow Interrupt And Session State

## Architecture

- Add a Chatflow runtime profile layer over the existing workflow executor.
- Introduce a checkpoint store interface:
  - database implementation for MVP.
  - Redis-compatible interface for later scale.
- Add event emission to executor boundaries instead of hiding message/interrupt behavior inside UI code.
- Keep single-flow resume state inside one run/session.
- Keep cross-flow Task Stack explicitly out of scope.

## Backend Notes

- Add repository methods for sessions, events, checkpoints, and variable scopes.
- Extend existing run service to:
  - start a session.
  - emit events.
  - pause with checkpoint.
  - resume from checkpoint.
  - complete or fail with event trail.
- Implement variable resolver with ordered scopes.
- Add bounded history reader that consumes session events and persisted chat records.
- Add idempotency handling for resume.

## Frontend Notes

- Extend Chatflow run panel with waiting-state UI.
- Add resume form generated from interrupt schema.
- Show event timeline in bottom debug dock.
- Show scoped variables before and after resume.
- Keep single-node test behavior separate from full session run behavior.

## Data Notes

- Persist enough checkpoint data to continue safely:
  - current node.
  - edge state.
  - context variables.
  - pending interrupt schema.
- Do not persist provider secrets or raw credential material.
- Sanitize user-upload metadata before logging.

## Slice Order

018.1 -> 018.2 -> 018.3 -> 018.4 -> 018.5
