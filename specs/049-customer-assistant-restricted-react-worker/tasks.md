# Tasks 049: Customer Assistant Restricted ReAct Worker

## 049.0 Spec Sign-off

- [x] Confirm 049 is customer-assistant worker scope, not generic harness.
- [x] Confirm default tests use fake model/tool fixtures.
- [x] Confirm live LLM worker UAT is opt-in.
- [x] Confirm L2 events do not expose hidden chain-of-thought.

## 049.1 Worker Registry

- [x] Define static worker config schema and registry.
- [x] Add tests for task-type to worker lookup.

## 049.2 Restricted ReAct Loop

- [x] Implement bounded plan/validate/tool/observe/final loop.
- [x] Enforce max iterations and timeout.

## 049.3 Tool Policy

- [x] Add tool allowlist enforcement.
- [x] Convert high-risk write attempts to `proposed_action`.

## 049.4 Events And Integration

- [x] Persist L1/L2 worker events.
- [x] Return normalized `WorkerResult`.
- [x] Prove events appear through 048 SSE.

## 049.5 Acceptance

- [x] Run focused backend gates.
- [x] Run live UAT only when explicitly enabled. N/A in this run: no explicit
      live worker opt-in was provided, so fake-gated UAT evidence was saved.

## Evidence

- 049.0 sign-off:
  `artifacts/slices/049-customer-assistant-restricted-react-worker/049.0/signoff.md`
- 049.1-049.3 unit RED/green:
  `artifacts/slices/049-customer-assistant-restricted-react-worker/049.1/red.txt`,
  `artifacts/slices/049-customer-assistant-restricted-react-worker/049.1/unit.txt`
- 049.4 integration/SSE:
  `artifacts/slices/049-customer-assistant-restricted-react-worker/049.4/unit.txt`,
  `artifacts/slices/049-customer-assistant-restricted-react-worker/049.4/e2e.txt`
- 049.5 final:
  `artifacts/slices/049-customer-assistant-restricted-react-worker/049.5/backend.txt`,
  `artifacts/slices/049-customer-assistant-restricted-react-worker/049.5/uat.md`
