# 145 Edge Insert Visibility UAT

- Date: 2026-06-09
- Targets:
  - `http://127.0.0.1:5173/chatflows/{created}/canvas`
  - `http://127.0.0.1:5173/chatflows/create`

## Checks

- Hovering a connection line shows exactly one circular insert button.
- Moving away from an unselected line hides the insert button.
- Selecting a line keeps the insert button visible without relying on stale hover styling.
- Pane click clears selected/hovered edge classes and hides the insert button.
- Closing the insert palette clears stale edge state and hides the insert button.

## Evidence

- Workflow E2E: `artifacts/slices/145-edge-insert-visibility/e2e-workflow.txt`
- Chatflow E2E: `artifacts/slices/145-edge-insert-visibility/e2e-chatflow.txt`
- Unit/rem-adjacent canvas checks: `artifacts/slices/145-edge-insert-visibility/unit-rem.txt`
- Screenshots:
  - `artifacts/slices/145-edge-insert-visibility/screenshots/workflow-edge-hover-only.png`
  - `artifacts/slices/145-edge-insert-visibility/screenshots/chatflow-edge-visibility.png`
