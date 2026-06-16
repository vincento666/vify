# 077 Customer Assistant Observability Metrics

## Goal

Expose customer-assistant task/action/event metrics as a demo-ready product
surface so operators can see pending work, human confirmation adoption, failure
reasons, and recent task execution evidence without opening raw debug payloads.

## Acceptance Criteria

- The API exposes a session-scoped metrics endpoint under `/api/v1/customer-assistant`.
- Metrics include task status counts, proposed-action status counts, human
  confirmation adoption counters/rate, worker/event counts, and recent failure
  reasons.
- Metrics are derived from the existing session ledger and do not expose raw
  customer PII, tool parameters, API keys, or full event payloads.
- The workbench renders a compact observability panel for the active session.
- Browser UAT proves the panel updates after an operator edits and confirms a
  proposed task-control action.

## Slices

### 077.1 Backend Session Metrics API

Add service/router support and backend integration coverage for a
session-scoped metrics response.

### 077.2 Workbench Metrics Panel

Add frontend API/runtime/view-model wiring and a compact workbench panel with
browser UAT.

## Evidence

Evidence lives under
`artifacts/slices/077-customer-assistant-observability-metrics/<slice>/`.

## Non-goals

- Cross-session analytics, charts, and long-term warehouse exports are deferred.
- Full RBAC enforcement is covered by a later auth/redaction boundary slice.
- Raw event payload inspection stays in the existing event timeline; this slice
  only surfaces aggregate metrics and redacted reasons.
