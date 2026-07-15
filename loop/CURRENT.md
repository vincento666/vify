# Current Loop Scope: Spec 225 RuntimeLab SOP Live Stream

## Status

    mode: Open -> Closed Loop
    active spec: 225-runtime-lab-sop-live-stream
    active slice: 225.8 Cross-process Redis/outbox Stream-order Recovery
    phase: SLICE_CLOSED
    TDD method: tdd

## Worktree

    branch: codex/sop-runtime-v2-live-stream
    path: /Users/vincento/work/develop/hify-sop-runtime-v2-live-stream
    base: 828782ce
    merge target: codex/runtime-v2-production-upgrade
    dirty before slice: no; isolated from the user's original dirty worktree

## Tracer

    RuntimeLab message:stream
      -> durable SOP child-run ref
      -> Runtime V2 event cursor
      -> SSE delta|done|error projection
      -> incremental RuntimeLab transcript

## Frozen Scope

Allowed: Spec 225, RuntimeLab SOP stream adapter, Runtime V2 provider-delta and
async-resume seams, RuntimeLab stream UI, the shared Provider Transport async
capability and its Customer Assistant compatibility tests, directly related
tests/evidence, the single stale Spec-216-conflicting E2E assertion, and the
in-process Runtime V2 frontier extension in 225.7: parallel LLM/KNOWLEDGE and
safe-TOOL waves, fail-fast node timeout/cancellation fencing, idempotency
handoff, structured terminal failures, and compatible upper-layer degradation.
Every implementation slice starts with a focused observable RED.

225.8 additionally authorizes only read-side recovery for the existing Redis
stream/outbox boundary: normalize available records by durable event sequence,
then use a fresh durable backlog only when a live cursor has a sequence gap.
It does not authorize a new Redis publishing protocol, distributed publisher
lock, broker, schema change, queue, or public stream contract change.

## Stop Conditions

Stop for a migration, node-attempt ledger, new dependency, Customer Assistant
public behavior/API or worker change, new queue or scheduler, worker-capacity
or deployment change, auth/permission change, automatic node-retry expansion,
live-provider spend/credentials, or a write-side/global event-bus guarantee.
Record unmet external UAT as WAITING-HUMAN.

## TDD

`tdd` then `test-driven-development`: one public behavior, RED -> smallest
GREEN -> refactor -> focused verifier -> evidence. Local `loop/hooks` is not
present on base `828782ce`; manual RED evidence is mandatory.

## Result

225.1 through 225.5 are locally GREEN with manual RED/GREEN evidence and an
independent Reviewer PASS. 225.6 has a user-approved contract extension:
shared async transport, Runtime V2 async-provider consumption, and Customer
Assistant SSE/worker/shadow compatibility tests are GREEN. A fresh independent
reviewer initially found the cancellation seam split; the added real-provider
HTTP-stream integration proof is GREEN and its fresh closure review is PASS.
Slice 225.6 is closed. The authorized live OpenRouter/Qwen RuntimeLab UAT is
PASS and recorded in 225.5 evidence. Slice 225.7 is closed by an independent
Reviewer; Spec 225 all-slice closeout remains open.

## Active Extension: 225.7 Contract Confirmed

The user authorized an extension within the existing in-process Runtime V2
frontier executor: parallel waves for LLM/KNOWLEDGE/safe TOOL, node-timeout
fail-fast, structured failure events, and workflow/upstream error degradation.
The active evidence root is
`artifacts/slices/225-runtime-lab-sop-live-stream/225.7-parallel-waves-fail-fast/`.

Frozen contract:

- No node-attempt ledger, migration, new queue, worker-capacity change, or
  automatic node retry is authorized. Existing retry behavior outside this
  extension remains compatible; the new parallel paths do not add retries.
- A same-wave node may start only after all selected predecessors complete.
  LLM and KNOWLEDGE may run concurrently; TOOL requires explicit parallel-safe
  configuration plus pre-dispatch idempotency support, otherwise it is rejected
  from the wave or remains serialized.
- Timeout fails the run promptly, cancels cancellable peers, and fences late
  completions. Synchronous third-party calls cannot be forcibly stopped; their
  late results must not mutate the completed run.
- Failures remain compatible terminal run failures and add a sanitized
  `failure` payload. RuntimeLab retains the terminal SSE `error` string and
  adds `failure`; asynchronous workflow result data retains its existing
  envelope and adds `errorCode` plus `failure.message`. The initial codes are
  `WORKFLOW_NODE_FAILED` and `WORKFLOW_NODE_TIMEOUT`.
- A Chatflow node failure terminates only the failing run/turn. It must not
  poison the session or make the next eligible user interaction resume the
  failed run; the next turn starts through the existing normal run lifecycle.
  Customer Assistant keeps its existing failure/retry envelope and receives no
  public API or user-copy change.
- Idempotency is mandatory without a node-attempt ledger: duplicate start and
  resume retain their current run-level replay; lease takeover uses stable
  `runId/nodeKey/nodeType` keys injected *before* a safe external Tool call and
  requires an adapter receipt. A Tool that cannot honour that key cannot claim
  exactly-once behavior and is not parallel-safe.

TDD begins with a public LLM fan-out overlap RED proof, then one vertical
behavior at a time: KNOWLEDGE, safe-Tool pre-dispatch idempotency/receipt,
timeout and late-result fencing, failure projection, and next-turn isolation.

Closure evidence: the final independent Reviewer found no 225.7 P0/P1/P2.
It confirmed that the `RUNNING + SELECT ... FOR UPDATE` fence serializes delta
and terminal persistence, and that the production `McpFacade` remains serial
without a native receipt rather than making an exactly-once claim. Its focused
review reran 8 parallel-wave tests and 13 related failure/CA tests; ruff and
`git diff --check` passed. Redis XADD ordering across separate processes is an
existing event-bus boundary, not a claimed 225.7 guarantee or an event-bus
redesign added by this slice.

## Active Extension: 225.8 Contract Confirmed

Goal: prevent a cross-process/outbox Redis publication order from making a
Runtime V2 SSE client observe a later durable event (including a terminal one)
before an earlier durable delta or lifecycle event.

The normal path remains realtime Redis. Redis reader output is sorted and
deduplicated by durable `sequence`. If an ordered live batch has any
discontinuity from `afterSequence + 1`, the stream gateway obtains a fresh
short-lived database backlog; if it contains earlier events, it emits that
ordered backlog instead. If durable retention/compaction means no earlier
event exists, the later live event proceeds rather than blocking forever.

Success evidence: a fake Redis XADD reordering plus duplicate proves ordered,
deduplicated reads; a stream-gateway contract proves a live later event cannot
overtake a durable predecessor, including an internal live-batch gap; a
contiguous live event remains Redis-only;
focused, integration/contract, existing RuntimeLab regression, static checks,
and an independent Reviewer pass. Maximum repair attempts: five. Browser UAT
is regression-only because no UI behavior or public API changes.

Closure evidence: a fresh independent Reviewer found no 225.8 P0/P1/P2. It
verified Redis sorting/deduplication before `count`, leading and internal gap
recovery through the fresh durable session, contiguous Redis-only projection,
and the no-predecessor retention fallback. It reran the focused 12-test suite,
Ruff, and `git diff --check`; the recorded combined JUnit is 52/0 and the
RuntimeLab broad JUnit is 158/0. Slice 225.8 is closed. Spec 225 overall
closeout and its commit/merge gates remain separate.

## Residual Risks

- Runtime V2 remains a synchronous worker-domain engine. It runs the shared
  async provider coroutine in its worker thread; this avoids request/event-loop
  blocking but is not a native async graph scheduler.
- A standalone Chatflow worker must be running for actual execution; this spec
  does not deploy one.
- Live Qwen/OpenRouter UAT validates upstream delta ordering and RuntimeLab SSE
  projection. Provider-side cancellation billing still depends on OpenRouter's
  selected upstream host.
- The shared process-local provider stream limiter defaults to four. Cross-
  process or tenant-wide provider limits remain deployment/configuration
  concerns; no new scheduler is introduced by this spec.
- The production `McpFacade` does not currently expose a provider-native
  idempotent dispatch receipt. It therefore remains deliberately ineligible
  for a safe-Tool parallel wave, even with `parallelSafe`; the implementation
  has no false exactly-once claim. Actual production MCP Tool overlap needs a
  provider-native atomic idempotency/receipt capability (or the excluded
  durable ledger), so it requires a new contract rather than a process-local
  substitute.
