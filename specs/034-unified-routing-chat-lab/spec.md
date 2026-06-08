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
- Testers can clear the current lab conversation and start a fresh runtime-lab
  session without reloading the page.
- Flight-booking utterances use sales collection language for route/time/contact
  details and must not ask for an order number before a ticket exists.
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

## 034.9 Natural Booking And Session Reset Hardening

Status: complete.

034.9 fixes three user-visible lab badcases found during manual UAT:

- `我要定航班` did not match because the booking trigger catalog covered common
  `订` phrases but missed `定航班` / `定机票` variants.
- Flight booking reused the generic SOP collection prompt, so a sales flow could
  ask for an order number before a ticket existed.
- The lab did not expose a direct way to clear the current transcript and start
  a fresh runtime-lab session.

034.9 final behavior:

- `我要定航班` and detailed booking utterances start `flight_booking` through
  free-form routing.
- Booking starts by asking for missing origin, destination, travel time, phone,
  and passenger details. It does not ask for `订单号`.
- Booking start/continue can parse route, time, phone, and passenger variables
  from natural customer messages.
- Non-booking SOP start state keeps the existing empty `business_refs`
  contract, so active-task semantic switching is not mutated before routing
  arbitration.
- The page header includes `清空会话`, which creates a new runtime-lab session
  and clears transcript, route decision, task, and event state.

034.9 evidence:

- RED backend booking badcase:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/red-backend-booking.txt`;
- RED browser reset badcase:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/red-browser-reset.txt`;
- targeted backend runtime-lab gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/backend-runtime-lab.txt`;
- full backend pytest:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/backend-full-pytest.txt`;
- targeted frontend/rem gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/frontend-targeted-unit.txt`;
- full frontend unit:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/frontend-unit.txt`;
- frontend build:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/frontend-build.txt`;
- ruff:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/ruff.txt`;
- browser natural booking UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/browser-booking-natural.md`;
- browser session reset UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/browser-reset-session.md`;
- browser enabled-intent regression:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/browser-uat-enabled-intents.md`;
- browser sample-toggle regression:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/browser-uat.md`;
- browser 15-SOP/5-switch scale regression:
  `artifacts/slices/034-unified-routing-chat-lab/034.9-scale/browser-uat.md`.
- browser 15-SOP/5-switch Chatflow-bound regression output:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/browser-scale-chatflow-bound.txt`.
- workflow step-limit fixture hardening:
  `artifacts/slices/034-unified-routing-chat-lab/034.9/workflow-failure-behavior.txt`.

Full backend pytest initially exposed an unrelated workflow fixture badcase:
`test_step_limit_fails_cleanly_and_records_failed_run` used a self-looping `LLM`
node, so local databases with a configured live LLM agent could make the test
call an external provider 50 times before hitting step limit. The fixture now
uses a provider-free `MESSAGE` node while preserving the same step-limit
assertion, and full backend pytest passes.

Browser Chatflow-bound UAT also exposed a fixture badcase: a temporary refund
fixture used `VARIABLE_PARSE`, which is valid as mock SOP design coverage but is
not a currently executable Chatflow engine node type. The browser binding was
rebuilt with executable Chatflow nodes (`INFORMATION_COLLECTION`,
`VARIABLE_AGGREGATION`, `QUESTION`, `END`), then rerun with
`Chatflow-bound refund SOP: yes`.

## 034.10 Test-Stage OpenRouter Free LLM Arbitrator

Status: complete.

034.10 adds a live acceptance harness for testing real LLM intent arbitration
with OpenRouter free text models. This is explicitly a test-stage mechanism and
does not change production runtime-lab configuration. Production/runtime-lab
still uses exactly one LLM arbitrator model from system settings
(`runtime_lab_intent_arbitrator_model`) when `runtime_lab_intent_arbitrator_mode`
is `llm`.

034.10 final behavior:

- ordinary CI keeps using deterministic fake arbitration by default;
- production LLM arbitration remains single-model and system-configured;
- live 034.10 acceptance is opt-in via
  `HIFY_RUN_LIVE_RUNTIME_LAB_OPENROUTER_FREE_ARBITRATOR=1` plus
  `OPENROUTER_API_KEY`;
- the live harness discovers free text-output models from OpenRouter `/models`
  at runtime, using zero prompt and completion pricing as the filter;
- the test-stage harness tries free models one by one for a finite-candidate
  runtime-lab switch decision, skipping quota, transport, invalid JSON, and
  valid-but-wrong test-stage decisions;
- if free models do not produce a valid expected decision, the harness tries
  `xiaomi/mimo-v2-flash` as the final test-stage fallback.

034.10 evidence:

- OpenRouter free model discovery snapshot:
  `artifacts/slices/034-unified-routing-chat-lab/034.10/openrouter-free-model-discovery.txt`;
- opt-in live acceptance skipped in ordinary environment:
  `artifacts/slices/034-unified-routing-chat-lab/034.10/openrouter-free-arbitrator-skip.txt`;
- targeted backend gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.10/backend-targeted.txt`;
- full backend pytest:
  `artifacts/slices/034-unified-routing-chat-lab/034.10/backend-full-pytest.txt`;
- ruff:
  `artifacts/slices/034-unified-routing-chat-lab/034.10/ruff.txt`.

## 034.11 Live OpenRouter Full-Chain Acceptance

Status: complete.

034.11 verifies that the live LLM paths are not merely tested in isolation. It
uses one RuntimeLab session where a user starts a refund SOP, switches to an
invoice SOP, completes the invoice SOP, resumes the refund SOP, and completes
the refund SOP. The switch decision must be arbitrated by a real OpenRouter LLM,
and both SOP completion replies must come from real provider-backed Chatflow
`LLM` nodes. For speed and focused optimization, this gate uses
`qwen/qwen3.5-9b` as the default single target model. Latency-insensitive,
higher-intelligence investigations can opt into `deepseek/deepseek-v4-flash`
through the same model configuration surface.

034.11 final behavior:

- the intent arbitrator uses a single live OpenRouter target model, defaulting
  to `qwen/qwen3.5-9b`;
- the optional high-intelligence model for slower investigations is
  `deepseek/deepseek-v4-flash`;
- the SOP `LLM` nodes use the single configured Chatflow provider model;
- production/runtime-lab configuration remains single-model and unchanged;
- the route decision evidence must show `arbitrator_mode=llm` and
  `used_real_llm=true`;
- completed SOP replies must contain the live marker and must not contain
  `LLM mock:`, `Workflow mock:`, or `RAG mock:`;
- qwen-specific badcases are recorded as optimization input: reasoning-only
  output under too-small token limits, and provider rejection of multiple
  system messages;
- ordinary CI skips the live full-chain gate unless
  `HIFY_RUN_LIVE_RUNTIME_LAB_OPENROUTER_FULL_CHAIN=1` and
  `OPENROUTER_API_KEY` are set.

034.11 evidence:

- live full-chain OpenRouter acceptance:
  `artifacts/slices/034-unified-routing-chat-lab/034.11/live-openrouter-full-chain.md`;
- qwen full-chain command output:
  `artifacts/slices/034-unified-routing-chat-lab/034.11/qwen-full-chain.txt`;
- qwen 5-SOP live Chatflow LLM command output:
  `artifacts/slices/034-unified-routing-chat-lab/034.11/qwen-chatflow-sop-llm.txt`;
- ordinary non-live targeted acceptance:
  `artifacts/slices/034-unified-routing-chat-lab/034.11/non-live-targeted.txt`;
- full backend pytest:
  `artifacts/slices/034-unified-routing-chat-lab/034.11/backend-full-pytest.txt`;
- ruff:
  `artifacts/slices/034-unified-routing-chat-lab/034.11/ruff.txt`.

## 034.12 Mixed Natural Core Airline Routing Gate

Status: complete.

034.12 adds a smaller but more realistic airline business gate across the four
core areas: booking, refund, change, and consultation. The corpus contains 40
natural utterances, 10 per area. These utterances are not direct fixed commands;
they describe realistic travel, refund, change, and flight-status contexts while
still carrying enough business signal for deterministic routing when that is the
correct production behavior.

034.12 final behavior:

- all 40 natural scenarios complete their primary SOP through strong
  explicit/keyword routing;
- qwen LLM arbitration is exercised by representative active-task switch
  journeys, not forced for every scenario;
- representative live journeys follow the supported single-suspended-task
  pattern:
  `A start -> B switch -> B complete -> resume A -> A complete -> C complete`;
- representative live journeys use qwen-backed Chatflow `LLM` nodes for SOP
  completion markers;
- `deepseek/deepseek-v4-flash` remains documented as the optional
  high-intelligence model for slower investigations;
- badcases are recorded for provider timeout/reset behavior, contaminated test
  details that accidentally requested a different business SOP, and the test
  design issue of over-forcing LLM arbitration.

034.12 evidence:

- mixed routing summary:
  `artifacts/slices/034-unified-routing-chat-lab/034.12/mixed-routing-summary.md`;
- qwen live representative core airline output:
  `artifacts/slices/034-unified-routing-chat-lab/034.12/qwen-core-airline-live-output.txt`;
- qwen live representative journey detail:
  `artifacts/slices/034-unified-routing-chat-lab/034.12/qwen-core-airline-live.md`;
- non-live 40-case core airline output:
  `artifacts/slices/034-unified-routing-chat-lab/034.12/non-live-core-airline.txt`;
- badcase notes:
  `artifacts/slices/034-unified-routing-chat-lab/034.12/red-timeout.md`;
- ruff:
  `artifacts/slices/034-unified-routing-chat-lab/034.12/ruff.txt`.
