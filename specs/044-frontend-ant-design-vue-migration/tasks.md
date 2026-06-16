# Tasks 044: Frontend Ant Design Vue Migration

## 044.0 Inventory And Gate Design

- [x] Confirm latest spec number is `044`.
- [x] Record Element Plus dependency inventory.
- [x] Identify high-risk UI components and flows.
- [x] Add initial Element Plus usage inventory under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.0/`.
- [x] Define temporary import guard allowlist for migration.

## 044.1 Ant Foundation

- [x] RED: `ant-design-vue` install seam does not exist.
- [x] Add `ant-design-vue` dependency.
- [x] Add `@ant-design/icons-vue` dependency.
- [x] Add `frontend/src/app/ant-design.ts`.
- [x] Import Ant Design Vue CSS once.
- [x] Add theme bridge using project tokens where practical.
- [x] Keep Element Plus temporarily installed for unmigrated pages.
- [x] Add focused test proving app bootstrap uses the Ant install seam.
- [x] Save RED/GREEN evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.1/`.

## 044.2 Direct Feedback, Confirm, And Request Replacement

- [x] Inventory `ElMessage`, `ElMessageBox`, `el-popconfirm`, and
  `window.confirm` usage.
- [x] Replace `ElMessage` usage with Ant Design Vue `message` directly.
- [x] Replace `ElMessageBox.confirm` usage with Ant Design Vue `Modal.confirm`
  directly.
- [x] Replace `el-popconfirm` usage with `a-popconfirm`.
- [x] Ensure `request.ts`, `notify.ts`, and `useConfirm.ts` no longer import
  Element Plus.
- [x] Preserve confirm cancellation behavior where callers depend on rejected
  promises.
- [x] Remove or bypass exploratory `frontend/src/shared/ui/feedback.ts` and
  `frontend/src/shared/ui/confirm.ts` before final acceptance if no product
  caller still needs them.
- [x] Add focused tests for message/confirm behavior where it affects business
  flows.
- [x] Save evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.2/`.

## 044.3 Direct Table And Form Dialog Replacement

- [x] RED: `HifyTable` and `HifyFormDialog` still render Element Plus.
- [x] Replace `HifyTable` implementation with Ant Design Vue table/pagination.
- [x] Preserve existing table props used by Provider, MCP, and Agent list.
- [x] Preserve loading, empty, action slot, row key, and pagination behavior.
- [x] Replace `HifyFormDialog` implementation with Ant Design Vue modal/form.
- [x] Preserve validation and submit contract.
- [x] Update type imports away from Element Plus.
- [x] Run `frontend/src/components/base/hifyTableSizing.test.ts`.
- [x] Run affected Provider/MCP/Agent list tests.
- [x] Save evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.3/`.

## 044.4 App Shell, Navigation, And Icons

- [x] RED: app shell still imports `@element-plus/icons-vue`.
- [x] Replace app shell Element Plus icons with Ant icons or lucide icons.
- [x] Replace `el-tooltip` with `a-tooltip`.
- [x] Replace `el-avatar` with `a-avatar`.
- [x] Replace `el-icon` wrappers with local icon classes/components.
- [x] Preserve collapsed navigation behavior and active route highlighting.
- [x] Run `frontend/src/appNavigation.test.ts`.
- [x] Run browser UAT for main menu navigation.
- [x] Save evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.4/`.

## 044.5 Low-Risk Module Pages

- [x] RED: Provider, MCP, and Knowledge pages still contain Element Plus tags or
  imports.
- [x] Migrate Provider pages directly to Ant Design Vue.
- [x] Migrate MCP pages directly to Ant Design Vue.
- [x] Migrate Knowledge pages directly to Ant Design Vue, including upload.
- [x] Preserve data-testid hooks.
- [x] Run Provider/MCP/Knowledge focused unit tests.
- [x] Run browser UAT for Provider create/edit/delete/test connection.
- [x] Run browser UAT for Knowledge upload/import/export/delete.
- [x] Save evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.5-provider/`,
  `044.5-mcp/`, and `044.5-knowledge/`.

## 044.6 Medium-Risk Chat, Runtime Lab, And Agent

- [x] RED: Chat, Runtime Lab, or Agent pages still contain Element Plus tags or
  direct Element Plus feedback imports.
- [x] Migrate Chat conversation UI, delete confirmation, and send error states.
- [x] Migrate Runtime Lab route settings forms, selects, switches, and modal.
- [x] Migrate Agent list remaining Element Plus usage.
- [x] Migrate Agent workbench messages, inputs, selects, preview controls, and
  publish states.
- [x] Preserve route behavior from 043.
- [x] Run Chat, Runtime Lab, and Agent focused tests.
- [x] Run browser UAT for chat send/delete, runtime temporary model settings,
  and agent preview/publish.
- [x] Save evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.6-chat/`,
  `044.6-runtime-lab/`, `044.6-agent-list/`, and `044.6-agent-workbench/`.

## 044.7 High-Risk Evaluation Workbench

- [x] RED: Evaluation pages still contain Element Plus tags/imports.
- [x] Migrate evaluation tabs.
- [x] Migrate eval set list/detail tables.
- [x] Migrate evaluator catalog/workbench dialogs and segmented controls.
- [x] Migrate experiment stepper and run controls.
- [x] Migrate run report, compare analysis, CSV import/export interactions.
- [x] Preserve dense table layout and all data-testid hooks.
- [x] Run all evaluation unit tests.
- [x] Run browser UAT for eval set, evaluator, experiment, report, compare, CSV.
- [x] Save screenshots for dense table and dialog states.
- [x] Save evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.7/`.

## 044.8 High-Risk Workflow Canvas

> Complete. Workflow/chatflow list shell, API Resource workbench, canvas/create,
> and legacy Chatflow create surface are migrated to Ant.

- [x] RED: Workflow capsule pages still contain Element Plus tags/imports.
- [x] Migrate Workflow/Chatflow list pages.
- [x] Migrate API Resource workbench.
- [x] Migrate `WorkflowCreate.vue` toolbar, title input, side panels, config
  controls, variable selectors, publish dialog, test panel, debug details, and
  inline popovers.
- [x] Preserve Vue Flow canvas behavior.
- [x] Preserve keyboard handling and ignore-input detection after `.el-*`
  selectors are removed.
- [x] Replace app-owned `.el-*` deep selectors with Ant selectors or app-owned
  class names.
- [x] Preserve create/save/publish/run/debug/version rollback behavior.
- [x] Run workflow focused unit tests for migrated list shell.
- [x] Run API Resource focused unit, rem, build, E2E, and browser UAT gates.
- [x] Run workflow/chatflow E2E scripts relevant to canvas and publish.
- [x] Run browser UAT on desktop for migrated list shell.
- [x] Run browser UAT on desktop and narrow viewport for canvas.
- [x] Save screenshots for canvas, node config, publish dialog, and run panel.
- [x] Save list-shell evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.8-list/`.
- [x] Save API Resource evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.8-api-resource/`.
- [x] Save canvas evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.8/`.

## 044.9 Cleanup, Guard, Docs, And Final Gates

> Complete. Element Plus dependency, dynamic loader, and override stylesheet are
> removed after workflow/chatflow migration.

- [x] Remove `element-plus` from `frontend/package.json`.
- [x] Remove `@element-plus/icons-vue` from `frontend/package.json`.
- [x] Remove Element Plus global install from `main.ts`.
- [x] Remove `element-plus/dist/index.css` import.
- [x] Remove or replace `styles/element-override.css`.
- [x] Add final import/style guard with no Element Plus allowlist.
- [x] Remove or bypass exploratory `frontend/src/shared/ui` UI-adapter helpers
  from production usage; 044 keeps only `app/ant-design.ts` as the required UI
  integration seam.
- [x] Update frontend architecture docs with direct Ant Design Vue usage and
  `app/ant-design.ts` guidance.
- [x] Update integration packaging docs to mention Ant Design Vue dependency.
- [x] Run `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`.
- [x] Run `rtk npm --prefix frontend run test:unit`.
- [x] Run `rtk npm --prefix frontend run build`.
- [x] Run browser UAT for main routes.
- [x] Save final evidence under
  `artifacts/slices/044-frontend-ant-design-vue-migration/044.9/`.

## Final Acceptance

> Claimable. Final frontend gates and workflow/chatflow browser UAT are green.

- [x] Ant Design Vue is the only production UI library dependency.
- [x] No production `element-plus` or `@element-plus/icons-vue` imports remain.
- [x] No production `<el-*` template tags remain.
- [x] No app-owned `.el-*` or `--el-*` CSS assumptions remain.
- [x] `app/ant-design.ts` is the only required UI integration seam.
- [x] Production feature modules use Ant Design Vue directly, without a generic
  `shared/ui` UI-library adapter layer.
- [x] Provider, MCP, Knowledge, Chat, Runtime Lab, Agent, Evaluation, and
  Workflow behavior remains compatible.
- [x] High-risk Evaluation and Workflow UAT evidence exists.
- [x] Full frontend unit gate passes.
- [x] Frontend build passes.
- [x] rem governance passes.
