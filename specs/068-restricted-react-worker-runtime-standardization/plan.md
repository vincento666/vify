# Plan 068: Restricted ReAct Worker Runtime Standardization

## Loop Shape

```text
plan
  -> action: tool_call | final
  -> policy check
  -> observation
  -> final
```

If no tool call is needed, the worker returns final structured output.

## Event Levels

L2 events:

- `react_iteration_started`;
- `react_tool_call_started`;
- `react_tool_call_completed`;
- `react_tool_call_failed`;
- `react_observation_recorded`;
- `react_structured_output_completed`;
- `react_worker_completed`;
- `react_worker_failed`.

## Safety

All write-risk tool calls return proposed actions unless explicitly confirmed by
the operator flow.

Tool side effects are classified as read-only, proposed-write, or blocked.
Retryable side-effecting calls need idempotency keys. Default gates use
fake/deterministic tools and models.

Do not emit raw chain-of-thought/internal reasoning. Events should contain only
structured plan/action/observation summaries.
