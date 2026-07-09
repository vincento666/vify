# Spec 224 Plan

## Goal

Implement durable ToolRunner idempotency and circuit breaker semantics for AI
Assistant without expanding into sandbox, HA worker, or business adapter work.

## Slices

### 224.1 Ledger Contract And Migration

- Add durable operation and attempt schema.
- Add repository methods for create/read/update operation and attempt records.
- RED: process-local ledger loses idempotency across repository/service restart.

### 224.2 Side-Effect Operation Idempotency

- Generate and persist side-effect `operation_id` and idempotency key before
  dispatch.
- Reuse operation across retry and run resume.
- RED: duplicate side-effect tool execution creates two effects.

### 224.3 UNKNOWN Lifecycle

- Mark ambiguous dispatched attempts as `UNKNOWN`.
- Block automatic side-effect replay until reconciliation.
- Add structured model observation.
- RED: timeout ambiguity currently retries or fails without durable state.

### 224.4 Reconciliation And Release Authority

- Implement approved human/operator or deterministic adapter release path.
- Persist audit evidence for every release.
- RED: model-only or unaudited release is rejected.

### 224.5 Fallback Adapter Identity

- Preserve `operation_id` across primary/fallback attempts for same effect.
- Block fallback after side-effect `UNKNOWN` until release.
- RED: fallback creates independent side-effect operation.

### 224.6 Read Tool Ledger Policy

- Add read-tool retry/cache/expiration behavior.
- Keep read-tool policy separate from side-effect policy.
- RED: read timeout incorrectly blocks like high-risk side effect.

### 224.7 Durable Circuit Breaker

- Persist breaker state and transitions.
- Return breaker-open structured observation to the model.
- Add operator override audit.
- RED: breaker resets on process restart.

### 224.8 Eval And Audit Export

- Extend aggregate eval/runtime evidence for durable idempotency and breaker
  behavior.
- Export operation, attempt, `UNKNOWN`, release, fallback, and breaker audit
  evidence.

## Human Gates

Stop before implementation if:

- schema migration strategy is unclear;
- production retention policy needs compliance input;
- tool schemas must change;
- reconciliation authority requires product/ops workflow decisions;
- external side-effect systems are introduced.
