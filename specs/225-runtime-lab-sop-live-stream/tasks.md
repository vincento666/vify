# Tasks 225: RuntimeLab SOP live stream over Runtime V2

## 225.1 SSE surface and durable lifecycle bridge

- [x] Add one contract test that proves `messages:stream` is absent (RED).
- [x] Implement the minimal RuntimeLab SSE response and child-run correlation.
- [x] Add integration proof that an active child lifecycle is relayed live and
      JSON `messages` remains unchanged.
- [x] Record RED, GREEN, focused test, and diff-check output in
      `artifacts/slices/225-runtime-lab-sop-live-stream/225.1-sse-surface/`.

## 225.2 Genuine provider chunk path

- [x] Add a fake streaming-provider RED: first `llm_delta` precedes node
      completion and contains only an incremental chunk.
- [x] Add non-stream-provider fallback proof.
- [x] Implement provider-stream completion capability, immediate durable event
      append (no coalescing), and ordered final completion.
- [x] Record unit/integration evidence in `225.2-provider-deltas/`.

## 225.3 Async start and resume

- [x] Add RED coverage for start and resume returning durable refs without
      request-side `complete_run`, wait, or polling.
- [x] Implement reference-returning resume gateway and worker ownership.
- [x] Verify standalone worker claims and completes the resumptions.
- [x] Record evidence in `225.3-async-resume/`.

## 225.4 RuntimeLab UI stream consumption

- [x] Add RED frontend tests for incremental token merge, terminal state,
      disconnect cleanup, reconnect cursor, and JSON fallback.
- [x] Implement stream client and transcript projection without a runtime-state
      mirror.
- [x] Run rem gate and Browser UAT; record screenshots and commands in
      `225.4-ui-stream/`.

## 225.5 Acceptance

- [ ] Run targeted RuntimeLab, Runtime V2, worker, and legacy Chatflow stream
      regressions; correct the Spec-216-conflicting stale E2E assertion only.
- [ ] Run static checks, frontend broad tests/build/rem, and repeatable Browser
      UAT.
- [ ] Independent Checker and Reviewer inspect all artifacts and diff.
- [x] Mark live external-provider UAT PASS only with explicit authority and
      saved real-case evidence; otherwise record `WAITING-HUMAN`.

## 225.6 Shared Provider Transport and Customer Assistant preparation

- [x] Add a focused RED proving the shared Provider Transport lacks an
      event-loop-native stream while retaining a synchronous compatibility
      facade for existing callers.
- [x] Define the capability contract: async stream, cancellation, timeout,
      bounded concurrency, retry-before-visible-output only, and ordered
      delta/final semantics.
- [x] Implement the smallest adapter behind `ProviderBackedOpenAIChatClient`;
      do not change Customer Assistant routes, envelopes, worker scheduling,
      or persistence.
- [x] Add Customer Assistant unit/integration/E2E regressions for SSE, worker,
      and shadow callers using the shared adapter, including concurrent stream,
      cancellation, partial-failure, and non-stream fallback cases.
- [x] Run independent review and record RED/GREEN plus every applicable gate in
      `artifacts/slices/225-runtime-lab-sop-live-stream/225.6-provider-transport-ca/`.

## 225.7 Graph Parallel Waves and Fail-Fast Governance

- [x] Freeze the user-confirmed contract: LLM/KNOWLEDGE/safe-TOOL parallel
      waves; fail-fast timeout; structured failure/degradation; no ledger,
      migration, node-retry expansion, queue, capacity, or Customer Assistant
      public-contract change.
- [x] Add one public Runtime V2 LLM fan-out RED proof that independent ready
      nodes overlap and retain deterministic durable terminal projection.
- [x] Make the smallest LLM wave implementation green without sharing a worker
      DB session; each live delta and cancellation-status lookup uses a bounded
      short-lived session while provider await remains parallel.
- [x] Add the KNOWLEDGE RED/GREEN vertical behavior with a worker-private
      facade/session where the configured facade is database-backed.
- [x] Add the safe-TOOL RED/GREEN vertical behavior. A parallel-safe MCP Tool
      requires explicit configuration, a stable pre-dispatch idempotency key,
      and an adapter receipt; all other Tools stay serial/rejected.
- [x] Add RED/GREEN proof for per-node timeout fail-fast, peer cancellation
      when cancellable, and late completion fencing without automatic node
      retry or a node-attempt ledger.
- [x] Add a deterministic terminal-delta race proof: a callback that passed
      its cancellation check before timeout cannot append after the durable
      terminal failure event.
- [x] Add RED/GREEN proof for sanitized `WORKFLOW_NODE_FAILED` /
      `WORKFLOW_NODE_TIMEOUT` failure payloads: Workflow result data gets
      `errorCode` and generic `failure.message`; RuntimeLab terminal SSE
      preserves `error` and adds `failure`; Customer Assistant's current
      envelope remains unchanged.
- [x] Add RED/GREEN proof that a failed Chatflow run is turn-scoped: a next
      eligible message creates its normal next run and does not replay failed
      output or side effects.
- [x] Prove duplicate submit and worker-lease takeover preserve run-level
      idempotency and safe-Tool receipt behavior without a migration/ledger.
- [x] Run focused, broad, static, applicable UAT, evidence, and a fresh
      independent Checker/Reviewer gate; record all results in
      `artifacts/slices/225-runtime-lab-sop-live-stream/225.7-parallel-waves-fail-fast/`.

## 225.8 Cross-process Redis/outbox stream-order recovery

- [x] Freeze the user-authorized read-side contract: retain Redis realtime
      fast path; order/deduplicate available entries by durable sequence; on a
      cursor gap, use a fresh durable backlog before projection. No migration,
      new broker, global publisher lock, queue, or public API change.
- [x] Add RED proofs for Redis XADD order/duplicate normalization and for an
      SSE cursor that receives a later terminal/lifecycle event before its
      earlier durable predecessor, including an internal live-batch gap.
- [x] Make the smallest Redis reader and Runtime V2 stream-gateway changes
      green, including a fresh-session durable backlog seam.
- [x] Run focused, integration/contract, applicable RuntimeLab E2E/Browser
      regression, static checks, evidence, and a fresh independent review in
      `artifacts/slices/225-runtime-lab-sop-live-stream/225.8-cross-process-event-ordering/`.
