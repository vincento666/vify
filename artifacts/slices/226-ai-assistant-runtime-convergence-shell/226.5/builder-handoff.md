# Builder Handoff — 226.5

TDD method: `tdd`

## Scope

- Added an AI Assistant runtime-job contract and product adapter over the
  domain-neutral RuntimeJobRepository. Async requests persist only a safe run
  reference and return durable worker metadata.
- Registered AI Assistant in the standalone runtime worker composition. The
  API process no longer owns an autonomous executor, lock, or in-flight set.
- Added idempotent queue repair after an API/job commit boundary and bounded
  active-job admission with explicit HTTP 429 backpressure.
- Added durable heartbeat/takeover semantics. An expired worker can resume a
  RUNNING AI run from its persisted checkpoint; the new worker identity is
  auditable without exposing the raw lease fence.
- Added a lease guard to operational repository writes and primary/fallback
  tool dispatch. Old heartbeat, completion, event, and tool-dispatch attempts
  fail after lease loss.
- Pause and cancel fence the durable job; resume requeues the cancelled job or
  repairs a missing one.
- Added AI-specific terminal-failure projection. Retry exhaustion marks the AI
  run FAILED without routing through Workflow/Chatflow state.
- Replaced request-session SSE capture with an injectable EventStreamReader
  that opens and closes a scoped session per poll. The reader resolves trusted
  scope independently of Harness implementation details.
- Removed the frontend worker-process request. The browser now subscribes to
  SSE after enqueue; `/worker/process` remains only as a deprecated
  compatibility shim and ignores request execution configuration.

## RED

- `red-durable-worker.txt`
- `red-lease-fencing.txt`
- `red-sse-short-session.txt`
- `red-worker-separation.txt`

## GREEN Evidence

See `green.txt` for commands and final counts.

## Security And HA Review

- Raw lease fences remain in runtime_jobs only; checkpoints expose a short
  hash, worker id, attempt, and runtime job id.
- Durable job payload contains only `runRef`; model credentials/configuration
  remain in the scoped run contract and secret references.
- Compatibility worker payload is ignored, leaving the queued run as the only
  execution authority.
- Lease loss blocks repository mutation and tool dispatch; cancellation clears
  lease ownership before late completion.
- AI terminal projection persists a public failure class, not the raw handler
  exception, into the user-facing run/event payload.
- SSE polling reconstructs tenant/user/workspace scope and does not retain a
  request DB session.
- Residual: active-job admission uses the repository count gate rather than a
  cross-process hard semaphore. Worker concurrency and claim atomicity remain
  the hard execution bound; strict global queue cardinality can be added only
  if production capacity policy requires it.

## Explicit Gate Notes

- Browser UAT: N/A. This slice removes an invisible worker trigger but does not
  implement the activity-shell interaction; Browser UAT is required in 226.7.
- rem gate: N/A. No visual CSS or dimensions changed.
- Live provider: N/A. Provider-call budget remained zero.
- Migration/deploy: N/A. This slice has no schema change and deploy is not
  authorized.
- `/worker/process` deletion: deferred to 226.8 caller inventory; compatibility
  shim is explicitly deprecated.
- Full independent fresh-context review: not required by standard review
  context. Checker and Reviewer remain read-only roles and do not claim fresh
  context.

## Remaining Contract

- Stable RunActivity identity and real child lifecycle remain 226.6.
- Hify light activity shell, completed-row folding, live subagent presence, and
  Browser UAT remain 226.7.
- Obsolete compatibility flags/callers and duplicate historical paths remain
  evidence-gated cleanup in 226.8.
