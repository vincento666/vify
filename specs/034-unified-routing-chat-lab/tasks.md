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

## 034.4 Airline scale gate

- [x] RED: backend scale gate fails before 10 deep SOP manifests exist.
- [x] RED: frontend scenario model fails before 10 SOP presets exist.
- [x] Implement 10 airline SOP manifests with depth >= 5 and common node-type coverage.
- [x] Add realistic 100+ backend routing/collection/completion cases.
- [x] Keep real Chatflow-bound SOP path covered through runtime-lab adapter.
- [x] Run targeted frontend model test.
- [x] Run backend scale gate and existing runtime-lab E2E gates.
- [x] Run browser UAT through `/runtime-lab/chat` with 10 SOP surface.
- [x] Save badcase/fix notes and evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.4/`.
- [x] Commit 034.4 changes.

## 034.5 Free-dialogue trigger correction

- [x] RED: frontend scenario model fails until scenarios expose multiple free-form trigger utterances.
- [x] Remove the fixed `打开 SOP` action from the browser lab.
- [x] Keep scenario selection as trigger-sample filtering only.
- [x] Make trigger samples send realistic free-form user utterances through runtime-lab routing.
- [x] Run targeted frontend and REM gates.
- [x] Run browser UAT through `/runtime-lab/chat` with free-form trigger starts.

## 034.6 Strong trigger templates and four-area airline scale

- [x] RED: backend gate fails before strong trigger templates, classifier LLM metadata, and 15 SOP manifests exist.
- [x] Add configurable strong trigger templates for phrase, all-term, and regex matching.
- [x] Preserve deterministic fake classifier as default and expose `arbitrator_mode` / `used_real_llm`.
- [x] Add injectable constrained LLM arbitrator adapter for real LLM integration.
- [x] Expand airline catalog to 15 SOPs across sales, refund, change, and consultation.
- [x] Add 100+ realistic free-form start utterances with average turn length >= 5 characters.
- [x] Tune badcase routing collisions from the expanded corpus.
- [x] Update frontend lab scenario catalog to all 15 SOPs.
- [x] Run backend runtime-lab gates, full backend pytest, frontend REM, full frontend unit, frontend build, ruff, and browser UAT.
- [x] Save badcase/fix notes and evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.6/`.

## 034.7 Toggleable sample assistant panel

- [x] RED: browser UAT fails until the intent-sample visibility toggle exists.
- [x] Add a default-on switch to the intent sample panel.
- [x] Hide SOP samples, trigger samples, and flow reply samples when the switch is off.
- [x] Keep the free-form composer and runtime route inspector usable while samples are hidden.
- [x] Run targeted frontend/rem gate.
- [x] Run full frontend unit gate.
- [x] Run frontend build gate.
- [x] Run browser UAT for the toggle behavior.
- [x] Run the existing 15-SOP/5-switch browser scale UAT as regression.
- [x] Save evidence under `artifacts/slices/034-unified-routing-chat-lab/034.7/`
  and `artifacts/slices/034-unified-routing-chat-lab/034.7-scale/`.

## 034.8 Multi-select enabled intent scope

- [x] RED: backend gate fails until `enabledSopIds` scopes new SOP intent routing.
- [x] RED: browser UAT fails until each SOP sample exposes a selectable toggle.
- [x] Add `enabledSopIds` to runtime-lab message requests.
- [x] Filter explicit strong triggers and semantic recall to the enabled SOP set.
- [x] Prevent scoped routing from falling back to the full SOP catalog when no enabled candidate matches.
- [x] Keep active-task continuation and suspended-task resume available while new intents are scoped.
- [x] Replace frontend single selection with per-SOP checkbox multi-select.
- [x] Send the selected enabled SOP ids with every free-form message and sample click.
- [x] Run targeted backend, full backend pytest, frontend/rem, full frontend unit, build, ruff, and browser UAT.
- [x] Run the existing hide-sample and 15-SOP/5-switch browser UAT regressions.
- [x] Save evidence under `artifacts/slices/034-unified-routing-chat-lab/034.8/`
  and `artifacts/slices/034-unified-routing-chat-lab/034.8-scale/`.

## 034.9 Natural booking and session reset hardening

- [x] RED: backend gate fails until `我要定航班` starts `flight_booking`.
- [x] RED: backend gate fails until booking starts with sales collection language,
  not order-number collection language.
- [x] RED: browser UAT fails until the lab exposes a visible session reset
  control.
- [x] Add `定航班`/`定机票` style strong trigger coverage for flight booking.
- [x] Parse booking start utterances for origin, destination, travel time,
  phone, and passenger variables without requiring an order number.
- [x] Keep non-booking SOP start state compatible with existing
  `business_refs == {}` contracts.
- [x] Add a `清空会话` button that creates a fresh runtime-lab session and clears
  transcript/task/event state.
- [x] Harden the workflow step-limit fixture so full backend gates do not depend
  on a configured live LLM provider.
- [x] Run targeted backend runtime-lab gates and 100+ airline scale cases.
- [x] Run browser UAT for natural booking, session reset, enabled-intent scope,
  sample toggle, and 15-SOP/5-switch Chatflow-bound scale regression.
- [x] Save evidence under `artifacts/slices/034-unified-routing-chat-lab/034.9/`
  and `artifacts/slices/034-unified-routing-chat-lab/034.9-scale/`.

## Future specs, not 034 tasks

- [ ] Rename or consolidate final user-facing API to `/chat` or `/query`.
- [ ] Add FAQ/RAG/Agent/handoff fallback UI.
- [ ] Add route-rule authoring and policy tuning UI.
- [ ] Run live provider-backed LLM browser acceptance by default.
