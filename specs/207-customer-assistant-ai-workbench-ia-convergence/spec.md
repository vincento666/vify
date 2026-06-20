# Spec 207: Customer Assistant AI Workbench IA Convergence

Status: Completed and verified.
Date: 2026-06-20
Owner: Customer Assistant / Operator Workbench

## Goal

Converge the customer assistant right-side workbench around the operator's
default handling loop. The operator should no longer switch to a separate
`办理` tab for normal closure work. The default `聚焦` tab owns the business
object, task, recommendation, draft, risk, confirmation, receipt, and task
control path.

## User Need

When serving a traveler, the operator needs one default place to understand the
task, judge urgency, review the recommended reply, confirm sensitive actions,
and close the work. The AI assistant should be a simple chat surface, while
evidence and configuration stay available as research/debugging entries.

## In Scope

- Right workbench tabs are exactly `聚焦`, `AI助手`, `证据`, and `配置`.
- Remove the right-side `办理` tab and remove `operator-workbench-business-pane`.
- Move task handling closure into `聚焦`:
  - status bar;
  - task intent and emotion;
  - business object summary;
  - SOP handling tree;
  - risk and SLA/time-limit card;
  - recommended reply card;
  - sensitive confirmation card;
  - task ledger;
  - recommendation detail;
  - customer reply draft;
  - risk warnings;
  - confirmations;
  - execution/delivery/decision receipts;
  - task controls.
- Keep `AI助手` as a pure chat window with message stream and composer only.
- Mark `证据` and `配置` as research/debugging entry points.

## Out of Scope

- Backend runtime changes.
- Real RAG, real tool calling, or MCP enhancements.
- Reworking the left session rail or center passenger/operator lanes.
- Backend runtime behavior changes. One existing backend e2e assertion was
  aligned to the current async baggage-worker contract; no runtime code changed.

## Acceptance Criteria

- The right-side tab list is exactly `聚焦`, `AI助手`, `证据`, and `配置`.
- `办理`, `business`, and `operator-workbench-business-pane` are absent.
- `聚焦` contains the operator handling loop: status, intent/emotion, business
  objects, SOP tree, risk/time-limit card, recommended reply, sensitive
  confirmation, ledger, receipts, and controls.
- `AI助手` omits the internal header, task/config/metric panels, and business
  state panels. It remains a chat stream plus composer.
- `证据` and `配置` display `研究调试入口`.
- Browser UAT verifies the four-tab IA, focus-first closure path, assistant chat,
  and debug entries.

## Slice Evidence

- RED: `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-a-contract/red.txt`
- View-model RED:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-b-viewmodel/red.txt`
- Browser UAT RED:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-c-uat/red.txt`
- Browser UAT notes:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-c-uat/uat.md`
- Browser screenshots:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/screenshots/`

## Final Verification

- Frontend unit: `npm --prefix frontend run test:unit` passed 98 files / 413 tests.
- Frontend rem: `npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`
  passed.
- Frontend build: `npm --prefix frontend run build` passed with existing Vite CJS
  and chunk-size warnings.
- Backend unit: `PYTHONPATH=. uv run pytest tests/unit/customer_assistant`
  passed 36 tests.
- Backend contract:
  `PYTHONPATH=. uv run pytest tests/contract/customer_assistant tests/contract/test_ai_assistant_customer_bridge_api.py`
  passed 25 tests.
- Backend integration:
  `PYTHONPATH=. uv run pytest tests/integration/customer_assistant`
  passed 81 tests, 1 skipped.
- Backend e2e: `PYTHONPATH=. uv run pytest tests/e2e/customer_assistant`
  passed 3 tests.
- Browser UAT:
  `BASE_URL=http://127.0.0.1:5173/customer-assistant node frontend/e2e/customer-assistant-ai-workbench-ia-uat.mjs`
  passed.
- Final browser checkpoints:
  `HIFY_E2E_SCREENSHOT=artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/screenshots/final-uat-checkpoints.png node frontend/e2e/customer-assistant-final-uat-checkpoints.mjs`
  passed.
