# Tasks 061: Customer Assistant Async Worker Orchestration

## 061.0 Sign-off

- [x] Confirm 061 consumes worker async refs from 059.
- [x] Confirm fast worker behavior remains compatible.
- [x] Confirm pending workers are visible instead of hidden.
- [x] Confirm ChatflowSopWorker remains out of scope.
- [x] Confirm worker dispatch is idempotent for the same task state/version.
- [x] Confirm fan-out/join policy and max concurrency are explicit.
- [x] Confirm waiting worker prompts are preserved in recommendation/draft
      output.

## 061.1 Task Ledger Refs

- [x] RED: task state cannot persist worker run refs.
- [x] Store worker refs on task state or task result payload.
- [x] Surface refs through runtime response and event timeline.

## 061.2 Async Orchestration

- [x] RED: long-running worker blocks the whole turn until completion.
- [x] Spawn worker run through 059 runtime.
- [x] Deduplicate dispatch by task state/version and worker request hash.
- [x] Add wait-deadline behavior.
- [x] Add max-concurrency or backpressure handling.
- [x] Return pending state when worker remains running.

## 061.3 Result Consumption

- [x] RED: completed async worker result is not applied to task state.
- [x] Add chosen result consumption path.
- [x] Guard result consumption with task state version or equivalent stale-result
      check.
- [x] Emit events for worker result consumed or worker failure consumed.

## 061.4 Fan-out And Join Policy

- [x] RED: multiple worker refs cannot represent required/pending/failed join
      states.
- [x] Define required vs optional worker result semantics.
- [x] Represent partial recommendation with pending/failure warnings.
- [x] Represent waiting worker output as an actionable operator
      recommendation plus customer reply draft.
- [x] Preserve worker-provided prompt before falling back to assistant-generated
      text.
- [x] Prove parallel dispatch is not implemented as hidden serial blocking.

## 061.5 Product Evidence

- [x] Verify task ledger shows pending/running/completed worker states.
- [x] Verify recommendation warns when required worker evidence is still
      pending.
- [x] Verify waiting worker prompt appears as customer draft and operator next
      step.
- [x] Run focused frontend tests if UI payload changes.

## 061.6 Gates

- [x] Run customer-assistant backend gates.
- [x] Run Browser UAT for one pending-worker scenario.

## 061.7 Async Runtime Audit Closure 2026-06-16

- [x] RED: multiple async workers were not batch-started before the join
      deadline, and the unset default wait deadline made a slow async worker look
      blocking.
- [x] Batch-start async-capable worker runs before joining.
- [x] Return `RUNNING` plus real worker refs for slow low-risk workers when the
      default deadline is exceeded.
- [x] Preserve sync-friendly `chatflow_sop` default behavior and public
      customer-assistant error code compatibility.
- [x] Run focused and customer-assistant backend gates.

Evidence:

- RED: `artifacts/slices/061-customer-assistant-async-worker-orchestration/red.txt`
- Pending refresh integration: `artifacts/slices/061-customer-assistant-async-worker-orchestration/integration-pending-refresh.txt`
- Waiting prompt integration: `artifacts/slices/061-customer-assistant-async-worker-orchestration/integration-waiting-prompt.txt`
- API refresh contract: `artifacts/slices/061-customer-assistant-async-worker-orchestration/contract-refresh-api.txt`
- Backend gates: `artifacts/slices/061-customer-assistant-async-worker-orchestration/backend-gates.txt`
- Browser UAT: `artifacts/slices/061-customer-assistant-async-worker-orchestration/uat.md`
- Audit RED:
  `artifacts/slices/061-customer-assistant-async-worker-orchestration/061-audit-async-fanout-default/red.txt`
- Audit focused integration:
  `artifacts/slices/061-customer-assistant-async-worker-orchestration/061-audit-async-fanout-default/integration-focused.txt`
- Audit customer-assistant integration:
  `artifacts/slices/061-customer-assistant-async-worker-orchestration/061-audit-async-fanout-default/integration-customer-assistant.txt`
- Audit unit/contract:
  `artifacts/slices/061-customer-assistant-async-worker-orchestration/061-audit-async-fanout-default/unit-contract.txt`
- Audit lint:
  `artifacts/slices/061-customer-assistant-async-worker-orchestration/061-audit-async-fanout-default/ruff.txt`
