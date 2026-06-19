# Tasks

## 199.1 Workflow Public Run Gateway

- [x] RED: `/workflows/{id}/runs` returns legacy sync output instead of runtime
      refs.
- [x] RED: `/workflows/{id}/runs:stream` is missing.
- [x] GREEN: `/runs` starts Runtime Core v2 and returns refs.
- [x] GREEN: `/runs:stream` starts Runtime Core v2 and streams events.
- [x] GREEN: add explicit `/runs-legacy` compatibility endpoint.
- [x] Gate: focused workflow contract/integration tests.
- [x] Gate: frontend remScaleClosure and full unit.
- [x] Browser UAT with run refs, result/events/nodes, and SSE recovery.

## Evidence

- RED: `artifacts/slices/199-workflow-run-gateway/199.1/red.txt`
- Unit: `artifacts/slices/199-workflow-run-gateway/199.1/unit.txt`
- Contract: `artifacts/slices/199-workflow-run-gateway/199.1/contract.txt`
- Integration: `artifacts/slices/199-workflow-run-gateway/199.1/integration.txt`
- Backend gate: `artifacts/slices/199-workflow-run-gateway/199.1/backend-gate.txt`
- Frontend rem: `artifacts/slices/199-workflow-run-gateway/199.1/frontend-rem.txt`
- Frontend unit: `artifacts/slices/199-workflow-run-gateway/199.1/frontend-unit.txt`
- Browser UAT: `artifacts/slices/199-workflow-run-gateway/199.1/uat.txt`
- Browser UAT report: `artifacts/slices/199-workflow-run-gateway/199.1/uat.json`
