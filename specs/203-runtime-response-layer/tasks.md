# Tasks

## 203.1 Runtime Result Response Summary

- [x] RED: runtime result endpoint lacks response-layer summary fields.
- [x] GREEN: add `statusRef`, `latencyMs`, `usage`, `retryable`, `result`, and
      simplified `events`.
- [x] GREEN: preserve full `/events` payload details for debug/canvas.
- [x] Gate: focused runtime response-layer contract.
- [x] Gate: backend runtime/workflow regression.
- [x] Gate: frontend remScaleClosure and full unit.
- [x] Browser UAT confirms workflow run gateway still works.

## Evidence

- RED: `artifacts/slices/203-runtime-response-layer/203.1/red.txt`
- Focused green: `artifacts/slices/203-runtime-response-layer/203.1/focused-green.txt`
- Runtime integration: `artifacts/slices/203-runtime-response-layer/203.1/runtime-integration.txt`
- Backend gate: `artifacts/slices/203-runtime-response-layer/203.1/backend-gate.txt`
- Frontend rem: `artifacts/slices/203-runtime-response-layer/203.1/frontend-rem.txt`
- Frontend unit: `artifacts/slices/203-runtime-response-layer/203.1/frontend-unit.txt`
- Browser UAT: `artifacts/slices/203-runtime-response-layer/203.1/uat.txt`
- Browser UAT note: `artifacts/slices/203-runtime-response-layer/203.1/uat.md`
- Browser UAT report: `artifacts/slices/203-runtime-response-layer/203.1/uat.json`
