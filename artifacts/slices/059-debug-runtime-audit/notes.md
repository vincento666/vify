# 059 Debug Runtime Audit

Scope:
- Added focused workflow/chatflow E2E coverage for debug dock layout, errors panel, polish, stream preview, runtime timeline, and workflow run detail.
- Preserved red evidence for two stale assertions before fixing the audit contract:
  - `red-chatflow-runtime-timeline-ui.txt`: broad `完成` lookup collided with `已完成`.
  - `red-workflow-debug-dock-run.txt`: dock text was read before the run summary had finished loading.

Gates:
- `rtk node frontend/e2e/chatflow-debug-dock-layout.mjs` -> `e2e-chatflow-debug-dock-layout.txt`
- `rtk node frontend/e2e/chatflow-debug-errors-panel.mjs` -> `e2e-chatflow-debug-errors-panel.txt`
- `rtk node frontend/e2e/chatflow-debug-polish.mjs` -> `e2e-chatflow-debug-polish.txt`
- `rtk node frontend/e2e/chatflow-stream-typewriter.mjs` -> `e2e-chatflow-stream-typewriter.txt`
- `rtk node frontend/e2e/chatflow-runtime-timeline-ui.mjs` -> `e2e-chatflow-runtime-timeline-ui.txt`
- `rtk node frontend/e2e/workflow-debug-dock-run.mjs` -> `e2e-workflow-debug-dock-run.txt`
- `rtk npm --prefix frontend run test:unit` -> `unit-full.txt`
- `rtk npm --prefix frontend run build` -> `build.txt`
