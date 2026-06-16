# Spec 066: Customer Assistant Async Chatflow SOP Worker Adapter

## Goal

Allow the customer-assistant `ChatflowSopWorker` to use Hify Chatflow runtime v2
when the bound Chatflow graph is v2-compatible, while preserving the existing v1
adapter fallback.

## Dependency

066 depends on:

- 059 customer-assistant worker async runtime MVP;
- 061 customer-assistant async worker orchestration;
- 063 Hify Chatflow runtime v2 facade MVP;
- 064 Hify runtime v2 core node coverage pack 1;
- existing SOP multi-level routing and ChatflowSopRuntimeAdapter contract from
  031-033;
- 054 Chatflow/SOP data readiness.

## Product Boundary

In scope:

- ChatflowSopWorker can start a Chatflow v2 run for compatible graphs;
- worker state stores Chatflow runtime refs;
- Chatflow v2 events can be summarized into customer-assistant events;
- v1 fallback for unsupported graphs or missing v2 capability;
- resume of waiting Chatflow v2 checkpoint where supported.
- compatibility with the existing SOP multi-level router calling Chatflow SOP
  workers during multi-intent switching.

Out of scope:

- replacing the SOP multi-level router;
- moving multi-intent arbitration into Chatflow/Workflow runtime v2;
- node-level v1/v2 mixed Chatflow execution;
- requiring every SOP Chatflow to be v2-compatible;
- removing v1 ChatflowSopRuntimeAdapter;
- direct high-risk action execution.

## SOP Multi-level Router Boundary

The SOP multi-level router remains the owner of intent recognition, task
selection, route switching, suspend/resume, and fallback policy. This spec only
ensures that `ChatflowSopWorker` can be called by that router through either
Chatflow v2 refs or the legacy v1 adapter without changing router semantics.

The adapter must preserve router context:

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

The router may switch from one intent/SOP task to another and later resume a
previous task. Chatflow v2 execution must not leak checkpoint, variable, or
result state across those routed tasks.

## Hard Constraints

- Runtime selection is graph-level: v2-compatible whole graph or v1 fallback.
- Fallback must be explicit in events and diagnostics.
- Missing Chatflow binding is a data-readiness failure, not a worker runtime bug.
- Customer-facing behavior must remain compatible for existing refund SOP flows.
- Multi-intent switching behavior in the SOP router must remain compatible with
  the legacy ChatflowSopRuntimeAdapter path.
- Chatflow runtime v2 must not become the source of truth for SOP route state;
  it receives router context and returns execution refs/results.
- Starting a Chatflow v2 SOP run must be idempotent for the same assistant task,
  binding, checkpoint/request hash, and worker request.
- Actor, source, session, and task metadata must be propagated into the
  Chatflow run refs/events where supported.
- Worker timeout/cancel requests must propagate to Chatflow v2 cancellation or
  explicit cancellation-unsupported events.
- V1 fallback must not emit fake Chatflow v2 refs or live v2 progress events.
- Chatflow event summaries exposed to the customer-assistant timeline must be
  redacted and source-labelled.
- When Chatflow blocks on `QUESTION`, `HUMAN_INPUT`, or incomplete
  `INFORMATION_COLLECTION`, the Chatflow node's prompt/follow-up is the
  authoritative customer draft source for that turn.
- LLM recommendation aggregation may summarize or contextualize a waiting
  prompt for the operator, but must not change the concrete information the
  Chatflow node is asking the customer/operator to provide.

## Blocking Node Recommendation Boundary

Chatflow blocking nodes already carry usable waiting prompts:

- `QUESTION` exposes `interrupt.question`;
- `HUMAN_INPUT` exposes `interrupt.prompt`;
- `INFORMATION_COLLECTION` exposes `followup` and `interrupt.followup`;
- the SOP adapter normalizes these into `pendingPrompt` / `pending_prompt`.

For a waiting Chatflow SOP worker:

```text
operatorRecommendation = explain waiting reason, current node, missing fields,
  and next action for the operator
customerReplyDraft = node prompt/followup/pendingPrompt
checkpoint = Chatflow checkpoint/resume ref
```

If the node prompt is missing, the adapter may fall back to missing-field labels
or a generic prompt, but that fallback must be explicit in events/diagnostics.

## Acceptance Criteria

- Compatible Chatflow SOP worker starts a v2 runtime run and returns refs.
- Unsupported Chatflow SOP worker falls back to v1 with clear reason.
- Duplicate SOP worker dispatch for the same task/checkpoint does not start
  duplicate Chatflow v2 runs.
- Existing SOP multi-level router can call a v2-compatible Chatflow SOP and a
  v1 fallback Chatflow SOP in the same session without breaking intent/task
  switching.
- Switching from one SOP intent to another and resuming the first task preserves
  separate task context, checkpoint, variables, and results.
- Waiting/resume behavior works for a v2-compatible question path.
- Waiting Chatflow blocking nodes produce recommendation/draft output from the
  node prompt or `pendingPrompt`.
- Timeout/cancel semantics are visible at both worker and Chatflow summary
  levels.
- Customer-assistant task ledger and operator timeline show Chatflow v2 progress
  summaries.
- Existing v1 SOP tests remain green.

## MVP Exit

066 is complete when the existing SOP multi-level router can call Chatflow SOP
workers through v2-compatible runtime refs or v1 fallback without breaking
multi-intent switching, suspend/resume, or non-compatible SOP flows.
