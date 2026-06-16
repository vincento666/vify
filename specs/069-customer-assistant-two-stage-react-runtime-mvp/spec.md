# Spec 069: Customer Assistant Two-Stage ReAct Runtime MVP

## Goal

Evolve the customer-assistant main runtime from a controlled fixed loop into a
bounded Two-Stage ReAct runtime while preserving current product semantics.

The upgrade must be smooth: existing task recognition, ledger mutation, worker
dispatch, recommendation aggregation, actor rules, and proposed-action safety
must behave the same unless an explicit opt-in mode is enabled.

## Dependency

069 depends on:

- 055 LLM primary path with deterministic fallback;
- 057 operator turn mode;
- 061 customer-assistant async worker orchestration;
- 068 restricted ReAct worker runtime standardization.

## Product Boundary

In scope:

- Two-Stage ReAct wrapper for the main customer-assistant runtime;
- shadow/diff mode comparing controlled loop and Two-Stage ReAct output;
- opt-in primary mode with fallback to controlled loop;
- Stage 1: plan/task recognition/safety;
- Stage 2: execute allowed actions/workers;
- final recommendation when no action is needed, using the same product
  contract as the current `generate_recommendation` phase.

Out of scope:

- unrestricted self-looping autonomy;
- changing default product behavior;
- bypassing proposed actions;
- changing operator recommendation-only behavior;
- replacing worker runtime internals.

## Hard Constraints

- Default behavior remains the existing controlled loop.
- Same input and same ledger should produce equivalent task commands in shadow
  comparison before opt-in primary.
- Operator recommendation turns remain read-only by default.
- High-risk writes remain proposed actions.
- Fallback to controlled loop is mandatory for schema, safety, unsupported
  action, timeout, or confidence failures.
- Shadow mode must not dispatch extra workers, call side-effecting tools, or
  mutate task/runtime state.
- Stage 2 may execute only allowlisted runtime commands and worker dispatches.
- The Two-Stage `final` response is the successor of the current
  `generate_recommendation` phase and must produce the same output schema:
  `operatorRecommendation`, `customerReplyDraft`, `proposedActions`,
  task summaries, warnings, and evidence refs.
- Finalization must be evidence-bound: it may use task ledger state, worker
  results, waiting worker evidence, Chatflow blocking-node prompts,
  proposed-action state, safety policy, and conversation context; it must not
  invent new business facts.
- Waiting Chatflow/worker prompts are authoritative for customer drafts. The
  finalizer may explain them to the operator but must not change the concrete
  fields/questions requested by the worker.
- Two-Stage modes may persist debug-only structured plan/action/observation/final
  summaries mapped to the legacy three-stage contract, but must not persist raw
  chain-of-thought/internal reasoning.
- Raw chain-of-thought/internal reasoning must not be persisted or displayed;
  only structured stage summaries and decisions may be emitted.
- Opt-in primary rollout must be controlled by explicit config and must remain
  reversible at runtime/deploy time.
- Promotion from shadow to primary requires a documented equivalence threshold
  over the 054 synthetic/golden suite.

## Acceptance Criteria

- Shadow Two-Stage ReAct produces diff evidence without changing behavior.
- Shadow mode does not create additional worker/tool side effects.
- Opt-in mode can select Two-Stage output for safe cases.
- Fallback events explain controlled-loop fallback.
- Equivalence report covers task commands, ledger mutations, worker dispatches,
  recommendations, drafts, and proposed actions.
- Two-Stage final output is schema-compatible with current
  `generate_recommendation`.
- Two-Stage main-runtime events expose sanitized plan/action/observation/final
  progression while preserving `task_recognition -> task_execute_parallel ->
  generate_recommendation` semantics.
- Waiting-node final output preserves Chatflow/worker prompt text in the
  customer draft.
- Existing customer/operator UAT behavior remains consistent.
- No new direct-write path is introduced.

## MVP Exit

069 is complete when Two-Stage ReAct can be safely evaluated and optionally used
without disrupting the current customer-assistant product behavior.
