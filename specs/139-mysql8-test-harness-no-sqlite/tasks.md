# Tasks

- [x] Create spec, plan, and tasks for MySQL8-only test harness hardening.
- [x] RED: add static no-SQLite gate and save failure evidence.
- [x] Implement shared MySQL8 test harness with disposable DB creation only.
- [x] Migrate seed/bootstrap tests to MySQL8 harness.
- [x] Migrate runtime/customer-assistant direct SQLite engines.
- [x] Migrate contract/e2e/acceptance direct SQLite engines.
- [x] Run focused green tests.
- [x] Run full backend integration+contract with MySQL8.
- [x] Run e2e, acceptance, unit, live OpenRouter, and final static scans.
- [x] Update evidence and docs.
- [x] Commit the slice.

## Evidence

- RED static guard:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-red.txt`
- RED connection validator:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-connection-validator-red.txt`
- Focused MySQL8 boundary:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-boundary-green-3.txt`
- Full unit:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-unit-full-2.txt`
- Backend integration + contract:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-backend-integration-contract-mysql8-6.txt`
- E2E:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-e2e-mysql8-4.txt`
- Acceptance:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-acceptance-default-5.txt`
- RuntimeLab policy regression:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-runtime-lab-policy-green-1.txt`
- Customer assistant worker/SSE:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-worker-green-2.txt`
  and
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-e2e-sse-green-1.txt`
- Live OpenRouter customer assistant:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-live-customer-assistant-openrouter-1.txt`
- Live OpenRouter runtime v2:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite-live-runtime-v2-openrouter-1.txt`
- Final no-SQLite scan:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite/sqlite-static-scan-final.txt`
- Final secret scan:
  `artifacts/slices/139-mysql8-test-harness-no-sqlite/secret-scan.txt`
