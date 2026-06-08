# Spec 034: Unified Routing Chat Lab

## Goal

Add an experimental frontend conversation surface for validating the unified
runtime router with real user journeys.

034 moves the runtime-lab multi-intent SOP work from backend-only acceptance
into a browser-testable product surface. The page must let a tester open core
airline SOP scenarios, send free-form messages, observe route decisions, inspect
active/suspended task state, and compare this experimental route with the
existing ordinary Chat entry.

## Scope

In scope:

- a top-level composer menu entry for the experimental unified routing chat;
- a dedicated Vue route and page isolated from the existing `/chat` page;
- runtime-lab API client functions for session creation, message posting, task
  listing, and event listing;
- five airline SOP scenario presets matching the 032.5 backend business gate:
  `refund_ticket`, `change_flight`, `invoice_apply`, `baggage_service`, and
  `seat_checkin`;
- a simple SOP switch panel with a selected SOP and an open/start button;
- transcript rendering with route action, active task, suspended task, resume
  offer, and recent event visibility;
- frontend unit tests, REM governance tests, backend business gate reuse, and
  browser UAT evidence.

Out of scope:

- changing the production `/chat` API to `/query` or any final semantic API
  name;
- replacing the existing Chat page;
- adding frontend authoring for runtime routing rules;
- implementing FAQ/RAG/Agent/handoff policy beyond showing current runtime-lab
  decisions;
- making Chatflow import or depend on runtime-lab;
- proving live provider-backed LLM output unless live opt-in credentials are
  supplied.

## Integration Rules

- The lab page calls runtime-lab through HTTP only.
- The lab page may link to the ordinary Chat page, but it must not mutate Chat
  sessions or Agent configuration.
- Existing Chatflow remains the SOP execution substrate behind the 032 adapter.
- Runtime-lab remains the route control plane and task ledger owner.
- Frontend additions must follow REM scale governance.
- No backend route or schema change is required unless tests prove the current
  runtime-lab contract is insufficient.

## User Scenarios

The page must support these manual validation paths:

- start one SOP from the switch panel and continue it through normal messages;
- interrupt an active SOP with another SOP request;
- complete the second SOP and observe the resume offer for the suspended SOP;
- resume the suspended SOP using natural language;
- attempt a switch at a non-interruptible confirm step and observe rejection.

## Acceptance Criteria

- The composer menu exposes the experimental route.
- Browser navigation reaches the lab page without breaking existing `/chat`.
- A runtime-lab session can be created from the page.
- The selected SOP open button posts the correct start message.
- Free-form messages append user and assistant transcript rows.
- Runtime route action, active task, suspended task, and resume offer are
  visible after each turn.
- Intent samples, trigger samples, and flow reply samples can be hidden behind a
  default-on switch without disabling free-form routing.
- Testers can enable a subset of SOP intents from the sample catalog; free-form
  messages only start or switch into enabled SOPs while active continuation and
  suspended resume behavior remain available.
- The page includes a way to open the ordinary Chat surface for comparison.
- Unit and route tests pass.
- REM governance gate passes for changed frontend files.
- Backend 032.5 airline business gate still passes.
- Browser UAT exercises at least one multi-SOP jump/resume journey and saves
  evidence.

## Completion Gate

034 is complete only when:

- `spec.md`, `plan.md`, and `tasks.md` are present;
- RED test evidence is saved;
- implementation passes targeted frontend tests;
- frontend REM gate passes;
- targeted backend runtime-lab airline business gate passes;
- browser UAT evidence is saved under
  `artifacts/slices/034-unified-routing-chat-lab/`;
- one git commit contains the 034 frontend lab and evidence changes.

## 034.0 Spec Sign-off

Status: ready for 034.1 TDD.

034.0 establishes the experimental frontend boundary only. It does not change
runtime-lab routing behavior, Chatflow execution, the existing Chat page, or API
schema. Implementation must start with RED tests for the route, menu entry,
scenario model, and runtime-lab API client.

## 034 Completion Sign-off

Status: complete.

034 has delivered the isolated unified routing chat lab frontend:

- top-level composer menu entry at `/runtime-lab/chat`;
- runtime-lab API client for sessions, messages, tasks, and events;
- five airline SOP presets aligned with the 032.5 business gate;
- browser-visible transcript, route decision, task ledger, resume offer, and
  recent events;
- ordinary `/chat` comparison entry without coupling Agent chat into
  runtime-lab.

Final evidence:

- RED frontend evidence:
  `artifacts/slices/034-unified-routing-chat-lab/034.1/red.txt`;
- targeted frontend green:
  `artifacts/slices/034-unified-routing-chat-lab/034.1/green-targeted.txt`;
- REM gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.2/rem.txt`;
- full frontend unit:
  `artifacts/slices/034-unified-routing-chat-lab/034.2/frontend-unit-full.txt`;
- frontend build:
  `artifacts/slices/034-unified-routing-chat-lab/034.2/frontend-build.txt`;
- backend airline gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.2/backend-airline-gate.txt`;
- browser UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.2/browser-uat.md`.

## 034.3 Browser Acceptance Expansion Sign-off

Status: complete.

034.3 extends browser UAT only. It must not change production runtime behavior.
It expands coverage from one jump/resume journey to:

- `refund_ticket -> invoice_apply -> resume refund_ticket`;
- `change_flight -> baggage_service -> resume change_flight`;
- `seat_checkin -> refund_ticket -> resume seat_checkin`;
- confirm-step switch rejection with `REJECT_SWITCH_CONTINUE_ACTIVE`.

Evidence must be saved under
`artifacts/slices/034-unified-routing-chat-lab/034.3/`.

034.3 final evidence:

- targeted frontend route/model/API tests:
  `artifacts/slices/034-unified-routing-chat-lab/034.3/frontend-targeted.txt`;
- expanded browser UAT output:
  `artifacts/slices/034-unified-routing-chat-lab/034.3/browser-uat-output.txt`;
- expanded browser UAT report:
  `artifacts/slices/034-unified-routing-chat-lab/034.3/browser-uat.md`;
- expanded browser UAT screenshot:
  `artifacts/slices/034-unified-routing-chat-lab/034.3/browser-uat-unified-routing-chat-lab.png`.

## 034.4 Airline Scale Gate

Status: complete.

034.4 expands the lab from five demo SOPs to ten airline customer-service SOPs.
Each SOP design must expose at least five runtime nodes/steps and the catalog as
a whole must exercise LLM-style policy copy, branching/intent routing, variable
aggregation, question/confirmation, API/mock business lookup, and variable
parsing. Backend acceptance must include at least 100 realistic utterance cases,
five switch/resume journeys, and a real Chatflow-bound SOP path through
`ChatflowSopRuntimeAdapter`.

Browser UAT must use the `/runtime-lab/chat` page, not direct API only, and save
report/screenshot under
`artifacts/slices/034-unified-routing-chat-lab/034.4/`.

034.4 final coverage:

- 10 airline SOPs: refund, change, invoice, baggage, seat/check-in, flight
  status, special assistance, pet travel, irregular flight, and membership
  mileage.
- Each SOP exposes at least five designed steps, with catalog-level coverage for
  LLM, branch/condition, intent recognition, variable aggregation, question,
  API/mock lookup, and variable parsing nodes.
- Backend scale gate covers 100 realistic start utterances, collection,
  confirmation, five switch/resume journeys, and one real Chatflow-bound SOP.
- Browser UAT drives the real `/runtime-lab/chat` page against a running backend
  with `refund_ticket` bound to Chatflow and the other SOPs using fallback SOP
  runtime.

034.4 evidence:

- RED backend: `artifacts/slices/034-unified-routing-chat-lab/034.4/red-backend.txt`;
- RED frontend: `artifacts/slices/034-unified-routing-chat-lab/034.4/red-frontend.txt`;
- backend scale: `artifacts/slices/034-unified-routing-chat-lab/034.4/backend-scale.txt`;
- runtime-lab regression:
  `artifacts/slices/034-unified-routing-chat-lab/034.4/backend-runtime-lab-regression.txt`;
- workflow/chatflow regression:
  `artifacts/slices/034-unified-routing-chat-lab/034.4/backend-workflow-chatflow-regression.txt`;
- frontend full unit:
  `artifacts/slices/034-unified-routing-chat-lab/034.4/frontend-unit-full.txt`;
- browser UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.4/browser-uat.md`;
- badcases:
  `artifacts/slices/034-unified-routing-chat-lab/034.4/badcases.md`.

## 034.5 Free-Dialogue Trigger Correction

Status: complete.

The lab must model real customer entry behavior: users type arbitrary airline
service utterances, and runtime-lab routing decides whether to start or switch
SOPs. The frontend must not require a fixed `open SOP` action. Scenario
selection remains useful only as a way to filter multi-trigger sample utterances
and follow-up reply samples.

034.5 final behavior:

- no fixed `打开 SOP` button;
- each airline scenario exposes at least three realistic trigger utterances;
- clicking a trigger sample sends the same free-form message as manual typing;
- browser UAT starts and switches SOPs through free-form text only.

034.5 evidence:

- RED model gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.5/red-free-dialogue.txt`;
- frontend related/rem gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.5/frontend-related.txt`;
- browser UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.5/browser-uat.md`.

## 034.6 Strong Trigger Templates And Airline Four-Area Scale

Status: complete.

034.6 answers two routing-readiness questions:

- Strong SOP triggering can be configured with keyword templates, not only exact
  literal keywords. Templates support phrase matches, all-term matches, and
  regex matches with per-template score tuning.
- The default runtime-lab intent arbitrator remains deterministic fake mode.
  A constrained LLM arbitrator adapter now exists for injection, and every
  classifier result exposes `arbitrator_mode` and `used_real_llm` evidence so
  tests and operators can tell whether a real LLM was used.

The airline catalog is expanded to 15 SOPs across four business areas:

- sales: `flight_booking`, `fare_quote`, `group_booking`,
  `ancillary_sales`;
- refund: `refund_ticket`;
- change: `change_flight`, `passenger_info_change`;
- consultation: `invoice_apply`, `baggage_service`, `seat_checkin`,
  `flight_status`, `special_assistance`, `pet_cabin`, `irregular_flight`,
  `membership_service`.

034.6 final coverage:

- each SOP has depth >= 5 and at least three strong trigger templates;
- backend scale gate covers 150 realistic start utterances, collection,
  confirmation, five switch/resume journeys, and one real Chatflow-bound SOP;
- frontend lab exposes all 15 SOP trigger-sample groups while keeping free-form
  message entry as the actual trigger mechanism;
- browser UAT drives 15 complete journeys and five switch/resume journeys
  through `/runtime-lab/chat`.

034.6 evidence:

- RED backend:
  `artifacts/slices/034-unified-routing-chat-lab/034.6/red-backend-effective.txt`;
- backend runtime-lab gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.6/backend-runtime-lab-all-final.txt`;
- full backend pytest:
  `artifacts/slices/034-unified-routing-chat-lab/034.6/backend-full-pytest-final.txt`;
- frontend REM:
  `artifacts/slices/034-unified-routing-chat-lab/034.6/frontend-rem.txt`;
- full frontend unit:
  `artifacts/slices/034-unified-routing-chat-lab/034.6/frontend-unit.txt`;
- frontend build:
  `artifacts/slices/034-unified-routing-chat-lab/034.6/frontend-build.txt`;
- browser UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.6/browser-uat.md`;
- badcases:
  `artifacts/slices/034-unified-routing-chat-lab/034.6/badcases.md`.

## 034.7 Toggleable Sample Assistant Panel

Status: complete.

The lab now treats the left-side intent sample catalog as optional testing
assistance instead of required conversation scaffolding. The panel defaults on
for fast QA, but testers can switch it off to run pure free-form dialogue. When
off, SOP samples, trigger samples, and flow reply samples are hidden while the
composer, session controls, route inspector, task ledger, and event ledger keep
working.

034.7 evidence:

- RED browser toggle gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.7/red-samples-toggle.txt`;
- targeted frontend/rem gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.7/frontend-targeted-unit.txt`;
- full frontend unit:
  `artifacts/slices/034-unified-routing-chat-lab/034.7/frontend-unit.txt`;
- frontend build:
  `artifacts/slices/034-unified-routing-chat-lab/034.7/frontend-build.txt`;
- browser toggle UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.7/browser-uat.md`;
- browser 15-SOP scale regression:
  `artifacts/slices/034-unified-routing-chat-lab/034.7-scale/browser-uat.md`.

## 034.8 Multi-Select Enabled Intent Scope

Status: complete.

The intent sample catalog now acts as a runtime scope selector, not just a
visual sample list. Each SOP row has a checkbox. The frontend sends the selected
SOP ids as `enabledSopIds` on every runtime-lab message. Backend routing uses
that set to filter new SOP intent candidates from explicit strong triggers and
mock semantic recall, and scoped mode no longer falls back to the full SOP
catalog when no enabled intent matches. Active SOP continuation and suspended
task resume still work because they are task-state actions, not new intent
starts.

034.8 final behavior:

- default state keeps all 15 SOPs connected for broad regression testing;
- testers can deselect down to any subset, such as only A/B/C intents;
- disabled SOP utterances return `NO_MATCH` instead of starting or switching to
  a disabled SOP;
- enabled SOP utterances can still start and switch normally.

034.8 evidence:

- RED backend:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/red-backend-enabled-sop-ids.txt`;
- RED browser:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/red-browser-enabled-intents.txt`;
- backend scoped runtime-lab gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/backend-runtime-lab.txt`;
- full backend pytest:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/backend-full-pytest.txt`;
- targeted frontend/rem gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/frontend-targeted-unit.txt`;
- full frontend unit:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/frontend-unit.txt`;
- frontend build:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/frontend-build.txt`;
- ruff:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/ruff.txt`;
- browser enabled-intent UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/browser-uat-enabled-intents.md`;
- browser hide-sample regression:
  `artifacts/slices/034-unified-routing-chat-lab/034.8/browser-uat.md`;
- browser 15-SOP scale regression:
  `artifacts/slices/034-unified-routing-chat-lab/034.8-scale/browser-uat.md`.
