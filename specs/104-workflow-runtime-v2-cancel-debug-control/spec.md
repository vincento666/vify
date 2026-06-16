# Feature Spec: Workflow Runtime V2 Cancel Debug Control

## Status

Complete.

## User Story

As a demo operator using the Workflow/Chatflow canvas debug dock, I can cancel a running runtime v2 test run from the visible debug controls and immediately see the run settle into `CANCELLED` without leaving the canvas.

## Functional Requirements

- The frontend workflow API client must expose `cancelRuntimeV2Run(runId)` for `POST /api/v1/runtime-runs/{run_id}/cancel`.
- Runtime v2 debug projection must treat `workflow_run_cancelled` events and `CANCELLED` run snapshots as terminal cancelled state.
- The Workflow/Chatflow debug dock must show a cancel control only for active runtime v2 runs.
- Clicking cancel must call the runtime v2 cancel endpoint, refresh run/events/nodes, and update the visible run status to `CANCELLED`.
- Cancel controls must be disabled while cancellation is in flight and must disappear once the run is terminal.

## Non-Goals

- Changing backend runtime v2 cancellation semantics; durable backend cancel is covered by spec 102.
- Hard-stopping external provider calls that have already left the browser/backend process.
- Reworking the full debug dock layout or runtime v2 polling architecture.

## Acceptance Criteria

- RED frontend evidence proves the API helper and cancelled-event projection are missing before implementation.
- Focused frontend unit tests prove the cancel helper posts to the correct endpoint and cancelled events project to `CANCELLED`.
- Browser UAT starts a real runtime v2 Chatflow run from Chromium, opens the Workflow/Chatflow canvas debug dock, clicks the visible cancel control, and captures the resulting `CANCELLED` state.
- Frontend rem gate and focused workflow frontend tests are green.
- Full frontend build is green.

## Evidence

Evidence lives under `artifacts/slices/104-workflow-runtime-v2-cancel-debug-control/104.1/`.

- RED: `red.txt`
- Focused frontend unit tests: `frontend-focused.txt`
- Full frontend unit tests: `frontend-unit.txt`
- Frontend rem gate: `frontend-rem.txt`
- Frontend build: `frontend-build.txt`
- Browser UAT: `browser-uat.txt`
- Screenshot: `screenshots/runtime-v2-cancel-debug-control.png`
