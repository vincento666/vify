# 063 Config Panel Controls Audit

Scope:
- Verified workflow/chatflow node config sections use real collapsible headers with `aria-expanded`.
- Verified LLM config panel no longer exposes `输入参数` title and keeps input rows compact/aligned.
- Verified input/output parameter editors persist rows, types, variable references, output format, and duplicate validation.
- Verified lightweight icon buttons have svg icons plus visible border/background surfaces.

Gates:
- `HIFY_E2E_SCREENSHOT=artifacts/slices/063-config-panel-controls-audit/screenshots/workflow-config-section-collapse.png rtk node frontend/e2e/workflow-config-section-collapse.mjs` -> `e2e-workflow-config-section-collapse.txt`
- `HIFY_E2E_SCREENSHOT=artifacts/slices/063-config-panel-controls-audit/screenshots/workflow-config-panel-polish-026.png rtk node frontend/e2e/workflow-config-panel-polish-026.mjs` -> `e2e-workflow-config-panel-polish-026.txt`
- `HIFY_E2E_SCREENSHOT=artifacts/slices/063-config-panel-controls-audit/screenshots/workflow-shared-controls-polish.png rtk node frontend/e2e/workflow-shared-controls-polish.mjs` -> `e2e-workflow-shared-controls-polish.txt`
- `HIFY_E2E_SCREENSHOT=artifacts/slices/063-config-panel-controls-audit/screenshots/workflow-input-parameters.png rtk node frontend/e2e/workflow-input-parameters.mjs` -> `e2e-workflow-input-parameters.txt`
- `HIFY_E2E_SCREENSHOT=artifacts/slices/063-config-panel-controls-audit/screenshots/workflow-output-parameters.png rtk node frontend/e2e/workflow-output-parameters.mjs` -> `e2e-workflow-output-parameters.txt`
- `HIFY_E2E_SCREENSHOT=artifacts/slices/063-config-panel-controls-audit/screenshots/workflow-icon-button-final-polish.png rtk node frontend/e2e/workflow-icon-button-final-polish.mjs` -> `e2e-workflow-icon-button-final-polish.txt`
- `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` -> `rem.txt`
- `rtk npm --prefix frontend run test:unit` -> `unit-full.txt`
- `rtk npm --prefix frontend run build` -> `build.txt`
