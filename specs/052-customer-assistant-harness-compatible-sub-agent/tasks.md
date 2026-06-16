# Tasks 052: Customer Assistant Harness-Compatible Sub-Agent

## 052.0 Spec Sign-off

- [x] Confirm Hify contract name and fields for `spawn_sub_agent`.
- [x] Confirm whether 052 includes minimal async run handle or depends on a
      prior lifecycle spec.
- [x] Confirm cancellation is required or explicitly unsupported.
- [x] Confirm 052 does not refactor Workflow/Chatflow and only stabilizes the
      customer-assistant sub-agent calling convention.

## 052.1 Adapter Contract

- [x] Define request/response schemas.
- [x] Add fake harness caller tests.

## 052.2 Eventful Spawn

- [x] Return event stream ref and result ref.
- [x] Emit sub-agent lifecycle events.

## 052.3 Result Integration

- [x] Provide result fetch path.
- [x] Prove main-agent summarization can consume final result.

## 052.4 Worker Async Run Readiness

- [x] Document whether internal workers expose `workerRunId`,
      `workerStatusRef`, `workerEventStreamRef`, and `workerResultRef`.
- [x] If worker async refs are not implemented, reserve the fields and record a
      follow-up stabilization slice before Workflow/Chatflow runtime v2.
- [x] Prove the external sub-agent run remains eventful even when internal
      workers are still scheduler-bound.

## 052.5 Acceptance

- [x] Run contract and integration gates.

## Evidence

- RED: `artifacts/slices/052-customer-assistant-harness-compatible-sub-agent/052.1/red.txt`
- Focused contract: `artifacts/slices/052-customer-assistant-harness-compatible-sub-agent/052.1/unit.txt`
- Unit pack: `artifacts/slices/052-customer-assistant-harness-compatible-sub-agent/052.5/unit.txt`
- Contract pack: `artifacts/slices/052-customer-assistant-harness-compatible-sub-agent/052.5/contract.txt`
- Integration pack: `artifacts/slices/052-customer-assistant-harness-compatible-sub-agent/052.5/integration.txt`
- E2E pack: `artifacts/slices/052-customer-assistant-harness-compatible-sub-agent/052.5/e2e.txt`
- Live HTTP UAT: `artifacts/slices/052-customer-assistant-harness-compatible-sub-agent/052.5/uat.md`
- Browser screenshot: `artifacts/slices/052-customer-assistant-harness-compatible-sub-agent/052.5/screenshots/result-endpoint.png`
