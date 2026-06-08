# 062 Layout Geometry Audit

Scope:
- Added workflow/chatflow layout E2E coverage for toolbar centering against available canvas geometry.
- Verified debug dock does not overlap the right config/test-run panel.
- Verified workflow/chatflow test-run panel bottom aligns with the debug dock.

Gates:
- `HIFY_E2E_SCREENSHOT=artifacts/slices/062-layout-geometry-audit/screenshots/workflow-chatflow-layout-polish.png rtk node frontend/e2e/workflow-chatflow-layout-polish.mjs` -> `e2e-workflow-chatflow-layout-polish.txt`
- `rtk npm --prefix frontend run test:unit` -> `unit-full.txt`
- `rtk npm --prefix frontend run build` -> `build.txt`
