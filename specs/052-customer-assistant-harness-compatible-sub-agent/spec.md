# Spec 052: Customer Assistant Harness-Compatible Sub-Agent

## Goal

Expose the customer-assistant runtime as a harness-compatible eventful
sub-agent. The integration shape follows the mainstream delegation pattern:
the main agent calls a function/handoff to spawn a specialist sub-agent, then
the UI or harness observes that sub-agent through run status, result, and event
stream references.

There is no universal industry standard literally named `spawn_sub_agent`.
052 defines Hify's compatible contract explicitly.

## Dependency

052 depends on:

- 048 event stream;
- 049 restricted worker event vocabulary when React workers are exposed through
  the spawned sub-agent;
- 050 action lifecycle if proposed-action execution is exposed through the
  spawned sub-agent;
- any minimal run-handle capability available by implementation time.

## MVP Scope Guard

052 is an integration-contract MVP. It exposes customer assistant as an
eventful specialist sub-agent with run/status/result/event references. It must
not move customer-assistant logic into the main agent, require a full generic
harness rewrite, or refactor Workflow/Chatflow.

## Contract

Function-call shape:

```json
{
  "tool": "spawn_sub_agent",
  "arguments": {
    "agentType": "customer_assistant",
    "sessionId": "optional-existing-session",
    "input": {
      "message": "customer asks for refund and baggage info",
      "actor": "customer"
    },
    "eventLevel": "L1"
  }
}
```

Response shape:

```json
{
  "subAgentRunId": "customer-assistant-run-123",
  "status": "running",
  "eventStreamRef": "/api/v1/customer-assistant/sessions/1/events/stream?afterSequence=0",
  "resultRef": "/api/v1/customer-assistant/runs/123"
}
```

If full async run lifecycle is not available yet, 052 must either add the
minimal run handle it needs or explicitly block until the lifecycle spec is
ready. It must not pretend a blocking tool call is an eventful sub-agent.

## Async Run Boundary

052 should stabilize the externally visible async run shape for the spawned
customer-assistant sub-agent:

```text
spawn -> subAgentRunId
status -> running | waiting | completed | failed | cancelled
events -> eventStreamRef
result -> resultRef
```

Internal workers may still execute through the existing customer-assistant
scheduler in the MVP, but the contract must leave room for worker-level run
handles:

```text
workerRunId
workerStatusRef
workerEventStreamRef
workerResultRef
```

Workflow/Chatflow runtime v2 must wait until this sub-agent/worker async shape
is stable enough to serve as the reference calling convention.

## Event Types

```text
sub_agent_spawned
sub_agent_started
sub_agent_progress
sub_agent_waiting
sub_agent_completed
sub_agent_failed
sub_agent_cancelled
```

The UI may subscribe to the event stream directly. The main agent may consume
the final result and summarize after completion.

## Acceptance Criteria

- Main-agent/harness caller can spawn a customer-assistant sub-agent through a
  structured function-call contract.
- Caller receives run id, event stream ref, and result ref.
- Runtime events are visible without being narrated through the main agent.
- Final result can be fetched and summarized by the caller.
- Cancellation/status behavior is either implemented or explicitly marked
  unsupported in the contract response.
