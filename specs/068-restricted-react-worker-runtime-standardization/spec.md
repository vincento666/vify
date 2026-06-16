# Spec 068: Restricted ReAct Worker Runtime Standardization

## Goal

Standardize the existing restricted ReAct worker into a bounded, eventful worker
runtime with tool registry, tool policy, structured observations, and structured
final output.

This spec does not convert the whole customer-assistant runtime into ReAct.

## Dependency

068 depends on:

- 049 restricted ReAct worker;
- 059 worker async runtime MVP;
- 067 cross-runtime observability gate.

## Product Boundary

In scope:

- one restricted ReAct worker type;
- plan/action/observation/final loop;
- tool registry and tool policy gate;
- structured observation schema;
- structured final output schema;
- L2 worker events;
- timeout/cancel integration with worker runtime;
- high-risk tool calls become proposed actions.

Out of scope:

- unrestricted autonomous agent behavior;
- customer-assistant main runtime ReActification;
- broad harness replacement;
- direct execution of high-risk writes.

## Hard Constraints

- Tool set is explicit and allowlisted.
- High-risk or write tools must return proposed actions.
- Max iterations, timeout, and cancellation are enforced or honestly reported.
- Existing worker output semantics remain compatible.
- Tool side effects must be classified as read-only, proposed-write, or blocked.
- Tool calls that may be retried must carry idempotency keys or be read-only.
- Default MVP tests must use fake/deterministic tools and models; live network or
  live provider calls require explicit opt-in configuration.
- Internal chain-of-thought or raw model reasoning must not be emitted as worker
  events; only structured plan/action/observation summaries may be emitted.
- Action, observation, and final schemas must be versioned and redacted.
- Iteration, token/cost, and wall-clock budgets must be explicit.

## Acceptance Criteria

- Restricted ReAct worker emits standardized L2 events.
- Tool policy blocks unsupported tools.
- High-risk tool call produces proposed action.
- Retried tool calls do not duplicate side effects.
- Structured final output validates.
- Worker events expose structured summaries without raw hidden reasoning.
- Worker runtime refs/status/events remain compatible with 059.

## MVP Exit

068 is complete when one ReAct worker is a reliable bounded worker runtime, not
a free-form autonomous agent.
