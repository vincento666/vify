# Spec 046: Customer Assistant Operator Panel MVP

## Goal

Build the MVP-B frontend module for the ToB customer assistant: a main-menu
operator workspace that connects to Spec 045 customer-assistant runtime APIs,
shows separate customer-side and operator-side conversation areas, and
concentrates task execution controls, recommendations, proposed actions, and
runtime evidence on the operator side.

046 is a frontend/product spec. It must not implement or redefine the 045
runtime.

## Dependency

046 depends on 045.

Implementation readiness:

- 046 can be specified before 045 completes.
- 046 frontend implementation must not start API integration until 045.5 API
  Surface is green or stable mock contracts are generated from 045.
- 046 final browser UAT and acceptance must wait for 045.6 End-To-End Runtime
  Acceptance.

Required 045 capabilities:

- `POST /api/v1/customer-assistant/sessions`;
- `POST /api/v1/customer-assistant/sessions/{sessionId}/turns`;
- `GET /api/v1/customer-assistant/sessions/{sessionId}/tasks`;
- `GET /api/v1/customer-assistant/sessions/{sessionId}/events`;
- `POST /api/v1/customer-assistant/proposed-actions/{actionId}/confirm`;
- `POST /api/v1/customer-assistant/proposed-actions/{actionId}/reject`;
- separated `operatorRecommendation` and `customerReplyDraft`;
- persisted tasks, events, and proposed actions.

## Product Boundary

In scope:

- new frontend module route under the Hify main menu;
- top-level navigation item, recommended label `客服助手`;
- module route, recommended path `/customer-assistant`;
- API client for `/v1/customer-assistant/...`;
- two conversation areas:
  - customer-side conversation/transcript;
  - operator-side assistant conversation;
- operator-side task and control panels:
  - task ledger/status list;
  - operator recommendation;
  - customer reply draft;
  - proposed action confirm/reject;
  - runtime event timeline;
  - warnings and missing fields;
- session lifecycle: create session, send turn, refresh tasks/events;
- deterministic mock mode for frontend development before 045 is complete;
- Ant Design Vue implementation aligned with 044;
- rem governance and browser UAT.

Out of scope:

- implementing the 045 backend runtime;
- replacing Runtime Lab UI;
- omnichannel inbox, queue assignment, or real telephony integration;
- multi-tenant operator permission UI;
- live SSE/WebSocket streaming transport;
- persisting turn `source`/`actor` through the backend API, repository, and
  worker input payload;
- sending the customer reply to an external channel;
- executing external write actions on proposed-action confirmation;
- mobile-first operator console beyond responsive non-overlap requirements.

## Main Menu Integration

The module must be added to Hify's main navigation:

```text
frontend/src/appNavigation.ts
  -> path: /customer-assistant
  -> label: 客服助手
  -> icon: an operator/support/chat icon from Ant Design Icons or lucide
```

The route must be registered in:

```text
frontend/src/router/index.ts
  -> /customer-assistant
  -> CustomerAssistantPanel.vue
```

Route tests must prove that the navigation entry and route exist.

## Workspace Layout

The first screen is the actual operator workspace, not a landing page.

Required layout regions:

```text
Customer Conversation
  - customer messages / imported call transcript
  - customer-side input simulator for MVP

Operator Conversation
  - operator-to-assistant messages
  - assistant turn result summary
  - customer reply draft actions

Operator Panels
  - active task list
  - recommendation detail
  - proposed actions
  - runtime events
  - warnings / missing fields
```

The functional panels are concentrated on the operator side. The customer side
must stay focused on customer-visible conversation/transcript and should not
show internal task controls.

## Conversation Semantics

MVP has two conversation lanes.

### Customer Side

Purpose:

- represent the customer's request or call transcript;
- allow an operator/tester to enter a customer utterance for the next runtime
  turn;
- show the customer-facing draft only as a draft, not as sent message unless
  the operator explicitly applies it locally.

MVP behavior:

- customer input can trigger `POST /turns`;
- customer messages appear in the customer lane;
- customer reply drafts appear as pending drafts, not automatically sent.

### Operator Side

Purpose:

- show the assistant's operator-facing recommendation;
- let the operator ask internal follow-up messages to the assistant;
- inspect tasks, events, warnings, and proposed actions;
- confirm/reject proposed actions.

MVP behavior:

- operator input can also trigger a runtime turn, with message metadata marking
  the source as operator when the 045 API supports it;
- if 045 only accepts a single message string in MVP, the frontend normalizes
  both customer and operator inputs into the same `turns` API with local source
  metadata reserved for later.

## API Client Contract

Add `frontend/src/api/customerAssistant.ts`.

Required API types:

```text
CustomerAssistantSession
CustomerAssistantTurnResult
CustomerAssistantTask
CustomerAssistantEvent
CustomerAssistantProposedAction
CustomerAssistantTaskSummary
```

Required API functions:

```text
createCustomerAssistantSession()
sendCustomerAssistantTurn(sessionId, payload)
listCustomerAssistantTasks(sessionId)
listCustomerAssistantEvents(sessionId)
confirmCustomerAssistantAction(actionId)
rejectCustomerAssistantAction(actionId)
```

The API client must preserve Hify host request conventions and the
`{code, message, data}` envelope.

## Operator Panels

### Task Ledger Panel

Show task cards or a compact table with:

- task display name;
- task key/type;
- status;
- worker type;
- current missing fields;
- last update;
- failure reason when present.

### Recommendation Panel

Show:

- `operatorRecommendation`;
- `customerReplyDraft`;
- warnings;
- per-task summaries;
- copy/apply-draft controls.

The draft must be visually and semantically separate from the recommendation.

### Proposed Actions Panel

Show proposed actions with:

- title;
- action type;
- task association;
- risk/confirmation status;
- payload summary;
- confirm and reject controls.

Confirm/reject calls update local state from the backend response. They do not
send external customer messages or execute external writes in 046.

### Event Timeline Panel

Show L0/L1 events from 045:

- run events;
- task events;
- worker summary events;
- recommendation generation;
- errors.

Debug-only payloads may be collapsed by default.

## Visual And UX Boundary

This is an operational tool, not a marketing page.

Requirements:

- dense but readable workspace;
- no decorative hero sections;
- no nested cards inside cards;
- no giant display typography inside compact panels;
- stable dimensions for conversation panes, task rows, event rows, and action
  controls;
- Ant Design Vue components directly, aligned with 044;
- no Element Plus usage;
- app-owned visual dimensions use rem, not bare px.

## Acceptance Criteria

- Main menu contains `客服助手` and routes to `/customer-assistant`.
- The module renders a two-lane conversation workspace:
  - customer side;
  - operator side.
- Operator-side panels show task ledger, recommendation, reply draft, proposed
  actions, events, and warnings.
- Creating a session and sending a turn calls the 045 API client.
- Tasks and events refresh after a turn.
- Proposed actions can be confirmed/rejected through API calls.
- Customer reply draft is never auto-sent.
- Mock mode allows frontend tests before 045 final API acceptance.
- Unit tests cover route/nav, API client, view model, and panel state.
- Browser UAT verifies the workspace at desktop and narrow widths.
- Live backend browser UAT verifies `/customer-assistant` through Vite,
  FastAPI, DB, and customer-assistant runtime without mocking
  `/api/v1/customer-assistant/**`.
- rem governance passes for all new frontend styles.

## Completion Capability

After 046, Hify has a visible ToB customer-assistant module in the main menu.
Operators can see customer context, interact with the assistant, review task
state and runtime evidence, and decide whether to use drafts or confirm
proposed actions.
