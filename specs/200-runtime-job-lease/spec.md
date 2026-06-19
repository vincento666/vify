# Spec 200: Runtime Job Lease

## Goal

Introduce the first durable worker boundary for Runtime Core by persisting
runtime jobs and lease ownership before execution.

This covers the first vertical slice of Phase 7 in
`docs/chatflow-workflow-production-upgrade.md`.

## In Scope

- Add a `runtime_jobs` table to the baseline schema.
- Persist one runtime completion job for a Workflow Runtime Core run.
- Claim a job before the current inline worker executes it.
- Track job lifecycle fields: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`,
  `CANCELLED`.
- Track lease owner, lease token, heartbeat timestamp, lease expiry, attempt
  count, and last error.
- Support expired-lease takeover in the repository.
- Keep the existing in-process completion thread as the execution mechanism for
  this slice, but make it execute through a persisted job lease.

## Out of Scope

- A standalone worker process or CLI.
- Distributed row locking beyond the repository-level lease contract.
- Full retry scheduler/backoff.
- Chatflow turn-level durable jobs.
- Runtime resume/cancel conversion to async jobs.
- UI exposure for worker lease internals.

## Acceptance Criteria

- Calling `POST /api/v1/workflows/{id}/runs` creates a durable runtime job row.
- The inline completion worker claims the job, completes the run, and marks the
  job `COMPLETED`.
- A second worker cannot claim an active lease.
- An expired `RUNNING` lease can be claimed by another worker and increments the
  attempt count.
- Existing runtime result, events, and nodes behavior remains compatible.
