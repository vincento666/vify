# Spec 199: Workflow Run Gateway

## Goal

Make Workflow a run-first, async-first task model at the public API boundary.

This covers Phase 6 of `docs/chatflow-workflow-production-upgrade.md`.

## In Scope

- `POST /api/v1/workflows/{workflowId}/runs` starts Runtime Core v2 by default.
- `POST /api/v1/workflows/{workflowId}/runs:stream` starts Runtime Core v2 and
  streams runtime events.
- Workflow run responses expose:
  - `runId`
  - `status`
  - `statusRef`
  - `eventsRef`
  - `eventStreamRef`
  - `nodesRef`
  - `resultRef`
  - `versionId` / `version` when a published snapshot is selected
- Workflow runs do not require `sessionId`.
- Existing runtime result, events, nodes, resume, and cancel endpoints remain the
  query/control plane.
- Legacy synchronous workflow execution remains available through an explicit
  compatibility endpoint.

## Out of Scope

- Durable worker queue implementation.
- Frontend workflow debug UI redesign.
- Changing Chatflow session/message gateway behavior.

## Acceptance Criteria

- Calling `/workflows/{id}/runs` returns runtime refs instead of a synchronous
  `output` envelope.
- Calling `/workflows/{id}/runs:stream` returns a real SSE stream for the new
  run.
- The result, events, and nodes refs all resolve for the run.
- A targeted `versionId` uses the published snapshot and survives draft edits.
