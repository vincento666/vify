# Plan 061: Customer Assistant Async Worker Orchestration

## Implementation Shape

Extend the task ledger and worker scheduling path:

```text
TaskCommand -> TaskItem -> workerRunId -> worker refs -> WorkerResult
```

The runtime may use a short wait window:

```text
spawn worker
wait up to deadline
  if completed: apply result
  else: keep task RUNNING and return refs
```

## Result Consumption

MVP options:

- explicit refresh endpoint;
- next customer/operator turn consumes completed worker results;
- background completion callback updates task state.

Choose one and document why.

## Fan-out And Join

When a task dispatches multiple workers, represent each worker run separately and
define the join rule:

- required vs optional worker result;
- pending vs failed vs timed-out evidence;
- partial recommendation warnings;
- stale-result guard using task state version or equivalent.

Dispatch must be idempotent for the same task state/version and worker request.

Audit closure note: the runtime start phase is separated from the join phase for
customer-assistant async workers. The service first creates/submits all eligible
worker runs, then joins them against their configured wait deadlines, so parallel
dispatch is observable and not a hidden serial loop.

## Waiting Recommendation

If a worker returns `WAITING`, the assistant turn still returns a completed
response to the operator:

```text
worker WAITING
  -> waiting reason / required fields / node prompt / checkpoint ref
  -> operator recommendation: explain what is needed and why
  -> customer draft: preserve the worker/node prompt when available
  -> task remains WAITING for the next turn/resume
```

Do not wait for the worker to finish and do not return an empty recommendation.
Use assistant-generated text only when the worker did not provide a usable
customer-facing prompt.

## Compatibility

Existing `handle_turn` may still return a recommendation in simple cases. The
new behavior must be additive for workers that exceed the wait deadline.

Unset wait deadlines default to a short async-friendly window for the low-risk
worker path, while `chatflow_sop` preserves the legacy sync-friendly default
unless a caller explicitly configures a shorter deadline.

## Non-goals

Do not convert `ChatflowSopWorker` here. It depends on Hify Chatflow runtime v2
facade maturity and belongs to Spec 066.
