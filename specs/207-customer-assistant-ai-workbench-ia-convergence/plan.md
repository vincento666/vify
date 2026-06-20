# Plan: Customer Assistant AI Workbench IA Convergence

## Slice A: SDD And RED Contract

1. Update SDD and PRD to reflect the latest target IA.
2. Flip `frontend/src/views/customerAssistant/customerAssistantPanel.test.ts`
   from the previous five-tab contract to the new four-tab convergence contract.
3. Run the focused frontend unit test and preserve the expected RED output.
4. Do not edit production Vue or backend implementation in this slice.

## Slice B: Focus Projection View Model

1. Add a typed focus projection that turns runtime state into operator-facing
   session status, business-object summary, SOP nodes, and risk/time-limit
   summaries.
2. Drive RED with view-model unit tests before implementation.
3. Keep the projection deterministic and frontend-only so the backend API
   contract remains stable.

## Slice C: Browser UAT Harness

1. Add a Playwright UAT script for the final right-side IA.
2. Verify no `办理` tab, focus-first handling closure, AI chat-only surface, and
   research/debug labels for evidence/config.
3. Save screenshots under the 207 artifact directory.

## Main Integration

1. Remove the production `办理` tab and `operator-workbench-business-pane`.
2. Merge handling closure cards and migrated business controls into `聚焦`.
3. Remove the internal `AI助手` header and keep assistant content as chat
   messages plus composer.
4. Update existing UAT/checklist docs and final browser checkpoint script.
5. Align the existing customer-assistant runtime e2e test with the current async
   baggage-worker contract while preserving final completion and traceability
   assertions.

## Contract Shape

- Right-side tabs: `聚焦`, `AI助手`, `证据`, `配置`.
- Forbidden: `办理`, `business`, and `operator-workbench-business-pane`.
- `聚焦` owns business closure:
  task ledger, recommendation, draft, risk, confirmation, receipts, and task
  controls.
- `AI助手` is chat-only:
  chat window, message stream, and composer; no internal header, task panels,
  config panels, or metrics panels.
- `证据` and `配置` remain reachable but explicitly marked as
  `研究调试入口`.

## Gates

- RED focused frontend:
  `npm --prefix frontend run test:unit -- src/views/customerAssistant/customerAssistantPanel.test.ts`
- Evidence:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-a-contract/red.txt`
- GREEN focused frontend:
  `npm --prefix frontend run test:unit -- src/views/customerAssistant/customerAssistantPanel.test.ts src/views/customerAssistant/customerAssistantViewModel.test.ts src/remScaleClosure.test.ts`
- Frontend full unit:
  `npm --prefix frontend run test:unit`
- Frontend build:
  `npm --prefix frontend run build`
- Backend unit:
  `PYTHONPATH=. uv run pytest tests/unit/customer_assistant`
- Backend contract:
  `PYTHONPATH=. uv run pytest tests/contract/customer_assistant tests/contract/test_ai_assistant_customer_bridge_api.py`
- Backend integration:
  `PYTHONPATH=. uv run pytest tests/integration/customer_assistant`
- Backend e2e:
  `PYTHONPATH=. uv run pytest tests/e2e/customer_assistant`
- Browser UAT:
  `BASE_URL=http://127.0.0.1:5173/customer-assistant node frontend/e2e/customer-assistant-ai-workbench-ia-uat.mjs`
- Final browser checkpoint:
  `HIFY_E2E_SCREENSHOT=artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/screenshots/final-uat-checkpoints.png node frontend/e2e/customer-assistant-final-uat-checkpoints.mjs`

## Risk Controls

- Do not modify `CustomerAssistantPanel.vue` in Slice A.
- Do not touch unrelated dirty files created by parallel agents.
- Keep backend runtime code unchanged for this IA convergence.
- Treat evidence/config as research/debug entry points, not the primary operator
  flow.
- Keep all new visual sizing under the existing rem governance gate.
