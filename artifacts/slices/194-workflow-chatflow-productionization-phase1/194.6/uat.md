# Browser UAT: Runtime V2 Phase 1 Productionization

Date: 2026-06-19 Asia/Shanghai

Target: `http://127.0.0.1:15194`

Command:

```bash
rtk env HIFY_E2E_BASE_URL=http://127.0.0.1:15194 HIFY_E2E_ARTIFACT_DIR=/Users/vincento/work/develop/hify/artifacts/slices/194-workflow-chatflow-productionization-phase1/194.6 node frontend/e2e/runtime-v2-phase1-production-uat.mjs
```

Result: PASS.

Artifacts:

- Command output: `runtime-v2-phase1-production-uat.txt`
- JSON report: `runtime-v2-phase1-production-uat.json`
- Runtime v2 debug screenshot: `screenshots/runtime-v2-error-debug.png`
- API/Tool governance panel screenshot: `screenshots/api-tool-governance-panel.png`

Coverage:

- Positive runtime v2 run/debug: Chatflow `1705`, run `1219`, status `SUCCEEDED`, output `error route: division by zero`.
- Error routing: CODE node raised `division by zero`, runtime v2 emitted handled-error evidence, selected `error` branch, and debug dock displayed the run output.
- Negative publish validation:
  - Workflow `1703` failed publish with `api_1 resourceId is required`.
  - Workflow `1704` failed publish with `tool_1 tool resource is required`.
- Publish version binding:
  - Workflow `1702` published v1 `222` and v2 `223`.
  - Targeted v1 run `1217` returned `published-v1` with `versionId=222`.
  - Active v2 run `1218` returned `published-v2` with `versionId=223`.
- API/Tool governance UI:
  - Chatflow `1706` API node panel displayed auth mode, timeout, retry count, error behavior, output schema, and sensitive header fields.

Browser plugin note:

- The in-app Browser plugin was initialized and documented as required, but `browser.tabs.new()` timed out waiting for the webview to attach twice.
- Product UAT was completed with real Chromium via Playwright and screenshots were visually inspected.
