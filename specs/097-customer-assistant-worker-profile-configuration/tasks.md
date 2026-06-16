# Tasks: Customer Assistant Worker Profile Configuration

## 097.1 Runtime-Editable Worker Profiles

- [x] Create SDD docs and evidence directory.
- [x] Save RED backend failure for persisted profile override and routing.
  - Evidence: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/red-backend.txt`
- [x] Save RED frontend failure for missing API client/form.
  - Evidence: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/red-frontend.txt`
- [x] Implement DB schema/migration/repository support.
- [x] Implement catalog merge, service mutation, and router endpoint.
- [x] Run backend focused integration and schema gates.
  - Evidence: `backend-worker-profiles.txt`, `backend-schema.txt`, `ruff.txt`
- [x] Add frontend API update contract test and implementation.
- [x] Add customer assistant workbench profile edit flow.
- [x] Run frontend focused tests and rem gate.
  - Evidence: `frontend-focused.txt`, `frontend-unit-focused.txt`, `frontend-unit-full.txt`, `frontend-rem.txt`, `frontend-build.txt`
- [x] Run browser UAT and save evidence.
  - Evidence: `uat.txt`, `worker-profile-edit.png`
- [x] Commit focused feature point.
  - Commit: `feat(customer-assistant): edit worker profiles`
