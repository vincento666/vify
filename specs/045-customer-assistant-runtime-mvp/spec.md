# Spec 045: Customer Assistant Runtime MVP

## Goal

Build an independent ToB customer-assistant sub-agent runtime that can
recognize customer-service tasks, maintain a persisted task ledger, execute
multiple bounded workers in parallel, and return operator-facing
recommendations plus customer-facing draft replies.

045 deliberately removes LangChain/LangGraph from the runtime baseline. The
MVP keeps a lightweight, structured state machine and a controlled ReAct-shaped
loop owned by Hify.

## Why This Spec Exists

Specs 029-040 created a ToC-oriented runtime-lab control plane. That runtime is
optimized for a single customer conversation where the robot directly routes
and responds:

```text
user message
  -> route decision
  -> one active SOP/FAQ/RAG/Agent path
  -> customer-visible reply
```

The customer-assistant runtime has a different business posture. It is a ToB
operator-assistance runtime where the human operator remains the service owner,
and the robot acts as a supervised task assistant:

```text
customer/operator context
  -> task commands
  -> task ledger
  -> parallel workers
  -> operator recommendation + customer reply draft
```

Both runtimes may use the same Chatflow/SOP business capabilities. They must
not share the same top-level control model.

## Product Boundary

In scope:

- new `customer_assistant` backend module;
- independent `/api/v1/customer-assistant/...` API surface;
- database-backed assistant sessions, runs, tasks, events, and proposed
  actions;
- first-class `TaskLedger` state;
- controlled ReAct core with `max_iterations = 1` for MVP;
- deterministic/fake task-recognition controller for MVP;
- internal fan-out/join worker scheduler;
- real Chatflow/SOP worker through the existing `ChatflowSopRuntimeAdapter`;
- stub QA worker;
- stub recommendation aggregator;
- L0/L1 runtime events with schema reserved for nested worker spans;
- high-risk write operations represented as `proposed_action`, not executed
  automatically;
- tests proving single-task, multi-task, resume, failure, proposed-action, and
  event behavior.

Out of scope:

- LangChain or LangGraph dependency;
- replacing existing `ChatService` or `ChatOrchestrator`;
- replacing existing `runtime_lab` ToC router;
- full generic ReAct framework exposed to ordinary agents;
- real LLM task recognition;
- real LLM recommendation aggregation;
- real RAG/Agent worker;
- recursive eventful sub-agent traces;
- frontend operator panel in the first backend MVP slice;
- direct high-risk write execution without human confirmation.

## Runtime Relationship

045 reuses business capabilities from existing runtime work:

```text
Chatflow/SOP
SopExecutionRequest / SopExecutionResult / SopCheckpoint
ChatflowSopRuntimeAdapter
WorkflowService execute/resume/session state
MCP/API/RAG/Agent capabilities as future worker implementations
```

045 does not reuse the ToC runtime-lab main loop:

```text
RuntimeLabService.handle_message
RuntimeLabRouter single-active-task control
029 one-suspended-task policy
ToC direct customer reply ownership
```

The dependency direction remains one-way from the new customer-assistant module
to reusable adapter ports or application facades. Existing Workflow/Chatflow
modules must not import the new customer-assistant module.

## Core Runtime Shape

MVP execution is a one-iteration controlled ReAct loop:

```text
load session and ledger
  -> reason: deterministic task-recognition controller returns TaskCommand[]
  -> validate: runtime policy approves bounded actions
  -> act: apply ledger mutations and execute ready workers in parallel
  -> observe: persist WorkerResult events and task state
  -> final: aggregate operator recommendation and customer reply draft
```

The MVP keeps the old three-stage mental model:

```text
task_recognition -> task_execute_parallel -> generate_recommendation
```

but implements it with future-compatible loop terminology:

```text
reason -> validate -> act -> observe -> final
```

Future specs may increase `max_iterations` and expose the core as a reusable
agent runtime. 045 must not build that general framework yet.

## Task Ledger Model

`TaskLedger` is the source of truth for assistant task state. It must not be
derived from transient Chatflow variables.

Required task statuses:

```text
PENDING
RUNNING
WAITING
COMPLETED
FAILED
CANCELLED
```

Required task fields:

```text
id
session_id
task_key
task_type
business_key
short_id
status
worker_type
worker_ref
checkpoint_json
input_snapshot_json
last_result_json
proposed_actions_json
version
created_at
updated_at
completed_at
deleted
```

`task_key` is the runtime-level stable identity used to retain, cancel, and
deduplicate tasks across turns.

## Task Commands

The deterministic controller returns typed commands:

```text
ADD_TASK
RETAIN_TASK
CANCEL_TASK
SUSPEND_TASK
RESUME_TASK
CALL_WORKER
FINAL
```

MVP command recognition is deterministic:

- messages containing refund intent add or retain `refund_ticket`;
- messages containing baggage/allowance intent add or retain `baggage_qa`;
- messages containing order-like values continue active refund tasks;
- messages containing explicit cancel language cancel matching tasks.

LLM structured output is future work. The runtime contract must already accept
structured task commands so the controller can be swapped later.

## Worker Contract

Workers run bounded task units and return normalized `WorkerResult`.

Required fields:

```text
task_id
worker_type
status: WAITING | COMPLETED | FAILED
operator_recommendation
customer_reply_draft
missing_fields
evidence
safe_auto_actions_done
proposed_actions
checkpoint
events
error
```

MVP worker matrix:

| Worker | Status |
|--------|--------|
| `ChatflowSopWorker` | real, uses existing Chatflow SOP adapter |
| `StubQaWorker` | fake deterministic answer |
| `RecommendationAggregator` | fake deterministic aggregation |
| real RAG worker | out of scope |
| real Agent worker | out of scope |
| real LLM aggregation | out of scope |

## Parallel Execution

The runtime must support multiple ready tasks in one turn:

```text
ready tasks -> fan out -> worker execution -> join -> aggregate
```

Requirements:

- each task gets an independent worker timeout;
- one task failure must not fail the whole turn;
- worker results update only their own task state;
- joined results are ordered deterministically for response generation;
- graph/canvas-level parallelism is not introduced by this spec.

## Human Confirmation Boundary

MVP distinguishes safe automatic actions from high-risk proposed actions.

Automatically allowed:

- information collection;
- knowledge/FAQ/RAG style read-only answers;
- read-only API queries;
- Chatflow/SOP step execution up to waiting or recommendation points;
- recommendation and customer-draft generation.

Must become `proposed_action`:

- refund submission;
- ticket change submission;
- order modification;
- invoice submission;
- profile or passenger data modification;
- sending a customer message;
- creating an external handoff ticket when it mutates an external system.

The assistant runtime may persist, display, confirm, or reject proposed actions.
It must not execute high-risk writes automatically in 045.

## Result Contract

`AssistantTurnResult` must separate operator-facing and customer-facing output:

```text
run_id
session_id
reply_type
operator_recommendation
customer_reply_draft
task_summaries
proposed_actions
warnings
events
```

`operator_recommendation` is for the human operator. `customer_reply_draft` is
a draft the operator may review, edit, or send through a later channel/action.

## Event Contract

MVP supports L0 and L1 events.

L0 runtime events:

```text
run_started
task_recognized
task_added
task_retained
task_cancelled
task_started
task_waiting
task_completed
task_failed
recommendation_generated
run_completed
```

L1 worker summary events:

```text
worker_started
worker_checkpointed
worker_interrupted
worker_proposed_action
worker_result_received
```

Event envelope:

```text
id
session_id
run_id
sequence
type
visibility: operator | debug
source
task_id
parent_span_id
span_id
payload
created_at
```

Events must be persisted with monotonically increasing sequence per session.
L2 recursive worker traces are reserved for later specs.

## API Surface

MVP backend APIs:

```text
POST /api/v1/customer-assistant/sessions
POST /api/v1/customer-assistant/sessions/{sessionId}/turns
GET  /api/v1/customer-assistant/sessions/{sessionId}/tasks
GET  /api/v1/customer-assistant/sessions/{sessionId}/events
POST /api/v1/customer-assistant/proposed-actions/{actionId}/confirm
POST /api/v1/customer-assistant/proposed-actions/{actionId}/reject
```

The API response envelope must preserve existing Hify `{code, message, data}`
behavior.

## Acceptance Criteria

- A refund message creates or retains a `refund_ticket` task and runs the real
  Chatflow/SOP worker.
- A refund task can wait for missing information and continue on the next turn
  from persisted checkpoint state.
- A message containing refund and baggage intents creates two tasks and
  executes them through runtime-level fan-out/join.
- QA task uses the stub worker in 045 and returns a deterministic completed
  result.
- High-risk write operations are persisted as `proposed_action` and are not
  executed automatically.
- Operator recommendation and customer reply draft are separate fields.
- Events persist and can be listed in sequence.
- Idempotent turn submission does not duplicate tasks or proposed actions.
- Existing runtime-lab and Chatflow tests remain compatible.

## Completion Capability

After 045, Hify has a ToB customer-assistant runtime that can supervise
production-tested Chatflow/SOP business workers without depending on
LangChain/LangGraph and without conflating ToB operator assistance with the ToC
runtime-lab router.

## Completion Evidence

Spec 045 implementation slices 045.1 through 045.6 are complete. Evidence is
saved under `artifacts/slices/045-customer-assistant-runtime-mvp/`, including
RED, unit, integration/contract, E2E, UAT notes, focused runtime regressions,
lint, mypy, and full non-acceptance backend pytest output.
