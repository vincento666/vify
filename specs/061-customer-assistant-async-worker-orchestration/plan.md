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

## Non-goals

Do not convert `ChatflowSopWorker` here. It depends on Hify Chatflow runtime v2
facade maturity and belongs to Spec 066.
