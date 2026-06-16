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

## 034.10 Test-stage OpenRouter free LLM arbitrator

- [x] Keep production/runtime-lab LLM arbitrator configuration single-model
  only through system settings.
- [x] Add an opt-in acceptance harness for current test-stage OpenRouter free
  model pooling.
- [x] Discover zero-priced text-output models from OpenRouter `/models`
  dynamically instead of hard-coding a model list.
- [x] Try discovered free models as finite-candidate intent arbitrators, skipping
  quota, transport, invalid JSON, and test-expectation failures.
- [x] Fall back to `xiaomi/mimo-v2-flash` only inside the 034.10 live acceptance
  harness.
- [x] Preserve ordinary CI stability by skipping live OpenRouter arbitration
  unless `HIFY_RUN_LIVE_RUNTIME_LAB_OPENROUTER_FREE_ARBITRATOR=1` and
  `OPENROUTER_API_KEY` are set.
- [x] Run backend full pytest and save 034.10 evidence.

## 034.11 Live OpenRouter full-chain acceptance

- [x] Add an opt-in live acceptance gate that exercises one RuntimeLab
  conversation with both real OpenRouter intent arbitration and real
  provider-backed Chatflow `LLM` nodes.
- [x] Use `qwen/qwen3.5-9b` as the default single target model for focused,
  low-latency live arbitration testing.
- [x] Keep `deepseek/deepseek-v4-flash` documented as the opt-in
  high-intelligence model for latency-insensitive scenarios.
- [x] Keep Chatflow SOP LLM nodes on the single configured provider model.
- [x] Assert route evidence reports `arbitrator_mode=llm` and
  `used_real_llm=true` on the live switch decision.
- [x] Assert SOP completion replies contain live LLM markers and no mock LLM
  prefixes.
- [x] Fix qwen live badcases by disabling reasoning for the test-stage
  arbitrator, raising token limits, and avoiding multi-system-message Chatflow
  fixtures.
- [x] Preserve ordinary CI stability by skipping the full-chain live gate unless
  `HIFY_RUN_LIVE_RUNTIME_LAB_OPENROUTER_FULL_CHAIN=1` and
  `OPENROUTER_API_KEY` are set.
- [x] Run qwen full-chain live gate, qwen 5-SOP live Chatflow LLM gate, ordinary
  non-live targeted acceptance, ruff, and full backend pytest.

## 034.12 Mixed natural core airline routing gate

- [x] Add 40 natural core airline scenarios: booking/refund/change/consultation,
  10 per business area.
- [x] Keep utterances realistic and varied instead of direct fixed commands like
  `我要退票`.
- [x] Verify strong explicit/keyword candidate recall with all 40 natural
  scenarios completing their primary SOP. Historical 034 evidence used the old
  direct strong-routing path; 036-040 R1 is the current non-hard-stop central
  arbitration proof.
- [x] Verify qwen LLM arbitration with representative active-task switch
  journeys, not every scenario.
- [x] Verify the supported single-suspended-task journey:
  `A start -> B switch -> B complete -> resume A -> A complete -> C complete`.
- [x] Keep Chatflow SOP LLM nodes on qwen for the representative live journeys.
- [x] Record qwen/OpenRouter badcases: live timeout, provider connection reset,
  contaminated booking details, and over-forcing LLM arbitration.

## 034.13 Dev-seeded airline Chatflow configuration

- [x] RED: backend gate fails before a production seed module exists for the
  034 airline SOP Chatflows.
- [x] RED: frontend API/model gate fails before runtime config can be fetched
  and summarized.
- [x] Seed 15 official 034 airline SOPs as published Chatflow workflows in the
  current development database.
- [x] Make the seed script idempotent and write only non-secret RuntimeLab
  binding/model settings into local `.env`.
- [x] Seed a live provider/model/agent from process environment for local
  full-chain Chatflow LLM testing.
- [x] Add `/api/v1/runtime-lab/config` with Chatflow binding IDs/names,
  arbitrator mode/model/base URL, key-configured state, and availability.
- [x] Ensure runtime-lab Chatflow bindings inject agent/model repositories so
  Chatflow `LLM` nodes use the seeded provider.
- [x] Display bound Chatflow count, expanded SOP ID rows, arbitrator mode,
  model, key state, and availability in the frontend lab.
- [x] Fix browser UAT badcase where `flight_status` sample replies used order
  fields instead of a flight number.
- [x] Run targeted backend gate, full backend pytest, frontend/rem gate, full
  frontend unit, ruff, seed idempotence check, config API check, secret scan,
  and browser UAT.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.13/`.

## 034.14 Enabled-scope LLM fallback arbitration

- [x] RED: manual badcase `我要订广州飞北京的航班` returns `NO_MATCH`
  because candidate recall is empty under enabled scope.
- [x] Confirm current 034 implementation has mock semantic recall, not real
  embedding/vector retrieval.
- [x] Preserve strong trigger behavior; do not add a narrow keyword hack for
  this badcase.
- [x] Add enabled-scope finite candidate fallback when explicit and semantic
  recall are empty.
- [x] Keep fake arbitration from selecting the first fallback candidate by
  default; return clarification unless real/scripted arbitration selects.
- [x] Verify live qwen arbitration selects `flight_booking` from
  `enabled_scope_fallback` with `used_real_llm=true`.
- [x] Run targeted backend regression and ruff.

## 034.15 Funnel observability and no-template-padding gate

- [x] Do not add more strong trigger/templates to pass the badcase.
- [x] Document the current funnel boundary: strong templates, mock semantic
  recall, enabled-scope fallback, constrained LLM arbitration.
- [x] Add frontend route inspector fields for funnel stage, candidate source,
  and arbitrator evidence.
- [x] Verify the badcase reaches `flight_booking` through
  `enabled_scope_fallback -> post_classifier -> llm real`.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.15/`.

## 034.16 Chatflow followup and live-chain hardening

- [x] RED: `flight_booking` Chatflow collection asks for already collected route
  because followup text is static.
- [x] Add dynamic collection followup placeholders for collected field notice
  and missing field labels.
- [x] Reseed the current dev database so `flight_booking -> #5906` uses the
  dynamic followup template.
- [x] Verify exact utterance `我要订广州飞北京的航班` reaches
  `flight_booking` through `enabled_scope_fallback -> post_classifier -> llm`.
- [x] Verify exact utterance starts real Chatflow `#5906` and stores
  `__chatflow` checkpoint metadata.
- [x] Add classifier failure fallback so upstream LLM errors return `CLARIFY`
  with route evidence instead of HTTP 500.
- [x] Fix local live-provider selection mistake by reseeding the fixed 034
  OpenRouter provider from an existing `sk-or-v` provider, without writing
  secrets to `.env`.
- [x] RED/GREEN: treat Chatflow collection placeholder values such as `未指定`,
  `未知`, `未提供`, `无`, `none`, and `null` as missing.
- [x] Run browser UAT on the runtime-lab page and verify the sample no longer
  jumps to premature confirmation when required fields are placeholder values.
- [x] Run targeted backend gate, frontend/rem gate, ruff, live API replay,
  Chatflow checkpoint inspection, and secret scan.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.16/`.

## 034.17 Frontend Chatflow binding and trace inspector

- [x] RED: runtime-lab config contract fails until each SOP binding exposes a
  frontend canvas path.
- [x] RED: runtime-lab trace API fails until a session can expose bound
  Chatflow node state, events, debug links, and slot variables.
- [x] RED: frontend model tests fail until selectable SOP scope rows are built
  from backend Chatflow bindings instead of the static SOP fixture.
- [x] Add `/api/v1/runtime-lab/sessions/{session_id}/chatflow-trace` with
  task-level Chatflow metadata, node statuses, edges, events, visible scoped
  variables, session variables, and canvas/debug paths.
- [x] Extend `/api/v1/runtime-lab/config` binding rows with `canvasPath`.
- [x] Replace the left-panel hardcoded SOP checkbox list with a `接入` modal
  backed by the current runtime config Chatflow bindings.
- [x] Keep the visible left rail compact by showing the currently enabled
  Chatflow SOPs and linking each to its Chatflow canvas.
- [x] Add a right-panel Chatflow trace inspector that shows current node,
  completed count, running/completed indicators, execution path, events, and
  collected slot values.
- [x] Add assistant three-dot pending animation while a runtime-lab turn is
  waiting for backend routing/Chatflow execution.
- [x] Verify browser UAT with a natural free-form booking utterance that uses
  real LLM finite arbitration, starts bound Chatflow `flight_booking -> #5906`,
  records `route=广州到北京` and `travel_time=明天早上`, and opens
  `/chatflows/5906/canvas?runId=...&debug=1`.
- [x] Run frontend targeted/rem, full frontend unit, frontend build, backend
  ruff/targeted, backend runtime-lab wide regression, and browser UAT.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.17/`.

## 034.18 RuntimeLab live-routing and context carryover hardening

- [x] RED/GREEN: new SOP starts inherit completed session business context from
  prior task refs and checkpoints.
- [x] Inject inherited `collected`/`conversation` variables into real Chatflow
  runtime input.
- [x] Make all 15 airline Chatflow follow-up templates dynamic with
  `{{collected_notice}}` and `{{missing_labels}}`.
- [x] Promote booking completion order numbers from Chinese replies into
  business context.
- [x] Parse current-turn change time such as `改签到后天上午` before Chatflow
  collection.
- [x] Add full finite SOP fallback so empty lightweight recall enters
  constrained LLM arbitration instead of returning first-turn `NO_MATCH`.
- [x] Add qwen primary plus `deepseek/deepseek-v4-flash` fallback for
  provider-backed workflow/Chatflow LLM calls during test-stage RuntimeLab.
- [x] Normalize unexpected Chatflow runtime failures to adapter failure results
  instead of leaking HTTP 500.
- [x] Verify exact API chain:
  booking -> completed order -> change `刚才这张票改签到后天上午` reaches
  `change_flight` confirm with inherited `order_no`, `phone`,
  `passenger_name`, `route`, `travel_time`, and `target_time`.
- [x] Verify browser UAT: pending animation plays; Chatflow trace shows node
  status and variables; booking completion produces `order_no`; change SOP
  inherits order/phone/passenger and no longer repeats those slots.
- [x] Run backend runtime-lab regression, workflow fallback test, ruff,
  frontend rem/targeted, full frontend unit, frontend build, and browser UAT.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.18/`.

## 034.19 Pending indicator and history-aware slot extraction

- [x] RED: seeded airline Chatflow information-collection nodes did not enable
  history awareness.
- [x] RED: Chatflow SOP adapter did not pass RuntimeLab
  `metadata.history` into workflow runtime input.
- [x] RED: new SOP starts did not include prior RuntimeLab user messages in the
  adapter request metadata.
- [x] RED: history-aware collection could leak original itinerary time into
  `change_flight.target_time` when the current turn only said "名字等信息一样".
- [x] Add bounded RuntimeLab user-message history to `SopExecutionRequest`
  metadata and inject it into Chatflow `history`.
- [x] Seed all 15 airline Chatflow collection nodes with `includeHistory=true`
  and clearer "当前只差" missing-slot copy.
- [x] Add workflow collection field-level
  `historyMode=current_turn_only` and apply it to `change_flight.target_time`.
- [x] Make the frontend assistant pending state visibly render
  `正在生成回复` plus three animated dots.
- [x] Reseed current dev Chatflows `5906-5920` and restart the runtime-lab
  backend.
- [x] Verify real API chain:
  booking -> order -> change -> "名字等信息一样" -> "刚才的信息你忘记了吗"
  stays at missing `target_time`, then `改到后天上午` reaches confirm and
  `确认改签` completes.
- [x] Verify browser UAT pending indicator is visible before response.
- [x] Run backend targeted/badcase, backend wide RuntimeLab/workflow gate,
  frontend rem/targeted, full frontend unit, frontend build, and ruff.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.19/`.

## 034.20 Context inheritance guard

- [x] Verify every seeded airline information-collection node has
  `includeHistory=true`.
- [x] Verify every seeded airline information-collection field writes to
  `targetScope=conversation` with `targetVariable=<field.name>`.
- [x] RED: inherited cross-SOP context was directly committed into new SOP
  `collected` even when the user said they were handling another person.
- [x] Split prior context into `inheritedContext` versus committed
  `collected`.
- [x] Commit inherited context only when the user references prior context
  (`刚才`, `这张`, `那张`, `一样`, `继续刚才`, etc.).
- [x] Do not commit inherited context, and do not pass history to collection
  extraction for that turn, when the user indicates a new/other person
  (`另一个`, `别人`, `给同事`, `新乘机人`, etc.).
- [x] Verify real API scenario where `我要改签刚才那张机票` inherits order,
  phone, passenger, route, and original travel time.
- [x] Verify real API scenario where `我要给另一个人改签机票` starts
  `change_flight` with empty current business refs and asks for all required
  current slots.
- [x] Run targeted RED/GREEN, backend RuntimeLab/workflow wide gate, and ruff.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.20/`.

## 034.21 LLM and Chatflow observability

- [x] RED: RuntimeLab Chatflow trace nodes did not expose node-run inputs.
- [x] RED: LLM node execution did not project token usage into node outputs
  and stream events.
- [x] Add `workflow_node_run.inputs` storage and backfill-safe runtime column
  creation for existing local databases.
- [x] Capture rendered node inputs, runtime input, variable scopes, outputs,
  elapsed time, and token usage for Chatflow trace nodes.
- [x] Capture provider-backed Workflow/Chatflow LLM request payload,
  response payload, elapsed time, model, and token usage; estimate tokens when
  the provider omits usage.
- [x] Capture RuntimeLab LLM finite-intent arbitration input/output, elapsed
  time, and token usage under `classifierResult._debug`.
- [x] Add route-step timing for candidate recall, finite fallback, pre-policy,
  LLM arbitration, and post-policy decisions.
- [x] Add frontend AI message usage/elapsed meta, details button, and shared
  right-side floating debug panel for message and trace-node inspection.
- [x] Verify browser UAT: pending indicator, real LLM arbitration, message
  debug panel, trace-node debug panel, and no console errors.
- [x] Run frontend full unit/build/rem gate, backend RuntimeLab/workflow
  related regression, and ruff.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.21/`.

## 034.22 FAQ catalog and fallback Agent selector

- [x] Expand the RuntimeLab airline FAQ catalog to 116 entries across 23
  reason codes, including similar questions from booking, refund, change,
  baggage, invoice, check-in, abnormal-flight, membership, and assistance
  scenes.
- [x] Add FAQ/SOP conflict guards so consultation wording stays FAQ while
  transaction wording such as "提前买一点行李额度" can still start SOP.
- [x] Expose fallback Agent configuration in `/api/v1/runtime-lab/config`,
  including current binding, availability, and selectable enabled Agents.
- [x] Add `/api/v1/runtime-lab/fallback-agent` so the RuntimeLab UI can bind
  an existing Agent instead of relying on a hardcoded backend fallback.
- [x] Wire `existing_agent` fallback through the Agent/Chat service stack and
  keep RuntimeLab context in debug citations instead of leaking it into the
  user-facing Agent prompt.
- [x] Add the frontend fallback Agent selector, config summary, save action,
  and route outcome display.
- [x] Verify backend targeted and wide RuntimeLab gates, frontend rem/targeted
  and full unit gates, live HTTP FAQ sweep, and browser FAQ/SOP/Agent UAT.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.22-faq-agent-uat/` and
  `artifacts/slices/034-unified-routing-chat-lab/034.24-live-faq-sweep/`.

## 034.23 Handoff display UAT

- [x] Verify explicit transfer-to-human utterances keep active SOP state and
  render `HANDOFF_TO_HUMAN` in the route header.
- [x] Verify the route outcome card displays the handoff reason
  (`USER_REQUEST · explicit_signal`) and the assistant reply resolves after
  the pending animation.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.23-handoff-uat/`.

## 034.25 Route settings and model/Agent sourced selectors

- [x] Add a unified route settings modal in RuntimeLab chat for Chatflow
  bindings, finite-intent arbitration, thresholds, fallback Agent, and
  read-only FAQ/RAG/handoff policy summaries.
- [x] Populate arbitration model choices from project Model Management
  (`getModelOptions`) instead of free-text options.
- [x] Populate fallback Agent choices from enabled Agent module records and
  keep the existing save-to-policy endpoint available.
- [x] Remove the old left-panel fallback Agent quick selector so there is only
  one Agent configuration surface.
- [x] Send local threshold settings with each message and apply them only to
  the current RuntimeLab turn without mutating the backend policy default.
- [x] Send local arbitrator model config with each message and use it to
  instantiate the current-turn provider-backed finite-intent classifier.
- [x] Add primary/fallback temporary model configuration dialogs with Base URL,
  API key, model name, temperature, top-p, and max-token controls, and make
  those temporary configs instantiate the current-turn provider-backed
  finite-intent classifier without requiring Model Management records.
- [x] Add a temporary model connectivity test button that sends probe message
  `1`, displays a green success status for a real 200 provider response, and
  displays a red failure status with sanitized provider error details.
- [x] Keep non-hot-applied FAQ/RAG/handoff fields out of the per-message
  payload and display them as policy summaries instead of editable controls.
- [x] Include local threshold overrides in the idempotency request hash.
- [x] Normalize OpenAI/OpenRouter token usage fields so LLM arbitration debug
  displays non-zero `inputTokens`, `outputTokens`, and `totalTokens`.
- [x] Verify browser UAT: settings modal opens, model options are grouped by
  Provider, Agent options are selectable, old quick selector is gone, pending
  animation appears, real LLM arbitration runs, Chatflow starts, and debug
  token usage is visible.
- [x] Run frontend full unit/build/rem gate and backend RuntimeLab/runtime
  policy regression gates.
- [x] Save evidence under
  `artifacts/slices/034-unified-routing-chat-lab/034.25-route-settings-uat/`.

## Future specs, not 034 tasks

- [ ] Rename or consolidate final user-facing API to `/chat` or `/query`.
- [ ] Add visual route-rule authoring and policy tuning for FAQ/RAG/Agent/
  handoff fallback.
- [ ] Replace mock semantic recall with real embedding/vector recall and
  confidence scoring.
- [ ] Add an inspector lane for route funnel scores: explicit keyword,
  semantic/embedding top-k, LLM finite-arbitration decision, clarification,
  FAQ/RAG fallback, and final agent handoff.
- [ ] Export any manual badcase turn from the browser into a regression fixture.
- [ ] Run live provider-backed LLM browser acceptance by default.
