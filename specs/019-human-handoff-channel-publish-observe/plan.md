# Plan 019: Human Handoff, Channels, Publish, And Observe

## Architecture

- Add `TRANSFER_TO_HUMAN` as a Chatflow-only node executor and event producer.
- Add handoff service with ticket lifecycle independent from the workflow executor.
- Add channel adapter interface:
  - API adapter.
  - Web adapter.
  - disabled third-party adapter shells until implemented.
- Add versioned publish service for Workflow and Chatflow.
- Add observe query service over runs, node runs, events, resource calls, sessions, and handoff tickets.

## Backend Notes

- Handoff ticket creation must be transactional with session status update.
- Closing or returning a handoff can optionally resume a paused Chatflow through 018 resume APIs.
- Publish creates immutable graph snapshots and active version pointers.
- Channel invocation always resolves a published version, not mutable draft graph.
- Observe APIs must sanitize inputs/outputs and support pagination.

## Frontend Notes

- Extend Chatflow palette with `转人工` only when executor is available.
- Add publish validation modal and channel assignment UI.
- Add observe route or tab with:
  - run list.
  - session list.
  - trace detail.
  - handoff ticket detail.
  - aggregate metric tiles.
- Keep operational UI dense and scannable, not a marketing dashboard.

## Data Notes

- Add publish version tables or equivalent persistence.
- Add handoff ticket table.
- Add channel config table with credential references only.
- Add audit records for publish, channel update, handoff assign/close, and rollback.

## Slice Order

019.1 -> 019.2 -> 019.3 -> 019.4 -> 019.5
