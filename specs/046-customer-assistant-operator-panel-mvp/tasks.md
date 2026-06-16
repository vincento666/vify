# Tasks 046: Customer Assistant Operator Panel MVP

## 046.0 Spec Sign-off

- [x] Confirm `046-customer-assistant-operator-panel-mvp` follows
      `045-customer-assistant-runtime-mvp`.
- [x] Confirm 046 is MVP-B frontend/operator panel scope, not backend runtime
      scope.
- [x] Confirm dependency: implementation may use mock contracts, but real API
      integration waits for 045.5 and final UAT waits for 045.6.
- [x] Confirm the module is a Hify main-menu module.
- [x] Confirm the workspace has separate customer-side and operator-side
      conversation areas, with functional panels concentrated on the operator
      side.
- [x] Save documentation evidence under
      `artifacts/slices/046-customer-assistant-operator-panel-mvp/046.0/`.

## 046.1 Route, Navigation, And API Client Contract

- [x] RED: route/navigation/API client tests fail.
- [x] Add `/customer-assistant` route.
- [x] Add `客服助手` main-menu entry.
- [x] Add `frontend/src/api/customerAssistant.ts` with typed API wrappers.
- [x] Add fixture contracts matching 045 turn/tasks/events/actions payloads.
- [x] Gates pass and evidence is saved.

## 046.2 View Model And Mock Runtime State

- [x] RED: view-model tests fail for customer/operator lanes and panels.
- [x] Implement message normalization for customer-side and operator-side
      conversations.
- [x] Implement task grouping/status summaries.
- [x] Implement recommendation and customer draft state.
- [x] Implement proposed-action confirm/reject state transitions using mocked
      API responses.
- [x] Implement event timeline formatting.
- [x] Gates pass and evidence is saved.

## 046.3 Operator Workspace UI

- [x] RED: component/static UI tests fail for required regions.
- [x] Implement `CustomerAssistantPanel.vue`.
- [x] Render customer conversation/transcript lane.
- [x] Render operator conversation lane.
- [x] Render operator task ledger panel.
- [x] Render recommendation and customer reply draft panel.
- [x] Render proposed actions panel.
- [x] Render event timeline and warnings/missing-fields panel.
- [x] Keep customer side free of internal task controls.
- [x] Run rem governance for new styles.
- [x] Gates pass and evidence is saved.

## 046.4 Real API Integration

- [x] Wait for 045.5 API Surface to be green or explicitly signed stable.
- [x] RED: integration tests fail against the real 045 API contract.
- [x] Wire create-session and send-turn actions to real API client.
- [x] Refresh tasks and events after each turn.
- [x] Confirm/reject proposed actions through the real endpoints.
- [x] Preserve mock mode only for tests/development fixtures.
- [x] Gates pass and evidence is saved.

## 046.5 Operator Interaction Polish

- [x] RED: interaction tests fail for draft/apply/action states.
- [x] Add copy/apply controls for `customerReplyDraft`.
- [x] Ensure applying a draft is local only and does not send externally.
- [x] Add loading, empty, failed, and replayed/idempotent turn states.
- [x] Add collapsed debug payloads for event details.
- [x] Add accessible labels/tooltips for icon-only controls.
- [x] Gates pass and evidence is saved.

## 046.6 Browser UAT And Final Acceptance

- [x] Wait for 045.6 End-To-End Runtime Acceptance.
- [x] Run focused frontend tests for the customer assistant module.
- [x] Run `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`.
- [x] Run full frontend unit tests.
- [x] Run frontend build if required by current slice gates.
- [x] Browser UAT desktop route `/customer-assistant`.
- [x] Browser UAT narrow viewport route `/customer-assistant`.
- [x] Verify no text overlap and no hidden action controls.
- [x] Save screenshots and UAT notes under
      `artifacts/slices/046-customer-assistant-operator-panel-mvp/046.6/`.

## 046.7 MVP Gap Closure: Production State And Live Backend UAT

- [x] RED: panel contract test proves production component still imported
      `customerAssistantFixtures` and displayed `Mock Runtime`.
- [x] Remove production `mockCustomerAssistantTurnResult` initialization.
- [x] Render production empty state until first user/operator turn creates a real
      session.
- [x] Update browser scripts that depended on initial mock data to submit a turn
      before validating draft/action controls.
- [x] Add live backend Playwright script that does not mock
      `/api/v1/customer-assistant/**`.
- [x] Run real FastAPI + Vite + browser UAT and save screenshots/evidence under
      `artifacts/slices/046-customer-assistant-operator-panel-mvp/046.live-backend/`.
- [x] Record `source`/`actor` backend persistence as post-MVP follow-up because
      current API still accepts only `message` and `idempotencyKey`.

## Later Specs

- [ ] SSE/WebSocket live runtime events.
- [ ] Persist turn `source`/`actor` through customer assistant API, repository,
      and worker input payload.
- [ ] real omnichannel customer inbox.
- [ ] operator assignment and queue management.
- [ ] call transcript import and speech integration.
- [ ] sending approved customer drafts to external channels.
- [ ] proposed-action external write execution after explicit confirmation.
- [ ] multi-session/multi-customer operator dashboard.
