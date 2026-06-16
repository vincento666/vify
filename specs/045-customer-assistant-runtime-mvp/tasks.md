# Tasks 045: Customer Assistant Runtime MVP

## 045.0 Spec Sign-off

- [x] Confirm `045-customer-assistant-runtime-mvp` is the next stable spec id
      after `044-frontend-ant-design-vue-migration`.
- [x] Confirm boundary: independent ToB runtime, not LangChain/LangGraph, not
      `runtime_lab` main-loop reuse.
- [x] Confirm MVP worker matrix: real `ChatflowSopWorker`, stub QA, stub
      aggregator, deterministic controller.
- [x] Confirm all high-risk writes become `proposed_action`.
- [x] Save documentation evidence under
      `artifacts/slices/045-customer-assistant-runtime-mvp/045.0/`.

## 045.1 Domain Model And Persistence

- [x] RED: repository/model tests fail for sessions, runs, tasks, events, and
      proposed actions.
- [x] Add `customer_assistant` infra schema and repository.
- [x] Add domain dataclasses/value objects for `TaskLedger`, `TaskItem`,
      `TaskCommand`, `WorkerResult`, `AssistantTurnResult`, `RuntimeEvent`,
      and `ProposedAction`.
- [x] Persist event sequence monotonically per assistant session.
- [x] Prove idempotency fields prevent duplicate turn effects.
- [x] Gates pass and evidence is saved:
      `artifacts/slices/045-customer-assistant-runtime-mvp/045.1/`.

## 045.2 Controlled ReAct Core And Deterministic Controller

- [x] RED: loop tests fail for reason/validate/act/observe/final flow.
- [x] Implement one-iteration `ControlledReActCore`.
- [x] Implement deterministic task-recognition controller for refund, baggage,
      order-value continuation, and explicit cancel phrases.
- [x] Implement strict action policy for supported task commands.
- [x] Ensure unsupported commands are rejected without ledger mutation.
- [x] Gates pass and evidence is saved:
      `artifacts/slices/045-customer-assistant-runtime-mvp/045.2/`.

## 045.3 Task Ledger And Parallel Scheduler

- [x] RED: scheduler tests fail for multi-task fan-out/join and isolated
      failure handling.
- [x] Implement ledger mutation for add, retain, cancel, suspend, resume, and
      task result updates.
- [x] Implement local parallel worker scheduler with per-task timeout.
- [x] Ensure one worker failure does not fail the whole turn.
- [x] Persist task updates and worker-result events.
- [x] Gates pass and evidence is saved:
      `artifacts/slices/045-customer-assistant-runtime-mvp/045.3/`.

## 045.4 ChatflowSopWorker And Stub Workers

- [x] RED: real Chatflow/SOP worker integration test fails.
- [x] Implement `ChatflowSopWorker` using `ChatflowSopRuntimeAdapter` and
      normalized `SopExecutionRequest`/`SopExecutionResult`.
- [x] Implement `StubQaWorker`.
- [x] Implement deterministic recommendation aggregator that separates
      operator recommendation and customer reply draft.
- [x] Map any high-risk worker output to persisted `proposed_action`.
- [x] Prove refund task can wait and continue from persisted checkpoint.
- [x] Gates pass and evidence is saved:
      `artifacts/slices/045-customer-assistant-runtime-mvp/045.4/`.

## 045.5 API Surface

- [x] RED: API contract tests fail for customer-assistant session, turn, tasks,
      events, and proposed-action endpoints.
- [x] Add `/api/v1/customer-assistant/sessions`.
- [x] Add `/api/v1/customer-assistant/sessions/{sessionId}/turns`.
- [x] Add task and event list endpoints.
- [x] Add proposed-action confirm/reject endpoints.
- [x] Preserve `{code, message, data}` response envelope.
- [x] Prove idempotent turn submission does not duplicate tasks/actions.
- [x] Gates pass and evidence is saved:
      `artifacts/slices/045-customer-assistant-runtime-mvp/045.5/`.

## 045.6 End-To-End Runtime Acceptance

- [x] RED: API E2E fails for refund + baggage multi-task scenario.
- [x] Prove single refund task: start, wait for order info, continue.
- [x] Prove multi-task fan-out/join: refund + baggage QA.
- [x] Prove proposed actions are not auto-executed.
- [x] Prove event stream list is ordered and includes L0/L1 events.
- [x] Run targeted existing Chatflow/runtime-lab regressions.
- [x] Run full backend pytest or document unrelated failures.
- [x] Save final acceptance evidence under
      `artifacts/slices/045-customer-assistant-runtime-mvp/045.6/`.

## 045.7 MVP Gap Closure: API Chatflow SOP Wiring

- [x] RED: contract test proves bound `refund_ticket` SOP did not use
      `ChatflowSopRuntimeAdapter` while API service defaulted to fake SOP wiring.
- [x] Build customer assistant API service with bound Chatflow SOP adapter when
      `runtime_lab_sop_chatflow_ids` is configured.
- [x] Keep no-binding `FakeSopRuntimeAdapter` as explicit dev/test fallback only.
- [x] Inject `LocalWorkerScheduler` with `chatflow_sop` and `stub_qa` workers from
      the API router dependency.
- [x] Run customer assistant backend gate and runtime adapter regression.
- [x] Save evidence under
      `artifacts/slices/045-customer-assistant-runtime-mvp/045.live-chatflow-wiring/`.

## Later Specs

- [ ] LLM structured task-recognition controller.
- [ ] LLM recommendation aggregator.
- [ ] real RAG worker.
- [ ] real Agent worker.
- [ ] SSE/WebSocket runtime event streaming.
- [ ] minimal operator assistant frontend panel.
- [ ] multi-iteration controlled ReAct loop.
- [ ] generic shared agent runtime adoption by ordinary Agent chat.
