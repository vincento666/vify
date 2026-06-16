# Feature Spec: Customer Assistant Worker Profile Config Surface

## Status

Complete.

## User Story

As a customer-assistant operator preparing the MVP demo, I can see the configured worker profiles that the current demo tenant will use before and during a session, including each task type, worker route, model policy, prompt, tool refs, risk policy, and enabled state.

## Functional Requirements

- The customer assistant workbench must render a dedicated worker profile configuration panel loaded from `/api/v1/customer-assistant/worker-profiles`.
- Each profile row must show `taskType`, `taskKey`, `workerType`, `workerRef`, `modelPolicyRef`, `promptRef`, `toolRefs`, `riskPolicyRef`, and enabled state.
- The panel must expose loading and error state from the existing worker profile load path.
- Existing task rows must continue to show matched profile metadata for active tasks.
- If the existing frontend API helper remains sufficient, operators may edit a profile from the configuration panel and save through `updateCustomerAssistantWorkerProfile`.
- The slice must stay inside `frontend/src/views/customerAssistant`, `frontend/e2e/customer-assistant-*`, `specs/110-customer-assistant-worker-profile-config-surface`, and matching evidence artifacts.

## Non-Goals

- Changing backend worker profile APIs, seed data, runtime lab, workflow runtime, live acceptance, or knowledge-QA behavior.
- Adding new profile fields or changing profile matching semantics.
- Building a full admin page with create/delete/version history.

## Acceptance Criteria

- RED frontend test proves the operator workbench lacks a dedicated configured profile panel.
- Focused frontend tests pass after implementation.
- Frontend rem gate passes because this slice touches Vue/CSS visual code.
- Browser UAT verifies the panel loads profile data in the customer assistant workbench and captures a screenshot.
- SDD tasks and evidence are updated and the slice is committed when gates pass.

## Evidence

Evidence lives under `artifacts/slices/110-customer-assistant-worker-profile-config-surface/110.1/`.

- RED: `red.txt`
- Focused frontend unit: `frontend-customer-assistant.txt`
- Full frontend unit: `frontend-unit-full.txt`
- Frontend build: `frontend-build.txt`
- Frontend rem: `frontend-rem.txt`
- Browser UAT: `uat.md`
- Screenshot: `screenshots/worker-profile-config-surface.png`
