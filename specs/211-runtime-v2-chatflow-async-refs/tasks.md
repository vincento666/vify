# Tasks 211: Runtime V2 Chatflow Async Refs Closure

## 211.1 Chatflow Runs Stream

- [x] RED: `/api/v1/chatflows/{id}/runs:stream` contract/e2e coverage fails
      before endpoint implementation.
- [x] Add Chatflow runtime-v2 stream endpoint.
- [x] Verify success, failure, waiting input, and runtime reconnect.
- [x] Verify idle heartbeat behavior.

Evidence:

- RED/env preflight: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.1-chatflow-runs-stream/red.txt`
- Contract: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.1-chatflow-runs-stream/contract.txt`
- E2E: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.1-chatflow-runs-stream/e2e.txt`

## 211.2 Runtime Invocation Gateway

- [x] RED: gateway import and behavior tests fail before implementation.
- [x] Add shared gateway with `startOnly`, `startAndWait`,
      `startAndStreamRef`, and `resumeAndWait` semantics.
- [x] Route Workflow/Chatflow public start gateways through the shared layer.
- [x] Verify Workflow/Chatflow gateway contracts.

Evidence:

- RED: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.2-runtime-invocation-gateway-red.txt`
- Unit: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.2-runtime-invocation-gateway-unit.txt`
- Workflow contract: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.2-runtime-invocation-gateway-workflow-contract.txt`

## 211.3 SOP Adapter Async Refs

- [x] RED: SOP v2 can return runtime refs before completion in async mode.
- [x] Use the shared runtime invocation gateway in SOP adapter paths.
- [x] Preserve old synchronous compatibility behavior.

Evidence:

- RED gateway: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.3-sop-adapter-gateway/red.txt`
- RED async: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.3-sop-adapter-gateway/async-red.txt`
- RED config: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.3-sop-adapter-gateway/config-red.txt`
- Unit/config: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.3-sop-adapter-gateway/unit-config.txt`
- Integration/e2e/customer-assistant regression:
  `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.3-sop-adapter-gateway/gates.txt`

## 211.4 Customer Assistant Chatflow SOP Async Refs

- [x] RED: `chatflow_sop` worker returns pending refs without blocking for
      completion when wait deadline requires async behavior.
- [x] Stream live worker/runtime events consistently into worker and session
      surfaces.
- [x] Generate blocking reason and operator recommendation for waiting input.

Evidence:

- RED gateway enqueue:
  `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.4-customer-assistant-async-refs/gateway-red.txt`
- Gateway unit:
  `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.4-customer-assistant-async-refs/gateway-unit.txt`
- Worker async product path:
  `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.4-customer-assistant-async-refs/worker-async.txt`
- Unit/integration/contract gates:
  `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.4-customer-assistant-async-refs/gates.txt`

## 211.5 Standalone Runtime Worker Owner Filtering

- [x] RED: workflow-only worker does not claim queued Chatflow jobs.
- [x] Add `--owner workflow|chatflow|both` to `scripts/runtime_job_worker.py`.
- [x] Verify lease takeover for Chatflow jobs.

Evidence:

- RED unit: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.5-runtime-worker-owner/red-unit.txt`
- RED contract: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.5-runtime-worker-owner/red-contract.txt`
- Unit: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.5-runtime-worker-owner/unit.txt`
- Integration: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.5-runtime-worker-owner/integration.txt`
- Contract: `artifacts/slices/211-runtime-v2-chatflow-async-refs/211.5-runtime-worker-owner/contract.txt`

## 211.6 Docs And UAT Matrix

- [ ] Update stream/ref endpoint matrix.
- [ ] Run browser UAT for runtime-lab SOP, customer-assistant task panel, and
      canvas runtime state alignment.
