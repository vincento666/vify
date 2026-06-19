# Tasks

## 202.1 Workflow Safe Retry From Completed Nodes

- [x] RED: standalone worker duplicates completed node runs after a simulated
      worker crash.
- [x] GREEN: rehydrate completed node outputs into runtime context.
- [x] GREEN: continue from the first not-yet-completed active-path node.
- [x] Gate: focused safe-retry contract.
- [x] Gate: backend runtime/workflow regression.
- [x] Gate: frontend remScaleClosure and full unit.
- [x] Browser UAT confirms fresh run completion remains compatible.

## Evidence

- RED: `artifacts/slices/202-runtime-job-safe-retry/202.1/red.txt`
- Focused green: `artifacts/slices/202-runtime-job-safe-retry/202.1/focused-green.txt`
- Runtime integration: `artifacts/slices/202-runtime-job-safe-retry/202.1/runtime-integration.txt`
- Backend gate: `artifacts/slices/202-runtime-job-safe-retry/202.1/backend-gate.txt`
- Frontend rem: `artifacts/slices/202-runtime-job-safe-retry/202.1/frontend-rem.txt`
- Frontend unit: `artifacts/slices/202-runtime-job-safe-retry/202.1/frontend-unit.txt`
- Browser UAT: `artifacts/slices/202-runtime-job-safe-retry/202.1/uat.txt`
- Browser UAT report: `artifacts/slices/202-runtime-job-safe-retry/202.1/uat.json`
