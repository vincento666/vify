# Runtime V2 Production Upgrade Acceptance Matrix

## Scope

Goal: upgrade Chatflow/Workflow API and canvas debugging UI to production-grade runtime v2 with unified production entries, default live observation plus durable recovery, durable Chatflow jobs, SOP/customer-assistant runtime refs/events, SDD/TDD evidence, browser UAT, and per-slice commits.

## Slices

| Slice | Modification scope | RED evidence | Green evidence | Residual risk |
|---|---|---|---|---|
| SOP/customer-assistant projection | `app/modules/runtime_lab/domain/chatflow_adapter.py`, `app/modules/customer_assistant/domain/workers.py`, `app/modules/customer_assistant/domain/service.py`, customer-assistant integration tests | `sop-customer-assistant-projection/red.txt` | `sop-customer-assistant-projection/focused-green.txt` | UI selector drift remains possible; browser UAT covers current gateway/recovery path. |
| Chatflow durable worker | `app/modules/workflow/runtime_job_worker.py`, chatflow worker contract tests | `chatflow-durable-worker/red.txt` | `chatflow-durable-worker/focused-green.txt` | External worker deployment/cadence is still deployment config, not app code. |
| Canvas SSE debug | `frontend/src/views/workflow/runtimeV2Debug.ts`, `WorkflowCreate.vue`, runtime debug tests | `canvas-sse-debug/red.txt` | `canvas-sse-debug/focused-green.txt` | Terminal debug replay intentionally uses durable state instead of keeping SSE open. |
| Chatflow default entry | `app/modules/workflow/web/router.py`, frontend workflow API/canvas callers, contract/integration migrations | `chatflow-default-entry/red.txt` | `chatflow-default-entry/focused-green.txt`, `chatflow-default-entry/integration-green.txt` | Legacy `/runs-legacy` remains for compatibility by design. |
| Chatflow message durable jobs | `app/modules/workflow/web/router.py`, `tests/contract/test_chatflow_session_gateway_api.py` | `chatflow-message-durable-job/red.txt` | `chatflow-message-durable-job/focused-green.txt`, `chatflow-message-durable-job/integration-green.txt` | Inline wait path now claims/completes a job synchronously; external workers can still claim queued no-wait jobs. |
| Runtime-lab stale binding fallback | `app/modules/runtime_lab/domain/chatflow_adapter.py`, `app/modules/runtime_lab/web/router.py`, runtime-lab/customer-assistant tests | `runtime-lab-stale-binding-fallback/red.txt` | `runtime-lab-stale-binding-fallback/focused-green.txt`, `runtime-lab-stale-binding-fallback/policy-green.txt` | Fallback is opt-in for runtime-lab only; customer-assistant bound missing Chatflow still fails visibly. |

## Final Gates

| Gate | Evidence |
|---|---|
| Backend unit/contract/integration | `final-gates/backend-unit-contract-integration.txt` (`891 passed, 10 skipped`) |
| Frontend unit + rem closure | `final-gates/frontend-unit-rem.txt` (`98` files, `416` tests; includes `src/remScaleClosure.test.ts`) |
| Runtime v2 production/debug browser UAT | `browser-uat/runtime-v2-phase1/runtime-v2-phase1-production-uat.json` |
| Unified routing SOP Chatflow refs/SSE browser UAT | `browser-uat/unified-routing/unified-routing-runtime-v2-browser-uat.json` |
| Customer-assistant Chatflow refs/SSE/recovery browser UAT | `browser-uat/customer-assistant/customer-assistant-runtime-v2-browser-uat.json` |
| Canvas live EventSource browser UAT | `browser-uat/canvas-sse/canvas-live-eventsource-browser-uat.json` |
| Canvas cancel/debug browser UAT | `browser-uat/canvas-sse/screenshots/workflow-runtime-v2-cancel-debug-control.png` and command output: `PASS runtime v2 cancel debug control chatflow=6057 run=5158` |

## Endpoint Semantics

| Entry | Production meaning |
|---|---|
| `POST /api/v1/workflows/{id}/runs` | Workflow runtime v2 default durable async gateway. |
| `POST /api/v1/workflows/{id}/runs:stream` | Workflow stream entry backed by runtime v2 event stream. |
| `POST /api/v1/workflows/{id}/runs-legacy` | Explicit compatibility entry. |
| `POST /api/v1/chatflows/{id}/runs` | Chatflow runtime v2 default durable async gateway. |
| `POST /api/v1/chatflows/{id}/messages` | Chatflow production message gateway using runtime v2 refs and durable jobs. |
| `POST /api/v1/chatflows/{id}/runs-legacy` | Explicit legacy synchronous Chatflow compatibility entry. |
| `/api/v1/runtime-runs/{runId}` + `/events` + `/events/stream` + `/nodes` + `/result` | Unified runtime v2 status/events/SSE/nodes/result observation model. |

## Browser UAT Environment Note

The browser UAT used a deterministic local Chatflow binding (`refund_ticket:6055`) to avoid external OpenRouter dependence from previously seeded airline LLM SOPs. The reports prove runtime v2 refs/events/SSE behavior and not third-party model connectivity.
