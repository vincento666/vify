# Spec 063: Hify Chatflow Runtime V2 Facade MVP

## Goal

Move the Chatflow runtime v2 spike onto the shared Hify runtime v2 core while
preserving Chatflow-specific session, checkpoint, and resume semantics.

This keeps the product validation Chatflow-first, but the implementation must
use the shared core from 062.

## Dependency

063 depends on:

- 058 Chatflow runtime v2 spike;
- 062 Hify Workflow/Chatflow shared runtime v2 core.

## Product Boundary

In scope:

- Chatflow facade over shared runtime v2 core;
- minimal supported paths:
  - `START -> MESSAGE -> END`
  - `START -> QUESTION -> resume -> END`
- Chatflow session and checkpoint projection;
- v2 live event stream with pre-terminal event visibility;
- Chatflow canvas/debug run projection over runtime v2 node status/events;
- legacy Chatflow sync and SSE replay compatibility;
- preservation of caller context from external routers such as the SOP
  multi-level router;
- graph-level v2 compatibility checker.

Out of scope:

- broad node coverage beyond the minimal paths;
- Hify Workflow facade;
- ChatflowSopWorker migration;
- WebSocket/Redis;
- node-level v1/v2 mixed execution.

## Hard Constraints

- Unsupported Chatflow graphs must be rejected or fall back as a whole run.
- Legacy Chatflow SSE remains completion-time replay.
- V2 live events must use a v2 endpoint or explicit v2 mode.
- Existing Chatflow session/checkpoint behavior must remain compatible.
- Chatflow debug run UI must consume runtime v2 async refs/status/events instead
  of legacy completion-time replay when v2 mode is selected.
- Chatflow facade events must be projections of the shared runtime event store,
  not a second authoritative event log.
- Resume requests must be idempotent for the same checkpoint and user input.
- Fallback/rejection must be explicit and must not emit fake v2 live refs.
- Chatflow runtime v2 must preserve external router caller context but must not
  become the owner of SOP multi-level routing or multi-intent switching.

## Acceptance Criteria

- Chatflow v2 facade uses shared runtime core refs/events.
- Minimal message and question/resume paths work.
- Repeated resume for the same checkpoint/input does not corrupt checkpoint
  state or duplicate terminal events.
- `workflow_run_started` or `workflow_node_started` is observable before
  terminal result.
- Chatflow debug panel receives real-time node status updates while the run is
  active.
- Node running/completed/waiting/failed visual states match runtime v2 node
  statuses.
- A node error stops the Chatflow v2 run and updates the debug panel to failed.
- Unsupported graph reports unsupported nodes instead of partial mixed execution.
- Fallback/rejection reasons are visible in events or diagnostics.
- Legacy endpoint regression tests stay green.

## MVP Exit

063 is complete when Chatflow v2 no longer depends on a Chatflow-only runtime
island for the minimal supported paths.
