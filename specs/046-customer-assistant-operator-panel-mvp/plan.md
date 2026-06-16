# Plan 046: Customer Assistant Operator Panel MVP

## Architecture

Add a new frontend module:

```text
frontend/src/api/customerAssistant.ts
frontend/src/views/customerAssistant/
├── CustomerAssistantPanel.vue
├── customerAssistantViewModel.ts
├── customerAssistantViewModel.test.ts
├── customerAssistantApi.test.ts
├── customerAssistantRoutes.test.ts
└── customerAssistantRemGovernance.test.ts
```

Wire it into:

```text
frontend/src/appNavigation.ts
frontend/src/router/index.ts
```

Use Ant Design Vue directly, consistent with Spec 044. Do not introduce a
generic UI-library adapter.

## Dependency Handling

046 should use a typed API client and deterministic fixture data while 045 is
still being implemented.

Implementation modes:

```text
contract/mock mode
  -> view model tests and static UI can run before 045.5

real API mode
  -> enabled after 045.5 API Surface is stable

final UAT
  -> after 045.6 E2E Runtime Acceptance
```

The frontend contract must track 045 names:

```text
operatorRecommendation
customerReplyDraft
taskSummaries
proposedActions
warnings
events
```

If 045 changes API fields, 046 must update the API client and view model
together.

## Layout Plan

Recommended desktop layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ Customer Assistant module toolbar                             │
├───────────────────────┬───────────────────────┬──────────────┤
│ Customer conversation │ Operator conversation │ Operator     │
│ / transcript          │ / assistant turns     │ panels       │
│                       │                       │              │
│ customer input        │ operator input        │ tasks        │
│                       │ reply draft           │ actions      │
│                       │ recommendation        │ events       │
└───────────────────────┴───────────────────────┴──────────────┘
```

Narrow layout may stack the operator panels below conversations, but text and
controls must not overlap.

## View Model

Keep interaction logic outside the Vue template where possible:

- session creation state;
- message list normalization;
- current turn status;
- task status grouping;
- event timeline formatting;
- proposed action confirmation state;
- copy/apply draft state;
- warning and missing-field summaries.

The view model should accept fixture data so tests can validate UI state before
the backend is complete.

## API Client

Implement typed wrappers:

```text
createCustomerAssistantSession
sendCustomerAssistantTurn
listCustomerAssistantTasks
listCustomerAssistantEvents
confirmCustomerAssistantAction
rejectCustomerAssistantAction
```

Use existing request utilities and host fetch conventions. Keep payload shapes
close to 045 and expose frontend-friendly types.

## UX Notes

- The customer side represents the external customer conversation or call
  transcript.
- The operator side is where the human works with the assistant.
- Customer reply draft is reviewable text, not an automatic outbound message.
- Proposed actions require explicit operator confirm/reject.
- Event details should be expandable to avoid visual noise.
- Task status should remain visible while the operator reads recommendations.

## Testing Strategy

Required tests:

- route/nav test for `/customer-assistant` and main-menu entry;
- API client path/payload tests;
- view-model tests for turn result normalization;
- proposed-action confirm/reject state tests;
- component smoke/render test when existing frontend test tooling supports it;
- rem governance test for new view styles.

Required gates:

- focused unit tests for new module;
- `frontend/src/remScaleClosure.test.ts` when visual files are added;
- full frontend unit test before completion;
- browser UAT screenshots after 045.6 is available.

## Slice Order

046.0 -> 046.1 -> 046.2 -> 046.3 -> 046.4 -> 046.5 -> 046.6
