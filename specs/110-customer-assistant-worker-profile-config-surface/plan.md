# Plan: Customer Assistant Worker Profile Config Surface

## Slice 110.1 Worker Profile Visibility In Operator Workbench

1. Add a RED customer-assistant panel contract test for a dedicated configured worker profile panel.
2. Render the loaded worker profile catalog from the existing `workerProfiles` state.
3. Reuse the existing worker profile edit/save helpers where possible so the panel is demo-usable without backend changes.
4. Keep all new visual dimensions in `rem` and preserve existing task-ledger profile behavior.
5. Run focused customer-assistant frontend tests and the frontend rem gate.
6. Run browser UAT against `/customer-assistant`, save screenshot/report, update SDD evidence, and commit.

## Test Strategy

- RED/GREEN: `frontend/src/views/customerAssistant/customerAssistantPanel.test.ts`
- Focused regressions:
  - `frontend/src/views/customerAssistant/customerAssistantViewModel.test.ts`
  - `frontend/src/views/customerAssistant/customerAssistantInteractions.test.ts`
  - `frontend/src/views/customerAssistant/customerAssistantRuntime.test.ts`
- Frontend rem gate: `frontend/src/remScaleClosure.test.ts`
- Browser UAT: new `frontend/e2e/customer-assistant-worker-profile-config-surface.mjs`

## Risk Notes

- The existing API already supports list and patch; this slice should not touch backend code.
- The panel reuses the same `workerProfiles` state as task rows, so stale state risk is limited to the existing load/save lifecycle.
- Edit from the profile catalog must avoid requiring an active task row; cancellation and save state should share the existing form refs.
