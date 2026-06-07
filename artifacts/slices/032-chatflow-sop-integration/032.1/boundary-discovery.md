# 032.1 Chatflow Boundary Discovery

## Status

Discovery complete. Current Chatflow code is sufficient to start 032.2 RED
tests for one real Chatflow-backed SOP path.

This is documentation-only discovery. It does not add application code, tests,
API behavior, or schema changes.

## Existing Chatflow Capabilities

Current Chatflow provides the minimum integration primitives needed by the
031 adapter contract:

- `WorkflowService.execute` can run a Chatflow and return run status/output.
- `_record_chatflow_state` records Chatflow session state, message events,
  interrupt events, and checkpoints.
- `WorkflowService.get_session_state` returns current session status, waiting
  event, and latest waiting checkpoint.
- `WorkflowService.resume_run` resumes an interrupted run from a persisted
  checkpoint.
- `ChatflowStateRepository` owns Chatflow session, event, and checkpoint tables.

Relevant source areas:

- `app/modules/workflow/domain/service.py`
- `app/modules/workflow/infra/chatflow_state_repository.py`
- `app/modules/workflow/web/router.py`
- `app/modules/workflow/web/schemas.py`

Existing test coverage includes Chatflow session state, resume reliability,
question/human-input resume, and information-collection resume.

## Chosen Adapter Call Path

032 should implement:

```text
RuntimeLabService
  -> SopRuntimeAdapter
  -> ChatflowSopRuntimeAdapter
  -> WorkflowService.execute
  -> WorkflowService.get_session_state
  -> WorkflowService.resume_run
  -> ChatflowStateRepository
```

The adapter should call domain services directly. It should not call HTTP
endpoints from inside backend code.

## First Real SOP Fixture

Use one test-only aviation Chatflow fixture:

```text
START
  -> INFORMATION_COLLECTION(order_no)
  -> QUESTION(confirm)
  -> END
```

Why this fixture:

- it resembles the mock `collect_order_no -> confirm -> completed` SOP;
- `INFORMATION_COLLECTION` can produce a waiting checkpoint when required
  fields are missing;
- `QUESTION` can produce a second waiting checkpoint for confirmation;
- scoped variable and collected value behavior can be verified.

## Contract Mapping

Expected adapter mappings:

- `start_sop`: run the configured Chatflow with `sys.query` and runtime metadata.
- `continue_sop`: if the prior checkpoint is waiting, resume it with the latest
  message; otherwise run with resume-shaped input only if the test fixture
  requires it.
- `suspend_sop`: map an existing waiting Chatflow checkpoint into
  `SopCheckpoint`.
- `resume_sop`: resume from mapped checkpoint and return normalized
  `SopExecutionResult`.

## Known Contract Constraints

Current Chatflow does not expose a general external "pause arbitrary running
node" API. Therefore:

- `suspend_sop` must not pretend to pause arbitrary in-flight execution;
- `suspend_sop` may only preserve an already waiting/interrupted checkpoint;
- if no waiting checkpoint exists, the adapter must return a controlled failure
  or be treated as non-suspendable by the runtime.

No 031 contract change is required before 032.2, but 032 implementation should
respect this constraint in tests.
