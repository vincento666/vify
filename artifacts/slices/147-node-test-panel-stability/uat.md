# 147 Node Test Panel Stability UAT

- Date: 2026-06-10
- Targets:
  - `http://127.0.0.1:5173/workflows/{created}/canvas`
  - `http://127.0.0.1:5173/chatflows/{created}/canvas`

## Checks

- Opening the selected-node test drawer no longer changes canvas flow width, node geometry, viewport scale, viewport translation, or zoom label.
- Closing the selected-node test drawer keeps the same canvas metrics.
- Closing the right-side config panel while the selected-node drawer stays open snaps the drawer to the screen right gutter.
- The selected-node drawer is layered above the bottom toolbar, debug dock, and config panel.
- Workflow selected-node run still executes only the selected node.
- Chatflow selected-node run still injects chatflow profile variables and does not continue downstream.

## Evidence

- RED: `artifacts/slices/147-node-test-panel-stability/red.txt`
- Stability E2E: `artifacts/slices/147-node-test-panel-stability/e2e.txt`
- Workflow node-test E2E: `artifacts/slices/147-node-test-panel-stability/e2e-workflow-node-test.txt`
- Chatflow node-test E2E: `artifacts/slices/147-node-test-panel-stability/e2e-chatflow-node-test.txt`
- Unit: `artifacts/slices/147-node-test-panel-stability/unit.txt`
- rem gate: `artifacts/slices/147-node-test-panel-stability/rem.txt`
- Build: `artifacts/slices/147-node-test-panel-stability/build.txt`
- Screenshots: `artifacts/slices/147-node-test-panel-stability/screenshots/`
