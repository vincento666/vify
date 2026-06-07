# Tasks 034: Unified Routing Chat Lab

## 034.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Define isolated frontend lab scope.
- [x] Preserve one-way runtime-lab integration boundary.
- [x] Document browser UAT and backend gate requirements.

## 034.1 Frontend route, model, and API TDD

- [x] RED: route/menu test fails before implementation.
- [x] RED: SOP scenario model test fails before implementation.
- [x] RED: runtime-lab API client test fails before implementation.
- [x] Implement composer menu entry and Vue route.
- [x] Implement runtime-lab API client.
- [x] Implement SOP scenario presets and transcript helpers.
- [x] Implement `UnifiedRoutingChatLab.vue`.
- [x] Save RED and GREEN evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.1/`.

## 034.2 High-spec gates and browser UAT

- [x] Run targeted frontend tests.
- [x] Run frontend REM governance gate.
- [x] Run targeted backend runtime-lab airline business gate.
- [x] Run frontend build gate.
- [x] Run full frontend unit gate.
- [x] Run browser UAT against the lab page.
- [x] Save UAT notes and screenshot under
  `artifacts/slices/034-unified-routing-chat-lab/034.2/`.
- [x] Commit 034 changes.

## 034.3 Browser acceptance expansion

- [x] Extend browser UAT to three multi-SOP jump/resume journeys.
- [x] Add confirm-step non-interruptible rejection browser coverage.
- [x] Save UAT notes and screenshot under
  `artifacts/slices/034-unified-routing-chat-lab/034.3/`.
- [x] Run targeted frontend route/model/API tests.
- [x] Run expanded browser UAT.
- [x] Commit 034.3 changes.

## Future specs, not 034 tasks

- [ ] Rename or consolidate final user-facing API to `/chat` or `/query`.
- [ ] Add FAQ/RAG/Agent/handoff fallback UI.
- [ ] Add route-rule authoring and policy tuning UI.
- [ ] Run live provider-backed LLM browser acceptance by default.
