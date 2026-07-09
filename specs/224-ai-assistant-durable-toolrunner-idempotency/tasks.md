# Spec 224 Tasks

## 224.1 Ledger Contract And Migration

Status: `pending`

- [ ] RED: operation ledger state is lost across service/repository restart.
- [ ] Define migration for operation and attempt records.
- [ ] Add repository contract tests for create, claim, update, and lookup.
- [ ] Verify no event sequence dependency in operation identity.

## 224.2 Side-Effect Operation Idempotency

Status: `pending`

- [ ] RED: duplicate side-effect dispatch creates duplicate business effect.
- [ ] Generate deterministic `operation_id`.
- [ ] Persist idempotency key before dispatch.
- [ ] Reuse operation across retry and resume.
- [ ] Emit audit and trace spans.

## 224.3 UNKNOWN Lifecycle

Status: `pending`

- [ ] RED: dispatched timeout lacks durable `UNKNOWN` operation state.
- [ ] Mark ambiguous attempts as `UNKNOWN`.
- [ ] Block automatic replay for side-effect `UNKNOWN`.
- [ ] Return structured observation to model.
- [ ] Enforce MVP retention policy.

## 224.4 Reconciliation And Release Authority

Status: `pending`

- [ ] RED: model-only `UNKNOWN` release is rejected.
- [ ] Add release authority contract.
- [ ] Persist actor, reason, evidence, previous state, next state, timestamp.
- [ ] Add audit export coverage.

## 224.5 Fallback Adapter Identity

Status: `pending`

- [ ] RED: fallback attempt creates independent operation for same effect.
- [ ] Share `operation_id` across primary and fallback attempts.
- [ ] Give every adapter attempt a unique `attempt_id`.
- [ ] Block fallback after side-effect `UNKNOWN` until release.

## 224.6 Read Tool Ledger Policy

Status: `pending`

- [ ] RED: read timeout follows side-effect UNKNOWN blocking.
- [ ] Allow safe read retry within budget.
- [ ] Add optional read cache by request hash.
- [ ] Add shorter read retention policy.

## 224.7 Durable Circuit Breaker

Status: `pending`

- [ ] RED: breaker state resets on process restart.
- [ ] Persist breaker state by provider/tool/adapter/risk/error key.
- [ ] Implement CLOSED, OPEN, HALF_OPEN transitions.
- [ ] Add cooldown and probe behavior.
- [ ] Add operator override audit.

## 224.8 Eval And Audit Export

Status: `pending`

- [ ] RED: aggregate eval cannot prove durable idempotency or breaker evidence.
- [ ] Export operation and attempt ledger evidence.
- [ ] Export UNKNOWN release evidence.
- [ ] Export fallback identity evidence.
- [ ] Export circuit breaker evidence.
- [ ] Add checker/reviewer artifacts for every slice.
