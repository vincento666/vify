# Feature Spec: Workflow Runtime V2 Cancel Lifecycle

## Status

Complete.

## User Story

As a demo operator debugging a long-running Chatflow/Workflow runtime v2 run, I can cancel a running run and trust that the run reaches a durable terminal `CANCELLED` state instead of continuing in the background and later reporting success.

## Functional Requirements

- `POST /api/v1/runtime-runs/{run_id}/cancel` must mark `RUNNING` and `INTERRUPTED` runtime v2 runs as terminal `CANCELLED`.
- Cancelling a run must append a schema-versioned `workflow_run_cancelled` event with owner/run status metadata.
- The runtime v2 completion worker must re-check run status after the configured delay and before executing nodes so a cancelled run cannot be overwritten to `SUCCEEDED`.
- Cancelling an already `CANCELLED` run must be idempotent and return the same terminal result.
- Cancelling already terminal non-cancellable runs (`SUCCEEDED`, `FAILED`) must not rewrite the terminal state; it returns a snapshot explaining cancellation was not applied.

## Non-Goals

- Hard-stopping external tool/LLM processes that have already left the process boundary.
- New UI controls in workflow/chatflow canvases.
- Distributed cancellation locks beyond the repository-backed state transition needed for the local MVP.

## Acceptance Criteria

- RED backend evidence shows the existing unsupported cancel contract fails the new `CANCELLED` lifecycle expectations.
- Focused integration tests prove a cancelled running run remains `CANCELLED` after the background completion delay.
- Focused integration tests prove idempotent cancel on an already-cancelled run.
- Runtime v2 event listing includes `workflow_run_cancelled` and no later `workflow_run_completed` for the cancelled run.
- Browser UAT uses a real Chromium session to start and cancel a runtime v2 run through the API and observe the durable cancelled result.

## Evidence

Evidence lives under `artifacts/slices/102-workflow-runtime-v2-cancel-lifecycle/102.1/`.

- RED: `red.txt`
- Focused integration: `integration.txt`
- Runtime v2 facade regressions: `runtime-v2-facades.txt`
- Browser UAT: `browser-uat.txt`
- Screenshot: `screenshots/runtime-v2-cancel.png`
