# Tasks

## 204.1 Chatflow Message Response Summary

- [x] RED: Chatflow message response lacks Phase 8 summary fields.
- [x] GREEN: project runtime `result`, `latencyMs`, `usage`, `retryable`, and
      simplified `events` into message responses.
- [x] Gate: focused Chatflow session gateway contract.
- [x] Gate: backend runtime/workflow regression.
- [x] Gate: frontend remScaleClosure and full unit.
- [x] Browser UAT confirms workflow gateway remains compatible.

## Evidence

- RED: `artifacts/slices/204-chatflow-message-response-layer/204.1/red.txt`
- Focused green: `artifacts/slices/204-chatflow-message-response-layer/204.1/focused-green.txt`
- Backend gate: `artifacts/slices/204-chatflow-message-response-layer/204.1/backend-gate.txt`
- Frontend rem: `artifacts/slices/204-chatflow-message-response-layer/204.1/frontend-rem.txt`
- Frontend unit: `artifacts/slices/204-chatflow-message-response-layer/204.1/frontend-unit.txt`
- Browser UAT: `artifacts/slices/204-chatflow-message-response-layer/204.1/uat.txt`
- Browser UAT note: `artifacts/slices/204-chatflow-message-response-layer/204.1/uat.md`
- Browser UAT report: `artifacts/slices/204-chatflow-message-response-layer/204.1/uat.json`
