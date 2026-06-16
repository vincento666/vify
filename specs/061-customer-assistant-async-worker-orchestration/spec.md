# Spec 061: Customer Assistant Async Worker Orchestration

## Goal

Make the customer-assistant runtime consume real worker async refs instead of
only returning final worker state inside the parent turn payload.

The runtime may still keep a synchronous compatibility path, but it must be able
to spawn worker runs, observe worker status/events/results, and update the task
ledger when worker results arrive.

## Dependency

061 depends on:

- 059 customer-assistant worker async runtime MVP;
- 054 synthetic eval and Chatflow/SOP data readiness for regression cases;
- 055 LLM primary path only if enabled; deterministic remains the default;
- 057 operator turn mode for actor/turn-mode safety.

## Product Boundary

In scope:

- task ledger creates or links worker runs;
- worker status/result refs are stored in task state;
- assistant runtime can wait for fast worker completion or leave workers
  running;
- bounded fan-out/join policy for multiple worker refs when a task needs more
  than one worker;
- pending worker state is visible in events and task ledger;
- completed worker results can be consumed by a later polling/refresh/turn path;
- old synchronous turn behavior remains compatible for fast workers.

Out of scope:

- async ChatflowSopWorker;
- rewriting the assistant runtime as full ReAct;
- multi-process queueing;
- Workflow/Chatflow runtime v2 changes.

## Hard Constraints

- Existing customer request behavior must remain semantically equivalent for
  completed workers.
- Operator recommendation turns must remain read-only by default.
- High-risk writes stay proposed actions.
- Async orchestration must not hide worker failures behind empty
  recommendations.
- Async orchestration must not hide waiting worker prompts behind generic
  recommendations.
- Worker dispatch must be idempotent for the same task state/version and worker
  request; retries must not create duplicate worker runs.
- Late or stale worker results must not overwrite a newer task state version.
- Parallel worker dispatch must obey an explicit max-concurrency/backpressure
  policy.

## Fan-out And Join Boundary

`N` worker parallelism means the assistant runtime links multiple worker runs to
one assistant run/task and observes them independently. It is not a hidden
serial loop.

The MVP join policy must be explicit:

- which worker results are required before a recommendation is considered
  complete;
- which worker results may remain pending with warnings;
- how failed, timed-out, cancelled, or stale worker results are represented;
- whether result consumption happens during the same turn, a later turn, a
  polling refresh, or a background reconciliation job.

## Waiting Recommendation Boundary

When a worker reaches a waiting/blocking point, the current assistant turn is
complete only after it produces a waiting recommendation.

The recommendation source order is:

1. Worker or Chatflow node-provided customer-facing prompt.
2. Worker-provided missing field labels and waiting reason.
3. Assistant-generated fallback text only when the worker did not provide a
   usable prompt.

The assistant may summarize the waiting state for the operator, but it must not
silently rewrite a concrete node prompt into a different customer request.

## Acceptance Criteria

- A task can reference a real `workerRunId`.
- A worker can remain `RUNNING` after the assistant turn returns.
- Later status/result observation updates task state or recommendation evidence.
- Waiting worker result produces an operator recommendation and customer draft
  based on the worker/node waiting prompt.
- Duplicate dispatch attempts for the same task state do not create duplicate
  worker runs.
- Stale worker results are ignored or recorded without corrupting newer task
  state.
- Existing fast-path worker behavior remains compatible.
- UI/event payloads distinguish pending worker state from completed results.

## MVP Exit

061 is complete when customer-assistant task orchestration can genuinely observe
one async worker lifecycle without waiting for every worker to finish before the
turn can return.

## Audit Closure 2026-06-16

Async fan-out must batch-start all eligible customer-assistant worker runs before
joining on the wait deadline. A turn that creates multiple async-capable tasks
must not hide a serial `start -> wait -> start -> wait` loop behind worker refs.

When no wait deadline is configured, low-risk async workers use a short default
deadline and return `RUNNING` plus real worker refs if they are still executing.
`chatflow_sop` keeps its existing sync-friendly default wait unless an explicit
short deadline is configured, preserving the current SOP compatibility contract.
