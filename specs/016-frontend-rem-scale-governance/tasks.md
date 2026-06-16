# Tasks 016: Frontend REM Scale Governance

## 016.1 Scale foundation

- [x] RED: add scale contract tests and save failure output.
- [x] Implement `frontend/src/utils/uiScale.ts`.
- [x] Implement `frontend/src/composables/useUiScale.ts`.
- [x] Install global scale in `frontend/src/main.ts`.
- [x] Bind `html` font-size to `--hify-root-font-size`.
- [x] Convert first base font/space/radius/layout tokens to REM.
- [x] Unit gate passes.
- [x] Build gate passes.
- [x] Browser UAT confirms root variables update.
- [x] Evidence saved under `artifacts/slices/016-frontend-rem-scale-governance/016.1-scale-foundation/`.

## 016.2 Shared shell and Element Plus bridge

- [x] RED: shell/token governance tests fail for app chrome and base components.
- [x] Convert `App.vue` visual dimensions to REM tokens/classes.
- [x] Convert `HifyTable.vue` and `HifyFormDialog.vue` defaults to REM-compatible values.
- [x] Expand Element Plus token bridge for component sizes and common surface density.
- [x] E2E route smoke passes.
- [x] Browser UAT covers sidebar/topbar/table/dialog.
- [x] Evidence saved.

## 016.3 Management pages

- [x] RED: provider management page governance test fails on visual px props.
- [x] Convert provider list visual dimensions, dialog props, popover width, table row height, and action spacing.
- [x] Provider unit/build/e2e/browser UAT gates pass.
- [x] RED: page governance tests fail for remaining agent/knowledge/MCP/evaluation/list pages.
- [x] Convert agent list visual dimensions.
- [x] Convert knowledge list/document and MCP list visual dimensions.
- [x] Convert workflow/chatflow list visual dimensions.
- [x] Convert evaluation panels visual dimensions.
- [x] E2E route smoke passes.
- [x] Browser UAT covers representative pages.
- [x] Evidence saved under `artifacts/slices/016-frontend-rem-scale-governance/016.3-management-pages-provider/`.

## 016.4 Workflow and Chatflow canvas

- [x] RED: canvas governance tests fail until visual px and geometry allowlist are separated.
- [x] Convert workflow/chatflow canvas visual chrome to REM tokens.
- [x] Preserve graph coordinates, edge path math, drag offsets, DOM measurements as geometry units.
- [x] E2E node add/config/debug path passes.
- [x] Browser UAT covers multi-width canvas and click sanity.
- [x] Evidence saved under `artifacts/slices/016-frontend-rem-scale-governance/016.4-workflow-chatflow-canvas/`.

## 016.5 Agent Workbench and Chat

- [x] RED: workbench/chat governance tests fail for visual px.
- [x] Convert Agent Workbench visual layout.
- [x] Convert Chat visual layout.
- [x] Existing workbench/chat unit tests pass.
- [x] E2E preview/chat smoke passes.
- [x] Browser UAT screenshots saved.
- [x] Evidence saved under `artifacts/slices/016-frontend-rem-scale-governance/016.5-agent-workbench-chat/`.

## 016.6 Governance closure

- [x] RED: all-source governance test fails on remaining unclassified visual px.
- [x] Migrate or explicitly allowlist remaining raw units.
- [x] Add docs for Hify REM governance.
- [x] Full frontend unit gate passes.
- [x] Frontend build gate passes.
- [x] Relevant e2e gate passes.
- [x] Browser UAT final pass covers required routes/widths.
- [x] Specs/tasks updated with evidence links under `artifacts/slices/016-frontend-rem-scale-governance/016.6-governance-closure/`.
