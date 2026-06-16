# Spec 057: Customer Assistant Operator Turn Mode

## Goal

Add an explicit operator-turn mode so human operator questions can ask the
assistant for recommendations without mutating the customer task ledger by
default.

047 intentionally persisted `actor` without branching the state machine. 057
uses that foundation to separate customer-driven work from operator-side
internal questions.

Operator advice must be useful, not just a blank recommendation shell. The MVP
therefore builds a read-only advisory path over the current task ledger,
knowledge-base evidence, Chatflow/SOP metadata, and harness/sub-agent execution
where available.

## Dependency

057 depends on:

- 047 actor persistence;
- 048 event stream;
- 054 synthetic cases including operator turns;
- 055 LLM primary/fallback if enabled, otherwise deterministic fallback;
- existing knowledge-base retrieval capabilities;
- database-backed Chatflow/SOP definitions or explicit fallback mock strategy.

## Product Boundary

In scope:

- operator turn classification;
- default recommendation-only operator turns;
- no task ledger mutation for ordinary operator questions;
- read-only operator advisory context built from task ledger, runtime events,
  knowledge-base snippets, and Chatflow/SOP metadata;
- optional harness/sub-agent orchestration for bounded advisory work;
- optional proposed task commands when the assistant believes a ledger mutation
  would help;
- explicit operator confirmation before applying proposed task commands;
- UI distinction between customer input, operator question, and runtime action.

Out of scope:

- fully separate operator conversation memory;
- multi-operator collaboration;
- live interruption of currently running workers;
- WebSocket transport.
- autonomous execution of proposed task commands.

## Turn Modes

```text
customer_task_turn
operator_recommendation_turn
system_trigger_turn
operator_apply_task_command
```

Default behavior:

- `actor=customer` can mutate the ledger through normal task recognition.
- `actor=operator` is recommendation-only unless it explicitly confirms a
  proposed task command.
- `actor=system` follows a configured system-trigger policy.

## State Machine Boundary

`operator_recommendation_turn` must not enter the customer task state machine.
It may read the ledger, events, knowledge, Chatflow/SOP metadata, and bounded
advisory worker summaries, but by default it must not:

- add, retain, suspend, resume, or cancel tasks;
- dispatch task workers;
- change task checkpoints;
- execute proposed actions.

Operator-originated task changes must be represented as proposed task commands
and applied only through `operator_apply_task_command` after explicit
confirmation.

## Advisory Context

The operator recommendation path should assemble a context pack:

```text
current task ledger
latest customer transcript/messages
runtime event summary
knowledge-base snippets
Chatflow/SOP step metadata
harness/sub-agent result summaries
```

For MVP, each source may be optional. Missing sources must produce warnings
rather than silent empty recommendations.

## Harness Boundary

057 may call bounded harness/sub-agent workers for read-only advisory tasks,
such as:

- summarize current refund task state;
- retrieve policy snippets;
- inspect relevant Chatflow/SOP step metadata;
- propose next operator action.

These advisory workers must not mutate the ledger directly. Any mutation must
return as a proposed task command requiring operator confirmation.

## Acceptance Criteria

- Operator input such as "I need a refund" does not add a refund task by
  default.
- Operator recommendation turns do not enter the customer task state machine or
  dispatch task workers by default.
- Operator can ask for internal handling advice and receive a recommendation.
- Recommendation cites or summarizes at least one available evidence source
  when knowledge, Chatflow, or task state exists.
- Assistant can propose ledger changes as proposed task commands.
- Proposed task commands require explicit confirmation before mutation.
- Browser UAT verifies customer and operator lanes behave differently.

## MVP Exit

057 is complete when the operator can ask a useful internal question and receive
a recommendation grounded in available task, knowledge, Chatflow/SOP, or
harness evidence. If evidence sources are missing, the UI must show explicit
warnings instead of returning an empty recommendation shell.

057 does not need live worker interruption or WebSocket transport.
