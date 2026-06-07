# Tasks 029: Isolated Runtime Router Lab

## 029.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record that this workstream was discussed as 026 but uses directory id
  029 because 026-028 already exist.
- [x] Commit the spec documents only.

## 029.1 Schema and repository

- [x] RED: repository tests fail for session/task/checkpoint/event/command
  persistence.
- [x] Add `runtime_lab_session`.
- [x] Add `runtime_lab_task`.
- [x] Add `runtime_lab_checkpoint`.
- [x] Add `runtime_lab_event`.
- [x] Add `runtime_lab_command`.
- [x] Implement repository methods for create session, append event, create
  task, update task state, create checkpoint, list tasks, list events, and
  store/replay idempotent command response.
- [x] Enforce one active task per session through service logic and transaction
  tests.
- [x] Save evidence under
  `artifacts/slices/029-isolated-runtime-router-lab/029.1/`.
- [x] Gates pass.
- [x] Commit 029.1 only.

## 029.2 Mock SOP adapter

- [x] RED: mock SOP adapter tests fail for start, continue, confirm, complete,
  and checkpoint generation.
- [x] Add mock SOP manifests for `refund_ticket`, `change_flight`, and
  `invoice_apply`.
- [x] Implement `collect_order_no -> confirm -> completed`.
- [x] Mark `collect_order_no` interruptible and `confirm` non-interruptible.
- [x] Persist collected `order_no` into task/checkpoint state.
- [x] Save evidence under
  `artifacts/slices/029-isolated-runtime-router-lab/029.2/`.
- [x] Gates pass.
- [x] Commit 029.2 only.

## 029.3 Router core

- [x] RED: route decision tests fail for no-active start, active default
  continue, strong switch trigger, and no-match.
- [x] Implement strong keyword routing from mock SOP manifests.
- [x] Implement active-task default `CONTINUE_ACTIVE_SOP`.
- [x] Implement `START_SOP`.
- [x] Implement route decision evidence with reason and matched keyword.
- [x] Save evidence under
  `artifacts/slices/029-isolated-runtime-router-lab/029.3/`.
- [x] Gates pass.
- [x] Commit 029.3 only.

## 029.4 Suspend/start and resume offer

- [x] RED: integration tests fail for A -> B suspend/start and automatic resume
  offer after B completes.
- [x] Implement `SUSPEND_AND_START` for interruptible active task step.
- [x] Implement `REJECT_SWITCH_CONTINUE_ACTIVE` for non-interruptible active
  task step.
- [x] Enforce `max_suspended_tasks=1` with
  `REJECT_SWITCH_SUSPENDED_LIMIT`.
- [x] Generate `ResumeOffer` after task completion when suspended task exists.
- [x] Emit `TASK_SUSPENDED`, `TASK_STARTED`, `TASK_COMPLETED`, and
  `RESUME_OFFERED` events.
- [x] Save evidence under
  `artifacts/slices/029-isolated-runtime-router-lab/029.4/`.
- [x] Gates pass.
- [x] Commit 029.4 only.

## 029.5 Resume task

- [x] RED: resume tests fail for `继续`, `继续刚才`, and `继续第一个`.
- [x] Resolve minimum resume phrases against the current `ResumeOffer`.
- [x] Implement `RESUME_TASK` by restoring the suspended task checkpoint.
- [x] Mark the resumed task `RUNNING`.
- [x] Clear or complete the consumed resume offer according to the service
  contract.
- [x] Emit `TASK_RESUMED` and route-decision events.
- [x] Save evidence under
  `artifacts/slices/029-isolated-runtime-router-lab/029.5/`.
- [x] Gates pass.
- [x] Commit 029.5 only.

## 029.6 Runtime-lab API contract

- [x] RED: API contract tests fail for create session, post message, list
  tasks, and list events.
- [x] Add `POST /api/v1/runtime-lab/sessions`.
- [x] Add `POST /api/v1/runtime-lab/sessions/{session_id}/messages`.
- [x] Add `GET /api/v1/runtime-lab/sessions/{session_id}/tasks`.
- [x] Add `GET /api/v1/runtime-lab/sessions/{session_id}/events`.
- [x] Return debug evidence: `reply`, `routeDecision`, `activeTask`,
  `suspendedTasks`, `resumeOffer`, and `events`.
- [x] Keep the existing `/api/v1` success envelope.
- [x] Save evidence under
  `artifacts/slices/029-isolated-runtime-router-lab/029.6/`.
- [x] Gates pass.
- [x] Commit 029.6 only.

## 029.7 Reliability gates and API E2E

- [x] RED: reliability tests fail for duplicate idempotency key, event ordering,
  and concurrent active task conflict.
- [x] Implement idempotent message replay by `(session_id, idempotency_key)`.
- [x] Ensure duplicate idempotency key does not create duplicate task/event
  records.
- [x] Ensure route transitions preserve one active task per session.
- [x] Add API E2E:
  - start refund;
  - switch to invoice at interruptible step;
  - complete invoice;
  - receive resume offer;
  - resume refund;
  - reach confirm;
  - reject switch from non-interruptible confirm step.
- [x] Save UAT request/response summaries under
  `artifacts/slices/029-isolated-runtime-router-lab/029.7/uat.md`.
- [x] Save evidence under
  `artifacts/slices/029-isolated-runtime-router-lab/029.7/`.
- [x] Gates pass.
- [x] Commit 029.7 only.

## Future specs, not 029 tasks

- [ ] Semantic recall and constrained NLP/LLM arbitration.
- [ ] Real Chatflow SOP adapter contract.
- [ ] Real Chatflow SOP integration.
- [ ] FAQ/RAG answer routing.
- [ ] Knowledge/Clarification Agent fallback.
- [ ] Human handoff policy.
