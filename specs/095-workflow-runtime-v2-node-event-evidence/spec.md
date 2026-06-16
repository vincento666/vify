# Spec 095: Workflow Runtime V2 Node Event Evidence

## Goal

Expose runtime v2 node events in the workflow canvas debug node detail panel so
operators can inspect why a node is running, completed, failed, or waiting
without expanding raw event payloads.

## Acceptance Criteria

- Node detail view formats `node.events` into compact runtime event evidence
  rows with sequence, event type, status, and redacted reason/error details.
- WAITING/BLOCKED and FAILED node events are visible in the node detail panel.
- Secrets in event reason/error payloads are redacted before rendering.
- Existing token/cost/latency and LLM fallback evidence remains unchanged.
- Browser UAT verifies a runtime event evidence row in the workflow debug dock.

## Non-goals

- Do not change runtime v2 execution semantics.
- Do not add new node lifecycle APIs.
- Do not alter persisted event schemas.
- Do not solve version publishing or resume/cancel product flows in this slice.

## Evidence

Evidence lives under
`artifacts/slices/095-workflow-runtime-v2-node-event-evidence/095.1/`.
