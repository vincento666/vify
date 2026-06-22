# Browser UAT Summary

Local server:

```text
HIFY_BACKEND_PORT=18080 HIFY_FRONTEND_PORT=15173
HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS=refund_ticket:6055
HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_MODE=fake
```

Passed:

```text
rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:15173 HIFY_E2E_ARTIFACT_DIR=.../browser-uat/runtime-v2-phase1 node frontend/e2e/runtime-v2-phase1-production-uat.mjs
PASS runtime v2 phase1 production UAT

rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:15173 node --input-type=module <unified-routing-runtime-v2-browser-uat>
PASS unified routing runtime-v2 browser UAT session=771 run=5154

rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:15173 node --input-type=module <customer-assistant-runtime-v2-browser-uat>
PASS customer assistant runtime-v2 browser UAT session=63 run=5156

rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:15173 HIFY_E2E_SCREENSHOT=.../workflow-runtime-v2-cancel-debug-control.png node frontend/e2e/workflow-runtime-v2-cancel-debug-control.mjs
PASS runtime v2 cancel debug control chatflow=6057 run=5158

rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:15173 node --input-type=module <canvas-live-eventsource-browser-uat>
PASS canvas live EventSource browser UAT chatflow=6058 run=5159
```

Observed:

- Runtime-lab SOP path completed a Chatflow runtime v2 run, exposed `statusRef`, `eventsRef`, `eventStreamRef`, `nodesRef`, and `resultRef`, and returned an SSE frame from `chatflow_runtime_v2`.
- Customer-assistant UI used `/sessions/{id}/messages`, not legacy `/turns`, and projected Chatflow runtime v2 node states into assistant events.
- Canvas live trial opened a browser `EventSource` to `/api/v1/runtime-runs/{runId}/events/stream`.
- Canvas debug replay and cancel controls rendered durable runtime state and cancelled a runtime v2 run through `/runtime-runs/{runId}/cancel`.
