# Plan 052: Customer Assistant Harness-Compatible Sub-Agent

## Architecture

Add a thin adapter around the customer-assistant runtime:

```text
app/modules/customer_assistant/harness_adapter.py
```

Do not move customer-assistant business logic into the main agent.

## MVP Boundary

052 should make customer assistant callable as an eventful sub-agent before
attempting any canvas runtime unification. The MVP contract is intentionally
small:

```text
spawn
status
events
result
optional cancel
```

Worker-level async run refs may be reserved if they are not implemented in the
first slice, but the adapter must not collapse into a blocking function call
that hides runtime progress.

## Integration Model

```text
main agent
  -> spawn_sub_agent(customer_assistant)
  -> receives refs
UI/harness
  -> subscribes to eventStreamRef
main agent
  -> fetches resultRef
  -> summarizes final answer
```

## Test Strategy

- contract tests for spawn request/response;
- event ref validity test;
- result ref fetch test;
- cancellation/status behavior tests if supported.
