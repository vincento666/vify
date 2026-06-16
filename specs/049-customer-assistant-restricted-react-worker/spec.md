# Spec 049: Customer Assistant Restricted ReAct Worker

## Goal

Introduce a restricted customer-assistant `react_worker` worker type for
bounded task execution. This is not a global agent harness. It is a task-bound
worker that can use an allowlisted tool set, produce structured output, and
emit eventful progress.

## Dependency

049 depends on:

- 045 task ledger and worker scheduler;
- 047 shadow/live LLM foundation where useful;
- 048 L1 event streaming.

## Boundary

In scope:

- code/static worker registry;
- `workerType = react_worker`;
- task-type-bound worker configs;
- tool allowlist;
- model policy reference;
- max iterations;
- per-worker timeout;
- structured output schema;
- proposed-action-only handling for high-risk writes;
- L1/L2 events without exposing hidden chain-of-thought.

Out of scope:

- generic agent builder UI;
- arbitrary tool execution;
- unbounded autonomous loops;
- replacing Chatflow/SOP workers;
- automatic high-risk write execution;
- LangChain/LangGraph adoption.

## MVP Scope Guard

049 is a bounded worker MVP. It adds one restricted `react_worker` type that can
run under the existing customer-assistant scheduler and return a normal
`WorkerResult`. It does not introduce a generic agent harness or retrofit
Workflow/Chatflow. Worker-level async run handles are reserved for the later
eventful sub-agent/worker stabilization step before Workflow/Chatflow runtime
v2.

## ReAct Shape

049 may start with a constrained loop:

```text
plan -> validate_action -> act_tool -> observe -> final
```

Future specs may generalize this into a normal ReAct loop where a turn returns
when no tool call is selected. 049 must keep the implementation bounded and
task-specific.

The "plan" phase should produce a structured action proposal, not hidden
reasoning text for the UI.

## Reserved Worker Config Fields

```text
workerType
workerRef
taskType
businessKey
toolPolicyRef
modelPolicyRef
timeoutMs
maxIterations
outputSchemaRef
```

## Event Levels

L1 events:

```text
react_worker_started
react_worker_completed
react_worker_failed
```

L2 events:

```text
react_iteration_started
react_tool_call_started
react_tool_call_completed
react_tool_call_failed
react_observation_recorded
react_structured_output_completed
```

L2 events must summarize reasoning and observations. They must not expose raw
hidden chain-of-thought.

## Acceptance Criteria

- A configured `react_worker` can complete a read-only task with a fake model
  and fake tools.
- Tool calls outside the allowlist are rejected and recorded as worker failure.
- Max-iteration and timeout limits are enforced.
- High-risk write intent becomes `proposed_action`.
- L1 events appear in the 048 panel stream.
- L2 events are persisted for debug/eval but not promoted to the main product
  timeline by default.
