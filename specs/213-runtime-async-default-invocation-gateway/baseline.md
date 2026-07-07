# Baseline — Spec 213

## 213.3 SOP Router State Mirror Removal

Status: GREEN

Closed at: `db41ff92`

Sealing tests and baseline are committed by this document's commit.

Scope closed:

- SOP Router task ledger stores runtime-lab ownership fields and child Chatflow refs.
- `runtime_lab_checkpoint` table removed.
- `runtime_lab_task.current_step` and `runtime_lab_task.business_refs` removed.
- Public task payloads no longer expose `currentStep` or `businessRefs`.
- Runtime refs are exposed through `activeTask.chatflowSession` / trace `chatflow`.
- Production runtime-lab bootstrap requires explicit SOP-to-Chatflow bindings and no longer injects `FakeSopRuntimeAdapter`.

Evidence:

- RED: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.3/red.txt`
- Unit sealing tests: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.3/unit.txt`
- Integration sealing tests: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.3/integration.txt`
- Runtime-lab unit suite: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.3/unit-runtime-lab.txt`
- Runtime-lab integration suite: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.3/integration-runtime-lab.txt`
- 213.3.6 UAT: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.3.6/uat.md`

## 213.4 Customer-Assistant Worker Async Refs

Status: GREEN

Closed at: slice commit `feat(customer-assistant): worker defaults to async runtime refs`

Scope closed:

- Bound customer-assistant `chatflow_sop` workers default to async runtime invocation.
- First response returns customer-assistant `workerAsyncRefs` plus child Chatflow runtime v2 refs.
- Explicit sync fallback remains available through `HIFY_CUSTOMER_ASSISTANT_SOP_RUNTIME_INVOCATION_MODE=sync`.
- Follow-up turns preserve the same child `runId` and avoid v1/failed checkpoint degeneration while the child run is still starting.
- E2E/UAT used deterministic local `refund_ticket` Chatflow id `13555` to avoid live provider dependency.

Evidence:

- RED: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.4/red.txt`
- Targeted green: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.4/green-targeted.txt`
- Unit: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.4/unit.txt`
- Integration: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.4/integration.txt`
- E2E: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.4/e2e.txt`
- Browser UAT: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.4/uat.md`
- Shared adapter regressions: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.4/unit-runtime-lab-regression.txt`, `artifacts/slices/213-runtime-async-default-invocation-gateway/213.4/integration-runtime-lab-regression.txt`

## 213.5 RunId Recovery

Status: GREEN

Closed at: slice commit `test(runtime): cover runId-based disconnect recovery`

Scope closed:

- `GET /api/v1/runtime-runs/{runId}` rebuilds the full six-ref family, including `nodesRef` and `runtimeRefs`, from runId.
- `GET /api/v1/runtime-runs/{runId}/result` exposes the same recovery refs as the status endpoint.
- `GET /api/v1/runtime-runs/{runId}/events?afterSequence=N` replays only events after the caller's last durable sequence.
- `GET /api/v1/runtime-runs/{runId}/nodes` rehydrates durable node-run state for recovered canvas/task views.
- Existing legacy resume E2E scripts still pass against a real browser/dev-server combination.

Evidence:

- RED: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.5/red.txt`
- Contract: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.5/contract.txt`
- Integration: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.5/integration.txt`
- E2E: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.5/e2e.txt`
- Browser UAT: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.5/uat.md`

## 213.6 Spec 212 Entry Gate Regression

Status: GREEN

Closed at: slice commit `test(runtime): seal spec 213 exit regression`

Scope closed:

- Chatflow multi-turn, message/question input, information collection, intent recognition, transfer-to-human, resume API, and channel UAT scripts pass.
- Workflow LLM, API resource/tool builder, tool-call, transform, knowledge/condition, execute-workflow, and agent-call UAT scripts pass.
- Runtime-lab SOP refs, Chatflow v2 binding, and unified-routing scale UAT pass with 15 scenarios and 5 switches.
- Backend unit, integration, and contract suites pass after fixing runtime-lab provider-backed/fake-mode resolver and chatflowSession fixture regressions.
- Frontend unit and rem governance gates pass.

Evidence:

- Unit: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.6/unit.txt`
- Integration: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.6/integration.txt`
- Contract: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.6/contract.txt`
- Frontend unit: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.6/frontend-unit.txt`
- Frontend rem: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.6/rem.txt`
- Browser UAT: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.6/uat.md`
- Diff check: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.6/diff-check.txt`

## 213.7 Chatflow SOP Bridge Async Progress Race

Status: GREEN

Closed at: slice commit `fix(customer-assistant): stabilize chatflow SOP runtime bridge`

Scope closed:

- `chatflow_sop` resume no longer turns runtime v2 failures into `runtimeVersion=1 / runId=null / FAILED` checkpoints.
- Runtime v2 resume now waits briefly for terminal result or checkpoint advance before projecting worker state.
- Provider/runtime failures return an explicit retryable WAITING envelope that preserves existing v2 refs.
- Customer-assistant SOP runtime can run deterministic LLM mock mode for ordinary UAT via `HIFY_CUSTOMER_ASSISTANT_SOP_LLM_MODE=mock`; default remains live/provider-backed for explicit live scenarios.
- `customer-assistant-chatflow-runtime-gateway-uat.mjs` passed 10 consecutive browser runs with first / second / confirm turns preserving runtime v2 refs and confirm completion.

Evidence:

- RED 10x reproduction: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.7/red-uat-10x.txt`
- RED targeted adapter tests: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.7/red.txt`
- RED SOP LLM mode config: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.7/red-sop-llm-mode.txt`
- Unit: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.7/unit.txt`
- Integration: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.7/integration.txt`
- Contract: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.7/contract.txt`
- E2E 10x: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.7/e2e-10x.txt`
- Browser UAT: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.7/uat.md`
- Diff check: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.7/diff-check.txt`

## 213.X Retire runs-v2 Alias

Status: GREEN for default gates; live production-node UAT is `ENV-BLOCKED-LIVE-MODEL`

Closed at: slice commit `refactor(runtime): retire /runs-v2 alias in favour of unified /runs`

Scope targeted:

- `/runs` is the only async-durable Chatflow / Workflow debug start URL.
- Backend `run_workflow_v2` / `run_chatflow_v2` alias handlers are removed while `_start_*_runtime_v2_gateway` stays unchanged.
- Frontend runtime v2 API clients, e2e scripts, acceptance tests, and integration tests use `/runs`.
- `docs/testing/acceptance-gates.md` now records `/runs` as canonical and asserts the former alias is absent from active routes/source entrypoints.

Evidence:

- RED route/static contract: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/red.txt`
- RED impact scan: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/red-impact.txt`
- Canonical route/static contract: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/green-contract-static.txt`
- Unit: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/unit.txt`
- Integration: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/integration.txt`
- Contract: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/contract.txt`
- Frontend unit: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/frontend-unit.txt`
- Frontend rem: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/rem.txt`
- E2E summary: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/e2e.txt`
- Browser UAT: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/uat.md`
- Live model blocker: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.X/e2e-live-blocked.txt`

## 214.5 Spec 214 Exit Regression

Status: GREEN

Closed at: slice commit `test(runtime): seal spec 214 exit regression` (`a120f00bb505797a9e569527d9220ec1abf4f7c9`)

Scope closed:

- Runtime v2 terminal result payloads now include durable `sessionId`, so Runtime Lab SOP reconstruction can recover Chatflow session variables across HTTP requests.
- Runtime-lab Chatflow SOP v2 bridge waits long enough for the scale gate terminal result to settle.
- Backend unit, integration, and contract suites pass after the regression fix.
- Frontend unit and rem governance gates remain green.
- Chatflow, Workflow, and Runtime-lab SOP Browser UAT groups pass under the spec 212/213 entry gate set.

Evidence:

- RED SOP scale: `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/red-sop-scale.txt`
- RED runtime result session id: `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/red-runtime-result-session-id.txt`
- Unit: `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/unit.txt`
- Integration: `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/integration.txt`
- Contract: `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/contract.txt`
- Frontend unit: `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/frontend-unit.txt`
- Frontend rem: `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/rem.txt`
- Browser UAT: `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/uat.md`

## 215.7 Spec 215 Exit Regression

Status: GREEN

Closed at: slice commit `test(runtime): seal spec 215 exit regression`

Scope closed:

- Frontier scheduler exit gates preserve spec 212/213/214 Chatflow, Workflow, and Runtime Lab SOP entry behavior.
- Explicit `allowFanOut` default-edge graphs now remain accepted by the updated runtime v2 facade contract.
- Runtime v2 resume now treats raw durable node-run `SUCCEEDED` and projected `COMPLETED` as completed states when rebuilding frontier context.
- Runtime Lab SOP bridge can resume after a question node and advance to confirm/completed instead of restarting the previous waiting/info node.
- Browser UAT used deterministic mock-safe LLM routing for ordinary gates; live agent rows were disabled for the run and restored afterward.

Evidence:

- RED outdated contract: `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/red-integration-outdated-contract.txt`
- RED bridge resume: `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/red-v2-bridge-resume.txt`
- Targeted bridge resume green: `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/green-v2-bridge-resume.txt`
- Unit: `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/unit.txt`
- Integration: `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/integration.txt`
- Contract: `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/contract.txt`
- Frontend unit: `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/frontend-unit.txt`
- Frontend rem: `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/rem.txt`
- Browser UAT: `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/uat.md`

## 218.8 Spec 218 Exit Regression

Status: GREEN

Closed at: spec 218 exit @ SHA `24ac674c`

Scope closed:

- Runtime V2 production job scheduling has DB pool config, atomic claim,
  heartbeat / lease takeover, retry / DLQ, idempotency layers, stable
  proposed-action keys, standalone worker entry, and request-thread offload.
- Backend unit, integration, and contract suites pass after the 218.7 worker
  offload implementation.
- Frontend unit and rem governance gates remain green.
- The spec 212.5 / 214.5 / 215.7 / 216.6 / 217.7 Browser UAT set passes
  against `/runs` with a standalone Runtime V2 worker.
- Live OpenRouter-dependent LLM UAT uses an environment-provided key only; no
  secret is written to repo evidence.

Evidence:

- Unit: `artifacts/slices/218-runtime-production-job-scheduler/218.8/unit.txt`
- Integration: `artifacts/slices/218-runtime-production-job-scheduler/218.8/integration.txt`
- Contract: `artifacts/slices/218-runtime-production-job-scheduler/218.8/contract.txt`
- Frontend unit: `artifacts/slices/218-runtime-production-job-scheduler/218.8/frontend-unit.txt`
- Frontend rem: `artifacts/slices/218-runtime-production-job-scheduler/218.8/rem.txt`
- Browser UAT: `artifacts/slices/218-runtime-production-job-scheduler/218.8/uat.md`
