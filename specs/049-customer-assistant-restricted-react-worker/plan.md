# Plan 049: Customer Assistant Restricted ReAct Worker

## Architecture

Add worker-local modules:

```text
app/modules/customer_assistant/domain/react_worker.py
app/modules/customer_assistant/domain/worker_registry.py
app/modules/customer_assistant/domain/tool_policy.py
```

Keep registry configuration in code/static config for 049. Do not add a DB
configuration UI.

## Implementation Strategy

Start with fake model/tool fixtures for default gates. Add live model UAT only
behind explicit opt-in configuration.

The worker returns normal 045 `WorkerResult` so the existing scheduler,
aggregator, proposed-action boundary, and 048 event stream continue to work.

## Test Strategy

- red unit tests for registry lookup and tool allowlist;
- red worker tests for max iterations and timeout;
- fake model integration test for structured output;
- proposed-action safety test;
- event persistence test for L1/L2 summaries.
