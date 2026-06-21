# Plan: Customer Assistant AI Workbench IA Convergence

## Reopened Scope

The first 207 pass removed the `办理` tab, but it kept too many migrated
business panels inside `聚焦`. This pass keeps the four-tab contract and fixes
the remaining focus-workbench product issues plus the P0 backend blockers that
prevent real UAT.

## Slice A: Focus IA And Recommendation Consolidation

1. Update the panel contract so `聚焦` no longer requires legacy peer panels.
2. Move the task/SOP tree directly below the status/next-step block.
3. Keep one recommended reply card and make send/copy/edit use
   `customerReplyDraft`.
4. Keep one high-sensitive confirmation card with progressive detail affordance.
5. Preserve `AI助手` as chat-only and `证据`/`配置` as research/debug entries.

## Slice B: Seeded Pending Actions

1. Add a failing backend test for seeded story pending action confirmation.
2. Update seeded pending action payloads to the current proposed task command
   contract.
3. Prove seeded actions can be confirmed/rejected without
   `Invalid proposed task command`.

## Slice C: Live Multi-Task Worker Runtime

1. Reproduce the live multi-task 500 as closely as possible with existing
   MySQL/integration harnesses.
2. Isolate SQLAlchemy sessions/connections across async worker persistence so
   PyMySQL packet sequence errors do not occur.
3. Prove a real multi-task turn can proceed to task/action/recommendation data.

## Slice D: Profile Defaults And Refund Recognition

1. Add tests for default profile catalog values and stale override avoidance.
2. Guard the local/default profile path against the old baggage stub profile.
3. Add recognition coverage for natural refund phrasing with a flight object,
   such as `退 MU5137 的票`.

## Main Integration

- Right-side tabs: `聚焦`, `AI助手`, `证据`, `配置`.
- Forbidden: `办理`, `business`, and `operator-workbench-business-pane`.
- `聚焦` owns a compact business closure path, not copied legacy panels.
- `AI助手` is chat-only:
  chat window, message stream, and composer; no internal header, task panels,
  config panels, or metrics panels.
- `证据` and `配置` remain reachable but explicitly marked as
  `研究调试入口`.
- Main agent merges all slices, resolves conflicts, runs the full gate set, and
  commits each accepted sub-feature.

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

- Do not touch unrelated dirty files created by parallel agents.
- Keep backend fixes limited to the specific P0 blockers.
- Treat evidence/config as research/debug entry points, not the primary operator
  flow.
- Keep all new visual sizing under the existing rem governance gate.
