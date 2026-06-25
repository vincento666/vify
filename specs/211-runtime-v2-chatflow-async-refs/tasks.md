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

- [ ] RED: SOP v2 can return runtime refs before completion in async mode.
- [ ] Use the shared runtime invocation gateway in SOP adapter paths.
- [ ] Preserve old synchronous compatibility behavior.

## 211.4 Customer Assistant Chatflow SOP Async Refs

- [ ] RED: `chatflow_sop` worker returns pending refs without blocking for
      completion when wait deadline requires async behavior.
- [ ] Stream live worker/runtime events consistently into worker and session
      surfaces.
- [ ] Generate blocking reason and operator recommendation for waiting input.

## 211.5 Standalone Runtime Worker Owner Filtering

- [ ] RED: workflow-only worker does not claim queued Chatflow jobs.
- [ ] Add `--owner workflow|chatflow|both` to `scripts/runtime_job_worker.py`.
- [ ] Verify lease takeover for Chatflow jobs.

## 211.6 Docs And UAT Matrix

- [ ] Update stream/ref endpoint matrix.
- [ ] Run browser UAT for runtime-lab SOP, customer-assistant task panel, and
      canvas runtime state alignment.
