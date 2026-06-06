# Spec 029: Isolated Runtime Router Lab

## Goal

Build an isolated, database-backed runtime/router lab for SOP-first customer
service conversation control before integrating with the existing Chatflow,
Agent, FAQ, RAG, or handoff runtimes.

This spec was discussed as the next "026" workstream, but the repository
already contains `026`, `027`, and `028` specs. The stable directory id is
therefore `029-isolated-runtime-router-lab`.

## Why This Spec Exists

Hify already has single-Chatflow interrupt/resume work in `018` and customer
service runtime parity work in `022`. Those specs intentionally do not provide
cross-SOP dynamic task switching, a unified runtime session, or a task-ledger
based conversation controller.

The next capability must be proven without destabilizing the current
Workflow/Chatflow engine:

- user starts one SOP;
- user switches to another SOP while the first one is interruptible;
- the first SOP is suspended with a checkpoint;
- the second SOP completes;
- the robot offers to resume the suspended SOP;
- the user resumes by conversation text;
- the original SOP continues from its checkpoint.

The first implementation must be isolated and one-way only. Existing
Chatflow/Workflow/Agent code must not depend on the new runtime lab.

## Product Boundary

In scope:

- new isolated runtime/router module;
- database-backed runtime session, task, checkpoint, event, and command state;
- mock SOP adapter only;
- three mock aviation-style SOPs:
  - `refund_ticket`;
  - `change_flight`;
  - `invoice_apply`;
- strong keyword routing for mock SOPs;
- one active task per session;
- task ledger that supports multiple suspended tasks in the data model;
- 029 policy limit of at most one suspended task;
- minimum resume offer and resume resolution;
- `/api/v1/runtime-lab/...` API surface for backend contract testing;
- debug-oriented API responses with route decision, tasks, offer, and events;
- strict Spec Kit + TDD slice evidence;
- git commit after spec creation and after each completed implementation slice.

Out of scope:

- real Chatflow execution;
- real Agent execution;
- real FAQ, RAG, embedding, BM25, ES, rerank, or LLM classifier;
- frontend or browser UI;
- multi-suspended-task disambiguation;
- semantic suspended-task recall;
- operational route-rule configuration UI;
- final product API naming such as `/chat`, `/query`, or
  `/conversations/{id}/messages`.

The `runtime-lab` API namespace is temporary. Later integration specs may expose
a product API under a more user-facing name after the isolated runtime passes
its gates.

## Core Principles

- Route control is separate from SOP execution.
- The router decides whether to continue, start, suspend/start, resume, or
  reject a switch.
- SOP nodes remain responsible for business slot validation.
- The first lab uses strong rules only; weak semantic routing is deferred.
- The runtime is persisted from day one because resume, idempotency, ordering,
  and auditability are the core risk.
- `RuntimeTaskLedger` is the source of truth. A task stack is only a future
  projection or policy view.
- Existing Chatflow/Workflow services are not modified by this spec.

## Runtime Model

### RuntimeSession

Represents one isolated lab conversation.

Required fields:

- `id`
- `status`: `ACTIVE`, `COMPLETED`, `HANDOFF`, `EXPIRED`
- `active_task_id`
- `version`
- `created_at`
- `updated_at`
- `deleted`

### RuntimeTask

Represents one mock SOP runtime instance, not an SOP template.

Required fields:

- `id`
- `session_id`
- `sop_id`
- `status`: `RUNNING`, `SUSPENDED`, `WAITING`, `COMPLETED`, `CANCELLED`,
  `FAILED`
- `current_step`
- `checkpoint_id`
- `parent_task_id`
- `resume_summary`
- `business_refs`
- `created_at`
- `updated_at`
- `suspended_at`
- `completed_at`
- `expires_at`
- `deleted`

### RuntimeCheckpoint

Stores enough mock SOP state to continue safely.

Required fields:

- `id`
- `session_id`
- `task_id`
- `sop_id`
- `current_step`
- `pending_prompt`
- `collected`
- `status`: `ACTIVE`, `SUPERSEDED`, `COMPLETED`, `EXPIRED`
- `created_at`
- `updated_at`
- `deleted`

### RuntimeEvent

Append-only audit trail for the lab runtime.

Required event types:

- `SESSION_CREATED`
- `USER_MESSAGE`
- `ROUTE_DECISION`
- `TASK_STARTED`
- `TASK_CONTINUED`
- `TASK_SUSPENDED`
- `TASK_COMPLETED`
- `RESUME_OFFERED`
- `TASK_RESUMED`
- `SWITCH_REJECTED`
- `COMMAND_REPLAYED`
- `ERROR`

Events must have monotonically increasing `sequence` per session.

### RuntimeCommand

Idempotency record for incoming message commands.

Required fields:

- `id`
- `session_id`
- `idempotency_key`
- `request_hash`
- `response_payload`
- `created_at`

`(session_id, idempotency_key)` must be unique when an idempotency key is
provided.

## Mock SOP Manifest

The 029 lab stores route keywords in mock SOP manifests. Later specs can promote
them into configurable route rules.

Each mock SOP manifest includes:

- `sop_id`
- `display_name`
- `trigger_keywords`
- `strong_trigger_keywords`
- `steps`
- `interruptible_steps`
- `resume_prompt`

Required mock SOPs:

```text
refund_ticket
change_flight
invoice_apply
```

Required step behavior:

- `collect_order_no`
  - interruptible: true;
  - ordinary user input is saved as `order_no`;
  - next step is `confirm`.
- `confirm`
  - interruptible: false;
  - user message `confirm` or `确认` completes the task.
- `completed`
  - terminal.

## Routing Behavior

### No Active Task

If a strong SOP trigger is matched, start the target mock SOP.

Example:

```text
User: 我要退票
Decision: START_SOP(refund_ticket)
```

### Active Task Default

If a session has an active task and no strong switch/resume/hard-exit signal is
matched, the router returns `CONTINUE_ACTIVE_SOP`.

The mock SOP adapter then decides how to process the message.

### Interruptible Switch

If the active task is at an interruptible step and the user strongly triggers a
different mock SOP:

```text
Decision: SUSPEND_AND_START
```

The runtime must:

- persist a checkpoint for the active task;
- mark the active task `SUSPENDED`;
- start the new task as `RUNNING`;
- emit route, suspend, and start events in one transaction.

### Non-Interruptible Switch Rejection

If the active task is at a non-interruptible step and the user strongly triggers
a different mock SOP:

```text
Decision: REJECT_SWITCH_CONTINUE_ACTIVE
```

The runtime must not create or start the new task. The reply must explain that
the current step cannot be interrupted.

### Suspended Task Limit

The data model supports multiple suspended tasks, but 029 policy allows at most
one suspended task per session.

If the user attempts a third SOP while one task is already suspended and another
task is active, the runtime must reject the switch and preserve existing tasks.

### Completion And Resume Offer

When a task completes and the session has suspended tasks, the response must
include a `resumeOffer`.

029 only verifies automatic resume offers after task completion.

Example:

```text
Invoice task completed.
Resume offer: continue suspended refund task.
```

### Resume Resolution

029 supports minimum text resume resolution:

- `继续刚才`
- `继续第一个`
- `继续`

These phrases resolve to the single suspended task in the current `resumeOffer`.

Multiple suspended-task disambiguation is out of scope.

## API Surface

Temporary lab endpoints:

```text
POST /api/v1/runtime-lab/sessions
POST /api/v1/runtime-lab/sessions/{session_id}/messages
GET  /api/v1/runtime-lab/sessions/{session_id}/tasks
GET  /api/v1/runtime-lab/sessions/{session_id}/events
```

Message request fields:

- `message`
- `idempotencyKey`

Message response fields:

- `reply`
- `routeDecision`
- `activeTask`
- `suspendedTasks`
- `resumeOffer`
- `events`

The response is intentionally evidence-rich because this is a lab contract.

## Route Decision Actions

Required 029 actions:

- `START_SOP`
- `CONTINUE_ACTIVE_SOP`
- `SUSPEND_AND_START`
- `REJECT_SWITCH_CONTINUE_ACTIVE`
- `REJECT_SWITCH_SUSPENDED_LIMIT`
- `COMPLETE_TASK`
- `OFFER_RESUME`
- `RESUME_TASK`
- `NO_MATCH`
- `ERROR`

Later specs may add:

- `ANSWER_FAQ`
- `ANSWER_RAG`
- `ASK_CLARIFICATION`
- `RUN_AGENT`
- `HANDOFF_TO_HUMAN`

## Acceptance Gates

029 is complete only when all slices pass their required evidence gates:

- RED evidence before implementation per slice;
- unit tests for pure routing and mock SOP behavior;
- integration tests for DB-backed state transitions;
- contract tests for `runtime-lab` APIs;
- API E2E scripts for the full A -> B -> resume A flow;
- UAT markdown records with request/response summaries;
- git commit after spec creation and after each completed slice.

No frontend rem or browser UAT gate is required in 029 because no frontend files
are in scope.

## Evolution Roadmap

Detailed specs are intentionally deferred until 029 passes.

Planned follow-up stages:

- `030` Mock semantic routing and constrained intent arbitration:
  add candidate recall, keyword score evidence, and later embedding/LLM
  arbitration with mock data.
- `031` Chatflow SOP adapter contract:
  define the one-way adapter from the isolated runtime into existing Chatflow
  run/resume APIs without making Chatflow depend on the runtime.
- `032` Chatflow SOP integration:
  connect one real Chatflow path after adapter contract gates pass.
- `033` FAQ/RAG/Agent/handoff fallback policy:
  add `ANSWER_FAQ`, `ANSWER_RAG`, controlled Knowledge/Clarification Agent, and
  `HANDOFF_TO_HUMAN` strategies.
