# Feature Spec: Customer Assistant Operator Audit Trace

## Status

Complete.

## User Story

As a customer-service operator or demo reviewer, I can open a session-scoped audit trace that shows which operator-facing actions were proposed, edited, confirmed, rejected, executed, refreshed, or completed without exposing raw customer PII, API keys, tool parameters, or full event payloads.

## Functional Requirements

- Add a read-only `GET /api/v1/customer-assistant/sessions/{session_id}/operator-audit` endpoint.
- The endpoint returns `{sessionId, list, total}` with chronological audit rows derived from the existing event ledger.
- Audit rows must include only a white-listed shape: `id`, `sequence`, `eventType`, `title`, `actor`, `source`, `status`, `targetType`, `targetId`, `summary`, `createdAt`.
- Relevant event families include proposed-action lifecycle events, task-control events, worker/task execution status events, worker refresh result consumption, and operator advisory context packing.
- Sensitive values in summaries must be sanitized; raw payloads must not be returned.
- The workbench renders a compact operator audit panel separate from the raw event timeline.

## Non-Goals

- Full export/download and advanced filtering.
- Rewriting existing event emission semantics.
- Showing raw event payload details in the audit panel.

## Acceptance Criteria

- RED backend evidence shows the new endpoint is missing.
- Backend focused tests prove audit rows include action/task/worker events and redact phone/order/token/API key values.
- Frontend API/runtime/view-model/panel tests prove the feed is loaded and rendered.
- Browser UAT proves an operator task-control flow shows audit rows in the workbench and no raw sensitive values.
- Frontend rem gate and build pass for visual changes.

## Evidence

Evidence lives under `artifacts/slices/103-customer-assistant-operator-audit-trace/103.1/`.

- RED backend: `red.txt`
- RED frontend: `red-frontend.txt`
- Backend focused tests: `backend-focused.txt`
- Auth contract: `auth-contract.txt`
- Frontend focused tests: `frontend-focused.txt`
- Frontend rem gate: `frontend-rem.txt`
- Frontend build: `frontend-build.txt`
- Browser UAT: `browser-uat.txt`
- Screenshot: `screenshots/operator-audit.png`
