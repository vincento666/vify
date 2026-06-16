# Plan: Customer Assistant Action Ledger Refresh

## Slice 108.1 Proposed Action Mutation Ledger Refresh

1. Add a RED runtime unit test showing proposed-action mutation helpers refresh server ledgers after reject/execute/edit.
2. Reuse the existing `refreshCustomerAssistantRuntimeLedgers` helper for all proposed-action mutation flows.
3. Preserve the already-covered proposed-task-command confirmation behavior while removing its bespoke refresh branch.
4. Run focused frontend unit tests for the runtime and customer assistant view/control contracts.
5. Run browser UAT against the customer assistant workbench and save evidence.
6. Update SDD evidence and commit the focused slice.

## Test Strategy

- Frontend unit RED/GREEN: `frontend/src/views/customerAssistant/customerAssistantRuntime.test.ts`
- Focused customer assistant regressions:
  - `frontend/src/views/customerAssistant/customerAssistantInteractions.test.ts`
  - `frontend/src/views/customerAssistant/customerAssistantViewModel.test.ts`
  - `frontend/src/views/customerAssistant/customerAssistantPanel.test.ts`
- Browser UAT: `frontend/e2e/customer-assistant-interactions.mjs`

## Risk Notes

- This slice changes state refresh behavior, not visual styles; frontend rem gates are not required because no visual dimensions are touched.
- A full ledger refresh after action mutations costs extra API calls, but keeps the operator-facing closed loop correct and consistent with task-control proposal/confirmation paths.
- If backend state diverges from the direct mutation response, server ledgers are treated as canonical.
