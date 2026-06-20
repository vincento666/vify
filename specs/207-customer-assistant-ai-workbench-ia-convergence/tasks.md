# Tasks: Customer Assistant AI Workbench IA Convergence

## Slice A: SDD And RED Contract

- [x] SDD: create Spec 207 IA convergence spec, plan, and tasks.
- [x] PRD: update customer assistant AI workbench redesign target to the latest
  four-tab IA.
- [x] RED contract: flip `customerAssistantPanel.test.ts` to require the new
  right workbench target.
- [x] RED evidence: run the focused frontend unit test and save output to
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-a-contract/red.txt`.
- [x] GREEN implementation: satisfied by main integration after Slice B/C.

## Slice B: Focus Projection View Model

- [x] RED view-model tests require operator-facing session status, business
  summary, SOP nodes, and risk/time-limit summaries.
- [x] Implement `formatCustomerAssistantFocusProjection`.
- [x] Fix reply-ready priority so a generated customer draft wins over
  missing-info waiting state.
- [x] Gate: focused view-model and panel unit tests passed.

## Slice C: Browser UAT Harness

- [x] Add `frontend/e2e/customer-assistant-ai-workbench-ia-uat.mjs`.
- [x] RED evidence captured before Vue implementation.
- [x] UAT verifies no `办理` tab, focus-first closure, pure AI chat, and
  evidence/config debug labels.
- [x] UAT screenshots saved under
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/screenshots/`.

## Main Integration

- [x] Remove the `办理` tab and all `activeWorkbenchTab === 'business'` branches.
- [x] Move task ledger, recommendation, draft, warnings, confirmations, receipts,
  and task controls into the `聚焦` pane.
- [x] Add focus status, intent/emotion, business-object summary, SOP handling
  tree, risk/time-limit card, recommended reply card, and sensitive confirmation
  card.
- [x] Replace the assistant internal header/panel structure with a pure chat
  window.
- [x] Label evidence/config panes with `研究调试入口`.
- [x] Update final browser checkpoint script and UAT checklist.
- [x] Align the existing backend customer-assistant e2e test to the current
  async baggage-worker contract without changing backend runtime code.

## Evidence

- RED:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-a-contract/red.txt`
- View-model RED:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-b-viewmodel/red.txt`
- UAT RED:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-c-uat/red.txt`
- UAT notes:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/slice-c-uat/uat.md`
- UAT screenshots:
  `artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/screenshots/`

## Final Gates

- [x] Frontend full unit:
  `npm --prefix frontend run test:unit` passed 98 files / 413 tests.
- [x] Frontend rem:
  `npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` passed.
- [x] Frontend build:
  `npm --prefix frontend run build` passed.
- [x] Backend unit:
  `PYTHONPATH=. uv run pytest tests/unit/customer_assistant` passed 36 tests.
- [x] Backend contract:
  `PYTHONPATH=. uv run pytest tests/contract/customer_assistant tests/contract/test_ai_assistant_customer_bridge_api.py`
  passed 25 tests.
- [x] Backend integration:
  `PYTHONPATH=. uv run pytest tests/integration/customer_assistant` passed 81
  tests, 1 skipped.
- [x] Backend e2e:
  `PYTHONPATH=. uv run pytest tests/e2e/customer_assistant` passed 3 tests.
- [x] Browser UAT:
  `BASE_URL=http://127.0.0.1:5173/customer-assistant node frontend/e2e/customer-assistant-ai-workbench-ia-uat.mjs`
  passed.
- [x] Final browser checkpoints:
  `HIFY_E2E_SCREENSHOT=artifacts/slices/207-customer-assistant-ai-workbench-ia-convergence/screenshots/final-uat-checkpoints.png node frontend/e2e/customer-assistant-final-uat-checkpoints.mjs`
  passed.

## Remaining Risk

- Vite build still reports existing CJS API deprecation and chunk-size warnings.
- Evidence/config remain first-level research/debug tabs for the demo; the
  production shell should later sink them behind per-node and per-card
  `查看依据` affordances.
