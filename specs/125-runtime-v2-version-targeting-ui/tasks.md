# Tasks 125: Runtime V2 Version Targeting UI

## 125.1 Published Version Runtime V2 Test

- [x] Create SDD docs and evidence directory.
- [x] Add RED frontend API coverage for runtime v2 `versionId` payloads.
- [x] Add RED UI contract coverage for runtime-v2 version-list action/results.
- [x] Save RED frontend failure.
  - Evidence: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/red.txt`
- [x] Implement runtime v2 API helper payload support.
- [x] Implement publish dialog runtime-v2 test action/result.
- [x] Verify focused frontend gate.
  - Evidence: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/frontend-focused.txt`
- [x] Verify frontend rem gate.
  - Evidence: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/frontend-rem.txt`
- [x] Run full frontend unit gate.
  - Evidence: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/frontend-unit.txt`
  - Result: blocked by out-of-scope customer-assistant failures:
    `deliverCustomerAssistantAction` / `deliverCustomerAssistantRuntimeAction`.
- [x] Run frontend build gate.
  - Evidence: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/frontend-build.txt`
  - Result: blocked by out-of-scope customer-assistant type errors in tests.
- [x] Run browser UAT and save evidence.
  - Evidence: `artifacts/slices/125-runtime-v2-version-targeting-ui/125.1/uat.md`
- [x] Update docs/tasks evidence.
- [x] Commit focused slice.
