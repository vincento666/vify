# 075 Plan

## 075.1 Backend Catalog And Routing Override

Implementation shape:

- Add a customer-assistant worker profile catalog domain module.
- Defaults preserve existing refund and baggage task routing.
- Parse `HIFY_CUSTOMER_ASSISTANT_WORKER_PROFILES_JSON` from settings.
- Thread the catalog into `DeterministicTaskRecognitionController`.
- Expose `GET /api/v1/customer-assistant/worker-profiles`.
- Update demo seed env output with the default profile JSON.

TDD seams:

- RED backend integration: endpoint is missing and override config is ignored.
- GREEN domain parser plus service/router integration.
- Seed gate: generated env contains non-secret worker profile JSON.

## 075.2 Workbench Profile Visibility

- Add frontend API/runtime helper.
- Render compact active profile metadata in the customer-assistant workbench.
- Run rem and browser UAT.

## 075.3 Profile Evaluation Gate

- Add eval/observe events or records that include profile refs.
- Verify proposed-action high-risk behavior remains gated.

## Gates

Each slice saves RED, unit/integration, browser UAT when visible frontend changes
are made, docs evidence, and commits independently.
