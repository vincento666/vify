# Browser UAT: Runtime V2 Redis Stream Event Channel

Date: 2026-06-19 Asia/Shanghai

Target:

- Frontend: `http://127.0.0.1:15196`
- Backend: `http://127.0.0.1:15195`

Command:

```bash
rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:15196 HIFY_E2E_ARTIFACT_DIR=/Users/vincento/work/develop/hify/artifacts/slices/195-runtime-v2-redis-stream-event-channel/195.1 HIFY_E2E_REPORT=/Users/vincento/work/develop/hify/artifacts/slices/195-runtime-v2-redis-stream-event-channel/195.1/runtime-v2-uat.json node frontend/e2e/runtime-v2-phase1-production-uat.mjs
```

Result: PASS.

Artifacts:

- Command output: `browser-uat.txt`
- JSON report: `runtime-v2-uat.json`
- Debug screenshot: `screenshots/runtime-v2-error-debug.png`
- Governance screenshot: `screenshots/api-tool-governance-panel.png`

Coverage:

- Runtime v2 run/debug and event refs remain usable after stream bus insertion.
- Error routing still reaches the debug dock.
- Version binding and negative publish validation still pass.
- UI governance panel remains visible.
