# Plan

## Slice 201.1 Standalone Runtime Job Worker

1. Add RED service tests for a worker that claims a queued job and marks it
   completed or failed.
2. Add RED contract coverage that patches inline thread creation, starts a
   Workflow run, then completes it with `run_once`.
3. Implement a generic `RuntimeJobWorker` service.
4. Implement a workflow-specific worker factory that wires
   `WorkflowRuntimeV2Service.complete_run`.
5. Add `scripts/runtime_job_worker.py` for `--once` and polling mode.
6. Refactor the inline transition thread to call the same worker service when a
   job id is provided.
7. Run focused worker tests, broad runtime/workflow regression, frontend
   rem/unit, and browser UAT.

## Risks

- Inline transition execution remains enabled in this slice so existing API
  tests and UAT keep completing automatically.
- Multi-process locking and retry backoff remain bounded by the repository lease
  contract from Spec 200.
