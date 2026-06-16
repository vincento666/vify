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

Architecture note updated on 2026-06-09: 034.6 completed the original strong
trigger template capability. In the latest 036-042 routing architecture, those
templates and keyword hits are treated as candidate-recall signals for SOP
intent candidates. They are not final non-hard-stop exits. Only explicit
handoff/safety hard stops may finish before central constrained LLM
arbitration.

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
  explicit/keyword candidate recall plus arbitration. Historical 034 evidence
  used the older strong-routing path; 036-040 R1 proves the current central
  arbitration path for non-hard-stop decisions;
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

## 034.13 Dev-Seeded Airline Chatflow Configuration

Status: complete.

034.13 promotes the 034 airline SOP corpus from test fixtures into the current
development database/system configuration. The runtime-lab frontend now exposes
which Chatflow IDs are bound, which arbitrator mode is active, and which model
is configured, so testers can tell whether they are using fake routing, live LLM
routing, and real Chatflow-backed SOPs.

034.13 final behavior:

- a seed script creates or updates 15 published airline Chatflow SOPs in the
  current development database;
- the seed script writes local RuntimeLab binding settings without writing API
  keys to `.env`;
- a live Chatflow LLM agent/provider can be seeded from process environment for
  local full-chain testing;
- `/api/v1/runtime-lab/config` returns SOP binding IDs/names plus arbitrator
  mode/model/base URL/key availability without exposing secrets;
- the runtime-lab service injects Chatflow agent/model repositories when
  Chatflow SOP bindings are configured, allowing SOP `LLM` nodes to call the
  seeded provider;
- the frontend config panel displays bound Chatflow count, expanded SOP-to-ID
  rows, arbitrator mode, configured model, key state, and availability;
- browser UAT confirms the path
  `flight_status -> flight_booking -> resume flight_status -> refund_ticket`
  through the visible `/runtime-lab/chat` page.

034.13 seeded Chatflow IDs in the current development database:

```text
flight_booking: 5906
fare_quote: 5907
group_booking: 5908
ancillary_sales: 5909
refund_ticket: 5910
change_flight: 5911
passenger_info_change: 5912
invoice_apply: 5913
baggage_service: 5914
seat_checkin: 5915
flight_status: 5916
special_assistance: 5917
pet_cabin: 5918
irregular_flight: 5919
membership_service: 5920
```

034.13 badcases/fixes:

- `flight_status` sample replies used order-number fields even though the
  Chatflow requires a flight number; fixed the sample to provide `航班号 CA6034`.
- active booking detail like `经济舱，价格优先` could be misread as ticket-price
  consultation; tightened fare quote matching and preserved high-confidence
  active continuation.
- resuming a suspended task while another task is active could surface as a
  server error; now returns a route rejection instead of failing the request.

034.13 evidence:

- RED summary:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/red-summary.md`;
- seed output:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/seed-output.txt`;
- config API output:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/config-api.json`;
- targeted backend gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/backend-targeted.txt`;
- targeted frontend/rem gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/frontend-targeted-rem.txt`;
- full backend pytest:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/backend-full.txt`;
- full frontend unit:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/frontend-full.txt`;
- ruff:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/ruff.txt`;
- browser UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/browser-uat.md`;
- browser transcript:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/browser-transcript.json`;
- screenshots:
  `artifacts/slices/034-unified-routing-chat-lab/034.13/screenshots/config-panel.png`,
  `artifacts/slices/034-unified-routing-chat-lab/034.13/screenshots/full-flow.png`.

## 034.14 Enabled-Scope LLM Fallback Arbitration

Status: complete.

034.14 fixes a funnel-routing gap exposed by manual browser use. The utterance
`我要订广州飞北京的航班` did not hit a strong trigger template and the current
mock semantic recall did not return a candidate. Because the frontend sends the
enabled SOP scope, runtime-lab incorrectly returned `NO_MATCH` before invoking
the configured LLM arbitrator.

034.14 final behavior:

- strong trigger/template matching remains unchanged and does not fake a match
  for the badcase;
- real embedding/vector retrieval is still not implemented in 034;
- when explicit and semantic recall return no candidates but `enabledSopIds`
  contains SOPs, runtime-lab builds a finite `enabled_scope_fallback` candidate
  pool;
- fake arbitration keeps this fallback below the deterministic confidence
  threshold and returns clarification instead of selecting the first SOP;
- live/scripted LLM arbitration can select from the finite fallback pool;
- qwen live arbitration selects `flight_booking` for
  `我要订广州飞北京的航班` with `used_real_llm=true`.

034.14 evidence:

- RED summary:
  `artifacts/slices/034-unified-routing-chat-lab/034.14/red-summary.md`;
- live API summary:
  `artifacts/slices/034-unified-routing-chat-lab/034.14/live-api-summary.md`;
- targeted backend tests:
  `tests/unit/runtime_lab/test_explicit_signals.py`,
  `tests/integration/runtime_lab/test_runtime_lab_semantic_policy.py`.

## 034.15 Funnel Observability And No-Template-Padding Gate

Status: complete.

034.15 clarifies the intended routing architecture and adds browser-visible
evidence so manual UAT can tell whether a turn passed through the real funnel or
was merely covered by a broad trigger template. The current 034 implementation
does not yet include real embedding/vector retrieval; it has strong trigger
templates, mock semantic recall, enabled-scope finite candidate fallback, and
constrained LLM arbitration.

034.15 final behavior:

- do not widen strong trigger/templates just to raise pass rate for natural
  utterances;
- when light matching misses, enabled-scope fallback candidates are handed to
  the configured finite arbitrator;
- the route inspector displays `funnel`, `source`, and `arbitrator` evidence;
- the badcase `我要订广州飞北京的航班` is verified as
  `enabled_scope_fallback -> post_classifier -> llm real -> flight_booking`;
- real embedding/vector confidence scoring remains a future task, not a hidden
  claim of 034.

034.15 evidence:

- analysis:
  `artifacts/slices/034-unified-routing-chat-lab/034.15/funnel-routing-analysis.md`;
- live funnel response:
  `artifacts/slices/034-unified-routing-chat-lab/034.15/live-funnel-response.json`.

## 034.16 Chatflow Followup And Live Chain Hardening

Status: complete.

034.16 fixes the remaining manual badcases found while replaying
`我要订广州飞北京的航班` against the dev-seeded airline Chatflows.

034.16 final behavior:

- the utterance reaches `flight_booking` through
  `enabled_scope_fallback -> post_classifier -> llm`;
- route evidence reports `classifierResult.used_real_llm=true`;
- runtime-lab starts the bound Chatflow `flight_booking -> #5906`;
- Chatflow information collection records `route=广州飞北京`;
- followup text is rendered from actual missing fields and no longer asks for
  the already collected route;
- LLM classifier failures degrade to `CLARIFY` with `llm_error` evidence instead
  of HTTP 500;
- Chatflow collection treats placeholder extraction values such as `未指定`,
  `未知`, `未提供`, `无`, `none`, and `null` as missing.

034.16 badcases/fixes:

- Static collection template: `route` was already collected but the bot still
  asked for 出发到达城市. Fixed dynamic `{{collected_notice}}` and
  `{{missing_labels}}` rendering in the workflow information collection node and
  reseeded `flight_booking`.
- Wrong local provider selection: the restart/reseed helper initially picked a
  latest `sk-test` provider and OpenRouter returned 401. Re-ran with the
  existing OpenRouter `sk-or-v` provider and reseeded the fixed 034 provider.
- LLM classifier failure: upstream auth/quota/model errors used to escape as a
  server error. Added classifier failure fallback evidence.
- Placeholder extraction: browser UAT exposed Chatflow LLM values like `未指定`
  being treated as complete. Added collection value filtering and regression
  coverage.

034.16 evidence:

- RED collection followup:
  `artifacts/slices/034-unified-routing-chat-lab/034.16/red.txt`;
- classifier failure RED/GREEN:
  `artifacts/slices/034-unified-routing-chat-lab/034.16/classifier-failure-red.txt`,
  `artifacts/slices/034-unified-routing-chat-lab/034.16/classifier-failure-green.txt`;
- placeholder RED/GREEN:
  `artifacts/slices/034-unified-routing-chat-lab/034.16/placeholder-values-red.txt`,
  `artifacts/slices/034-unified-routing-chat-lab/034.16/placeholder-values-green.txt`;
- live exact API response:
  `artifacts/slices/034-unified-routing-chat-lab/034.16/live-followup-response-4.json`;
- live Chatflow checkpoint:
  `artifacts/slices/034-unified-routing-chat-lab/034.16/live-chatflow-checkpoint-4.txt`;
- browser UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.16/uat.md`,
  `artifacts/slices/034-unified-routing-chat-lab/034.16/browser-uat-chatflow-checkpoint.txt`;
- targeted backend gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.16/backend-targeted.txt`;
- targeted frontend/rem gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.16/frontend-targeted-rem.txt`;
- ruff:
  `artifacts/slices/034-unified-routing-chat-lab/034.16/ruff.txt`.

## 034.17 Frontend Chatflow Binding And Trace Inspector

Status: complete.

034.17 makes the runtime-lab page inspect and operate on the actual bound
Chatflow SOPs instead of only showing a static airline SOP fixture.

034.17 final behavior:

- `/api/v1/runtime-lab/config` returns each bound SOP's `canvasPath` so the
  frontend can open the real Chatflow canvas.
- `/api/v1/runtime-lab/sessions/{session_id}/chatflow-trace` returns the
  current RuntimeLab task's bound Chatflow metadata, run/session/checkpoint
  identity, canvas/debug paths, node statuses, edges, events, visible scoped
  variables, collected values, business refs, and Chatflow session variables.
- The left rail shows current Chatflow binding count and a compact enabled SOP
  list; the `接入` button opens a centered modal where testers can check/uncheck
  the currently bound Chatflow SOPs.
- Each bound SOP row can open the actual Chatflow canvas.
- The right inspector shows the current Chatflow execution card: current node,
  completed count, running/completed indicators, node path, recent events, and
  slot variables.
- While a backend turn is running, the assistant side shows a three-dot pending
  animation before replacing it with the real reply.

034.17 browser UAT:

- Reloaded `http://127.0.0.1:5175/runtime-lab/chat`.
- Confirmed the config panel shows 15 Chatflow SOP bindings, `llm ·
  qwen/qwen3.5-9b`, API key configured, and available.
- Opened the `接入` modal and verified 15 bound SOP rows, 15 checked options,
  and a working `flight_booking` row.
- Toggled `flight_booking` off and back on; the modal summary moved from
  `14/15` to `15/15`.
- Sent the natural free-form booking utterance
  `明天早上我要从广州飞北京参加会，麻烦帮我先订一班到达别太晚的航班。`.
- Confirmed the pending assistant three-dot animation appeared.
- Confirmed the reply returned `START_SOP` for `flight_booking`.
- Confirmed the Chatflow trace panel showed bound Chatflow `#5906`, 6 nodes,
  current node `collect · 机票预订信息收集`, `start` completed, downstream
  nodes pending, and slot values `route=广州到北京`,
  `travel_time=明天早上`.
- Confirmed trace `调试` opened
  `/chatflows/5906/canvas?runId=5968&debug=1`.

034.17 badcases/fixes:

- Old local backend process was still serving config without `canvasPath`; the
  process was restarted on the new code and config was rechecked.
- A wide fake-adapter backend regression failed once because local Chatflow
  bindings leaked into the legacy fake path. The suite was rerun with
  `HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS=''` and passed.
- Element Plus dialog close state can leave a hidden dialog shell in DOM during
  browser automation. UAT used targeted DOM checks and page reload to avoid
  confusing hidden transition state with visible UI.

034.17 evidence:

- browser UAT:
  `artifacts/slices/034-unified-routing-chat-lab/034.17/uat.md`;
- screenshot:
  `artifacts/slices/034-unified-routing-chat-lab/034.17/screenshots/runtime-lab-chatflow-trace.png`;
- frontend targeted/rem:
  `artifacts/slices/034-unified-routing-chat-lab/034.17/frontend-targeted-1.txt`;
- frontend full unit:
  `artifacts/slices/034-unified-routing-chat-lab/034.17/frontend-unit-full-1.txt`;
- frontend build:
  `artifacts/slices/034-unified-routing-chat-lab/034.17/frontend-build-1.txt`;
- backend targeted/ruff:
  `artifacts/slices/034-unified-routing-chat-lab/034.17/backend-targeted-1.txt`;
- backend runtime-lab wide regression:
  `artifacts/slices/034-unified-routing-chat-lab/034.17/backend-runtime-lab-full-2.txt`.

## 034.18 RuntimeLab Live-Routing And Context Carryover Hardening

Status: complete.

034.18 fixes the user-visible badcases found after 034.17: first-turn natural
booking text could still return `NO_MATCH`, switching from a completed booking
to change-flight did not reliably carry slots into the next Chatflow, and qwen
free upstream rate limits could bubble up as browser-visible HTTP 500.

034.18 final behavior:

- If explicit/template and mock semantic recall return no candidates, RuntimeLab
  now builds the full finite SOP candidate set and invokes constrained LLM
  arbitration instead of returning `NO_MATCH`.
- New SOP starts receive accumulated session business context from prior task
  `business_refs` and latest checkpoints.
- `ChatflowSopRuntimeAdapter` injects inherited `collected`, `conversation`,
  and `conversation.*` values into Chatflow runtime input, and merges obvious
  current-turn business slots before collection.
- All 15 seeded airline Chatflow SOPs use dynamic information-collection
  followups, so already-recorded slots are shown in `collected_notice` and only
  missing fields are requested.
- Booking completion prompts now produce a deterministic mock order number
  (`CA1301-20231027-8899`), and adapter parsing promotes Chinese `订单编号`
  replies into business context.
- Change-flight text such as `改签到后天上午` is parsed into `target_time`
  before Chatflow collection.
- RuntimeLab's live Chatflow LLM model remains `qwen/qwen3.5-9b`, with
  `deepseek/deepseek-v4-flash` configured as a test-stage fallback model for
  provider-backed workflow/Chatflow LLM calls.
- Unexpected Chatflow runtime exceptions are normalized into
  `CHATFLOW_START_FAILED` / `CHATFLOW_RESUME_FAILED` adapter results instead of
  leaking HTTP 500.

034.18 API UAT:

- Exact chain:
  `这周工作临时排开了，想看看广州去北京明天上午的航班还能不能订，乘机人张三，用 13800138000 联系`
  -> `可以，帮我确认出票`
  -> `我想把刚才这张票改签到后天上午`.
- First turn used `finite_intent_fallback` and real qwen constrained
  arbitration to select `flight_booking`.
- Booking completed with `order_no=CA1301-20231027-8899`.
- Change-flight started `change_flight`, reached `confirm`, and carried
  `order_no`, `phone`, `passenger_name`, `route`, `travel_time`, and
  `target_time=后天上午`.

034.18 browser UAT:

- Reloaded `http://127.0.0.1:5175/runtime-lab/chat`; config showed 15/15
  Chatflow bindings,
  `llm · qwen/qwen3.5-9b / fallback deepseek/deepseek-v4-flash`, API key
  configured, and ready.
- Confirmed the assistant pending animation appears as
  `data-testid=runtime-lab-typing` / `.typing-indicator`.
- Drove the visible sample journey:
  booking sample -> booking info sample -> booking confirm -> change sample.
- Confirmed trace panel showed real bound Chatflow node state, completed/pending
  statuses, and variables.
- Confirmed completed booking trace stored `order_no=CA1301-20231027-8899`.
- Confirmed change SOP inherited `order_no`, `phone`, and `passenger_name` and
  did not repeat those slot requests. The sample only asked for target change
  time because the sample phrase used "更早一班" rather than a concrete date.

034.18 badcases/fixes:

- Natural first turn with no lightweight candidate returned `NO_MATCH`; fixed
  through full finite SOP fallback into constrained LLM arbitration.
- Cross-SOP context was not available to new Chatflow starts; fixed session
  business context aggregation and runtime input injection.
- Seeded SOP followups were static; fixed all 15 to dynamic missing-slot
  templates and reseeded current dev Chatflows.
- Booking order number was reply text only; fixed seeded final prompt and
  Chinese order number parsing.
- qwen free upstream 429 produced browser `Internal Server Error`; fixed
  workflow LLM fallback model support and adapter failure normalization.

034.18 evidence:

- UAT report:
  `artifacts/slices/034-unified-routing-chat-lab/034.18/uat.md`;
- screenshot:
  `artifacts/slices/034-unified-routing-chat-lab/034.18/screenshots/browser-uat-context-carryover.png`;
- API chain:
  `artifacts/slices/034-unified-routing-chat-lab/034.18/live-api-booking-to-change-after-target-time-merge.jsonl`;
- backend gate:
  `artifacts/slices/034-unified-routing-chat-lab/034.18/backend-runtime-lab-final-green.txt`;
- frontend full unit:
  `artifacts/slices/034-unified-routing-chat-lab/034.18/frontend-full-unit-final-green.txt`;
- frontend build:
  `artifacts/slices/034-unified-routing-chat-lab/034.18/frontend-build-final-green.txt`;
- ruff:
  `artifacts/slices/034-unified-routing-chat-lab/034.18/ruff-final.txt`;
- browser backend log tail:
  `artifacts/slices/034-unified-routing-chat-lab/034.18/backend-uat-log-tail.txt`.

## 034.19 Pending Indicator And History-Aware Slot Extraction

Status: complete.

034.19 fixes two user-visible regressions found during live RuntimeLab
inspection:

- the assistant pending state was too subtle and could disappear before the user
  perceived it;
- history-aware information collection carried prior booking context into
  `change_flight`, but the extraction layer needed field-level control so
  original itinerary time was not mistaken for the requested new change time.

034.19 final behavior:

- The frontend pending message now visibly renders `正在生成回复` plus three
  animated dots while a RuntimeLab turn is waiting for backend routing and
  Chatflow execution.
- RuntimeLab builds a bounded `history` list from prior user turns and includes
  it in `SopExecutionRequest.metadata`.
- `ChatflowSopRuntimeAdapter` injects that `history` into Chatflow runtime
  input, so nodes with `includeHistory=true` can use the prior conversation.
- The seeded 15 airline Chatflow information-collection nodes now set
  `includeHistory=true`.
- Follow-up text now says `当前只差...`, making it explicit that inherited slots
  such as order number, phone, and passenger name are already recorded.
- Workflow information collection supports field-level
  `historyMode=current_turn_only`; seeded `change_flight.target_time` uses this
  mode so it can only be filled from the current user turn, not from historical
  original itinerary time.

034.19 API UAT:

- Real API chain after reseeding and backend restart:
  `我要订广州飞北京的航班，明天上午走，乘机人张三，手机号 13800138000`
  -> `可以，帮我确认出票`
  -> `我要改签刚才那张机票`
  -> `名字等信息是一样的`
  -> `刚才的信息你忘记了吗`
  -> `改到后天上午`
  -> `确认改签`.
- Booking completed with `order_no=CA1301-20231027-8899`.
- Change-flight inherited `order_no`, `phone`, `passenger_name`, `route`, and
  `travel_time`.
- The "same information" and "did you forget" turns stayed in collection and
  replied that only `期望改签时间` was missing.
- `改到后天上午` filled `target_time=后天上午`, reached confirm, and
  `确认改签` completed the SOP.

034.19 browser UAT:

- Reloaded `http://127.0.0.1:5175/runtime-lab/chat`.
- Triggered a left-panel sample and confirmed the pending row was visible with
  text `正在生成回复` and three `.typing-dots` children.
- Typed full-chain browser UAT could not be completed because this in-app
  browser automation session reports `Browser Use virtual clipboard is not
  installed` on `textarea.fill`; the same full chain was verified through the
  real RuntimeLab API.

034.19 evidence:

- UAT report:
  `artifacts/slices/034-unified-routing-chat-lab/034.19/uat.md`.

## 034.20 Context Inheritance Guard

Status: complete.

034.20 addresses the distinction between "context is available" and "context
is committed to the current SOP". This prevents the runtime from accidentally
using the previous passenger/order when the user starts a new business for
another person.

034.20 final behavior:

- All 15 seeded airline information-collection nodes have
  `includeHistory=true`.
- Every seeded collection field writes to conversation context through
  `targetScope=conversation` and `targetVariable=<field.name>`.
- RuntimeLab adapter requests now include `inheritedContext` for prior business
  context, but prior values are committed into current `collected` only when
  the user explicitly references prior context.
- Context-reference terms include examples such as `刚才`, `这张`, `那张`,
  `一样`, and `继续刚才`.
- Reset/new-person terms such as `另一个`, `别人`, `其他人`, `新乘机人`,
  `给同事`, and `不是刚才` keep prior values out of current `collected` and
  avoid passing history to the extractor for that turn.

034.20 API UAT:

- `我要改签刚才那张机票` after booking completion started `change_flight` and
  inherited `order_no`, `phone`, `passenger_name`, `route`, and `travel_time`.
- `我要给另一个人改签机票` after booking completion also started
  `change_flight`, but current `businessRefs` stayed `{}` and the bot asked
  for `订单号、手机号、乘机人姓名、期望改签时间`.

034.20 evidence:

- UAT report:
  `artifacts/slices/034-unified-routing-chat-lab/034.20/uat.md`.
