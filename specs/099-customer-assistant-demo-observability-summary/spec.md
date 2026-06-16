# Feature Spec: Customer Assistant Demo Observability Summary

## Status

Slice 099.1 complete.

## User Story

As a demo operator, I can see a single observability summary for all seeded customer-assistant demo stories so that a productized MVP walkthrough shows task health, human-confirmation adoption, and failure reasons before drilling into one session.

## Functional Requirements

- Expose a read-only `GET /api/v1/customer-assistant/demo-stories/metrics` endpoint.
- Aggregate only seeded demo-story sessions from the repeatable MVP demo seed.
- Include story count, session count, task status counts, proposed-action status counts, human-confirmation pending/adopted/terminal/adoption rate, event counts, worker event counts, redacted recent failure reasons, and per-story compact rows.
- Keep payloads secret-free: no raw customer phone, order number, API key, tool parameters, or full event payloads.
- Add frontend API typing/helper for the new endpoint.
- Render a compact demo-level metrics strip above the seeded story picker in the customer-assistant workbench.

## Non-Goals

- Long-term analytics warehouse, charts, or cross-tenant reporting.
- Replacing the existing per-session metrics panel.
- Adding new seed stories or mutating demo data.

## Acceptance Criteria

- RED backend evidence shows the demo-story metrics endpoint is initially missing.
- RED frontend evidence shows the API helper and workbench summary are initially missing.
- Backend integration verifies aggregate counts, per-story rows, and redacted failure reasons.
- Frontend focused tests verify the API helper and workbench summary contract.
- Browser UAT proves the customer-assistant workbench displays the aggregate summary for seeded stories.
- Rem gate and build pass for visual changes.
- Docs/tasks record evidence paths and final status.

## Evidence

- RED backend: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/red-backend.txt`
- RED frontend: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/red-frontend.txt`
- Backend demo-story metrics: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/backend-demo-story-metrics.txt`
- Ruff: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/ruff.txt`
- Frontend focused: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/frontend-focused.txt`
- Frontend rem gate: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/frontend-rem.txt`
- Frontend build: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/frontend-build.txt`
- Demo seed: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/seed.txt`
- Browser UAT: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/uat.txt`
- Browser UAT report: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/uat-report.json`
- Browser UAT screenshot: `artifacts/slices/099-customer-assistant-demo-observability-summary/099.1/demo-story-metrics.png`
