# Spec 047: Customer Assistant LLM Shadow And Actor

## Goal

Add two production-readiness foundations to the customer-assistant runtime:

- first-class `actor` persistence for customer, operator, and system turns;
- opt-in LLM shadow mode for task recognition and recommendation generation.

047 must not let LLM output control the main runtime path. The deterministic
045 controller and aggregator remain the source of truth unless a later spec
explicitly promotes an LLM path out of shadow mode.

## Dependency

047 depends on:

- 045 Customer Assistant Runtime MVP;
- 046 Customer Assistant Operator Panel MVP.

047 does not depend on LangChain, LangGraph, or a generic agent harness.

## Product Boundary

In scope:

- persist `actor=customer|operator|system` through turn input, run payload,
  runtime events, and worker input snapshots;
- default `actor` to `customer` for backwards compatibility;
- update the 046 frontend client to send `actor` instead of local-only
  `source`;
- keep one runtime state machine for all actors in 047;
- add customer-assistant LLM shadow configuration;
- add fake shadow client for deterministic tests;
- add live shadow client using the existing Hify OpenAI-compatible provider
  stack;
- run task-recognition shadow after deterministic recognition;
- run recommendation shadow after deterministic aggregation;
- persist structured shadow outputs, parse failures, latency, and diffs as
  debug runtime events;
- add opt-in live LLM shadow UAT.

Out of scope:

- channel/source modeling such as web, phone, inbox, main-agent, or harness;
- operator-turn branching or recommendation-only operator mode;
- LLM output mutating the task ledger, task commands, worker dispatch, proposed
  actions, or final user-visible response;
- replacing the 045 deterministic controller;
- replacing the 045 deterministic aggregator;
- streaming LLM tokens;
- generic ReAct worker implementation;
- LangChain/LangGraph adoption.

## MVP Scope Guard

047 is a safety and observability MVP. It only adds durable actor metadata and
shadow-mode evidence. It must not promote LLM output into the production control
path, add operator-turn branching, or change the existing task/worker runtime
semantics.

## Actor Model

047 introduces `actor`, not `source`.

Allowed values:

```text
customer
operator
system
```

Meaning:

- `customer`: the external customer's utterance or transcript fragment;
- `operator`: the human operator talking to the assistant;
- `system`: an internal runtime trigger or scheduled/system-generated turn.

`source` remains a component/source field for events and worker evidence, such
as:

```text
customer_assistant
chatflow_sop
stub_qa
llm_shadow
react_worker
```

047 must not use `actor` to fork the state machine. Operator-specific dispatch
is reserved for a later turn-mode spec.

## API Contract

Update the turn request:

```text
POST /api/v1/customer-assistant/sessions/{sessionId}/turns
```

Request:

```json
{
  "message": "I need a refund",
  "idempotencyKey": "optional-client-key",
  "actor": "customer"
}
```

Rules:

- omitted `actor` is treated as `customer`;
- invalid actor returns a normal API validation error;
- idempotency hash must include `actor` so the same message from customer and
  operator are not treated as the same turn;
- response shape remains compatible with 045 except events may include
  `actor`.

Update event payloads and API event rows with:

```text
actor
```

The existing `source` field stays as component source.

## Persistence Boundary

047 must persist actor in durable data, not only in transient request objects.

Required persistence points:

- assistant run input payload and/or explicit run actor column;
- runtime event row and event API payload;
- task input snapshot when a command adds or retains a task;
- shadow event payloads.

If the repository keeps JSON input payloads for runs, actor may be added there
for MVP. Events should expose actor directly in the formatted API event because
048 will use events as the streaming source of truth.

## Shadow Mode

Shadow mode means:

```text
call LLM -> parse strict schema -> compare with deterministic result
          -> persist evidence -> ignore for main runtime behavior
```

Shadow output must not:

- mutate the task ledger;
- dispatch workers;
- create or change proposed actions;
- override operator recommendation;
- override customer reply draft;
- change run status;
- fail the turn when the LLM call fails.

## Shadow Configuration

Add customer-assistant scoped settings:

```text
HIFY_CUSTOMER_ASSISTANT_LLM_SHADOW_MODE=off|fake|live
HIFY_CUSTOMER_ASSISTANT_LLM_SHADOW_MODEL_CONFIG_ID=<model_config_id>
HIFY_CUSTOMER_ASSISTANT_LLM_SHADOW_TASK_RECOGNITION=true|false
HIFY_CUSTOMER_ASSISTANT_LLM_SHADOW_RECOMMENDATION=true|false
```

Defaults:

```text
mode = off
task_recognition = true
recommendation = true
model_config_id = unset
```

Live mode requires `model_config_id`. Fake mode must not call the network.

## LLM Client Boundary

Use existing Hify provider capabilities:

```text
ProviderModelFacade
OpenAIChatRequestBuilder
ProviderBackedOpenAIChatClient
OpenAIAdapterParser
```

Add only a thin customer-assistant shadow client and schema parser. Do not add a
new LLM framework.

## Strict Shadow Schemas

Task-recognition shadow output:

```json
{
  "commands": [
    {
      "type": "ADD_TASK",
      "taskKey": "refund_ticket:ORDER-100",
      "taskType": "refund_ticket",
      "businessKey": "ORDER-100",
      "workerType": "chatflow_sop",
      "workerRef": "refund_ticket",
      "reason": "customer asked for refund"
    }
  ],
  "confidence": 0.82,
  "warnings": []
}
```

Recommendation shadow output:

```json
{
  "operatorRecommendation": "Ask for the ticket number before confirming refund.",
  "customerReplyDraft": "I can help with the refund. Could you provide the ticket number?",
  "warnings": [],
  "taskSummaries": []
}
```

Parsing failures produce shadow failure events and do not fail the turn.

## Shadow Event Types

Persist debug events in `customer_assistant_event`:

```text
llm_shadow_started
llm_shadow_completed
llm_shadow_failed
llm_shadow_diff_recorded
```

Required payload fields:

```text
phase: task_recognition | recommendation
mode: fake | live
modelConfigId
actor
baseline
shadow
diff
latencyMs
error
```

Payloads should be structured so Spec 051 can export them into evaluation
cases.

## Acceptance Criteria

- Existing 045/046 behavior remains green when shadow mode is `off`.
- A turn without `actor` is persisted and returned as `customer`.
- A turn with `actor=operator` is persisted in run input, event payloads, and
  task input snapshots without changing 045 state-machine behavior.
- Frontend turn payload uses `actor`, not `source`.
- Fake task-recognition shadow runs and records strict parsed output plus diff.
- Fake recommendation shadow runs and records strict parsed output plus diff.
- Shadow LLM failure records a debug event and the main turn still succeeds.
- Live shadow UAT can be enabled explicitly with a real model config and is not
  part of default test gates.

## Completion Capability

After 047, Hify can observe real LLM behavior beside the deterministic
customer-assistant runtime while preserving production safety. The runtime also
has enough actor metadata for later operator-turn dispatch without introducing
channel complexity.
