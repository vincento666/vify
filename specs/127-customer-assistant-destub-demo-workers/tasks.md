# Tasks: Customer Assistant Destub Demo Workers

## 127.1 Backend Seed/Profile Destub

- [x] Create SDD docs and evidence directory.
- [x] Save RED test failure in `artifacts/slices/127-customer-assistant-destub-demo-workers/127.1/red.txt`.
- [x] Remove productized-demo/default MVP `stub_qa` worker/profile markers.
- [x] Preserve deterministic demo worker behavior behind productized route
  names.
- [x] Run focused unit gate and save evidence.
- [x] Run focused integration gate and save evidence.
- [x] Run ruff on touched Python files and save evidence.
- [x] Mark docs complete and commit focused slice.

## Evidence

- RED: `artifacts/slices/127-customer-assistant-destub-demo-workers/127.1/red.txt`
- Focused unit: `artifacts/slices/127-customer-assistant-destub-demo-workers/127.1/unit.txt`
- Focused integration: `artifacts/slices/127-customer-assistant-destub-demo-workers/127.1/integration.txt`
- Worker-profile API integration: `artifacts/slices/127-customer-assistant-destub-demo-workers/127.1/worker_profiles_integration.txt`
- MVP bootstrap contract: `artifacts/slices/127-customer-assistant-destub-demo-workers/127.1/bootstrap_contract.txt`
- Ruff: `artifacts/slices/127-customer-assistant-destub-demo-workers/127.1/ruff.txt`
- Browser UAT: not required; 127.1 only changes backend seed/default
  configuration, with persisted topology covered by integration tests.

## Notes

- A combined run of `test_mvp_demo_bootstrap_contract.py` followed by
  `test_worker_profiles.py` still leaks `HIFY_DATABASE_URL` from the existing
  bootstrap contract fixture into the next file. Both files pass in isolation;
  evidence is saved separately to avoid hiding that unrelated fixture issue.
