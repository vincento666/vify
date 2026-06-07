# 032.3 Implementation Plan

## Status

Pre-implementation sign-off only. No implementation has been written in this
gate.

032.3 starts only after 032.2 RED evidence is captured.

## Adapter Responsibility

Implement `ChatflowSopRuntimeAdapter` behind the 031 `SopRuntimeAdapter` port.

The adapter should:

- call `WorkflowService.execute` for `start_sop`;
- call `WorkflowService.resume_run` for waiting checkpoint continuation;
- call `WorkflowService.get_session_state` or repository methods to find the
  latest waiting checkpoint;
- map Chatflow checkpoint/session/event state into `SopCheckpoint`;
- map Chatflow run output/status into `SopExecutionResult`;
- return normalized `FAILED` results instead of leaking raw Chatflow exceptions.

## Runtime Boundary

Runtime-lab remains responsible for:

- active/suspended/completed task state;
- route decisions;
- command idempotency;
- event timeline;
- resume-offer policy.

Chatflow remains responsible for:

- internal node execution state;
- Chatflow run status;
- Chatflow checkpoint content;
- Chatflow scoped variables.

## Implementation Constraint

Do not add reverse imports from Workflow/Chatflow into `runtime_lab`.
The 031 dependency-direction gate must continue to pass.
