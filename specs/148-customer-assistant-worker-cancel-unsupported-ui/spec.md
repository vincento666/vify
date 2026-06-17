# Feature Spec: Customer Assistant Worker Cancel Unsupported UI

## Status

Complete.

## User Story

As a customer-assistant operator, when an async worker is still running, I can
request cancellation from the workbench and immediately see the durable
unsupported-cancellation evidence instead of guessing whether the request was
accepted.

## Functional Requirements

- Add a frontend API helper for
  `POST /api/v1/customer-assistant/worker-runs/{workerRunId}/cancel`.
- Running tasks with supported `workerAsyncRefs.workerRunId` must show a
  `请求取消` worker-level control next to the existing `刷新结果` control.
- Clicking the control must call the worker cancel endpoint and refresh tasks,
  events, proposed actions, metrics, and operator audit.
- The refreshed workbench must show `worker_cancel_requested` and
  `worker_cancel_unsupported` evidence when the backend reports unsupported
  cancellation.
- The task-control `取消` proposed-action flow remains unchanged; this slice is
  specifically for worker-run cancellation evidence.

## Privacy And MySQL Scope

- No new backend schema or persistence behavior is introduced.
- Browser/UAT fixtures must prove order-like ids and tool payloads are not
  exposed through the new cancellation evidence row.
- No SQLite fallback or fixture path is allowed.

## Non-Goals

- Implementing hard cooperative cancellation for workers.
- Changing backend cancellation status semantics.
- Adding WebSocket/SSE worker control streams.

## Acceptance Criteria

- RED API/runtime/panel tests fail before implementation because the frontend
  lacks a worker cancel helper and UI control.
- Focused frontend tests pass after implementation.
- Browser UAT proves a running async worker exposes `请求取消`, calls the cancel
  endpoint, refreshes ledgers, and renders unsupported-cancel evidence.
- `remScaleClosure`, full frontend unit, and frontend build pass.

## Evidence

Evidence lives under
`artifacts/slices/148-customer-assistant-worker-cancel-unsupported-ui/148.1/`.

- RED frontend: `red-frontend.txt`
- Focused frontend: `frontend-focused.txt`
- Frontend rem gate: `rem.txt`
- Full frontend unit: `frontend-full.txt`
- Frontend build: `frontend-build.txt`
- Browser UAT: `browser-uat.txt`
- Screenshot: `screenshots/worker-cancel-unsupported.png`

## Completion Evidence

- RED frontend captured missing API/runtime/panel worker-cancel support.
- Focused frontend tests passed for API, runtime, and panel contracts.
- Full frontend unit passed: 91 files / 366 tests.
- `remScaleClosure` passed.
- Frontend build passed.
- Browser UAT passed and verified `请求取消`, cancel endpoint call,
  `worker_cancel_unsupported`, later refresh, and final completed task state.
