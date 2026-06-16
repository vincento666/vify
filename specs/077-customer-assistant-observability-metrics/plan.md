# 077 Plan

## 077.1 Backend Session Metrics API

- Add a lightweight metrics DTO in the customer-assistant service layer.
- Aggregate counts from existing task, proposed-action, and event repositories.
- Derive `confirmationAdoptionRate` from confirmed/executed actions over total
  non-pending outcomes.
- Include recent failure reasons from task/result/event summaries using the
  central sanitizer.
- Expose `GET /api/v1/customer-assistant/sessions/{session_id}/metrics`.

TDD seams:

- RED integration test: endpoint is missing.
- RED integration test: returned metrics must not leak raw phone/order/token
  values from task checkpoints or event payloads.
- GREEN implementation with repository/service/router additions only.

## 077.2 Workbench Metrics Panel

- Add frontend API type/helper and runtime refresh wiring.
- Add a compact operator observability panel with counts, adoption rate, and
  recent failure reasons.
- Update panel contract tests and browser UAT.

## Gates

Each slice saves RED, unit/integration, browser UAT when frontend-visible,
docs evidence, and commits independently.
