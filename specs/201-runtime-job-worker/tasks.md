# Tasks

## 201.1 Standalone Runtime Job Worker

- [x] RED: worker service module is missing.
- [x] RED: Workflow run cannot be completed by standalone worker when inline
      thread is patched out.
- [x] GREEN: implement generic `RuntimeJobWorker`.
- [x] GREEN: implement workflow runtime job worker factory.
- [x] GREEN: add script entry point for `--once` and polling mode.
- [x] GREEN: inline transition thread uses the same worker service.
- [x] Gate: focused worker service + gateway tests.
- [x] Gate: backend runtime/workflow regression.
- [x] Gate: frontend remScaleClosure and full unit.
- [x] Browser UAT confirms run completion remains compatible.

## Evidence

- RED: `artifacts/slices/201-runtime-job-worker/201.1/red.txt`
- Focused green: `artifacts/slices/201-runtime-job-worker/201.1/focused-green.txt`
- Script once: `artifacts/slices/201-runtime-job-worker/201.1/script-once.txt`
- Runtime integration: `artifacts/slices/201-runtime-job-worker/201.1/runtime-integration.txt`
- Backend gate: `artifacts/slices/201-runtime-job-worker/201.1/backend-gate.txt`
- Frontend rem: `artifacts/slices/201-runtime-job-worker/201.1/frontend-rem.txt`
- Frontend unit: `artifacts/slices/201-runtime-job-worker/201.1/frontend-unit.txt`
- Browser UAT: `artifacts/slices/201-runtime-job-worker/201.1/uat.txt`
- Browser UAT report: `artifacts/slices/201-runtime-job-worker/201.1/uat.json`
