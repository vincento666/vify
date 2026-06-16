# Plan 066: Customer Assistant Async Chatflow SOP Worker Adapter

## Runtime Selection

```text
SOP multi-level router selects task/intent
  -> lookup sop_id -> chatflow_id
check data readiness
check graph v2 compatibility
  if compatible: run Chatflow v2
  else: run v1 adapter fallback
```

Do not mix node-level v1/v2 execution.
V2 SOP run start must be idempotent for the same assistant task, binding,
checkpoint/request hash, and worker request.
Unexpected v2 start failures crossing the legacy SOP adapter port are
normalized to the legacy `CHATFLOW_START_FAILED` contract and keep the richer
`CHATFLOW_V2_START_FAILED` diagnostic code as metadata.

The SOP router remains the owner of multi-intent switching, suspend/resume, and
fallback policy. Chatflow v2 is only the execution target selected by the
adapter.

## Router Context Contract

Preserve these fields across v2 refs/events and v1 fallback diagnostics:

```text
sop_key
route_id
route_turn_id
intent_key
task_id
session_id
actor
source
```

Compatibility scenarios:

- intent A starts a Chatflow v2 SOP and waits for missing information;
- intent B is routed and completed while intent A is suspended;
- intent A resumes with its original checkpoint and variables;
- an unsupported SOP falls back to v1 without fake v2 refs;
- a v2-compatible and v1-fallback SOP can coexist in the same session.

## Event Projection

Chatflow runtime events remain Chatflow runtime events. Customer Assistant should
pass live runtime v2 node events through as first-class worker events, then
project compatibility summaries:

- worker started;
- Chatflow run started;
- current node/stage;
- router-selected SOP key and task id;
- waiting checkpoint;
- completed/failed;
- fallback reason.

Projected summaries must carry source labels and redact payloads. Raw Chatflow
refs may remain available for debug, but v1 fallback must not fabricate v2 refs
or v2 live events.

First-class live Chatflow events must be ordered before the compatibility
`worker_result_received` summaries and preserve runtime correlation refs:
`runtimeRunId`, `sourceEventId`, `sourceSequence`, node key, and SOP router
caller context.

## Blocking Node Recommendation

When Chatflow returns an interrupt, prefer the node's own customer-facing text:

```text
QUESTION.interrupt.question
HUMAN_INPUT.interrupt.prompt
INFORMATION_COLLECTION.followup
INFORMATION_COLLECTION.interrupt.followup
SopCheckpoint.pending_prompt
```

The customer assistant recommendation layer should split this into:

- operator recommendation: why the run is waiting and what the operator should
  do next;
- customer draft: the node prompt/followup text to send or adapt;
- checkpoint evidence: run/checkpoint refs for the next turn.

LLM aggregation may polish the operator explanation, but it must not alter the
specific fields/question requested by the Chatflow node.

## Resume

If Chatflow v2 returns a checkpoint, store it in the worker/task checkpoint and
resume through runtime v2 resume refs.

Timeout/cancel requests from the worker layer should propagate to Chatflow v2
cancellation where supported, or emit explicit cancellation-unsupported
evidence.
