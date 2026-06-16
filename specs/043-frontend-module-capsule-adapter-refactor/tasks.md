# Tasks 043: Frontend Module Capsule Adapter Refactor

## 043.0 Spec And Boundary

- [x] Confirm latest spec number is `043`.
- [x] Confirm Workflow remains one Module capsule with Workflow, Chatflow,
  Canvas, API Resource, and Observe.
- [x] Confirm Chat and Runtime Lab are separate Module capsules.
- [x] Confirm Agent and Evaluation use shared adapters for cross-Module
  resources and links.
- [ ] Record initial frontend dependency inventory under
  `artifacts/slices/043-frontend-module-capsule-adapter-refactor/043.0/`.

## 043.1 Shared Seam Foundation

- [ ] RED: direct imports cannot yet use `shared/resource` ports.
- [ ] Add `src/shared/api/request.ts` and compatibility exports.
- [ ] Add `src/shared/host/request.ts` and compatibility exports.
- [ ] Add `src/shared/ui` exports for base table/dialog/confirm/notify.
- [ ] Add `src/shared/resource/ports.ts`.
- [ ] Add `src/shared/resource/hifyAdapters.ts`.
- [ ] Add `src/shared/resource/registry.ts`.
- [ ] Add `src/shared/navigation/linkResolver.ts`.
- [ ] Add unit tests for resource registry default adapter behavior.
- [ ] Save RED/GREEN evidence under `artifacts/slices/043-frontend-module-capsule-adapter-refactor/043.1/`.

## 043.2 Router And Navigation Aggregation

- [ ] RED: route aggregation module does not exist.
- [ ] Add `src/app/router.ts` to compose Module route exports.
- [ ] Add `src/app/navigation.ts` to compose Module nav exports.
- [ ] Add initial `routes.ts` and `nav.ts` for each Module.
- [ ] Keep existing route paths compatible.
- [ ] Update `src/router/index.ts` to delegate to `src/app/router.ts`.
- [ ] Update `src/appNavigation.ts` to delegate to `src/app/navigation.ts`.
- [ ] Add tests proving existing paths and menu order remain stable.
- [ ] Save evidence under `artifacts/slices/043-frontend-module-capsule-adapter-refactor/043.2/`.

## 043.3 Provider, MCP, Knowledge Capsules

- [ ] RED: module import guard fails for current scattered structure.
- [ ] Move Provider pages/model/API to `src/modules/provider`.
- [ ] Move MCP pages/model/API to `src/modules/mcp`.
- [ ] Move Knowledge pages/model/API to `src/modules/knowledge`.
- [ ] Preserve compatibility imports if needed for incremental rollout.
- [ ] Prove each low-risk capsule imports only itself, `shared/*`, and libraries.
- [ ] Run focused module route/page tests.
- [ ] Save evidence under `artifacts/slices/043-frontend-module-capsule-adapter-refactor/043.3/`.

## 043.4 Workflow Capsule Move

- [ ] RED: Workflow capsule route export cannot serve all existing Workflow,
  Chatflow, API Resource, Observe, and Canvas routes.
- [ ] Move `views/workflow/*` to `src/modules/workflow`.
- [ ] Keep Workflow, Chatflow, Canvas, API Resource, and Observe in one capsule.
- [ ] Move `api/workflow.ts` and `api/observe.ts` into Workflow capsule or
  expose through Workflow capsule public API.
- [ ] Preserve route behavior for `/workflows`, `/chatflows`,
  `/workflow/api-resources`, and `/observe`.
- [ ] Do not refactor `WorkflowCreate.vue` internals beyond path/import changes.
- [ ] Run focused workflow route/canvas tests and rem gate.
- [ ] Save evidence under `artifacts/slices/043-frontend-module-capsule-adapter-refactor/043.4/`.

## 043.5 Chat And Runtime Lab Split

- [ ] RED: Runtime Lab still shares Chat Module directory.
- [ ] Move `ChatView.vue` and chat API/model to `src/modules/chat`.
- [ ] Move `UnifiedRoutingChatLab.vue`, `unifiedRoutingChatLab.ts`, and
  runtimeLab API/model to `src/modules/runtime-lab`.
- [ ] Add `AgentCatalogPort` usage in Chat for runnable Agent choices.
- [ ] Add shared link resolver usage in Runtime Lab for Chatflow canvas/debug.
- [ ] Preserve `/chat` and `/runtime-lab/chat` routes.
- [ ] Run focused chat/runtime-lab tests and browser UAT.
- [ ] Save evidence under `artifacts/slices/043-frontend-module-capsule-adapter-refactor/043.5/`.

## 043.6 Agent Resource Adapters

- [ ] RED: Agent imports raw cross-Module APIs directly.
- [ ] Replace Agent direct model/provider dependency with `ModelCatalogPort`.
- [ ] Replace Knowledge dependency with `KnowledgeCatalogPort`.
- [ ] Replace MCP dependency with `ToolCatalogPort`.
- [ ] Replace Workflow/Chatflow dependency with `FlowCatalogPort`.
- [ ] Replace preview Chat dependency with `AgentPreviewPort`.
- [ ] Replace hard-coded cross-Module links with `linkResolver`.
- [ ] Keep Agent workbench behavior unchanged.
- [ ] Run focused Agent list/workbench/preview tests and browser UAT.
- [ ] Save evidence under `artifacts/slices/043-frontend-module-capsule-adapter-refactor/043.6/`.

## 043.7 Evaluation Target Adapters

- [ ] RED: Evaluation imports raw Agent/Workflow APIs directly.
- [ ] Add `EvaluationTargetCatalogPort`.
- [ ] Replace Agent target loading through target catalog adapter.
- [ ] Replace Workflow/Chatflow target loading through target catalog adapter.
- [ ] Replace target evidence/debug URLs through `linkResolver`.
- [ ] Preserve Evaluation Workbench tabs, Eval Set detail, reports, compare,
  CSV import/export behavior.
- [ ] Run focused Evaluation tests and browser UAT.
- [ ] Save evidence under `artifacts/slices/043-frontend-module-capsule-adapter-refactor/043.7/`.

## 043.8 Import Guard, Docs, And Packaging

- [ ] Add architecture/import guard preventing `modules/A` from importing
  `modules/B/pages` or `modules/B/model`.
- [ ] Add docs for host integration of one Module capsule.
- [ ] Update frontend packaging docs so test files can still be excluded from
  integration export.
- [ ] Run full frontend unit gate.
- [ ] Run frontend build.
- [ ] Run browser UAT for main menu routes.
- [ ] Save evidence under `artifacts/slices/043-frontend-module-capsule-adapter-refactor/043.8/`.

## Final Acceptance

- [ ] All 043 slices complete.
- [ ] `frontend/src/modules/*` contains production Module capsules.
- [ ] `frontend/src/shared/*` contains public seams.
- [ ] `frontend/src/app/*` composes router/nav/shell.
- [ ] Agent and Evaluation use adapters for cross-Module resources.
- [ ] Chat and Runtime Lab are separate capsules.
- [ ] Workflow remains one capsule with Chatflow tabs.
- [ ] Import guard passes.
- [ ] Full frontend tests and build pass.
- [ ] Browser UAT evidence recorded.
