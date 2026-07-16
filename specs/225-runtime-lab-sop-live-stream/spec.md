# Spec 225: RuntimeLab SOP live stream over Runtime V2

## Status

Open / Contract frozen 2026-07-13. Implementation starts with Slice 225.1.

## Problem

RuntimeLab can route an SOP message to Chatflow Runtime V2, but the current
`POST .../messages` response is a one-shot JSON acknowledgement. The browser
does not subscribe to the child run's lifecycle events, resume paths can wait
and complete inline, and LLM `llm_delta` is synthesized after synchronous
completion. The integration is therefore a control-plane bridge, not an
end-user async, live streaming conversation.

## Goal

For RuntimeLab SOP conversations only, provide an async-first and recoverable
SSE path that forwards Runtime V2 lifecycle events and provider token chunks as
they happen. A user can start or resume an SOP interaction, see incremental
answer text without a page refresh, reconnect from a durable sequence, and
receive one terminal `done` or `error` envelope.

### 225.7 safe-Tool capability boundary

A Tool may join an in-process parallel frontier only when its configured MCP
adapter natively accepts the stable pre-dispatch idempotency key and returns a
durable provider receipt. The current production `McpFacade` does not expose
that capability, so it remains serial even if the node is marked
`parallelSafe`. This slice does not emulate the guarantee with process memory
or add the excluded attempt ledger/migration; enabling real production MCP
Tool overlap requires a new contract and provider-native receipt support.

## Public Contract

### Existing compatibility

- Keep `POST /api/v1/runtime-lab/sessions/{session_id}/messages` unchanged:
  its JSON envelope and accepted payload remain supported.
- Keep existing Runtime V2 event-stream consumers compatible. Existing
  `delta|done|error` semantics and `{code, message, data}` API conventions do
  not change.
- Do not change Customer Assistant behavior, its transport, or its worker
  contract.

### New RuntimeLab stream

Add `POST /api/v1/runtime-lab/sessions/{session_id}/messages:stream`.

- Request body is the existing RuntimeLab message request. Response media type
  is `text/event-stream`.
- Each SSE `data:` row is JSON and has `type: "delta" | "done" | "error"`.
  It includes the RuntimeLab session id, the durable child `runId` once known,
  and a monotonically increasing `sequence` where a child-runtime event is
  represented.
- `delta` maps route/lifecycle progress and raw provider text chunks. Provider
  text uses `source: "provider"` and `delta` containing only newly produced
  text; it must be emitted before final node/run completion.
- A terminal event is exactly one `done` or `error`. `done` carries the normal
  final RuntimeLab result projection; `error` is a compatible structured error
  and does not turn a domain failure into an HTTP 200 JSON body.
- Reconnection uses the child Runtime V2 event cursor (`afterSequence` /
  `Last-Event-ID` where the existing stream supports it). It may replay events
  missed by this browser, but the first connected stream must tail live events,
  not wait for an already materialized final answer.

### Async and execution contract

- Initial SOP invocation and SOP continuation/resume return durable child run
  references and enqueue or wake work; request handling must not poll, sleep,
  call `complete_run`, or execute the full child run inline.
- The standard standalone Chatflow Runtime V2 worker remains the execution
  prerequisite. This spec neither deploys nor schedules a worker.
- Runtime V2 must expose an async provider-streaming completion boundary.
  Incremental provider chunks are appended to the durable runtime event log
  before final output persistence. Batching may coalesce at most 100 ms or
  256 characters, whichever occurs first, without reordering or inventing a
  post-completion full-text delta.
- Providers or node types without a streaming capability retain a clear
  non-streaming fallback: no fake token sequence, then final lifecycle/output
  events only.

## Scope

Included:

- RuntimeLab SOP message stream adapter, session/run correlation, terminal
  projection, and reconnect cursor forwarding.
- Runtime V2 invocation/resume reference APIs and worker-owned execution.
- Runtime V2 LLM provider chunk propagation, durable event batching, and
  completion ordering.
- RuntimeLab Vue stream consumption, incremental transcript updates, reconnect
  handling, and retained non-streaming fallback.
- Shared Provider Transport preparation needed to replace blocking provider I/O
  with an async capability while preserving the synchronous caller contract for
  existing Chat, Agent, Customer Assistant, Runtime Policy, and Evaluation
  consumers.
- Customer Assistant compatibility evidence for that shared transport only;
  no Customer Assistant public API, worker scheduling, persistence, or product
  behavior change is authorized in this spec.
- An in-process Runtime V2 frontier extension: independent ready LLM and
  KNOWLEDGE nodes may form a parallel wave; a TOOL may join only when it is
  explicitly parallel-safe, accepts a stable idempotency key before dispatch,
  and returns a receipt. Per-node timeouts fail the run promptly, cancel
  cancellable peers, and fence late results. Terminal failures add sanitized
  structured data while retaining all existing envelope fields.
- A narrow cross-process stream-order recovery: Redis is still the normal
  realtime path, but its available entries are ordered and deduplicated by
  durable event sequence. If a Redis cursor starts after the next expected
  sequence, Runtime V2 reads a fresh durable event backlog before projecting a
  later live event, so a terminal frame cannot overtake an earlier durable
  delta at the SSE boundary.
- Unit, integration/contract, E2E, Browser UAT, static, rem, and worker
  evidence required by the slices below.

Excluded:

- Customer Assistant transport or behavior changes beyond consuming the
  compatibility-preserving shared Provider Transport adapter.
- A new scheduler, worker deployment, auto-started worker, queue backend, or
  event-bus redesign. The 225.8 read-side recovery may reuse the existing
  Redis stream, outbox, and durable event log only; it does not add a broker,
  global publisher lock, or delivery guarantee beyond the SSE projection.
- Removal or semantic change of existing RuntimeLab JSON messaging endpoints.
- A new direct Chatflow public stream API except narrowly shared Runtime V2
  internals needed by this contract.
- Database schema changes, dependencies, pricing, auth, or permission changes.
  Stop for explicit review if any becomes necessary.
- A node-attempt ledger, migration, automatic node retry, queue/scheduler or
  worker-capacity/deployment change, and any Customer Assistant public API or
  user-copy change.

## Acceptance

1. A RuntimeLab SOP start emits live `delta` records while the standalone
   Chatflow worker executes, followed by exactly one terminal record.
2. A RuntimeLab SOP resume is durable and async-first; tests prove no request
   path calls `complete_run` or bounded polling helpers.
3. A streaming-capable fake provider proves an `llm_delta` arrives before node
   completion and is not one synthesized final-answer delta. A non-streaming
   provider proves the documented fallback.
4. Disconnect/reconnect from a sequence cursor neither duplicates nor loses
   durable child events within the existing retention window.
5. The RuntimeLab UI shows incremental output and reaches the same final state
   as the retained JSON flow. Browser UAT captures start, disconnect/reconnect,
   resume, provider error, and unavailable-worker states.
6. Existing RuntimeLab JSON, Runtime V2 event stream, and targeted Chatflow
   contracts stay green. E2E asserts child-ledger refs rather than a removed
   RuntimeLab execution-state mirror; V2 covers switch, async worker drain,
   resume, and completion end to end.
7. Shared Provider Transport preparation proves that the async implementation
   preserves existing synchronous callers, emits live chunks before completion,
   prevents duplicate visible output after partial failure, and leaves Customer
   Assistant's SSE, worker, and shadow contracts unchanged.
8. Independent ready LLM/KNOWLEDGE nodes have observable overlap while their
   durable output and terminal event projection remains compatible. A TOOL is
   parallel only with explicit safety configuration, pre-dispatch stable
   idempotency key, and receipt; otherwise it is not scheduled in that wave.
9. A node timeout is fail-fast: the workflow is terminal `FAILED`, cancellable
   peers are asked to cancel, and late output cannot mutate the terminal run.
   No new automatic node retry or node-attempt ledger is introduced.
10. Terminal node failure/timeout emits sanitized `failure` with
    `WORKFLOW_NODE_FAILED` or `WORKFLOW_NODE_TIMEOUT`; asynchronous workflow
    result data retains its current envelope and adds `errorCode` plus generic
    `failure.message`, and RuntimeLab SSE retains its string `error` plus the
    additive `failure` object.
11. A Chatflow node failure ends only that turn/run. The next eligible user
   interaction follows the normal next-run lifecycle and does not replay the
   failed run; Customer Assistant's failure/retry envelope remains unchanged.
12. When an existing Redis stream/outbox path exposes any durable-sequence gap
    (including an internal gap in a live batch), Runtime V2 SSE emits the
    available durable backlog in sequence order before the later event. Normal
    contiguous Redis reads remain realtime and do not require a database
    backlog read.

## Evidence and Goal Gate

- Evidence root:
  `artifacts/slices/225-runtime-lab-sop-live-stream/`.
- Success predicate: all accepted slices have independent verifier evidence for
  their required gates, no scope-stop condition is triggered, and the final
  Browser UAT is repeatable.
- Builder cannot self-close the goal. Checker verifies commands, artifacts,
  and contract adherence; Reviewer verifies diff scope and compatibility.
- Maximum targeted repair attempts: five per failed verifier. On exhaustion,
  record the failing evidence and stop for human direction.
- Live external-provider UAT is `WAITING-HUMAN` until a real provider,
  credentials, cost budget, and explicit execution authority are available.
  Fake-provider realtime tests remain mandatory and do not claim that live gate.

## Slice Order

| Slice | Vertical behavior | Gate |
|---|---|---|
| 225.1 | RuntimeLab exposes the new SSE message surface and relays a durable child lifecycle to a connected client while preserving JSON messaging | contract + integration RED/GREEN |
| 225.2 | Runtime V2 captures genuine provider chunks before node completion, durably batches them, and proves non-stream fallback | unit + integration |
| 225.3 | SOP start and resume both use durable async references; no inline completion or polling | unit + contract + worker integration |
| 225.4 | RuntimeLab UI consumes the stream, incrementally updates, reconnects by cursor, and retains JSON fallback | frontend unit + Browser UAT |
| 225.5 | Cross-runtime regression, worker/UAT evidence, stale E2E correction, and live-provider gate disposition | independent verification |
| 225.6 | Shared Provider Transport async capability and Customer Assistant compatibility preparation; no CA behavior change | RED + unit + CA integration/E2E + independent review |
| 225.7 | In-process parallel LLM/KNOWLEDGE/safe-TOOL frontier waves, fail-fast timeout/fencing, structured failures, and turn-scoped Chatflow degradation | vertical RED/GREEN + takeover/upper-layer contracts + independent review |
| 225.8 | Cross-process Redis/outbox sequence recovery at the Runtime V2 SSE read boundary; no event-bus redesign | RED/GREEN + unit/contract/integration + independent review |
