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

## 097.1 Review Hardening

- [x] Save RED review-fix failure for tenant leakage and disabled override fallback.
  - Evidence: `artifacts/slices/097-customer-assistant-worker-profile-configuration/097.1/red-review-fixes.txt`
- [x] Scope worker-profile overrides by tenant/org and keep disabled overrides from suppressing default/env profiles.
- [x] Freeze worker-profile migration metadata and add idempotent tenant/org scope migration.
- [x] Make browser UAT cleanup mandatory instead of best-effort.
- [x] Run review-fix integration, schema, and lint gates.
  - Evidence: `review-fixes-worker-profiles.txt`, `review-fixes-schema.txt`, `review-fixes-ruff.txt`
- [x] Reuse focused frontend/rem evidence for unchanged UI code.
  - Evidence: `review-fixes-frontend.txt`
- [x] Run review-fix browser UAT and save screenshot.
  - Evidence: `review-fixes-uat.txt`, `worker-profile-edit-review-fix.png`
