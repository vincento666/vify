# Spec 189: AI Assistant Customer Assistant Subagent Bridge

## Status

Slice `189.0` documentation sign-off is complete. Slice `189.1` backend bridge
tracer is complete for a read-only AI Assistant tool that exposes
customer-assistant sub-agent run references without mutating customer-assistant
business state.

## Goal

Add the first PRD Phase 6 bridge between the generic AI Assistant harness and
the existing customer-assistant sub-agent surface:

```text
AI Assistant tool call
  -> customer_assistant_subagent_bridge
  -> safe run/status/event/result refs
  -> persisted AI Assistant tool call and events
  -> no business writes
```

## Scope

In scope:

- read-only AI Assistant tool manifest for customer-assistant bridge refs;
- deterministic handler using existing customer-assistant harness adapter refs;
- API contract proving the tool can be called through
  `/api/v1/ai-assistant/sessions/{sessionId}/messages`;
- compatibility check against existing customer-assistant harness sub-agent
  API contract;
- MySQL8-backed AI Assistant contract tests;
- no frontend visual changes.

Out of scope:

- changing `app/modules/customer_assistant/**` runtime behavior;
- spawning new customer-assistant work from AI Assistant in this tracer;
- automatic customer-assistant business writes;
- live LLM tests by default;
- frontend UI changes;
- SQLite/PostgreSQL persistence paths;
- observability/benchmark/governance.

## Acceptance Criteria

- RED evidence shows the bridge tool missing before implementation.
- Bridge manifest is read-only, has no write resources, and exposes typed input
  schema for `sessionId` and `runId`.
- AI Assistant API can call the tool and persist the output as a normal tool
  call.
- Output includes `agentType`, `subAgentRunId`, `eventStreamRef`, `resultRef`,
  `workerAsyncRefs`, and `cancellation`.
- Existing customer-assistant harness sub-agent contract remains green.
- No `app/modules/customer_assistant/**` files are modified by this slice.
- Real LLM probes remain optional and environment-gated through OpenRouter only.

