# Feature Spec: Customer Assistant Pending Worker Refresh

## Status

Complete.

## User Story

As a customer-service operator, when a task is still running in an async worker, I can see the durable worker run reference and manually refresh completed worker results from the workbench instead of relying on hidden API calls.

## Functional Requirements

- Preserve backend semantics and use the existing `POST /api/v1/customer-assistant/sessions/{id}/worker-results/refresh` endpoint.
- Add frontend API typing/helper for worker-result refresh.
- Carry `workerAsyncRefs` from task summaries into the operator task row model.
- Render worker run id/status refs for supported async worker tasks.
- Add a "刷新结果" operator control that calls the refresh endpoint and reloads tasks/events/actions/metrics.
- Keep cancel hidden for this slice; current worker cancellation is unsupported for MVP workers.

## Non-Goals

- WebSocket/SSE worker control UI.
- Hard cancellation for running workers.
- New backend worker lifecycle semantics.

## Acceptance Criteria

- RED frontend evidence shows missing API/runtime/view-model/UI support.
- Frontend focused tests verify API helper, runtime refresh, task-row refs, and panel markup.
- Browser UAT proves a running task with worker async refs shows the refresh control and reloads completed state.
- Rem gate and build pass for UI changes.

## Evidence

Evidence lives under `artifacts/slices/101-customer-assistant-pending-worker-refresh/101.1/`.

- RED: `red-frontend.txt`
- Focused frontend tests: `frontend-focused.txt`
- Frontend rem gate: `frontend-rem.txt`
- Frontend build: `frontend-build.txt`
- Browser UAT: `uat.txt`
- Screenshot: `screenshots/worker-refresh.png`
