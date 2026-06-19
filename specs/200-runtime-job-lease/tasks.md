# Tasks

## 200.1 Runtime Job Lease MVP

- [x] RED: runtime job repository import/table is missing.
- [x] RED: Workflow Run Gateway does not persist a runtime job.
- [x] GREEN: register `runtime_jobs` baseline schema.
- [x] GREEN: implement runtime job enqueue/claim/heartbeat/complete/fail.
- [x] GREEN: Workflow Run Gateway creates a job and inline worker executes
      through a claimed lease.
- [x] Gate: focused repository + workflow gateway tests.
- [x] Gate: backend runtime/workflow regression.
- [x] Gate: frontend remScaleClosure and full unit.
- [x] Browser UAT confirms run completion still works with job persistence.

## Evidence

- RED: `artifacts/slices/200-runtime-job-lease/200.1/red.txt`
- Focused green: `artifacts/slices/200-runtime-job-lease/200.1/focused-green.txt`
- Schema/unit: `artifacts/slices/200-runtime-job-lease/200.1/schema-unit.txt`
- Runtime integration: `artifacts/slices/200-runtime-job-lease/200.1/runtime-integration.txt`
- Backend gate: `artifacts/slices/200-runtime-job-lease/200.1/backend-gate.txt`
- Frontend rem: `artifacts/slices/200-runtime-job-lease/200.1/frontend-rem.txt`
- Frontend unit: `artifacts/slices/200-runtime-job-lease/200.1/frontend-unit.txt`
- Browser UAT: `artifacts/slices/200-runtime-job-lease/200.1/uat.txt`
- Browser UAT report: `artifacts/slices/200-runtime-job-lease/200.1/uat.json`
