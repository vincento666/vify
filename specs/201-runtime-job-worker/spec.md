# Spec 201: Runtime Job Worker Run Once

## Goal

Add a standalone Runtime Job Worker execution path for Workflow Runtime Core jobs.

This is the second vertical slice of Phase 7 in
`docs/chatflow-workflow-production-upgrade.md`.

## In Scope

- Add a reusable `RuntimeJobWorker` service that claims one job and executes it.
- Add a workflow worker factory that can complete a `runtime_v2_completion` job
  outside the HTTP request path.
- Add a CLI/script entry point that can run one job or poll for jobs.
- Reuse the worker service from the current inline transition thread.
- Keep public workflow run responses unchanged from Spec 199/200.

## Out of Scope

- Disabling inline transition execution by default.
- Full retry/backoff scheduler.
- Runtime resume/cancel as durable jobs.
- Chatflow message-turn worker conversion.
- UI changes.

## Acceptance Criteria

- With the inline thread patched out, a Workflow run remains `RUNNING` with a
  `QUEUED` runtime job.
- Calling the standalone worker `run_once` claims that job, completes the
  Workflow run, and marks the job `COMPLETED`.
- The worker can be invoked from a script entry point.
- Existing Workflow Run Gateway behavior remains compatible when inline
  transition execution is enabled.
